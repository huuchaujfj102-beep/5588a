"""OneFlow GitHub-triggered REAL text-to-image provider: Hugging Face FLUX.1-schnell.

No API key -> hard fail on live runs. Dry-run never makes an image or paid call.
Images stay in GitHub Action artifact, not source-control history.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from .continuity_rules import compile_prompt, negative_constraints, RULE_VERSION

MODEL = "black-forest-labs/FLUX.1-schnell"
SHOT = re.compile(r"S(0[1-9]|1[0-2])\Z")
MODEL_LICENSE = "Apache-2.0 (FLUX.1-schnell checkpoint; review upstream terms)"
NEGATIVE = negative_constraints()


class ImageFlowError(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_request_path(raw):
    root = Path("oneflow/requests")
    if not raw:
        return None
    p = Path(raw)
    if not re.fullmatch(r"[a-zA-Z0-9._-]+\.json", p.name) or p.parent != root:
        raise ImageFlowError("Request path must be oneflow/requests/<safe-name>.json")
    if not p.is_file() or p.stat().st_size > 150000:
        raise ImageFlowError("Missing or oversized story request")
    return p


def _compile_image(text, *, max_chars=None, separate_negative=False):
    try:
        return compile_prompt(text, stage="image", max_chars=max_chars,
                              separate_negative=separate_negative)["prompt"]
    except ValueError as exc:
        raise ImageFlowError(str(exc)) from None


def prompt_from_request(path, shot_id, *, max_chars=None, separate_negative=False):
    p = safe_request_path(path)
    if not p:
        raise ImageFlowError("Story request is required")
    document = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ImageFlowError("Story request must be an object")
    shots = document.get("shots")
    if (not isinstance(shots, list) or not shots or
            not isinstance(shot_id, str) or not SHOT.fullmatch(shot_id)):
        raise ImageFlowError("Invalid story shots or shot ID")
    idx = int(shot_id[1:]) - 1
    if idx >= len(shots):
        raise ImageFlowError("Requested shot not in storyboard")
    shot = shots[idx]
    if (not isinstance(shot, dict) or any(
            not isinstance(shot.get(field), str) or not shot[field].strip()
            for field in ("visual", "motion", "camera"))):
        raise ImageFlowError("Story shot requires nonempty visual, motion and camera text")
    chars = document.get("characters", {})
    if (not isinstance(chars, dict) or any(
            not isinstance(name, str) or not isinstance(spec, str)
            for name, spec in chars.items())):
        raise ImageFlowError("Invalid character bible")
    # This is one STILL keyframe. Avoid sending the whole 60s story or all actors.
    visible = []
    for name, spec in chars.items():
        if name in shot["visual"] or any(
           alias in shot["visual"] for alias in
           (["王后", "老妇"] if name.startswith("王后") else
            ["七位矮人", "七位矿工"] if name.startswith("七位小矮人") else [])):
            visible.append(f"{name}: {spec}")
    locked = "; ".join(visible)
    text = (
        "1. LOCK: one still keyframe; preserve the requested style and framing; only characters explicitly visible "
        "in this shot. Character design and wardrobe fixed: " + locked + "\n"
        "2. STILL ACTION: decisive moment in shot; " + shot["visual"] +
        ". Motions implied, not multiple poses: " + shot["motion"] + "\n"
        "3. ENVIRONMENT: use only explicitly described scene details.\n"
        "4. CAMERA: a single stable still frame at: " + shot["camera"] + "\n"
        "5. LIGHTING: physically coherent natural/practical film lighting.\n"
        "6. QUALITY: clear details in the requested visual style; coherent anatomy and props.\n"
        "7. NEGATIVE: apply only relevant structural constraints; preserve requested style, text and symbols."
    )
    return _compile_image(text, max_chars=max_chars, separate_negative=separate_negative)


def build_prompt(brief=None, request_file=None, shot_id="S01", *, max_chars=None,
                 separate_negative=False):
    if request_file:
        return prompt_from_request(request_file, shot_id, max_chars=max_chars,
                                   separate_negative=separate_negative)
    if (not isinstance(brief, str) or len(brief.strip()) < 4
            or len(brief) > 4500):
        raise ImageFlowError("One-sentence brief needs 4-4500 characters")
    text = ("One single still image for human review before image-to-video. "
            "Preserve the user's requested style, framing, text and symbols. User brief: "
            + brief + ". One decisive moment, coherent subjects and props.")
    return _compile_image(text, max_chars=max_chars, separate_negative=separate_negative)


def build_plan(prompt, shot_id, seed, width, height):
    if not SHOT.fullmatch(shot_id):
        raise ImageFlowError("Invalid shot ID")
    if not isinstance(seed, int) or seed < 0 or seed > 2147483647:
        raise ImageFlowError("Seed must be a nonnegative 32-bit integer")
    if (width, height) not in ((768, 1344), (1024, 1024), (1344, 768)):
        raise ImageFlowError("Resolution must be one of approved bounded profiles")
    return {
        "status": "PLANNED_NOT_RENDERED",
        "shot_id": shot_id,
        "model": MODEL,
        "provider": "Hugging Face Inference Providers (auto)",
        "license_reference": MODEL_LICENSE,
        "seed": seed,
        "requested_width": width,
        "requested_height": height,
        "prompt": prompt,
        "prompt_chars": len(prompt),
        "negative_prompt": NEGATIVE,
        "negative_prompt_mode": "inline",
        "negative_prompt_field_supported": False,
        "negative_prompt_field_transmitted": False,
        "rule_version": RULE_VERSION,
        "needs_human_reference_approval": True,
        "generated_image": None,
    }


def image_generation(plan, token, output_path, client_cls=None):
    """Only a real provider-returned decoded image may be saved as generated."""
    if not token or not token.strip():
        raise ImageFlowError("MISSING_HF_TOKEN: configure GitHub Actions secret HF_TOKEN")
    if client_cls is None:
        from huggingface_hub import InferenceClient
        client_cls = InferenceClient
    from PIL import Image
    client = client_cls(provider="auto", api_key=token)
    image = client.text_to_image(
        prompt=plan["prompt"],
        model=MODEL,
        height=plan["requested_height"],
        width=plan["requested_width"],
        num_inference_steps=4,
        seed=plan["seed"],
    )
    if not isinstance(image, Image.Image):
        raise ImageFlowError("Provider did not return a decodable image")
    image.load()
    if min(image.size) < 384:
        raise ImageFlowError("Provider returned an undersized image")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise ImageFlowError("Output already exists; no silent overwriting")
    image.convert("RGB").save(output_path, format="PNG")
    # Independently re-read produced bytes to reject empty/corrupt output.
    with Image.open(output_path) as check:
        check.verify()
    if not output_path.is_file() or output_path.stat().st_size < 200:
        raise ImageFlowError("Generated image missing or implausibly small")
    return {
        **plan,
        "status": "IMAGE_GENERATED_REVIEW_REQUIRED",
        "generated_image": output_path.name,
        "actual_width": image.width,
        "actual_height": image.height,
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "not_verified": [
            "identity consistency", "copyright/provenance", "realism",
            "visual quality", "Wan I2V compatibility",
        ],
    }


def execute(args, token=None, client_cls=None):
    prompt = build_prompt(args.brief, args.request_file, args.shot)
    plan = build_plan(prompt, args.shot, args.seed, args.width, args.height)
    root = Path(args.output).resolve()
    if args.dry_run:
        return {**plan, "status": "DRY_RUN_NO_IMAGE_GENERATED"}
    if not args.approve_one_image:
        raise ImageFlowError("Billable inference must be explicitly authorized (--approve-one-image)")
    # Only create output directory after credentials/preflight checks.
    secret = token if token is not None else os.environ.get("HF_TOKEN", "")
    if not secret:
        raise ImageFlowError(
            "MISSING_HF_TOKEN: configure a fine-grained HF_TOKEN with inference-only permissions"
        )
    target = root / (args.shot + ".png")
    if target.exists():
        raise ImageFlowError("Output already exists; choose an empty task folder to avoid double billing")
    root.mkdir(parents=True, exist_ok=True)
    report = image_generation(plan, secret, target, client_cls)
    (root / (args.shot + ".json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description="GitHub OneFlow real FLUX image via HF")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--brief", help="One sentence, original cinematic still")
    mode.add_argument("--request-file", help="Approved repository story request")
    p.add_argument("--shot", default="S01")
    p.add_argument("--seed", type=int, default=128839)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=1344)
    p.add_argument("--output", default="private-inputs/generated-images")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--approve-one-image", action="store_true")
    args = p.parse_args(argv)
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
        return 0
    except (ImageFlowError, OSError, ValueError) as exc:
        print("IMAGE_FLOW_FAILED: " + str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Avoid logging upstream response bodies that could contain secrets.
        print("IMAGE_PROVIDER_FAILED: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
