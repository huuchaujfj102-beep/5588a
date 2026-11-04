"""Guarded cloud timeline render adapters (Shotstack and JSON2Video).

OFFLINE by default. Sending a request can charge money; requires explicit
confirmation, a quoted price within a project cap, API credentials and a
pre-inserted idempotency lock. No blind retries after ambiguous HTTP failure.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from .longform import LongformError, build_render_payload, connection, load_timeline

RENDERERS = {
    "shotstack": ("https://api.shotstack.io/edit/stage/render", "SHOTSTACK_API_KEY", "x-api-key"),
    "json2video": ("https://api.json2video.com/v2/movies", "JSON2VIDEO_API_KEY", "x-api-key")
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_json(opener, request):
    try:
        response = opener(request, timeout=30)
        with response as stream:
            body = stream.read(131073)
            if len(body) > 131072:
                raise LongformError("Provider response too large")
            result = json.loads(body.decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise LongformError(
            "Render provider call uncertain or failed. DO NOT auto-retry; inspect provider dashboard"
        ) from None
    if not isinstance(result, dict):
        raise LongformError("Malformed provider response")
    return result


def prepare_submission(conn, episode_id, provider, payload, *,
                       confirm_paid=False, quote_rmb=None, budget_cap_rmb=None):
    if provider not in RENDERERS:
        raise LongformError("Unsupported render provider")
    if not confirm_paid:
        raise LongformError("Paid render BLOCKED: --confirm-paid required")
    if (quote_rmb is None or budget_cap_rmb is None or
        not 0 <= quote_rmb <= budget_cap_rmb or budget_cap_rmb <= 0):
        raise LongformError("Paid render BLOCKED: valid quote and budget cap required")
    # Rebuild from reviewed assets: do not trust an arbitrary external payload.
    approved = build_render_payload(load_timeline(conn, episode_id), provider)
    if approved != payload:
        raise LongformError("Render payload differs from rights-reviewed SQLite timeline")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 1_500_000:
        raise LongformError("Render payload too large for safe submission")
    digest = hashlib.sha256(raw).hexdigest()
    job_id = hashlib.sha256((episode_id + provider + digest).encode("utf-8")).hexdigest()[:24]
    existing = conn.execute("SELECT status,remote_id FROM render_jobs WHERE id=?",
                            (job_id,)).fetchone()
    if existing:
        raise LongformError("Duplicate paid render blocked: prior job "
                            + job_id + " state=" + str(existing[0]))
    with conn:
        conn.execute(
            "INSERT INTO render_jobs "
            "(id,episode_id,provider,status,request_digest,remote_id,receipt_json,cost_actual,currency)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (job_id,episode_id,provider,"SUBMITTING",digest,None,None,None,"CNY")
        )
    return job_id, raw


def submit(conn, episode_id, provider, payload, *, confirm_paid=False,
           quote_rmb=None, budget_cap_rmb=None, api_key=None, opener=None):
    if provider not in RENDERERS:
        raise LongformError("Unsupported render provider")
    endpoint, env_key, header = RENDERERS[provider]
    token = api_key or os.environ.get(env_key)
    if not token:
        raise LongformError("Missing " + env_key + "; no remote request sent")
    job_id, raw = prepare_submission(
        conn, episode_id, provider, payload, confirm_paid=confirm_paid,
        quote_rmb=quote_rmb, budget_cap_rmb=budget_cap_rmb
    )
    request = urllib.request.Request(
        endpoint, data=raw, headers={header: token, "Content-Type": "application/json"},
        method="POST")
    safe_open = opener or urllib.request.build_opener(NoRedirect()).open
    response = _read_json(safe_open, request)
    if provider == "shotstack":
        remote_id = (response.get("response") or {}).get("id")
    else:
        remote_id = response.get("project")
    if not remote_id or not isinstance(remote_id, str):
        raise LongformError("Unknown provider receipt: no retry; inspect dashboard")
    with conn:
        conn.execute("UPDATE render_jobs SET status=?,remote_id=?,receipt_json=? WHERE id=?",
                     ("SUBMITTED",remote_id,json.dumps(response,ensure_ascii=False),job_id))
    return {"job_id":job_id,"remote_id":remote_id,"provider":provider,
            "status":"SUBMITTED_NOT_PUBLISHED","actual_cost":"UNKNOWN"}



def poll_render(conn, job_id, *, api_key=None, opener=None):
    """Read-only provider poll; never grants editorial approval or publication."""
    row = conn.execute("SELECT provider,remote_id,status FROM render_jobs WHERE id=?",
                       (job_id,)).fetchone()
    if not row or not row[1]:
        raise LongformError("Only remotely submitted render jobs may be polled")
    provider, remote_id, old_status = row
    if old_status not in ("SUBMITTED", "REMOTE_PROCESSING", "RENDERED_AWAITING_QA", "REMOTE_FAILED"):
        raise LongformError("Unsafe remote render status")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{4,128}", remote_id):
        raise LongformError("Unsafe provider task ID")
    endpoint, env_key, header = RENDERERS[provider]
    token = api_key or os.environ.get(env_key)
    if not token:
        raise LongformError("Missing " + env_key)
    if provider == "shotstack":
        url = "https://api.shotstack.io/edit/stage/render/" + remote_id
    else:
        url = "https://api.json2video.com/v2/movies?project=" + remote_id
    request = urllib.request.Request(url, headers={header:token}, method="GET")
    safe_open = opener or urllib.request.build_opener(NoRedirect()).open
    result = _read_json(safe_open, request)
    if provider == "shotstack":
        details = result.get("response") or {}
    else:
        details = result.get("movie") or {}
    remote_status = details.get("status", "")
    if not isinstance(remote_status, str):
        raise LongformError("Malformed remote status")
    if remote_status == "done":
        status = "RENDERED_AWAITING_QA"
    elif remote_status in ("failed", "error", "timeout"):
        status = "REMOTE_FAILED"
    else:
        status = "REMOTE_PROCESSING"
    with conn:
        conn.execute("UPDATE render_jobs SET status=?,receipt_json=? WHERE id=?",
                     (status,json.dumps(result,ensure_ascii=False),job_id))
    return {"job_id":job_id,"provider":provider,"status":status,
            "remote_status":remote_status,"editorial_approval":False,
            "platform_published":False}

def main(argv=None):
    p = argparse.ArgumentParser(description="Explicit paid API render submission")
    p.add_argument("--db", required=True)
    p.add_argument("--episode-id", required=True)
    p.add_argument("--provider", choices=sorted(RENDERERS), required=True)
    p.add_argument("--confirm-paid", action="store_true")
    p.add_argument("--quote-rmb", type=float, required=True)
    p.add_argument("--budget-cap-rmb", type=float, required=True)
    args = p.parse_args(argv)
    try:
        with connection(args.db) as conn:
            approved = build_render_payload(load_timeline(conn, args.episode_id), args.provider)
            result = submit(conn, args.episode_id, args.provider, approved,
                            confirm_paid=args.confirm_paid, quote_rmb=args.quote_rmb,
                            budget_cap_rmb=args.budget_cap_rmb)
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except LongformError as exc:
        p.exit(2,"BLOCKED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
