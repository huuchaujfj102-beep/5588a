"""Vidu Q3 official native 10/15-second video adapter.

No live POST without --confirm-paid. A timed-out POST is never retried.
Vidu task status is queried by task_id only; transient GET failures are resumable.
Official API: https://platform.vidu.com/docs/api-reference/video-models/vidu-q3/text-to-video
"""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.vidu.com"
MODEL = "viduq3-pro"
MAX_JSON = 1_048_576
MAX_IMAGE = 9_000_000
MAX_VIDEO = 250_000_000
STATES_PENDING = {"created", "queueing", "processing"}
TASK_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")


class ViduError(Exception):
    pass


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def key_from_env():
    key = os.environ.get("VIDU_API_KEY", "")
    if not key or key != key.strip() or any(c.isspace() for c in key) or key.lower().startswith("token "):
        raise ViduError("VIDU_API_KEY must be the bare Vidu secret, without spaces or Token prefix")
    return key


def api_request(method, path, *, key, payload=None, opener=None):
    if method not in ("GET", "POST") or not path.startswith("/ent/v2/"):
        raise ViduError("Unsafe API route")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Authorization": "Token " + key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    call = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with call(req, timeout=180 if method == "POST" else 30) as resp:
            raw = resp.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            raise ViduError("Vidu response too large")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ViduError("Vidu response is not a JSON object")
        return data
    except urllib.error.HTTPError as exc:
        # Never disclose upstream body, key, headers or private prompt.
        raise ViduError("Vidu HTTP " + str(exc.code) +
                        "; no successful response. Do not automatically repeat a billable POST.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ViduError("Vidu transport/timeout; " +
                        ("POST acceptance UNKNOWN, do not submit again until reconciled"
                         if method == "POST" else "status GET may be resumed without another POST")) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ViduError("Vidu returned invalid JSON; " +
                        ("POST acceptance UNKNOWN" if method == "POST" else "retry GET by task ID")) from None


def image_data_uri(filename):
    p = Path(filename)
    if not p.is_file():
        raise ViduError("First-frame file is missing")
    data = p.read_bytes()
    if not 128 <= len(data) <= MAX_IMAGE:
        raise ViduError("First frame must be 128B to 9MB")
    if p.suffix.lower() == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if min(width, height) < 128 or max(width, height) * 1.0 / min(width, height) >= 4:
            raise ViduError("First-frame dimensions or aspect ratio invalid")
    elif p.suffix.lower() in (".jpg", ".jpeg") and data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif p.suffix.lower() == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ViduError("First frame must be actual JPG, PNG or WebP")
    return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")


def build_payload(mode, prompt, seconds, resolution, first_frame=None):
    if mode not in ("text2video", "img2video"):
        raise ViduError("Mode must be text2video or img2video")
    if type(seconds) is not int or seconds not in (10, 15):
        raise ViduError("This production pilot accepts 10 or 15 seconds")
    if resolution not in ("540p", "720p", "1080p"):
        raise ViduError("Choose Vidu Q3 Pro 540p, 720p or 1080p")
    if not isinstance(prompt, str) or not 4 <= len(prompt.strip()) <= 20000:
        raise ViduError("Provide a 4–20000 character prompt")
    payload = {"model": MODEL, "prompt": prompt.strip(), "duration": seconds,
               "seed": 0, "resolution": resolution, "audio": True, "off_peak": False}
    if mode == "text2video":
        if first_frame:
            raise ViduError("Text-to-video cannot receive an image")
        payload["aspect_ratio"] = "9:16"
    else:
        if not first_frame:
            raise ViduError("Image-to-video requires an approved first-frame file")
        payload["images"] = [image_data_uri(first_frame)]
        payload["is_rec"] = False
    return payload


def safe_download_url(url):
    if not isinstance(url, str) or len(url) > 8192:
        raise ViduError("Invalid Vidu download URL")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ViduError("Video download requires HTTPS public host")
    try:
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(r[4][0]).is_global for r in addresses):
            raise ViduError("Non-public video download host")
    except OSError:
        raise ViduError("Video download host could not be resolved") from None
    return url


def download_video(url, target):
    # Signed result URLs expire quickly; never print or include them in artifacts.
    safe_download_url(url)
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            safe_download_url(urllib.parse.urljoin(req.full_url, newurl))
            return super().redirect_request(req, fp, code, msg, hdrs, newurl)
    call = urllib.request.build_opener(SafeRedirect()).open
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(".part")
    total = 0
    try:
        with call(urllib.request.Request(url, headers={"Accept": "video/mp4"}), timeout=90) as resp, part.open("wb") as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_VIDEO:
                    raise ViduError("Video exceeds 250MB cap")
                fh.write(chunk)
        with part.open("rb") as video_check:
            mp4_header = video_check.read(64)
        if total < 128 or b"ftyp" not in mp4_header:
            raise ViduError("Downloaded file is not an MP4")
        part.replace(target)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        raise ViduError("Vidu video download failed; resume by existing task ID") from None
    finally:
        part.unlink(missing_ok=True)


