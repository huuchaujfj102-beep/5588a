"""火山方舟 Seedance 图生视频，支持本地素材与任务续查。"""
import argparse
import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

from .providers import NoRedirect

API = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
FAST = "doubao-seedance-2-0-fast-260128"


def image_source(source):
    if urlsplit(source).scheme in {"https", "asset"}:
        if not urlsplit(source).netloc:
            raise ValueError("Invalid image URL or asset ID")
        return source
    path = Path(source)
    formats = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
    kind = formats.get(path.suffix.lower())
    if not kind or not path.is_file() or not 0 < path.stat().st_size <= 10_000_000:
        raise ValueError("Provide an HTTPS image URL, an asset ID, or a local JPG/PNG/WebP up to 10 MB")
    return f"data:image/{kind};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def build_payload(args):
    if not args.first_frame:
        raise ValueError("--first-frame is required for generation")
    content = []
    if args.prompt.strip():
        content.append({"type": "text", "text": args.prompt})
    for role, source in (("first_frame", args.first_frame), ("last_frame", args.last_frame)):
        if source:
            content.append({"type": "image_url", "role": role, "image_url": {"url": image_source(source)}})
    return {
        "model": args.model,
        "content": content,
        "duration": args.seconds,
        "resolution": args.resolution,
        "ratio": args.ratio,
        "generate_audio": args.audio,
    }


def request(url, key, payload=None):
    headers = {"Authorization": "Bearer " + key}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    try:
        with NoRedirect.opener().open(Request(url, data=data, headers=headers), timeout=45) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"Ark API HTTP {exc.code}") from None
    except (URLError, TimeoutError, ValueError):
        raise ValueError("Ark API request failed or returned invalid JSON") from None
    if not isinstance(result, dict):
        raise ValueError("Ark API returned an invalid response")
    return result


def run(args):
    payload = None if args.task_id else build_payload(args)
    if not args.task_id and not args.submit:
        print(json.dumps({
            "mode": "dry-run", "model": payload["model"], "duration": payload["duration"],
            "resolution": payload["resolution"], "ratio": payload["ratio"], "audio": payload["generate_audio"],
            "image_roles": [item["role"] for item in payload["content"] if item["type"] == "image_url"],
        }, ensure_ascii=False))
        return
    key = os.getenv("ARK_API_KEY", "").strip()
    if not key:
        raise ValueError("Configure ARK_API_KEY before calling Ark")
    task_id = args.task_id
    if not task_id:
        try:
            task_id = request(API, key, payload).get("id")
        except ValueError as exc:
            raise ValueError(f"{exc}. Check Ark task history before submitting again.") from None
    if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
        raise ValueError("Invalid Ark task ID. Check Ark task history before submitting again.")
    print(f"Ark task ID: {task_id}", flush=True)
    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        result = request(f"{API}/{task_id}", key)
        status = result.get("status")
        if status == "succeeded":
            url = result.get("content", {}).get("video_url", "")
            if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
                raise ValueError("Ark returned no valid HTTPS video URL")
            target = Path(args.out)
            temporary = target.with_name(target.name + ".part")
            try:
                with NoRedirect.opener().open(url, timeout=120) as response, temporary.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if temporary.stat().st_size == 0:
                    raise ValueError("Ark returned an empty video")
                temporary.replace(target)
            except (OSError, ValueError):
                raise ValueError("Video download failed. Resume with the same task ID.") from None
            finally:
                temporary.unlink(missing_ok=True)
            print(f"Saved {target}")
            return
        if status not in {"queued", "running"}:
            raise ValueError(f"Ark task ended with status {status}" if status in {"failed", "cancelled", "expired"}
                             else "Ark returned an unexpected task status")
        time.sleep(min(8, max(0, deadline - time.monotonic())))
    raise ValueError("Polling timed out. Resume with --task-id to avoid a second submission.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--submit", action="store_true", help="Submit one billable generation task")
    action.add_argument("--task-id", help="Resume an existing task with GET")
    parser.add_argument("--first-frame")
    parser.add_argument("--last-frame")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--model", default=FAST)
    parser.add_argument("--seconds", type=int, choices=range(4, 16), default=5)
    parser.add_argument("--ratio", choices=("9:16", "16:9", "1:1", "adaptive"), default="9:16")
    parser.add_argument("--resolution", choices=("480p", "720p"), default="720p")
    parser.add_argument("--audio", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=600)
    parser.add_argument("--out", default="seedance.mp4")
    args = parser.parse_args()
    if args.wait_seconds <= 0:
        parser.error("--wait-seconds must be positive")
    try:
        run(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
