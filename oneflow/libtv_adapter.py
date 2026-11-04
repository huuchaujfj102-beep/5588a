"""LibTV Agent-IM adapter for OneFlow Commercial V3.1.

Official Codex plugin OAuth MCP (https://mcp.liblib.tv/mcp) is a SEPARATE
connector. This module follows documented Agent-IM session OpenAPI from
libtv-labs/libtv-skills and requires LIBTV_ACCESS_KEY in a private runtime.

Default: offline plan ONLY. No credit usage or upload. Live operations require
explicit one-request consent and external account quote/usage review. Never
auto-retry an uncertain generation submission.
"""
import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import uuid
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://im.liblib.tv"
CANVAS = "https://www.liblib.tv/canvas?projectId="
RESULT_HOST = "libtv-res.liblib.art"
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # conservative; provider documents up to 200 MB
MAX_RESULT_BYTES = 250 * 1024 * 1024
VIDEO_EXT = {".mp4", ".mov", ".webm"}
URL_PATTERN = re.compile(r'https://libtv-res\.liblib\.art/[^\s"\'<>]+?\.(?:mp4|mov|webm|png|jpg|jpeg|webp)(?:\?[^\s"\'<>]*)?', re.I)


class LibTVBlocked(RuntimeError):
    pass


def plan(brief, reference=None):
    if not isinstance(brief, str) or not (8 <= len(brief.strip()) <= 3000):
        raise LibTVBlocked("Provide a meaningful 8–3000 character brief")
    return {
       "schema": "oneflow.libtv.v1",
       "status": "OFFLINE_PLAN_NOT_GENERATED",
       "provider": "LibTV",
       "transport": "Agent-IM OpenAPI, not Codex MCP",
       "reference": str(reference) if reference else None,
       "task": brief,
       "video_generated": False,
       "commercial_license_confirmed": False,
       "credits_verified": False,
       "requires": [
          "User-authorized LIBTV_ACCESS_KEY in private secret store",
          "Account/model price and quota confirmation before each generation",
          "One explicitly approved generation request",
          "Actual output and quality/rights checks before downstream editing",
          "Per-platform publishing authorization unrelated to LibTV session"
       ]
    }


def _secret():
    value = os.getenv("LIBTV_ACCESS_KEY", "")
    if not value or any(c in value for c in "\r\n"):
        raise LibTVBlocked("LIBTV_ACCESS_KEY missing or invalid; configure only in protected secrets")
    return value


