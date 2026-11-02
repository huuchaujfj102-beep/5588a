"""Douyin official OAuth video upload + create, AFTER OneFlow human approval.

Requires approved developer app video.create.bind scope AND user OAuth.
Never posts unless --consent explicitly given, and never claims public
publication merely from a successful create API response.
"""
import argparse
import json
import os
import sys
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .core import FlowError, authorize_publish, load_json, now, save_json

UPLOAD_URL = "https://open.douyin.com/api/douyin/v1/video/upload_video/"
CREATE_URL = "https://open.douyin.com/api/douyin/v1/video/create_video/"
MAX_DIRECT_UPLOAD_BYTES = 50_000_000


def _oauth():
    token = os.getenv("DOUYIN_ACCESS_TOKEN", "").strip()
    open_id = os.getenv("DOUYIN_OPEN_ID", "").strip()
    if not token or not open_id:
        raise FlowError("Douyin authorized access token and open_id are missing")
    if len(token) > 2048 or len(open_id) > 512:
        raise FlowError("Invalid Douyin OAuth metadata")
    return token, open_id


def _send(url, token, *, payload=None, raw=None, boundary=None, transport=None):
    headers = {"access-token": token, "Accept": "application/json"}
    if raw is not None:
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        body = raw
    else:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf8")
    request = urllib.request.Request(url, headers=headers, method="POST", data=body)
    class DenyRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    opener = transport or urllib.request.build_opener(DenyRedirect()).open
    try:
        with opener(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise FlowError("Douyin HTTP " + str(exc.code) +
                        "; request status uncertain, check provider privately") from None
    except Exception:
        raise FlowError("Douyin submission transport failure; do NOT blindly retry") from None
    if not isinstance(result, dict):
        raise FlowError("Invalid Douyin API response structure")
    return result


def _accepted(response):
    data, extra = response.get("data") or {}, response.get("extra") or {}
    return isinstance(data, dict) and isinstance(extra, dict) and (
        data.get("error_code", 0) == 0 and extra.get("error_code", 0) == 0)


def publish_approved_douyin(job, *, consent=False, text=None, visibility="private",
                             confirm_public=False, transport=None):
    """Only official submission. Returns 'pending' until real public URL verified."""
    root = Path(job).resolve()
    manifest = load_json(root / "manifest.json")
    authorize_publish(root, manifest, "douyin")
    if not consent:
        raise FlowError("Explicit per-platform consent required for Douyin posting")
    if visibility not in ("private", "public"):
        raise FlowError("Invalid Douyin post visibility")
    if visibility == "public" and not confirm_public:
        raise FlowError("Public posting requires separate --confirm-public permission")
    token, open_id = _oauth()
    current = manifest.setdefault("douyin_direct", {})
    if current.get("status") == "CREATE_ACCEPTED":
        return {"status": "pending", "item_id": current.get("item_id"),
                "notice": "Platform review/public availability not verified"}
    if current.get("status") in ("UPLOAD_ATTEMPTED", "CREATE_ATTEMPTED",
                                 "UPLOAD_UNKNOWN", "CREATE_UNKNOWN"):
        raise FlowError("A previous Douyin request is uncertain; check platform status, do not duplicate")
    if text is None:
        text = manifest["brief"][:250]
    if not isinstance(text, str) or not text.strip() or len(text) > 1000:
        raise FlowError("Douyin text must be 1-1000 characters")

    suffix = "?open_id=" + urllib.parse.quote(open_id, safe="")
    if not current.get("video_id"):
        clip = root / manifest["render"]
        if not clip.is_file():
            raise FlowError("Reviewed final MP4 is missing")
        size = clip.stat().st_size
        if size < 256 or size > MAX_DIRECT_UPLOAD_BYTES:
            raise FlowError("Only MP4 256 bytes to 50 MB supported by initial Douyin uploader")
        boundary = "oneflow" + uuid.uuid4().hex
        raw = (
            ("--" + boundary + "\r\n" +
             'Content-Disposition: form-data; name="video"; filename="film.mp4"\r\n' +
             "Content-Type: video/mp4\r\n\r\n").encode()
            + clip.read_bytes()
            + ("\r\n--" + boundary + "--\r\n").encode()
        )
        current["status"] = "UPLOAD_ATTEMPTED"
        current["attempted_at"] = now()
        save_json(root / "manifest.json", manifest)
        try:
            reply = _send(UPLOAD_URL + suffix, token, raw=raw,
                          boundary=boundary, transport=transport)
            if not _accepted(reply) or not isinstance(
                    ((reply.get("data") or {}).get("video") or {}).get("video_id"), str):
                raise FlowError("Douyin upload not accepted; check API error privately")
        except FlowError:
            current["status"] = "UPLOAD_UNKNOWN"
            save_json(root / "manifest.json", manifest)
            raise
        current["video_id"] = reply["data"]["video"]["video_id"]
        current["status"] = "UPLOAD_ACCEPTED"
        save_json(root / "manifest.json", manifest)

    current["status"] = "CREATE_ATTEMPTED"
    current["requested_visibility"] = visibility
    save_json(root / "manifest.json", manifest)
    try:
        reply = _send(CREATE_URL + suffix, token,
                      payload={"video_id": current["video_id"], "text": text,
                               "private_status": 0 if visibility == "public" else 1},
                      transport=transport)
        data = reply.get("data") or {}
        if not _accepted(reply) or not isinstance(data.get("item_id"), str):
            raise FlowError("Douyin create was not accepted; check platform before retry")
    except FlowError:
        current["status"] = "CREATE_UNKNOWN"
        save_json(root / "manifest.json", manifest)
        raise
    current["item_id"] = data["item_id"]
    current["status"] = "CREATE_ACCEPTED"
    current["accepted_at"] = now()
    # Private-status=1 ensures draft is visible to account owner; changing to
    # public requires a separate, clearly approved publish action.
    manifest["publication"]["douyin"] = {
        "status": "pending", "external_id": data["item_id"],
        "url": None, "updated_at": now(),
        "review_note": "Submission accepted, moderation/visibility not independently verified"}
    save_json(root / "manifest.json", manifest)
    return {"status": "pending", "item_id": data["item_id"],
            "notice": "Created an account-private video; publication not verified"}


def main(argv=None):
    p = argparse.ArgumentParser(description="Official Douyin private upload after human OneFlow approval")
    p.add_argument("--job", required=True)
    p.add_argument("--consent-private-upload", action="store_true")
    p.add_argument("--consent-public-post", action="store_true")
    p.add_argument("--confirm-public", action="store_true")
    p.add_argument("--text")
    args = p.parse_args(argv)
    try:
        if args.consent_public_post and args.consent_private_upload:
            raise FlowError("Choose exactly one Douyin visibility/consent mode")
        result = publish_approved_douyin(
            args.job,
            consent=args.consent_private_upload or args.consent_public_post,
            text=args.text,
            visibility="public" if args.consent_public_post else "private",
            confirm_public=args.confirm_public)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (FlowError, OSError, ValueError) as e:
        print("DOUYIN UPLOAD ERROR: " + str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
