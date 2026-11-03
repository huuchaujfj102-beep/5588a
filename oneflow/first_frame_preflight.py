"""Read-only validation of PUBLIC HTTPS reference frames before any paid video POST.

Does not generate media, send API keys, follow redirects, or alter task ledgers.
HTTP image retrieval is bounded; provider-side image fetch compatibility cannot
be guaranteed by this external check.
"""
import argparse
import urllib.error
import urllib.parse
import urllib.request

from .core import FlowError
from .qianfan_i2v import _checked_public_url

MAX_REFERENCE_BYTES = 9_000_000

def verify_public_image(url, *, transport=None):
    safe = _checked_public_url(url)
    parts = urllib.parse.urlsplit(safe)
    if parts.query or parts.fragment or parts.username or parts.password:
        raise FlowError("Reference image URL must be direct, with no signed query or credentials")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = transport or urllib.request.build_opener(NoRedirect()).open
    req = urllib.request.Request(
        safe, method="GET",
        headers={"Accept": "image/jpeg,image/png,image/webp"}
    )
    try:
        with opener(req, timeout=25) as response:
            mime = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
            raw = response.read(MAX_REFERENCE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        raise FlowError("PUBLIC_IMAGE_UNREACHABLE: no paid task created") from None
    if len(raw) > MAX_REFERENCE_BYTES or len(raw) < 128:
        raise FlowError("PUBLIC_IMAGE_SIZE_INVALID: no paid task created")
    kind = ("png" if raw.startswith(b"\x89PNG\r\n\x1a\n")
            else "jpg" if raw.startswith(b"\xff\xd8\xff")
            else "webp" if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
            else None)
    if kind is None or (mime and mime not in ("image/png", "image/jpeg", "image/webp", "application/octet-stream")):
        raise FlowError("PUBLIC_IMAGE_FORMAT_INVALID: no paid task created")
    return {"verified_public_image": True, "format": kind,
            "bytes": len(raw), "request_method": "GET", "paid_task_created": False,
            "note": "Availability to Baidu still not guaranteed"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    args = p.parse_args(argv)
    try:
        result = verify_public_image(args.url)
        print("PUBLIC_FRAME_PREFLIGHT_OK " + result["format"]
              + " bytes=" + str(result["bytes"]) + " (no paid task)")
        return 0
    except FlowError as exc:
        print("PUBLIC_FRAME_PREFLIGHT_BLOCKED: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
