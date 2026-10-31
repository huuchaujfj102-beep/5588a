"""OneFlow one-image fal.ai FLUX.1 schnell adapter (no automatic paid retries).

One external inference is permitted only with --approve-one-image and FAL_KEY.
Do not store tokens or reference assets in the public repository.
"""
import argparse
from io import BytesIO
import json
import math
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from oneflow.image_generation import (
    ImageFlowError, build_prompt, build_plan, sha256,
)

FAL_MODEL = "fal-ai/flux/schnell"
FAL_RATE_PER_ROUNDED_MP = 0.003
MAX_IMAGE_BYTES = 25 * 1024 * 1024


def estimate_usd(width, height):
    """Indicative current list price; never treated as a billing receipt."""
    return round(math.ceil(width * height / 1_000_000) * FAL_RATE_PER_ROUNDED_MP, 6)


def download_fal_image(url):
    """Download only from known fal output hosts, with a hard size cap."""
    from urllib.parse import urlsplit
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    allowed = (host in ("fal.media", "storage.googleapis.com") or
               host.endswith(".fal.media") or host.endswith(".fal.ai"))
    if p.scheme != "https" or not allowed or p.username or p.password:
        raise ImageFlowError("Unexpected image output host")
    import httpx
    chunks = []
    size = 0
    with httpx.stream("GET", url, timeout=45, follow_redirects=False) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise ImageFlowError("Provider image exceeds 25 MiB")
            chunks.append(chunk)
    return b"".join(chunks)


def generate_one(plan, token, target, submit=None, download=None):
    """Provider call and verified local image; dependency injection is for offline tests."""
    if not token or not token.strip():
        raise ImageFlowError("MISSING_FAL_KEY: add a fal.ai API key as repository secret FAL_KEY")
    target = Path(target)
    if target.exists():
        raise ImageFlowError("Output already exists; avoid double billing")
    args = {
        "prompt": plan["prompt"],
        "image_size": {"width": plan["requested_width"], "height": plan["requested_height"]},
        "num_inference_steps": 4,
        "num_images": 1,
        "seed": plan["seed"],
        "output_format": "png",
        "enable_safety_checker": True,
        "acceleration": "none",
    }
    if submit is None:
        # fal-client reads FAL_KEY from the environment, as injected by GitHub Actions.
        if token != os.getenv("FAL_KEY"):
            raise ImageFlowError("FAL_KEY must be supplied through the secure environment")
        import fal_client
        submit = fal_client.subscribe
    # Deliberately no retry and no second-provider fallback after a possible billable call.
    result = submit(FAL_MODEL, arguments=args)
    if not isinstance(result, dict) or not isinstance(result.get("images"), list) or len(result["images"]) != 1:
        raise ImageFlowError("Provider did not return exactly one image")
    if any(result.get("has_nsfw_concepts") or []):
        raise ImageFlowError("Provider safety screening rejected the output")
    item = result["images"][0]
    url = item.get("url") if isinstance(item, dict) else None
    if not isinstance(url, str) or not url:
        raise ImageFlowError("Provider returned no valid image URL")
    raw = (download or download_fal_image)(url)
    if not isinstance(raw, bytes) or len(raw) < 200 or len(raw) > MAX_IMAGE_BYTES:
        raise ImageFlowError("Missing, oversized or invalid provider image bytes")
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(raw)) as img:
            img.load()
            if min(img.size) < 384:
                raise ImageFlowError("Provider image is too small")
            actual_width, actual_height = img.size
            out = img.convert("RGB")
            target.parent.mkdir(parents=True, exist_ok=True)
            out.save(target, format="PNG")
        with Image.open(target) as check:
            check.verify()
    except (UnidentifiedImageError, OSError) as exc:
        target.unlink(missing_ok=True)
        raise ImageFlowError("Provider image cannot be decoded") from exc
    return {
        **plan,
        "status": "IMAGE_GENERATED_REVIEW_REQUIRED",
        "generated_image": target.name,
        "actual_width": actual_width,
        "actual_height": actual_height,
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
        "listed_estimate_usd": estimate_usd(actual_width, actual_height),
        "cost_is_estimate_not_receipt": True,
        "not_verified": [
            "identity consistency", "copyright/provenance", "realism",
            "visual quality", "image-to-video compatibility",
        ],
    }


def execute(args, token=None, submit=None, download=None):
    prompt = build_prompt(args.brief, args.request_file, args.shot)
    plan = build_plan(prompt, args.shot, args.seed, args.width, args.height)
    plan.update({
        "model": "FLUX.1-schnell",
        "provider": "fal.ai",
        "provider_endpoint": FAL_MODEL,
        "listed_estimate_usd": estimate_usd(args.width, args.height),
        "cost_is_estimate_not_receipt": True,
    })
    if args.dry_run:
        return {**plan, "status": "DRY_RUN_NO_IMAGE_GENERATED"}
    if not args.approve_one_image:
        raise ImageFlowError("Billable inference must be explicitly authorized (--approve-one-image)")
    secret = token if token is not None else os.environ.get("FAL_KEY", "")
    if not secret:
        raise ImageFlowError("MISSING_FAL_KEY: configure GitHub Actions secret FAL_KEY")
    root = Path(args.output).resolve()
    target = root / (args.shot + ".png")
    if target.exists():
        raise ImageFlowError("Output already exists; avoid double billing")
    result = generate_one(plan, secret, target, submit=submit, download=download)
    (root / (args.shot + ".json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description="OneFlow REAL FLUX image via fal.ai")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--brief")
    mode.add_argument("--request-file")
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
        # Never print provider response bodies, which might expose private data.
        print("IMAGE_PROVIDER_FAILED: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