def probe_mp4(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ViduError("FFprobe failed to inspect MP4")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise ViduError("No video track in provider MP4")
    return {"duration": float(data.get("format", {}).get("duration", 0)),
            "width": videos[0].get("width"), "height": videos[0].get("height"),
            "video_codec": videos[0].get("codec_name"), "has_audio": bool(audios)}


def render_portrait(raw, target, seconds):
    font = next((p for p in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc") if Path(p).is_file()), None)
    if not font:
        raise ViduError("CJK font missing; cannot apply 造镜者 watermark")
    base = ("[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=15:1[back];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];"
            "[back][front]overlay=(W-w)/2:(H-h)/2,"
            "drawtext=fontfile=" + font + ":text='造镜者':fontsize=h/23:"
            "fontcolor=white@0.13:"
            "x='(w-text_w)/2+0.18*w*sin(t*0.2)':"
            "y='(h-text_h)/2+0.12*h*sin(t*0.25)',"
            "format=yuv420p[v]")
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
         "-filter_complex", base, "-map", "[v]", "-map", "0:a?",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "24",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target)],
        capture_output=True, timeout=600)
    if result.returncode or not target.is_file():
        raise ViduError("FFmpeg export failed; raw clip is preserved")
    info = probe_mp4(target)
    if abs(info["duration"] - seconds) > 1.5:
        raise ViduError("Rendered duration does not match requested length")
    if (info["width"], info["height"]) != (1080, 1920):
        raise ViduError("Rendered aspect ratio is not 1080x1920")
    if not info["has_audio"]:
        raise ViduError("Video has no native audio; human review required")
    return info


def fetch_task(task_id, key):
    if not TASK_RE.fullmatch(task_id):
        raise ViduError("Invalid task ID")
    return api_request("GET", "/ent/v2/tasks/" + task_id + "/creations", key=key)


def run(args):
    root = Path(args.out).resolve()
    manifest_path = root / "vidu-status.json"
    if args.action == "generate":
        payload = build_payload(args.mode, args.prompt, args.seconds, args.resolution, args.first_frame)
        manifest = {"provider": "vidu", "model": MODEL, "mode": args.mode,
                    "seconds": args.seconds, "resolution": args.resolution,
                    "state": "PLANNED", "task_id": None, "billable_post_count": 0,
                    "note": "Unbilled plan; not a video generation."}
        save(manifest_path, manifest)
        if not args.confirm_paid:
            print("VIDU_DRY_RUN_OK: no provider call or charge")
            return
        key = key_from_env()
        manifest.update(state="POST_ACCEPTANCE_UNKNOWN", billable_post_count=1,
                        note="One authorized billable POST; never automatically retry.")
        save(manifest_path, manifest)
        endpoint = "/ent/v2/" + args.mode
        try:
            response = api_request("POST", endpoint, key=key, payload=payload)
        except ViduError as exc:
            manifest["note"] = str(exc)
            save(manifest_path, manifest)
            raise
        task_id = response.get("task_id")
        if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
            manifest["note"] = "POST response had no valid task ID; acceptance uncertain"
            save(manifest_path, manifest)
            raise ViduError("Vidu task ID missing; do not repeat a paid submission")
        manifest.update(task_id=task_id, state="SUBMITTED", credits=response.get("credits"),
                        note="Only query this task ID; do not re-submit.")
        save(manifest_path, manifest)
    elif args.action == "resume":
        task_id = args.task_id
        if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
            raise ViduError("Resume requires a real Vidu task ID")
        manifest = {"provider": "vidu", "model": MODEL, "state": "RESUMING",
                    "task_id": task_id, "seconds": args.seconds,
                    "billable_post_count": 0, "note": "Read-only status; no generation POST"}
        save(manifest_path, manifest)
        key = key_from_env()
    else:
        raise ViduError("Unsupported action")
    for attempt in range(args.poll_attempts):
        status = fetch_task(task_id, key)
        state = status.get("state")
        manifest["state"] = state
        manifest["credits"] = status.get("credits", manifest.get("credits"))
        save(manifest_path, manifest)
        if state == "failed":
            raise ViduError("Vidu task failed; check credits in provider console")
        if state == "success":
            creations = status.get("creations")
            if not isinstance(creations, list) or not creations or not isinstance(creations[0], dict):
                raise ViduError("Vidu reports success but no video creation URL")
            url = creations[0].get("url")
            if not url:
                raise ViduError("Vidu success has no video URL")
            raw = root / "source.mp4"
            download_video(url, raw)
            raw_info = probe_mp4(raw)
            if not 0 < raw_info["duration"] and abs(raw_info["duration"] - args.seconds) <= 1.5:
                raise ViduError("Provider output duration unexpected")
            final = root / "final-draft.mp4"
            info = render_portrait(raw, final, args.seconds)
            manifest["state"] = "DELIVERED"
            manifest["audit"] = info
            manifest["note"] = "Real MP4 generated; visual, audio and rights approval still required."
            save(manifest_path, manifest)
            print("VIDU_MP4_READY: final-draft.mp4, task ID recorded in artifact")
            return
        if state not in STATES_PENDING:
            raise ViduError("Unknown Vidu task state; resume by task ID after checking provider")
        if attempt < args.poll_attempts - 1:
            time.sleep(args.poll_seconds)
    raise ViduError("Vidu task still processing; use resume with existing task ID, never submit again")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["generate", "resume"], default="generate")
    parser.add_argument("--mode", choices=["text2video", "img2video"], default="text2video")
    parser.add_argument("--prompt", default="Same dark silver concept supercar accelerates intensely on sunset coastal road; real wheel rotation, realistic high-speed tracking camera, powerful original engine roar, consistent vehicle, no dialogue.")
    parser.add_argument("--seconds", type=int, choices=[10, 15], default=10)
    parser.add_argument("--resolution", choices=["540p", "720p", "1080p"], default="720p")
    parser.add_argument("--first-frame")
    parser.add_argument("--task-id")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--poll-attempts", type=int, default=60)
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--out", default="private-inputs/vidu-test")
    args = parser.parse_args(argv)
    try:
        if args.action == "resume" and args.confirm_paid:
            raise ViduError("Resume must not include paid generation approval")
        if not 1 <= args.poll_attempts <= 100 or not 0 <= args.poll_seconds <= 120:
            raise ViduError("Invalid polling settings")
        run(args)
        return 0
    except ViduError as exc:
        print("VIDU ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
