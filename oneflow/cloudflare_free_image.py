"""Cloudflare Workers AI FLUX.1 Schnell: one opt-in image, no retries or paid fallback.

Real inference requires GitHub secrets CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN.
The Free-plan attestation is user supplied; the API cannot itself guarantee an account
has not enabled paid billing. One request per approved job, max 4 diffusion steps.
"""
import argparse
import base64
import binascii
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from oneflow.image_generation import ImageFlowError, build_plan, build_prompt, sha256

MODEL = "@cf/black-forest-labs/flux-1-schnell"
ENDPOINT_ROOT = "https://api.cloudflare.com/client/v4/accounts"
MAX_RESPONSE_BYTES = 24 * 1024 * 1024
MAX_IMAGE_BYTES = 16 * 1024 * 1024


def validated_account(account_id):
    if not isinstance(account_id, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
        raise ImageFlowError("MISSING_OR_INVALID_CLOUDFLARE_ACCOUNT_ID: expected 32 hex chars")
    return account_id


def parse_image_response(raw):
    """Cloudflare REST API returns {success:true,result:{image:base64}}."""
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ImageFlowError("Cloudflare returned an invalid JSON envelope") from None
    if not isinstance(envelope, dict) or envelope.get("success") is not True:
        raise ImageFlowError("Cloudflare returned success=false or invalid envelope")
    result = envelope.get("result")
    encoded = result.get("image") if isinstance(result, dict) else None
    if not isinstance(encoded, str) or not encoded or len(encoded) > MAX_RESPONSE_BYTES:
        raise ImageFlowError("Cloudflare returned no bounded base64 image")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ImageFlowError("Cloudflare image base64 is invalid") from None
    if len(image) < 200 or len(image) > MAX_IMAGE_BYTES:
        raise ImageFlowError("Cloudflare image bytes missing or oversized")
    return image


def infer_once(prompt, account_id, token, *, steps=4, seed=128839, opener=None):
    validated_account(account_id)
    if not isinstance(token, str) or not token.strip():
        raise ImageFlowError("MISSING_CLOUDFLARE_API_TOKEN")
    if not 4 <= len(prompt.strip()) <= 2048:
        raise ImageFlowError("Prompt must be 4 to 2048 characters")
    if not isinstance(steps, int) or not 1 <= steps <= 4:
        raise ImageFlowError("Free smoke-test mode requires 1-4 steps")
    if not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ImageFlowError("Invalid random seed")

    # No AI Gateway, no paid fallback, no retries. Model API accepts these 3 fields.
    request = Request(
        f"{ENDPOINT_ROOT}/{account_id}/ai/run/{MODEL}",
        data=json.dumps({"prompt": prompt, "steps": steps, "seed": seed}, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with (opener or urlopen)(request, timeout=90) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ImageFlowError("Cloudflare API response is too large")
            return parse_image_response(raw)
    except HTTPError as exc:
        if exc.code == 429:
            raise ImageFlowError("CLOUDFLARE_QUOTA_OR_CAPACITY_429: no retry or upgrade") from None
        if exc.code in (401, 403):
            raise ImageFlowError(f"CLOUDFLARE_AUTH_OR_PLAN_HTTP_{exc.code}") from None
        raise ImageFlowError(f"CLOUDFLARE_HTTP_{exc.code}") from None
    except URLError:
        raise ImageFlowError("CLOUDFLARE_NETWORK_ERROR") from None


def execute(args, *, account_id=None, token=None, opener=None):
    prompt = build_prompt(brief=args.brief, shot_id=args.shot)
    plan = build_plan(prompt, args.shot, args.seed, 1024, 1024)
    plan.update({
        "model": MODEL,
        "provider": "Cloudflare Workers AI",
        "requested_width": None,
        "requested_height": None,
        "resolution_note": "Cloudflare model chooses native output dimensions; inspect actual_width/height",
        "steps": args.steps,
        "free_plan_attestation_required": True,
        "api_calls": 0,
    })
    if args.dry_run:
        return {**plan, "status": "DRY_RUN_NO_IMAGE_GENERATED"}
    if not args.approve_free_test or not args.confirm_workers_free:
        raise ImageFlowError("Manual approval and confirmation of Workers Free plan required")

    account = validated_account(account_id if account_id is not None else os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""))
    key = token if token is not None else os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not key:
        raise ImageFlowError("MISSING_CLOUDFLARE_API_TOKEN")

    output_root = Path(args.output).resolve()
    output_png = output_root / (args.shot + ".png")
    output_json = output_root / (args.shot + ".json")
    if output_png.exists() or output_json.exists():
        raise ImageFlowError("Existing output detected before inference; no duplicate request")

    # Do not perform a second provider call if decoding/verification fails.
    raw = infer_once(prompt, account, key, steps=args.steps, seed=args.seed, opener=opener)

    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if min(image.size) < 384:
                raise ImageFlowError("Provider image too small")
            w, h = image.size
            normalized = image.convert("RGB")
            output_root.mkdir(parents=True, exist_ok=True)
            normalized.save(output_png, format="PNG")
        with Image.open(output_png) as check:
            check.verify()
    except (UnidentifiedImageError, OSError) as exc:
        output_png.unlink(missing_ok=True)
        raise ImageFlowError("Cloudflare image failed decode/validation") from exc

    report = {
        **plan,
        "status": "IMAGE_GENERATED_REVIEW_REQUIRED",
        "actual_width": w,
        "actual_height": h,
        "generated_image": output_png.name,
        "bytes": output_png.stat().st_size,
        "sha256": sha256(output_png),
        "api_calls": 1,
        "price_note": "Free allowance is 10,000 neurons/day on Workers Free. No paid plan status verified.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "not_verified": [
            "mechanical accuracy", "copyright and provenance", "visual quality",
            "character/vehicle consistency", "image-to-video compatibility",
        ],
    }
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="OneFlow Cloudflare Workers AI free FLUX test")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--shot", default="S01")
    parser.add_argument("--seed", type=int, default=128839)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--output", default="private-inputs/generated-images-cloudflare")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--approve-free-test", action="store_true")
    parser.add_argument("--confirm-workers-free", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
        return 0
    except (ImageFlowError, ValueError, OSError) as exc:
        print("CLOUDFLARE_IMAGE_FAILED: " + str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Prevent upstream response bodies and secrets from leaking to Action logs.
        print("CLOUDFLARE_IMAGE_PROVIDER_FAILED: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
