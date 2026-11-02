"""Baidu Qianfan image/video async task submitters. No calls without opt-in."""
import os
import re
import json
import urllib.request

IMAGE_ENDPOINT = "https://qianfan.baidubce.com/beta/image/qianfan-image-v1"
VIDEO_ENDPOINT = "https://qianfan.baidubce.com/beta/video/generations/qianfan-video"

class MediaTaskError(Exception):
    pass

def submit(kind, *, prompt, model, image_url=None, ratio="9:16",
           duration=5, resolution="1k", allow_paid=False, transport=None):
    """Submit exactly one potentially billable task; never infer completion."""
    if not allow_paid:
        raise MediaTaskError("Explicit allow_paid=True required; no request sent")
    if kind not in ("image", "video"):
        raise MediaTaskError("kind must be image or video")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt)>2500:
        raise MediaTaskError("Invalid prompt")
    if ratio not in ("9:16", "16:9", "1:1"):
        raise MediaTaskError("Unsupported aspect ratio")
    if kind=="image":
        if model not in ("o1-base", "v3o") or resolution not in ("1k", "2k"):
            raise MediaTaskError("Unsupported image model or resolution")
        endpoint=IMAGE_ENDPOINT
        payload={"model":model,"type":"omni","model_parameters":{
            "prompt":prompt,"resolution":resolution,"aspect_ratio":ratio,
            "result_type":"single","n":1}}
    else:
        if model != "qianfan-video-latest":
            raise MediaTaskError("Unsupported video model")
        if not isinstance(image_url,str) or not image_url.startswith("https://"):
            raise MediaTaskError("Image-to-video requires HTTPS image URL")
        if not isinstance(duration,int) or not 3<=duration<=15:
            raise MediaTaskError("Duration outside safe 3-15 second test range")
        endpoint=VIDEO_ENDPOINT
        payload={"model":model,"type":"img2video","model_parameters":{
            "prompt":prompt,"images":[image_url],
            "settings":{"duration":duration,"aspect_ratio":ratio}}}
    key=os.environ.get("QIANFAN_API_KEY","")
    if not key.strip():
        raise MediaTaskError("Missing QIANFAN_API_KEY")
    req=urllib.request.Request(endpoint,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        method="POST")
    try:
        opener=transport or urllib.request.urlopen
        with opener(req,timeout=45) as response:
            result=json.load(response)
        if result.get("code")!=0 or not result.get("data",{}).get("task_id"):
            raise MediaTaskError("Provider did not accept task")
        return {"task_id":result["data"]["task_id"],
                "status":result["data"].get("task_status","submitted"),
                "kind":kind,"model":model}
    except MediaTaskError:
        raise
    except Exception:
        raise MediaTaskError("Qianfan task submission failed; inspect provider console") from None
