"""Auditable, *no inference* handoff from real OneFlow image artifact to video prep.

Does NOT call an AI video model, generate real movement or publish anything.
Makes a locked original asset, non-cropping portrait reference, storyboard/cue sheet,
optional clearly labeled static playback preview and release-readiness checklist.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .director import film_prompt
from .platforms import PROFILES, make_package


class HandoffError(ValueError):
    pass


MAX_BYTES = 16 * 1024 * 1024
STATUS = "ASSETS_READY_VIDEO_NOT_GENERATED_REVIEW_REQUIRED"
SAFE_SHOT = re.compile(r"S(?:0[1-9]|1[0-2])\Z")


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, content):
    Path(path).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_source(folder):
    folder = Path(folder)
    image_path, data_path = folder / "S01.png", folder / "S01.json"
    if not image_path.is_file() or image_path.is_symlink() or not data_path.is_file() or data_path.is_symlink():
        raise HandoffError("Expected regular source S01.png and S01.json")
    if not 200 <= image_path.stat().st_size <= MAX_BYTES:
        raise HandoffError("Source image empty or oversized")
    if not 30 <= data_path.stat().st_size <= 200_000:
        raise HandoffError("Source metadata empty or oversized")
    try:
        record = json.loads(data_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise HandoffError("Invalid source JSON") from None
    if not isinstance(record, dict):
        raise HandoffError("Source report must be an object")
    if record.get("shot_id") != "S01" or record.get("generated_image") != "S01.png":
        raise HandoffError("Wrong shot or image filename")
    if record.get("status") != "IMAGE_GENERATED_REVIEW_REQUIRED":
        raise HandoffError("Not a successfully generated, review-pending image")
    if record.get("provider") not in ("Cloudflare Workers AI", "OVHcloud AI Endpoints (anonymous)"):
        raise HandoffError("Unverified OneFlow image provider")
    checksum = record.get("sha256")
    if not isinstance(checksum, str) or not re.fullmatch("[0-9a-f]{64}", checksum):
        raise HandoffError("Source SHA256 metadata is missing")
    if digest(image_path) != checksum:
        raise HandoffError("Source PNG SHA256 does not match provider report")
    from PIL import Image, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = 30_000_000
    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            if image.format != "PNG" or min(image.size) < 384:
                raise HandoffError("Invalid original PNG format or dimensions")
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HandoffError("Source PNG failed to decode") from None
    if (record.get("actual_width"), record.get("actual_height")) != (width, height):
        raise HandoffError("Source width or height differs from signed report")
    return image_path, record, (width, height)


def original_brief(record):
    prompt = record.get("prompt", "")
    if not isinstance(prompt, str) or len(prompt) > 10000:
        raise HandoffError("Invalid source prompt")
    prefix = "User brief: "
    suffix = ". One moment, stable subjects and props"
    if prefix in prompt and suffix in prompt:
        return prompt.split(prefix, 1)[1].split(suffix, 1)[0].strip().rstrip(". ")
    return prompt[:3000].strip()


def plan_shots(brief, seconds):
    # Deterministic planning is not an LLM claim; motion and SFX must be approved.
    count = (seconds + 4) // 5
    if count > 12 or count < 1:
        raise HandoffError("Only 1-12 five-second shots allowed")
    cues = ["Introduce the locked scene and original subject",
            "Show the next physically plausible action",
            "Follow the subject with consistent camera direction",
            "Show an approved close-up only if reference supports it",
            "Continue the action without a location jump",
            "Advance the scene while retaining subject geometry",
            "Resolve motion in the correct narrative order"]
    jobs = []
    for i in range(count):
        focus = cues[min(i, len(cues) - 1)]
        jobs.append({
            "shot_id": f"S{i + 1:02d}",
            "seconds": min(5, seconds - i * 5),
            "status": "KEYFRAME_EXISTS_REVIEW_REQUIRED" if i == 0 else "SHOT_PLANNED_NO_IMAGE",
            "original_reference": "S01_original.png",
            "portrait_reference": "S01_portrait_letterbox.png",
            "camera_and_motion": "DRAFT_HUMAN_APPROVAL_REQUIRED",
            "seven_module_prompt": film_prompt(brief, focus, cues[min(i-1, len(cues)-1)] if i else None, i+1, count),
            "audio_cue": {
                "status": "CUE_ONLY_NO_AUDIO_FILE",
                "direction": "Use licensed original location-appropriate sound from approved source; no narration unless requested",
                "sound_file": None,
            },
            "video_file": None,
        })
    return jobs


def static_preview(input_png, out_mp4, seconds=5):
    """Static QA render only; burnt warning prevents confusion with generated motion."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise HandoffError("FFmpeg / ffprobe required for static media preview")
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not Path(font).is_file():
        raise HandoffError("Expected CI font missing for static-preview disclaimer")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", "24", "-i", str(input_png),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", f"drawtext=fontfile={font}:text='STILL PREVIEW - NO AI MOTION':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=70:box=1:boxcolor=black@0.8",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "96k",
        "-t", str(seconds), "-shortest", "-movflags", "+faststart", str(out_mp4),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=150)
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
             "-of", "json", str(out_mp4)], check=True, capture_output=True, text=True, timeout=15)
        info = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        raise HandoffError("Static preview FFmpeg / ffprobe failed") from None
    v = next((x for x in info.get("streams", []) if x.get("codec_type") == "video"), {})
    if (v.get("width"), v.get("height")) != (1080, 1920) or abs(float(info["format"]["duration"]) - seconds) > 0.5:
        raise HandoffError("Static preview dimensions/duration verification failed")
    return {"file": out_mp4.name, "label": "STATIC_STILL_NO_AI_MOTION", "duration_seconds": seconds,
            "silent_track": True, "sha256": digest(out_mp4)}


