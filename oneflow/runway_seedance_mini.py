"""Runway Dev Seedance 2.0 Mini native adapter; NO Volcengine dependency.

API verified: https://dev.runway.com/learn/seedance-2-0-api
Paid POST is explicit and never retried, including ambiguous timeouts.
This is separate from consumer Runway MCP account balances.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.dev.runwayml.com"
VERSION = "2024-11-06"
MODEL = "seedance2_mini"
RATES = {"480p": 7, "720p": 15}  # 2026-11-05 public standard credits/second
RATIOS = {"480p": {"496:864", "560:752", "640:640", "752:560", "864:496", "992:432"},
          "720p": {"720:1280", "834:1112", "960:960", "1112:834", "1280:720", "1470:630"}}
TASK_ID = re.compile(r"^[a-zA-Z0-9_-]{3,128}$")
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}


class SeedanceMiniError(RuntimeError):
    pass


def build_payload(*, prompt, duration=10, resolution="720p", portrait=True, first_frame_url=None, audio=True):
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 10000:
        raise SeedanceMiniError("Prompt must be 1-10000 characters")
    if type(duration) is not int or not 4 <= duration <= 15:
        raise SeedanceMiniError("Duration must be an integer 4-15 seconds")
    if resolution not in RATES:
        raise SeedanceMiniError("Mini only supports 480p/720p")
    ratio = ("720:1280" if resolution == "720p" else "496:864") if portrait else (
        "1280:720" if resolution == "720p" else "864:496")
    if ratio not in RATIOS[resolution]:
        raise SeedanceMiniError("Unsupported Mini output ratio")
    if type(audio) is not bool:
        raise SeedanceMiniError("audio must be boolean")
    body = {"model": MODEL, "promptText": prompt.strip(), "duration": duration,
            "ratio": ratio, "audio": audio}
    if first_frame_url is not None:
        parts = urllib.parse.urlsplit(first_frame_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise SeedanceMiniError("First frame must be a clean HTTPS URL")
        host = parts.hostname.lower()
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            raise SeedanceMiniError("Private first frame URL not allowed")
        try:
            if not ipaddress.ip_address(host).is_global:
                raise SeedanceMiniError("Private first frame URL not allowed")
        except ValueError:
            pass
        if len(first_frame_url) > 4096:
            raise SeedanceMiniError("First frame URL too long")
        body["promptImage"] = first_frame_url
    return body


def api_call(method, route, *, key, payload=None, opener=None):
    if method not in ("GET", "POST") or not route.startswith("/v1/"):
        raise SeedanceMiniError("Invalid route")
    headers = {"Authorization": "Bearer " + key, "X-Runway-Version": VERSION,
               "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API + route, data=data, headers=headers, method=method)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    call = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with call(req, timeout=180 if method == "POST" else 30) as res:
            raw = res.read(1048577)
        if len(raw) > 1048576:
            raise SeedanceMiniError("Response too large")
        answer = json.loads(raw)
        if not isinstance(answer, dict):
            raise SeedanceMiniError("Unexpected provider response")
        return answer
    except urllib.error.HTTPError as e:
        raise SeedanceMiniError("Provider HTTP " + str(e.code) +
            "; never repeat billable POST without account/task reconciliation") from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise SeedanceMiniError("Provider transport issue; " +
            ("POST acceptance UNKNOWN; do not resubmit" if method == "POST"
             else "GET status may be safely retried")) from None
    except (ValueError, UnicodeDecodeError):
        raise SeedanceMiniError("Provider returned invalid JSON; " +
            ("POST acceptance UNKNOWN; do not resubmit" if method == "POST"
             else "GET status may be safely retried")) from None


def secret():
    value = os.environ.get("RUNWAYML_API_SECRET", "")
    if not value or value != value.strip() or any(c.isspace() for c in value):
        raise SeedanceMiniError("Missing or invalid RUNWAYML_API_SECRET")
    return value


def write_status(out, state, *, task_id=None, quoted_credits=None, mode=None, prompt_sha256=None):
    path = Path(out).resolve()
    path.mkdir(parents=True, exist_ok=True)
    target = path / "seedance-mini-status.json"
    data = {"provider": "runway_dev", "model": MODEL, "state": state,
            "task_id": task_id, "estimated_standard_credits": quoted_credits,
            "mode": mode, "prompt_sha256": prompt_sha256}
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(target)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("dry-run", "generate", "status"), default="dry-run")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--resolution", choices=("480p", "720p"), default="720p")
    parser.add_argument("--landscape", action="store_true")
    parser.add_argument("--image-url", default=None)
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--out", default="build/seedance-mini")
    args = parser.parse_args(argv)
    if args.action == "status":
        if args.confirm_paid or args.image_url or not args.task_id or not TASK_ID.fullmatch(args.task_id):
            raise SeedanceMiniError("Status needs a known task id and no paid/image inputs")
        result = api_call("GET", "/v1/tasks/" + args.task_id, key=secret())
        state = result.get("status")
        if state not in TERMINAL | {"PENDING", "RUNNING", "THROTTLED"}:
            state = "UNKNOWN"
        write_status(args.out, state, task_id=args.task_id)
        print("SEEDANCE_MINI_TASK_STATUS=" + state)
        return
    if args.task_id:
        raise SeedanceMiniError("Existing task ID belongs to --action status")
    payload = build_payload(prompt=args.prompt, duration=args.duration,
                            resolution=args.resolution, portrait=not args.landscape,
                            first_frame_url=args.image_url, audio=not args.no_audio)
    cost = args.duration * RATES[args.resolution]
    mode = "image_to_video" if args.image_url else "text_to_video"
    sha = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()
    if args.action == "dry-run":
        if args.confirm_paid:
            raise SeedanceMiniError("Dry-run must not include paid confirmation")
        write_status(args.out, "DRY_RUN", quoted_credits=cost, mode=mode, prompt_sha256=sha)
        print("SEEDANCE_MINI_DRY_RUN_OK model=seedance2_mini duration=" +
              str(args.duration) + "s resolution=" + args.resolution + " mode=" +
              mode + " estimated_standard_credits=" + str(cost) + " paid_post_count=0")
        return
    if not args.confirm_paid:
        raise SeedanceMiniError("Generation needs explicit --confirm-paid")
    write_status(args.out, "POST_ACCEPTANCE_UNKNOWN", quoted_credits=cost,
                 mode=mode, prompt_sha256=sha)
    route = "/v1/image_to_video" if args.image_url else "/v1/text_to_video"
    result = api_call("POST", route, key=secret(), payload=payload)
    task_id = result.get("id")
    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        raise SeedanceMiniError("POST acceptance unknown: task ID missing; DO NOT RETRY")
    write_status(args.out, "SUBMITTED", task_id=task_id, quoted_credits=cost,
                 mode=mode, prompt_sha256=sha)
    print("SEEDANCE_MINI_SUBMITTED task_id=" + task_id + " paid_post_count=1")


if __name__ == "__main__":
    try:
        main()
    except SeedanceMiniError as exc:
        raise SystemExit("SEEDANCE_MINI_ERROR: " + str(exc)) from None
