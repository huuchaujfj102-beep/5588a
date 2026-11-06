"""Qianfan first-frame-to-video -> OneFlow MP4 -> film audit.

No paid task is submitted without --confirm-paid. Production is resumable by
task_id: a failed/pending GET/download never creates another POST. Final output
remains blocked from publication until OneFlow's separate human approval gate.

Run only with approved content in a PRIVATE persistent environment.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .core import (
    FlowError, assemble, audit, config, create, load_json, now, probe,
    primary_media, save_json,
)
from .platforms import make_package
from .qianfan_media import MediaTaskError, submit, task_status
from .continuity_rules import compile_prompt

PRICES_RMB_FIVE_SECONDS = {
    "VQ2-Turbo": {"720p": 1.25},
    "VQ2-Pro": {"720p": 1.71875},
    "VQ3-Turbo": {"720p": 1.875},  # 0.375 yuan/second; estimate
    "musesteamer-air-i2v": {"720p": 1.0},  # fixed 5s job; output pixels determined by model
}
MAX_MEDIA_BYTES = 150_000_000


def _checked_public_url(value):
    """Ensure a remote media URL cannot directly access local/private hosts."""
    if not isinstance(value, str) or len(value) > 4096:
        raise FlowError("Public HTTPS media URL is required")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.port not in (None, 443)
            or parsed.username or parsed.password):
        raise FlowError("Media URL must be HTTPS to a public host, without credentials")
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith((".local", ".internal")):
        raise FlowError("Private/local media host is forbidden")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise FlowError("Media host DNS lookup failed") from None
    if not addresses:
        raise FlowError("No public address for media URL")
    for record in addresses:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise FlowError("Media URL resolves to non-public IP")
    return value


def _image_data_uri(path):
    """Encode a private local frame without uploading it to any public web host."""
    p = Path(path).resolve()
    if not p.is_file():
        raise FlowError("First frame file does not exist")
    suffix = p.suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
        raise FlowError("First frame must be PNG/JPG/WEBP")
    data = p.read_bytes()
    if not 64 <= len(data) <= 9_000_000:
        raise FlowError("Local first frame must be 64 bytes to 9 MB")
    if suffix == ".png" and not data.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise FlowError("Invalid PNG header")
    if suffix in (".jpg", ".jpeg") and not data.startswith(bytes.fromhex("ffd8ff")):
        raise FlowError("Invalid JPEG header")
    if suffix == ".webp" and not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        raise FlowError("Invalid WEBP header")
    kind = "jpeg" if suffix in (".jpg", ".jpeg") else suffix.lstrip(".")
    return "data:image/" + kind + ";base64," + base64.b64encode(data).decode("ascii")


def build_prompt(brief):
    """Preserve the reference and action without turning unrelated subjects into cars."""
    if not isinstance(brief, str):
        raise FlowError("Brief must be text")
    clean = brief.strip()
    if not 4 <= len(clean) <= 950:
        raise FlowError("Brief length must be between 4 and 950 characters")
    vehicle = (any(token in clean for token in
                   ("超跑", "赛车", "汽车", "跑车", "车轮", "车辆", "轿车", "辆车")) or
               re.search(r"\b(?:car|vehicle|supercar|hypercar|racing)\b", clean, re.I))
    # Retain the established racing pilot only when speed is actually requested.
    vehicle = vehicle and (any(t in clean for t in ("加速", "飞驰", "疾驰")) or
                           re.search(r"\b(?:accelerat\w*|racing|speeding)\b", clean, re.I))
    if any(t in clean for t in ("保持静止", "静止不动", "原地不动", "停车", "刹车", "后退", "倒车")):
        vehicle = False
    if (re.search(r"(?:不(?:要|许|准|需|能|可)?|禁止|避免).{0,6}(?:加速|疾驰|飞驰)", clean)
            or re.search(r"\b(?:stationary|static|parked|brak\w*|revers\w*|stop\w*|idle)\b", clean, re.I)
            or re.search(r"\b(?:no|not|without|avoid|don't|do not)\s+(?:\w+\s+){0,3}accelerat\w*\b", clean, re.I)):
        vehicle = False
    text = (
        "Reference lock: EXACT SAME single vehicle in source frame; preserve "
        "body geometry, wheels, headlights, paint and original camera perspective. "
        "Action happens immediately, not a still photograph: ignition, wheels "
        "physically ROTATE, the car moves FORWARD along the road, accelerates fast, "
        "background sweeps backward with visible parallax and road motion blur. "
        "One continuous cinematic tracking shot. Original brief: " + clean +
        ". Keep motion physically coherent; no reset, no new car, no unrequested morphing, "
        "no unexplained teleportation, no extra wheels, no unrequested text, no jump back to start. "
        "Do not add unrequested speech or narration."
    ) if vehicle else (
        "Reference lock: preserve the approved subject identities, clothing, props, "
        "connections and scene from the source frame except the requested changes. "
        "Perform only the original requested action, with coherent support and contact. "
        "Original brief: " + clean +
        ". Do not invent unrequested subjects, props or dialogue."
    )
    try:
        return compile_prompt(text, stage="video", max_chars=2000)["prompt"]
    except ValueError as exc:
        raise FlowError(str(exc)) from None


def _fetch_video(url, path, opener=None):
    """Download HTTPS MP4 to private job directory; no redirects or API key."""
    url = _checked_public_url(url)
    class BlockRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None
    caller = opener or urllib.request.build_opener(BlockRedirect()).open
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    size = 0
    try:
        request = urllib.request.Request(url, method="GET",
                                         headers={"Accept": "video/mp4"})
        with caller(request, timeout=90) as response, tmp.open("wb") as stream:
            mime = response.headers.get("Content-Type", "") if response.headers else ""
            if mime and not (mime.startswith("video/") or
                             mime.startswith("application/octet-stream")):
                raise FlowError("Media download returned unexpected Content-Type")
            while True:
                buf = response.read(1024 * 1024)
                if not buf:
                    break
                size += len(buf)
                if size > MAX_MEDIA_BYTES:
                    raise FlowError("Video result exceeds 150 MB")
                stream.write(buf)
        if size < 128:
            raise FlowError("Downloaded video too small")
        with tmp.open("rb") as stream:
            if b"ftyp" not in stream.read(64):
                raise FlowError("Downloaded file does not look like MP4")
        os.replace(tmp, target)
        return target
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        raise FlowError("Video download failed; resume task instead of resubmitting") from None
    finally:
        if tmp.exists():
            tmp.unlink()


def _generate_original_sfx(root, seconds):
    """Original synthetic engine swell (not a recorded real vehicle sound)."""
    out = root / "media" / "original-engine-synth.wav"
    duration = str(seconds)
    signal = (
        "0.20*sin(2*PI*(55*t+9*t*t))"
        "+0.10*sin(2*PI*(110*t+18*t*t))"
        "+0.05*sin(2*PI*(220*t+36*t*t))"
    )
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "aevalsrc=" + signal + ":s=48000:d=" + duration,
         "-af", "afade=t=in:st=0:d=0.15,afade=t=out:st="
         + str(max(0, seconds - .35)) + ":d=0.35",
         "-ac", "2", "-c:a", "pcm_s16le", str(out)],
        capture_output=True, timeout=45, check=False,
    )
    if result.returncode or not out.exists():
        raise FlowError("Could not create original synthetic engine audio")
    return str(out.relative_to(root))


def _watermark_mp4(path, font_path=None):
    """Very faint drifting user-requested 造镜者 watermark; output reviewed AFTER overlay."""
    target = Path(path)
    if not font_path:
        for candidate in (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ):
            if Path(candidate).is_file():
                font_path = candidate
                break
    if not font_path:
        raise FlowError("Missing Noto CJK font for 造镜者 watermark")
    temp = target.with_name("watermarked-" + target.name)
    vf = (
        "drawtext=fontfile=" + font_path +
        ":text='造镜者':fontsize=h/21:fontcolor=white@0.13:"
        "x='(w-text_w)/2+0.20*w*sin(t*0.19)':"
        "y='(h-text_h)/2+0.15*h*sin(t*0.27)'"
    )
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(target), "-vf", vf, "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", str(temp)],
        capture_output=True, timeout=300, check=False,
    )
    if result.returncode or not temp.is_file():
        raise FlowError("Watermark rendering unavailable; no unreviewed replacement")
    os.replace(temp, target)


def plan(brief, first_frame, *, seconds=5, ratio="9:16", model="VQ2-Turbo",
         resolution="720p", sound="synthetic", platforms=(), out_root="private-inputs/oneflow-jobs",
         enable_watermark=True):
    """Zero-cost native single-shot plan; VQ3/VQ4 can accept up to 16s."""
    if model == "musesteamer-air-i2v" and seconds != 5:
        raise FlowError("MuseSteamer Air I2V currently supports exactly 5 seconds")
    if type(seconds) is not int or seconds not in (5, 10, 15):
        raise FlowError("Current native video workflow accepts 5, 10, or 15 seconds")
    if model not in ("VQ2-Turbo", "VQ2-Pro", "VQ3-Turbo", "VQ3-Pro", "VQ4", "musesteamer-air-i2v"):
        raise FlowError("Unsupported VQ or MuseSteamer model")
    if model.startswith("VQ2") and seconds > 10:
        raise FlowError("VQ2 duration is capped at 10 seconds; choose VQ3 or VQ4 for 15s")
    if resolution != "720p":
        raise FlowError("Pilot resolution is 720p; output may be upscaled by FFmpeg")
    if sound not in ("synthetic", "embedded"):
        raise FlowError("Choose synthetic or embedded audio")
    if sound == "embedded" and model not in ("VQ3-Turbo", "VQ3-Pro", "VQ4"):
        raise FlowError("Embedded audio requires VQ3 or VQ4; MuseSteamer uses synthetic SFX")
    if not first_frame or not isinstance(first_frame, str):
        raise FlowError("A first-frame image URL or local image file is required")
    file = Path(first_frame)
    if file.is_file():
        source = {"mode": "local", "path": str(file.resolve()),
                  "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
    else:
        # Do not put presigned query strings into public manifests.
        parsed = urllib.parse.urlsplit(first_frame)
        if parsed.scheme != "https" or not parsed.hostname:
            raise FlowError("Provide an existing local frame or public HTTPS URL")
        source = {"mode": "remote_public", "url": first_frame.split("?")[0]}
        # We do not persist a signed query URL; this pilot requires a stable public URL.
        if parsed.query:
            raise FlowError("Signed/private image URL: use a private local image instead")
    cfg = config()
    cfg["require_audio"] = True
    root = create(brief, seconds, ratio, list(platforms), out_root, cfg)
    manifest = load_json(root / "manifest.json")
    # Core normally divides long movies into 5s shots. Native VQ generation is
    # ONE model task and ONE clip, not N separate provider submissions.
    manifest["shots"] = manifest["shots"][:1]
    manifest["shots"][0]["seconds"] = seconds
    manifest["native_single_clip"] = True
    manifest["qianfan_i2v"] = {
        "source": source, "model": model, "resolution": resolution,
        "sound": sound, "watermark": bool(enable_watermark),
        "task_id": None, "status": "PLANNED", "consent": False,
        "estimated_model_cost_rmb": (
            PRICES_RMB_FIVE_SECONDS.get(model, {}).get(resolution)
            if seconds == 5 else None),
        "cost_note": "Estimate, subject to official billing and selected configuration",
    }
    manifest["warnings"].append("Human approval and official platform OAuth required before publishing.")
    save_json(root / "manifest.json", manifest)
    return root


def _source_frame(source):
    if source["mode"] == "local":
        path = source["path"]
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != source["sha256"]:
            raise FlowError("First frame changed since plan creation")
        return _image_data_uri(path)
    return _checked_public_url(source["url"])


def submit_once(job, *, confirm_paid=False):
    """At most one paid POST for a planned job; never auto retry."""
    root = Path(job).resolve()
    manifest = load_json(root / "manifest.json")
    task = manifest["qianfan_i2v"]
    if task.get("task_id") or task["status"] != "PLANNED":
        raise FlowError("This job has already attempted submission; use resume, never re-POST")
    if not confirm_paid:
        raise FlowError("No billable request without --confirm-paid")
    # Deterministic prompt/first-frame failures are preflight failures, not an
    # uncertain paid submission. Keep the attempt marker for the actual POST.
    prompt = build_prompt(manifest["brief"])
    source_frame = _source_frame(task["source"])
    # Store attempt marker BEFORE the network call: uncertainty never causes re-POST.
    task["status"] = "SUBMISSION_ATTEMPTED"
    task["consent"] = True
    task["attempted_at"] = now()
    manifest["status"] = "SUBMISSION_ATTEMPTED"
    save_json(root / "manifest.json", manifest)
    try:
        result = submit(
            "video", prompt=prompt, model=task["model"],
            image_url=source_frame, duration=manifest["seconds"],
            resolution=task["resolution"], audio=(task["sound"] == "embedded"),
            allow_paid=True,
        )
    except (MediaTaskError, FlowError) as exc:
        task["status"] = "SUBMISSION_UNCERTAIN"
        manifest["status"] = "FAILED"
        manifest["error"] = str(exc)
        save_json(root / "manifest.json", manifest)
        raise
    task["task_id"] = result["task_id"]
    task["status"] = result["status"]
    manifest["status"] = "VIDEO_PENDING"
    save_json(root / "manifest.json", manifest)
    return root


def resume(job, *, attempts=30, delay=10, fetcher=None, watermark=None):
    """Only GET existing task ID and download result; never submits a new task."""
    import time
    root = Path(job).resolve()
    manifest = load_json(root / "manifest.json")
    task = manifest.get("qianfan_i2v", {})
    task_id = task.get("task_id")
    if not task_id:
        raise FlowError("No confirmed task ID. Do not resubmit uncertain charged request")
    if manifest.get("approval"):
        raise FlowError("Approved movie cannot be modified")
    if task["status"] == "FINALIZED":
        return manifest["status"]
    from .qianfan_media import wait_for_task
    latest = wait_for_task("video", task_id, model=task["model"],
                           attempts=attempts, delay=delay)
    task["last_polled_at"] = now()
    task["status"] = latest["status"]
    save_json(root / "manifest.json", manifest)
    if latest["status"] == "failed":
        manifest["status"] = "FAILED"
        save_json(root / "manifest.json", manifest)
        raise FlowError("Qianfan video task failed; do not retry payment automatically")
    if latest["status"] not in ("success", "succeed", "succeeded"):
        manifest["status"] = "VIDEO_PENDING"
        save_json(root / "manifest.json", manifest)
        return "VIDEO_PENDING"
    clip = root / "media" / "S01-qianfan-raw.mp4"
    if not clip.exists():
        downloader = fetcher or _fetch_video
        downloader(latest["result_urls"][0], clip)
    if not clip.is_file():
        raise FlowError("No downloaded video file")
    original = probe(clip)
    if not primary_media(original, "video"):
        raise FlowError("Provider MP4 has no video stream")
    if task["sound"] == "embedded" and not primary_media(original, "audio"):
        raise FlowError("Embedded audio was paid for but provider returned silent video")
    shot = manifest["shots"][0]
    shot["video"] = str(clip.relative_to(root))
    shot["model_provenance"]["video"] = task["model"]
    shot["state"] = "VIDEO_GENERATED_UNREVIEWED"
    if task["sound"] == "synthetic":
        shot["audio"] = _generate_original_sfx(root, manifest["seconds"])
        shot["model_provenance"]["audio"] = "original_ffmpeg_synthetic_engine_not_recording"
    save_json(root / "manifest.json", manifest)
    movie = assemble(root, manifest, config())
    manifest["render"] = str(movie.relative_to(root))
    if task["watermark"] if watermark is None else bool(watermark):
        _watermark_mp4(movie)
    qc = audit(root, manifest, config(), movie)
    manifest["qc"] = "qc.json"
    manifest["status"] = "BLOCKED" if qc["status"] == "FAIL" else "AWAITING_HUMAN_REVIEW"
    task["status"] = "FINALIZED"
    task["downloaded_at"] = now()
    save_json(root / "manifest.json", manifest)
    for platform in manifest["platforms"]:
        pkg = make_package(manifest, platform)
        export = root / "release-package"
        export.mkdir(exist_ok=True)
        save_json(export / (platform + ".json"), pkg)
    return manifest["status"]


def main(argv=None):
    p = argparse.ArgumentParser(description="Qianfan one-sentence + reference frame -> reviewed OneFlow MP4")
    sub = p.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("run", help="Create native 5/10/15s plan; optional one paid video task")
    start.add_argument("--brief", required=True)
    src = start.add_mutually_exclusive_group(required=True)
    src.add_argument("--first-frame-url")
    src.add_argument("--first-frame-file")
    start.add_argument("--seconds", type=int, default=5)
    start.add_argument("--ratio", default="9:16")
    start.add_argument("--model", default="musesteamer-air-i2v")
    start.add_argument("--resolution", default="720p")
    start.add_argument("--sound", choices=("synthetic", "embedded"), default="synthetic")
    start.add_argument("--platform", action="append", default=[])
    start.add_argument("--out", default="private-inputs/oneflow-jobs")
    start.add_argument("--no-watermark", action="store_true")
    start.add_argument("--confirm-paid", action="store_true")
    start.add_argument("--skip-poll", action="store_true")
    follow = sub.add_parser("resume", help="Poll existing task, download, audit; no paid POST")
    follow.add_argument("--job", required=True)
    follow.add_argument("--attempts", type=int, default=30)
    follow.add_argument("--delay", type=int, default=10)
    args = p.parse_args(argv)
    try:
        if args.cmd == "run":
            root = plan(args.brief, args.first_frame_file or args.first_frame_url,
                        seconds=args.seconds, ratio=args.ratio,
                        model=args.model, resolution=args.resolution,
                        sound=args.sound, platforms=args.platform, out_root=args.out,
                        enable_watermark=not args.no_watermark)
            if args.confirm_paid:
                submit_once(root, confirm_paid=True)
                if not args.skip_poll:
                    resume(root)
            m = load_json(root / "manifest.json")
            print(json.dumps({"job": str(root), "status": m["status"],
                              "task_id": m.get("qianfan_i2v", {}).get("task_id")},
                             ensure_ascii=False))
            if args.confirm_paid and not args.skip_poll and m["status"] != "AWAITING_HUMAN_REVIEW":
                # Avoid a green CI status when provider task is still pending or
                # technical QC has blocked the result. The task ID is saved
                # for a read-only resume, never an automatic second POST.
                return 2
        else:
            state = resume(args.job, attempts=args.attempts, delay=args.delay)
            print(json.dumps({"job": str(Path(args.job).resolve()), "status": state},
                             ensure_ascii=False))
        return 0
    except (FlowError, MediaTaskError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("QIANFAN I2V ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
