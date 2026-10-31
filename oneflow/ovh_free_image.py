"""OneFlow free SDXL image adapter using OVHcloud's documented anonymous endpoint.

The public model is listed as Free. This adapter makes at most ONE external
inference request per invocation; it has no retries, credentials, or paid fallback.
"""
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from oneflow.image_generation import ImageFlowError, build_prompt, build_plan, sha256

MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
ENDPOINT = "https://stable-diffusion-xl.endpoints.kepler.ai.cloud.ovh.net/api/text2image"
MAX_IMAGE_BYTES = 16 * 1024 * 1024
DEFAULT_NEGATIVE = (
    "cartoon, duplicate cars, extra wheels, malformed tires, broken geometry, "
    "visible text, watermark, distorted bodywork, blurry"
)


def fetch_image_once(prompt, negative_prompt=DEFAULT_NEGATIVE, opener=None):
    """Exactly one anonymous call. Never automatically retry or switch provider."""
    if not isinstance(prompt, str) or not 4 <= len(prompt) <= 2048:
        raise ImageFlowError("OVH SDXL prompt must be 4-2048 characters")
    body = json.dumps({
        "prompt": prompt,
        "negative_prompt": negative_prompt,
    }, ensure_ascii=False).encode("utf-8")
    req = Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/octet-stream"},
    )
    call = opener if opener is not None else urlopen
    try:
        with call(req, timeout=90) as response:
            data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ImageFlowError("Provider image exceeds maximum response size")
            if len(data) < 200:
                raise ImageFlowError("Provider returned empty or invalid image")
            return data
    except HTTPError as exc:
        raise ImageFlowError("OVH_SD_XL_HTTP_" + str(exc.code)) from None
    except URLError as exc:
        raise ImageFlowError("OVH_SD_XL_NETWORK_ERROR") from None


def generate_one(plan, output_dir, transport=None):
    """Validate actual bytes and only claim generation after a decodable PNG exists."""
    from PIL import Image, UnidentifiedImageError

    output_dir = Path(output_dir)
    image_path = output_dir / (plan["shot_id"] + ".png")
    report_path = output_dir / (plan["shot_id"] + ".json")
    if image_path.exists() or report_path.exists():
        raise ImageFlowError("An output already exists; refusing duplicate model inference")

    bytes_in = fetch_image_once(plan["prompt"], opener=transport)
    try:
        with Image.open(BytesIO(bytes_in)) as img:
            img.load()
            if min(img.size) < 384:
                raise ImageFlowError("Provider returned an undersized image")
            actual_width, actual_height = img.size
            final = img.convert("RGB")
            output_dir.mkdir(parents=True, exist_ok=True)
            final.save(image_path, format="PNG")
        with Image.open(image_path) as check:
            check.verify()
    except (UnidentifiedImageError, OSError) as exc:
        image_path.unlink(missing_ok=True)
        raise ImageFlowError("Provider did not return decodable image bytes") from exc

    report = {
        **plan,
        "provider": "OVHcloud AI Endpoints (anonymous)",
        "model": MODEL,
        "status": "IMAGE_GENERATED_REVIEW_REQUIRED",
        "generated_image": image_path.name,
        "actual_width": actual_width,
        "actual_height": actual_height,
        "sha256": sha256(image_path),
        "bytes": image_path.stat().st_size,
        "pricing": "Listed as Free in OVHcloud public catalog; check current official terms",
        "request_count": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "not_verified": [
            "visual correctness", "car propulsion layout", "character identity",
            "copyright/provenance", "image-to-video compatibility"
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def execute(args, transport=None):
    prompt = build_prompt(args.brief, None, args.shot)
    # The SDXL endpoint has a fixed 1024x1024 output as documented.
    plan = build_plan(prompt, args.shot, args.seed, 1024, 1024)
    plan.update({
        "provider": "OVHcloud AI Endpoints (anonymous)",
        "model": MODEL,
        "status": "PLANNED_NOT_RENDERED",
        "api_url": ENDPOINT,
        "image_size_note": "SDXL output is fixed at 1024x1024, not native 9:16",
        "requires_api_key": False,
    })
    if args.dry_run:
        return {**plan, "status": "DRY_RUN_NO_IMAGE_GENERATED"}
    if not args.approve_free_test:
        raise ImageFlowError("Explicit free-test approval required: --approve-free-test")
    return generate_one(plan, args.output, transport=transport)


def main(argv=None):
    parser = argparse.ArgumentParser(description="OneFlow anonymous free OVH SDXL text-to-image")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--shot", default="S01")
    parser.add_argument("--seed", type=int, default=12991)
    parser.add_argument("--output", default="private-inputs/generated-images-ovh")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--approve-free-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
        return 0
    except (ImageFlowError, ValueError, OSError) as exc:
        print("OVH_FREE_IMAGE_FAILED: " + str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print("OVH_FREE_IMAGE_PROVIDER_FAILURE: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