def assemble_package(source, out, run_id, seconds, *, brief=None, preview=False):
    if not isinstance(run_id, int) or run_id < 1:
        raise HandoffError("Source run ID must be positive")
    if seconds not in (5, 15, 35, 60):
        raise HandoffError("Allowed storyboard durations: 5, 15, 35, 60 seconds")
    source_png, report, (w, h) = verify_source(source)
    title = brief.strip() if brief else original_brief(report)
    if not 4 <= len(title) <= 4500:
        raise HandoffError("Brief needs 4-4500 characters")
    target = Path(out)
    if target.exists() and any(target.iterdir()):
        raise HandoffError("Handoff destination must be empty to prevent mistaken overwrites")
    target.mkdir(parents=True, exist_ok=True)
    original = target / "S01_original.png"
    shutil.copyfile(source_png, original)
    from PIL import Image, ImageOps
    with Image.open(source_png) as im:
        fitted = ImageOps.contain(im.convert("RGB"), (1080, 1920), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1080, 1920), (8, 10, 13))
    canvas.paste(fitted, ((1080 - fitted.width)//2, (1920 - fitted.height)//2))
    portrait = target / "S01_portrait_letterbox.png"
    canvas.save(portrait, "PNG")
    jobs = plan_shots(title, seconds)
    plan = {
        "status": STATUS,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_id": run_id,
        "source_model": report["model"],
        "source_provider": report["provider"],
        "source_image_sha256": report["sha256"],
        "original_dimensions": {"width": w, "height": h},
        "portrait_dimensions": {"width": 1080, "height": 1920},
        "portrait_method": "non-cropping letterbox; original subject preserved; NOT native 9:16 generation",
        "source_approved": False,
        "human_visual_review_required": True,
        "portrait_native_9x16": False if w/h != 9/16 else True,
        "brief": title, "requested_duration_seconds": seconds,
        "shot_count": len(jobs),
        "shots": jobs,
        "model_video_requests": 0, "audio_model_requests": 0, "publisher_requests": 0,
        "gpu_runner": "runpod-wan22 (not connected or called by this handoff)",
        "video_handoff_gate": "REQUIRES_APPROVED_ASSETS_RUNPOD_GPU_AND_EXPLICIT_BILLING_APPROVAL",
        "release_gate": "BLOCKED_NO_REAL_VIDEO_AUDIO_RIGHTS_REVIEW_OR_PLATFORM_OAUTH",
    }
    write_json(target / "handoff.json", plan)
    write_json(target / "publication_drafts.json", {
        "status": "EDITORIAL_DRAFTS_NOT_AUTHORIZED_FOR_POSTING",
        "profiles": {name: make_package({"brief": title, "ratio": "9:16"}, name) for name in PROFILES},
    })
    (target / "wan_s01_prompt.txt").write_text(jobs[0]["seven_module_prompt"] + "\n", encoding="utf-8")
    preview_data = None
    if preview:
        preview_data = static_preview(portrait, target / "STATIC_PREVIEW_NO_AI_MOTION.mp4")
    summary = {
        "status": STATUS,
        "source": {"run_id": run_id, "sha256": report["sha256"], "provider": report["provider"],
                   "model": report["model"], "dimensions": [w, h]},
        "outputs": {"original": "S01_original.png", "portrait": portrait.name, "metadata": "handoff.json",
                    "publication_drafts": "publication_drafts.json", "wan_prompt": "wan_s01_prompt.txt",
                    "static_preview": preview_data},
        "readiness": {
            "image_checksum": "VERIFIED",
            "portrait_ready_for_visual_review": True,
            "video_generated": False,
            "audio_generated": False,
            "full_film_rendered": False,
            "visual_review_passed": False,
            "platforms_authorized": False,
            "published": False,
        },
    }
    write_json(target / "delivery.json", summary)
    (target / "README.txt").write_text(
        "OneFlow image -> video prep package. Real generated PNG verified by SHA256.\n"
        "The portrait is a non-cropping LETTERBOX, NOT a new native 9:16 render.\n"
        "STATIC_PREVIEW_NO_AI_MOTION.mp4 is an intentionally static, SILENT diagnostic, not Wan/AI video.\n"
        "No model inference, GPU use, audio synthesis or platform publishing performed here.\n"
        "Review character/car structure, composition, copyright and prompt before any GPU video run.\n"
        "Runpod WAN GPU and paid billing require separate explicit human approval.\n"
        "Never publish this package as a finished video.\n", encoding="utf-8")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description="OneFlow verified image -> video-prep package, no inference")
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--source-run-id", required=True, type=int)
    p.add_argument("--seconds", type=int, default=35)
    p.add_argument("--brief")
    p.add_argument("--static-preview", action="store_true")
    args = p.parse_args(argv)
    try:
        result = assemble_package(args.source, args.out, args.source_run_id, args.seconds,
                                  brief=args.brief, preview=args.static_preview)
        print(json.dumps({"status": result["status"], "source_run_id": result["source"]["run_id"],
                          "video_generated": False, "source_sha256": result["source"]["sha256"]}))
        return 0
    except (HandoffError, OSError, ValueError) as exc:
        print("HANDOFF_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
