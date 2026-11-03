"""Read-only VQ authorization diagnostics. No model generation and no public secrets."""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .qianfan_media import VIDEO_ENDPOINT, MediaTaskError, _key


def probe_vq_auth(*, transport=None):
    """GET an intentionally nonexistent task, never POST or consume generation quota.

    HTTP 400/404 means the target endpoint responded to the key, but does NOT
    establish model entitlement. HTTP 401/403 means fail before generating a frame.
    Other statuses remain inconclusive and are not considered success.
    """
    key = _key().strip()
    if key.lower().startswith("bearer "):
        raise MediaTaskError("QIANFAN_API_KEY contains 'Bearer ' prefix; store key only, without Authorization header")
    if any(c.isspace() for c in key):
        raise MediaTaskError("QIANFAN_API_KEY has whitespace; store only the raw API key")
    if not key.startswith("bce-v3/"):
        raise MediaTaskError("QIANFAN_API_KEY is not a recognized bce-v3 API key format; check Qianfan console")

    params = urllib.parse.urlencode({
        "task_id": "qianfan-readonly-preflight-nonexistent-task",
        "model": "VQ3-Turbo",
    })
    url = VIDEO_ENDPOINT + "?" + params
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + key,
                      "Accept": "application/json"}, method="GET"
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, hdrs, newurl):
            return None
    opener = transport or urllib.request.build_opener(NoRedirect()).open
    try:
        with opener(req, timeout=20) as response:
            status = int(response.status)
            # Deliberately do not log/read the provider body or request URL.
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise MediaTaskError("VQ read-only preflight network failure; no paid task created") from None
    if status == 401:
        raise MediaTaskError("VQ API HTTP 401: key invalid/expired/missing scope or account mismatch; STOP, no paid generation")
    if status == 403:
        raise MediaTaskError("VQ API HTTP 403: likely insufficient scope or permission; STOP, no paid generation")
    if status not in (400, 404):
        raise MediaTaskError(f"VQ API diagnostic inconclusive HTTP {status}; STOP before billable request")
    return {"http_status": status, "method": "GET", "created_task": False,
            "authorization": "endpoint_reached_not_model_entitlement"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=("VQ2-Turbo", "VQ2-Pro", "VQ3-Turbo",
                                        "VQ3-Pro", "VQ4"), required=True)
    args = p.parse_args(argv)
    try:
        result = probe_vq_auth()
        result["requested_model"] = args.model
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except MediaTaskError as exc:
        print("VQ PREFLIGHT BLOCKED: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