def _safe_response(req, limit=2000000):
    try:
        with urlopen(req, timeout=90) as resp:
            body = resp.read(limit + 1)
    except HTTPError as exc:
        raise LibTVBlocked("LibTV API returned HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise LibTVBlocked("LibTV network call uncertain (" + type(exc).__name__ +
                           "); inspect provider account before retrying") from None
    if len(body) > limit:
        raise LibTVBlocked("Unexpected oversized provider JSON response")
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise LibTVBlocked("Unparseable provider JSON response") from None
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        raise LibTVBlocked("Unexpected provider response envelope")
    return data["data"]


def _post(path, payload, key):
    body = json.dumps(payload, ensure_ascii=False).encode("utf8")
    req = Request(BASE+path, data=body, method="POST",
       headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    return _safe_response(req)


def create_session(brief, key, reference_url=None, session_id=None):
    # User-authored brief is preserved verbatim; ref URL appended as documented.
    msg = brief + ("\n参考图/视频：" + reference_url if reference_url else "")
    data = _post("/openapi/session",
                 {**({"sessionId":session_id} if session_id else {}),"message":msg},key)
    if not data.get("sessionId") or not data.get("projectUuid"):
        raise LibTVBlocked("Provider did not return sessionId and projectUuid; do not retry blindly")
    return {"session_id": data["sessionId"], "project_uuid": data["projectUuid"],
            "project_url": CANVAS + data["projectUuid"],
            "status": "SUBMITTED_NOT_YET_RENDERED"}


def upload_reference(path, key):
    path=Path(path)
    if not path.is_file() or path.suffix.lower() not in ALLOWED_EXT:
        raise LibTVBlocked("Real JPEG/PNG/WEBP or MP4/MOV/WEBM reference required")
    size=path.stat().st_size
    if size == 0 or size > MAX_UPLOAD_BYTES:
        raise LibTVBlocked("Reference file empty or over guarded 50MB limit")
    mime=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not (mime.startswith("image/") or mime.startswith("video/")):
        raise LibTVBlocked("Unsupported media MIME")
    boundary="OneFlow"+uuid.uuid4().hex
    blob=path.read_bytes()
    intro=(
      "--"+boundary+"\r\nContent-Disposition: form-data; name=\"accessKey\"\r\n\r\n"+key+"\r\n"
      "--"+boundary+"\r\nContent-Disposition: form-data; name=\"file\"; filename=\""+
      path.name.replace('"', '_')+"\"\r\nContent-Type: "+mime+"\r\n\r\n"
    ).encode("utf8")
    payload=intro+blob+("\r\n--"+boundary+"--\r\n").encode()
    req=Request(BASE+"/openapi/upload",data=payload,method="POST",headers={
      "Authorization":"Bearer "+key,
      "Content-Type":"multipart/form-data; boundary="+boundary})
    info=_safe_response(req)
    url=info.get("url","")
    if not _safe_asset_url(url):
        raise LibTVBlocked("Upload has no expected LibTV secure asset URL")
    return {"url":url,"sha256":hashlib.sha256(blob).hexdigest(),"bytes":size}


def _safe_asset_url(url):
    if not isinstance(url,str) or len(url)>2500:
        return False
    p=urlparse(url)
    return (p.scheme=="https" and p.hostname==RESULT_HOST and
            p.port is None and not p.username and not p.password and
            p.path.lower().endswith(tuple(ALLOWED_EXT)))


def extract_result_urls(messages):
    if not isinstance(messages,list):
        raise LibTVBlocked("Provider messages format invalid")
    values=[]
    for msg in messages:
        if not isinstance(msg,dict):
            continue
        content=msg.get("content","")
        if isinstance(content,str):
            values.extend(URL_PATTERN.findall(content))
            if msg.get("role")=="tool":
                try:
                    obj=json.loads(content)
                    result=obj.get("task_result",{})
                    for kind in ("images","videos"):
                        for entry in result.get(kind,[]):
                            if isinstance(entry,dict):
                                values.extend([entry.get("previewPath"),entry.get("url")])
                except (ValueError,AttributeError,TypeError):
                    pass
    return list(dict.fromkeys(x for x in values if _safe_asset_url(x)))


def query_session(session_id, key, after_seq=0):
    if not isinstance(session_id,str) or not re.fullmatch("[A-Za-z0-9_-]{8,128}",session_id):
        raise LibTVBlocked("Invalid session ID")
    if not isinstance(after_seq,int) or after_seq < 0:
        raise LibTVBlocked("Invalid afterSeq")
    path="/openapi/session/"+quote(session_id,safe="")
    if after_seq:
        path+="?afterSeq="+str(after_seq)
    req=Request(BASE+path,headers={"Authorization":"Bearer "+key,"Accept":"application/json"})
    data=_safe_response(req)
    messages=data.get("messages",[])
    urls=extract_result_urls(messages)
    return {"status":"RESULT_ASSETS_AVAILABLE_REVIEW_REQUIRED" if urls else "NOT_YET_DELIVERED",
            "session_id":session_id,"message_count":len(messages),
            "asset_urls":urls,
            "video_asset_urls":[x for x in urls if urlparse(x).path.lower().endswith(tuple(VIDEO_EXT))],
            "last_seq":max((x.get("seq",0) for x in messages
                          if isinstance(x,dict) and type(x.get("seq")) is int), default=after_seq)}


def download_result(asset_url, dest):
    if not _safe_asset_url(asset_url):
        raise LibTVBlocked("Asset URL must be a provider HTTPS media URL")
    dest=Path(dest)
    if dest.suffix.lower() not in ALLOWED_EXT:
        raise LibTVBlocked("Local destination extension is unsupported")
    dest.parent.mkdir(parents=True,exist_ok=True)
    req=Request(asset_url,headers={"User-Agent":"OneFlow/3.1"})
    try:
        with urlopen(req,timeout=150) as resp, dest.open("wb") as f:
            if urlparse(resp.geturl()).hostname != RESULT_HOST:
                raise LibTVBlocked("Untrusted download redirect")
            total=0
            while True:
                chunk=resp.read(1024*1024)
                if not chunk:
                    break
                total+=len(chunk)
                if total>MAX_RESULT_BYTES:
                    raise LibTVBlocked("Provider media over maximum download size")
                f.write(chunk)
    except LibTVBlocked:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise LibTVBlocked("Download failed; do not claim media generated") from None
    if dest.stat().st_size < 2048:
        dest.unlink(missing_ok=True)
        raise LibTVBlocked("Downloaded asset too small to trust")
    return {"path":str(dest),"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
            "status":"DOWNLOADED_REQUIRES_VISUAL_AND_COMMERCIAL_REVIEW"}


def main():
    p=argparse.ArgumentParser(description="OneFlow LibTV bridge (offline by default)")
    p.add_argument("--brief",default="为真实品牌制作原创高端商业视频，保持物体一致与可信物理")
    p.add_argument("--reference")
    p.add_argument("--out",default="private-inputs/libtv-trial")
    p.add_argument("--live-submit",action="store_true")
    p.add_argument("--approve-single-request",action="store_true")
    p.add_argument("--confirmed-cost-and-rights",action="store_true")
    p.add_argument("--session-id")
    p.add_argument("--check",action="store_true")
    p.add_argument("--after-seq",type=int,default=0)
    p.add_argument("--download-url")
    p.add_argument("--download-to")
    args=p.parse_args()
    root=Path(args.out)
    root.mkdir(parents=True,exist_ok=True)
    if args.check:
        if not args.session_id:
            raise LibTVBlocked("--check requires a real provider session ID")
        result=query_session(args.session_id,_secret(),args.after_seq)
    elif args.download_url:
        if not args.download_to:
            raise LibTVBlocked("--download-to required")
        result=download_result(args.download_url,args.download_to)
    elif args.live_submit:
        if not args.approve_single_request or not args.confirmed_cost_and_rights:
            raise LibTVBlocked("Explicit per-job credit quote / rights confirmation required")
        key=_secret()
        ref=upload_reference(args.reference,key)["url"] if args.reference else None
        result=create_session(args.brief,key,reference_url=ref,session_id=args.session_id)
    else:
        result=plan(args.brief,args.reference)
    (root/"libtv-job.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    try:
        main()
    except LibTVBlocked as e:
        print("LIBTV_BLOCKED:",str(e))
        raise SystemExit(2)
