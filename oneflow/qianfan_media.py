"""Baidu Qianfan async image and image-to-video adapters.

Both paid submissions require an explicit allow_paid=True. Reading an existing
task's status does not create another generation task. No media is written to
public GitHub Actions artifacts by this module.

Official API references (2026-10-22 video docs):
https://cloud.baidu.com/doc/qianfan-multimodal/s/8mmt3c9jr
https://cloud.baidu.com/doc/qianfan-multimodal/s/gmmt3c9im
https://cloud.baidu.com/doc/qianfan-multimodal/s/fmn5nsoey
https://cloud.baidu.com/doc/qianfan-multimodal/s/1mn5nsohk
https://cloud.baidu.com/doc/qianfan-api/s/Amg0lgcx4
https://cloud.baidu.com/doc/qianfan-api/s/Bmg0ma4hf
"""
import base64
import binascii
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error


IMAGE_ENDPOINT = "https://qianfan.baidubce.com/beta/image/qianfan-image-v1"
VIDEO_ENDPOINT = "https://qianfan.baidubce.com/beta/video/generations/qianfan-video"
MUSE_ENDPOINT = "https://qianfan.baidubce.com/video/generations"
MUSE_MODEL = "musesteamer-air-i2v"
IMAGE_MODELS = ("o1-base", "v3o")
VIDEO_MODELS = ("VQ2-Turbo", "VQ2-Pro", "VQ3-Turbo", "VQ3-Pro", "VQ4")
DONE = ("succeed", "success", "succeeded")
FAILED = ("failed",)
RUNNING = ("submitted", "processing", "created", "queueing", "pending", "queued", "running")


class MediaTaskError(Exception):
    """Do not propagate raw provider responses or HTTP request headers."""


def _key():
    key = os.environ.get("QIANFAN_API_KEY", "")
    if not key.strip():
        raise MediaTaskError("Missing QIANFAN_API_KEY; no request sent")
    return key



