"""Magic Hour 14-second car continuation: off by default, verified-credit live gate.

Use the genuine last frame of the user's source film; never substitute demo media.
The account must have enough prepaid credits. This adapter does not authorize
purchases, commercial release, GPU deployments, or any social publishing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


MODEL = "ltx-2.5"
SECONDS = 14
RESOLUTION = "480p"


class TrialBlocked(RuntimeError):
    pass


def plan():
    return {
        "provider": "magic-hour",
        "status": "PREPARED_NOT_AUTHORIZED_NOT_RENDERED",
        "model": MODEL,
        "duration_seconds": SECONDS,
        "resolution": RESOLUTION,
        "source": "genuine LAST frame of 1000023067.mp4, NOT example sunset",
        "input_ratio": "4:3",
        "aspect_warning": "LTX-2.5 lists 16:9, 9:16, 1:1; preview crop/reframe before stitching with 4:3 source",
        "license_gate": "FREE_TRIAL_NONCOMMERCIAL_REVIEW_ONLY",
        "billing_gate": "account verified, exact model cost quoted, explicit credit cap",
        "prompt": (
            "A single fourteen-second ultra-premium cinematic second act begins EXACTLY "
            "from the supplied genuine last frame of the previous car movie. Preserve "
            "the EXACT ORIGINAL silver-white low-profile biomechanical hypercar, "
            "transparent jade-green leaf vein glass panels, luminous biological "
            "neural structure, original turbine-spoke wheel size and placement, "
            "cream seats, sculpted front lip and headlights. Preserve golden-hour "
            "mountain lake, white futuristic curved glass buildings, trees, wet "
            "polished stone, waterfall and geography. Do not replace this model. "
            "0.0-2.5 s: low steady front three-quarter camera, jade neural pulses "
            "surge inside EXISTING transparent panels, headlamps sharpen, subtle "
            "suspension compression, breathing-like front lattice micro motion. "
            "2.5-5.0 s: cut to original wheel and nose macro detail; wheel gains "
            "real angular velocity, true tire-road grip and light wet-stone spray; "
            "the car accelerates forward onto a geographically connected lakeside "
            "driveway with plausible inertia, no teleport or flying. "
            "5.0-9.0 s: very smooth low side-rear tracking shot of SAME car moving "
            "fast past actual glass architecture and waterfall, accurate parallax "
            "and reflections, subtle green neural impulses racing in the shell. "
            "9.0-12.0 s: stunning but restrained high-speed climax: fine emerald "
            "aerodynamic photon ribbons flowing from real body trailing edges, "
            "minor optical air refraction; realistic tire motion and consistent "
            "car geometry, no invented engines or thrusters, no giant neon beams. "
            "12.0-14.0 s: elegant crane to rear-three-quarter sunset perspective; "
            "same hypercar follows curved lakeside road away, jade wake fades, "
            "mountains, lake and future buildings stay in correct places; hold "
            "the final half second steady. Audio: sophisticated low-frequency "
            "electric propulsion, soft energy hum, tires on damp ground, "
            "rising air rush and distant lake waterfall; absolutely no voiceover. "
            "Cinematic physically based glass/reflections, precise coherent motion, "
            "24fps look, restrained highlights. NEGATIVE: altered car, extra "
            "wheels, new wing, random rocket exhaust, warped glass, melted "
            "background, inconsistent sun, jump cuts breaking geography, "
            "flicker, floating, oversaturated cheap neon, unwanted lettering."
        )
    }


def available_credits(token):
    """GET /v1/account: credit field is publicly documented; no generation."""
    req = urllib.request.Request(
        "https://api.magichour.ai/v1/account",
        headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            obj = json.load(res)
    except Exception as exc:
        raise TrialBlocked("Cannot verify live account credits: " + type(exc).__name__) from None
    data = obj.get("data", obj) if isinstance(obj, dict) else None
    credits = data.get("credits") if isinstance(data, dict) else None
    if isinstance(credits, (int, float)) and not isinstance(credits, bool) and credits >= 0:
        return float(credits)
    raise TrialBlocked("GET /v1/account returned no parseable credits: no render attempted")


def extract_last_frame(video_path, dest):
    """Extract a real final decoded frame, never assume that frame 0 is the end."""
    video_path = Path(video_path)
    dest = Path(dest)
    if not video_path.is_file():
        raise TrialBlocked("Source film missing")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(video_path), "-update", "1", "-q:v", "2", str(dest)],
            timeout=240, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.SubprocessError):
        raise TrialBlocked("FFmpeg could not decode actual last frame") from None
    if not dest.is_file() or dest.stat().st_size < 4096:
        raise TrialBlocked("Final image extraction missing or invalid")
    return dest


def live(args):
    key = os.environ.get("MAGIC_HOUR_API_KEY")
    if not key:
        raise TrialBlocked("MAGIC_HOUR_API_KEY not configured; do not post it in chat")
    if not args.confirm_trial_credits or args.quoted_credits is None or args.credit_cap is None:
        raise TrialBlocked("Explicit account-specific credit quote and approved cap required")
    if not (0 < args.quoted_credits <= args.credit_cap):
        raise TrialBlocked("Quoted credit cost exceeds authorized cap")
    if available_credits(key) < args.quoted_credits:
        raise TrialBlocked("Available Magic Hour credits are insufficient")

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    if args.source_video:
        frame = extract_last_frame(args.source_video, outdir / "real_last_frame.jpg")
    elif args.source_frame:
        frame = Path(args.source_frame)
        if not frame.is_file() or frame.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            raise TrialBlocked("Must supply real last-frame JPG/PNG")
    else:
        raise TrialBlocked("Missing real source video or actual extracted last frame")

    try:
        from magic_hour import Client
    except ImportError:
        raise TrialBlocked("Install official SDK with pip install magic_hour") from None

    manifest = plan()
    manifest["status"] = "SUBMISSION_UNKNOWN_UNTIL_PROVIDER_RESPONSE"
    manifest["source_sha256"] = hashlib.sha256(frame.read_bytes()).hexdigest()
    manifest["quoted_credits"] = args.quoted_credits
    manifest["cap_credits"] = args.credit_cap
    manifest["publish_approved"] = False
    manifest_path = outdir / "magic_hour_job.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Official SDK example, but with actual uploaded vehicle last-frame image.
    # A transport timeout is not proof of failure; NEVER auto-resubmit a billable job.
    result = Client(token=key).v1.image_to_video.generate(
        assets={"image_file_path": str(frame.resolve())},
        style={"prompt": manifest["prompt"]},
        end_seconds=14,
        name="APEX MOTION Emerald 14-second continuation",
        model=MODEL,
        resolution=RESOLUTION,
        audio=True,
        wait_for_completion=True,
        download_outputs=True,
        download_directory=str(outdir))
    manifest["job_id"] = str(getattr(result, "id", "")) or None
    manifest["provider_status"] = str(getattr(result, "status", "unknown"))
    manifest["credits_charged"] = getattr(result, "credits_charged", None)
    manifest["downloaded_paths"] = [str(p) for p in (getattr(result, "downloaded_paths", None) or [])]
    manifest["status"] = ("RENDERED_REQUIRES_VISUAL_RIGHTS_QC" if
                          manifest["provider_status"] == "complete" and manifest["downloaded_paths"]
                          else "NOT_DELIVERED_CHECK_PROVIDER_JOB_BEFORE_RETRY")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"], "job_id": manifest["job_id"],
        "credits_charged": manifest["credits_charged"],
        "downloaded_paths": manifest["downloaded_paths"],
        "rights": manifest["license_gate"]}, ensure_ascii=False))
    if manifest["status"] != "RENDERED_REQUIRES_VISUAL_RIGHTS_QC":
        raise TrialBlocked("No completed downloaded video. Check job ID before retrying.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--source-frame")
    parser.add_argument("--source-video")
    parser.add_argument("--output", default="output/magic_hour_trial")
    parser.add_argument("--quoted-credits", type=float)
    parser.add_argument("--credit-cap", type=float)
    parser.add_argument("--confirm-trial-credits", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
    else:
        live(args)


if __name__ == "__main__":
    try:
        main()
    except TrialBlocked as exc:
        print("BLOCKED: " + str(exc))
        raise SystemExit(2)