def _safe_open(req, timeout):
    """Do not forward Bearer credentials across HTTP redirects."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    return urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout)


def _request(url, key, payload=None, transport=None):
    body = (json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if payload is not None else None)
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=body,
                                 method="POST" if body is not None else "GET")
    try:
        opener = transport or _safe_open
        with opener(req, timeout=45) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        # Record status only. Never emit provider response body, URLs, headers,
        # secrets or user-submitted prompt text into public Actions logs.
        raise MediaTaskError(
            "Qianfan API HTTP " + str(exc.code) +
            "; no task ID was confirmed. Check billing, entitlement and error code privately"
        ) from None
    except urllib.error.URLError:
        raise MediaTaskError("Qianfan API network/DNS/TLS failure; no task ID confirmed") from None
    except TimeoutError:
        raise MediaTaskError("Qianfan API request timeout; task acceptance unknown") from None
    except Exception:
        # Generic transport failure can otherwise hide accidental secret material.
        raise MediaTaskError("Qianfan API transport failure; task acceptance unknown") from None
    if not isinstance(data, dict):
        raise MediaTaskError("Qianfan response was not an object")
    return data



def probe_image_endpoint(*, transport=None):
    """Read-only GET of a clearly invalid task. Never submits media generation.

    HTTP 400/404 can indicate endpoint reachability, not model permission.
    API authentication and billing remain separate; no task ID is created.
    """
    url = IMAGE_ENDPOINT + "?task_id=qianfan-readonly-diagnostic-invalid-id"
    key = _key()
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + key,
                      "Accept": "application/json"}, method="GET")
    try:
        opener = transport or _safe_open
        with opener(req, timeout=20) as response:
            code = response.status
            # No response body is read or displayed.
        return {"http_status": int(code), "method": "GET",
                "created_task": False}
    except urllib.error.HTTPError as exc:
        return {"http_status": int(exc.code), "method": "GET",
                "created_task": False}
    except urllib.error.URLError:
        raise MediaTaskError("Read-only Qianfan endpoint probe failed: network/DNS/TLS") from None
    except TimeoutError:
        raise MediaTaskError("Read-only Qianfan endpoint probe timed out") from None


def _task_id(value):
    if (not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value)):
        raise MediaTaskError("Invalid Qianfan task ID")
    return value


def submit(kind, *, prompt, model, image_url=None, ratio="9:16",
           duration=5, resolution="1k", allow_paid=False, transport=None,
           audio=False):
    """Submit ONE potentially billable task. Does not imply generation success."""
    if not allow_paid:
        raise MediaTaskError("Explicit allow_paid=True required; no request sent")
    if kind not in ("image", "video"):
        raise MediaTaskError("kind must be image or video")
    if not isinstance(prompt, str) or not prompt.strip():
        raise MediaTaskError("Prompt is required")
    if ratio not in ("9:16", "16:9", "1:1"):
        raise MediaTaskError("Unsupported image aspect ratio")
    if kind == "image":
        if model not in IMAGE_MODELS or resolution not in ("1k", "2k"):
            raise MediaTaskError("Unsupported image model or resolution")
        if len(prompt) > 2500:
            raise MediaTaskError("Image prompt exceeds 2500 characters")
        endpoint = IMAGE_ENDPOINT
        payload = {"model": model, "type": "omni", "model_parameters": {
            "prompt": prompt, "resolution": resolution,
            "aspect_ratio": ratio, "result_type": "single", "n": 1}}
    else:
        if model not in VIDEO_MODELS + (MUSE_MODEL,):
            raise MediaTaskError("Unsupported Qianfan image-to-video model")
        if len(prompt) > 2000:
            raise MediaTaskError("Video prompt exceeds 2000 characters")
        if not isinstance(image_url, str) or not image_url:
            raise MediaTaskError("Image-to-video requires a first-frame image")
        if image_url.startswith("data:image/"):
            if len(image_url) > 14_000_000:
                raise MediaTaskError("Image data URI exceeds allowed size")
            match = re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", image_url)
            if not match:
                raise MediaTaskError("Invalid supported base64 image format")
            try:
                raw = base64.b64decode(match.group(1), validate=True)
            except (binascii.Error, ValueError):
                raise MediaTaskError("Invalid image base64 encoding") from None
            if len(raw) > 10_000_000 or len(raw) < 64:
                raise MediaTaskError("Base64 frame must be 64 bytes to 10 MB")
        else:
            parsed = urllib.parse.urlparse(image_url)
            if (parsed.scheme != "https" or not parsed.hostname
                    or parsed.username or parsed.password):
                raise MediaTaskError("Image-to-video requires a public HTTPS image URL")
        max_duration = 5 if model == MUSE_MODEL else (16 if model in ("VQ4", "VQ3-Pro", "VQ3-Turbo") else 10)
        if type(duration) is not int or not 1 <= duration <= max_duration or (model == MUSE_MODEL and duration != 5):
            raise MediaTaskError("Invalid duration for selected video model")
        if resolution not in ("540p", "720p", "1080p"):
            raise MediaTaskError("Choose 540p, 720p or 1080p for video")
        if type(audio) is not bool:
            raise MediaTaskError("audio must be boolean")
        if model == MUSE_MODEL:
            if audio:
                raise MediaTaskError("MuseSteamer Air I2V has no documented embedded audio")
            # Air uses /video/generations with content[]; never send VQ schema.
            # The input frame establishes video ratio; Air does not document resolution.
            endpoint = MUSE_ENDPOINT
            payload = {"model": MUSE_MODEL, "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ], "duration": 5, "watermark": False, "prompt_extend": False}
        else:
            endpoint = VIDEO_ENDPOINT
            # VQ's first-frame image determines ratio, not an aspect_ratio field.
            payload = {"model": model, "type": "img2video", "model_parameters": {
                "images": [image_url], "prompt": prompt, "duration": duration,
                "resolution": resolution, "audio": audio, "bgm": False,
                "is_rec": False, "watermark": False}}
    data = _request(endpoint, _key(), payload, transport=transport)
    if kind == "image":
        if data.get("code") != 0 or not isinstance(data.get("data"), dict):
            raise MediaTaskError("Qianfan image generation task not accepted")
        item = data["data"]
        task_id = _task_id(item.get("task_id"))
        status = item.get("task_status", "submitted")
    else:
        # Newer VQ API uses top-level task_id/status, unlike image API.
        task_id = _task_id(data.get("task_id"))
        status = data.get("status", "created")
    if status not in DONE + FAILED + RUNNING:
        raise MediaTaskError("Unrecognized Qianfan task status")
    return {"kind": kind, "model": model, "task_id": task_id,
            "status": status}


def task_status(kind, task_id, *, model=None, transport=None):
    """Read status of an ALREADY SUBMITTED task without creating new charges."""
    task_id = _task_id(task_id)
    if kind == "image":
        endpoint = IMAGE_ENDPOINT
    elif kind == "video":
        endpoint = MUSE_ENDPOINT if model == MUSE_MODEL else VIDEO_ENDPOINT
        if model is not None and model not in VIDEO_MODELS + (MUSE_MODEL,):
            raise MediaTaskError("Invalid video model")
    else:
        raise MediaTaskError("kind must be image or video")
    params = {"task_id": task_id}
    if kind == "video" and model and model != MUSE_MODEL:
        params["model"] = model
    data = _request(endpoint + "?" + urllib.parse.urlencode(params), _key(),
                    transport=transport)
    if kind == "image":
        if data.get("code") != 0 or not isinstance(data.get("data"), dict):
            raise MediaTaskError("Qianfan image status response was not successful")
        item = data["data"]
        status = item.get("task_status")
        result = item.get("task_result") or {}
        entries = result.get("images") or []
    else:
        item = data
        status = item.get("status")
        if model == MUSE_MODEL:
            content = item.get("content") or {}
            if not isinstance(content, dict):
                raise MediaTaskError("MuseSteamer content must be an object")
            video_url = content.get("video_url")
            entries = [{"url": video_url}] if isinstance(video_url, str) else []
        else:
            entries = item.get("creations") or []
    if status not in DONE + FAILED + RUNNING:
        raise MediaTaskError("Unrecognized Qianfan task status")
    if not isinstance(entries, list):
        raise MediaTaskError("Media result is not a list")
    urls = []
    if status in DONE:
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("url"), str):
                url = entry["url"]
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme == "https" and parsed.hostname:
                    urls.append(url)
        if not urls:
            raise MediaTaskError("Task marked successful but no HTTPS media result found")
    return {"kind": kind, "task_id": task_id,
            "status": status, "result_urls": urls}


def wait_for_task(kind, task_id, *, model=None, attempts=12, delay=10,
                  transport=None, sleep_fn=time.sleep):
    """Bounded polling. No re-submission. Returns pending state at timeout."""
    if type(attempts) is not int or not 1 <= attempts <= 60:
        raise MediaTaskError("Invalid maximum poll attempts")
    if not isinstance(delay, (int, float)) or not 0 <= delay <= 60:
        raise MediaTaskError("Invalid poll delay")
    last = None
    for number in range(attempts):
        last = task_status(kind, task_id, model=model, transport=transport)
        if last["status"] in DONE + FAILED:
            return last
        if number < attempts - 1:
            sleep_fn(delay)
    return last
