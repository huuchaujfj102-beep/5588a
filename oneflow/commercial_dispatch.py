"""Commercial V3 scheduled dispatcher, for an independently authorized publisher.

Never posts without: real immutable video hash, human review, per-item opt-in,
verified account OAuth & app approval AND live user release consent.
Not a cookie/browser automation or a shortcut around platform authorization.
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MANUAL = {"wechat_channels","xiaohongshu"}


class DispatchBlocked(RuntimeError):
    pass


def verified_file(queue):
    asset=queue.get("asset",{})
    file=Path(asset.get("local_path") or "")
    expected=asset.get("sha256")
    if not file.is_file() or file.stat().st_size==0:
        raise DispatchBlocked("Original approved video missing from private storage")
    h=hashlib.sha256()
    with file.open("rb") as f:
        for buf in iter(lambda:f.read(1024*1024),b""):
            h.update(buf)
    if not expected or h.hexdigest()!=expected:
        raise DispatchBlocked("Media checksum mismatch after human review")
    if not asset.get("reviewer") or not asset.get("rights_attested") or not asset.get("visual_review_verified"):
        raise DispatchBlocked("Human visual and rights attestation missing")
    if not expected or not re.fullmatch("[0-9a-f]{64}",expected):
        raise DispatchBlocked("Invalid SHA256")
    return file


def due_items(queue, approval, now):
    if now.tzinfo is None:
        raise DispatchBlocked("Timezone-aware now required")
    allowed=approval.get("per_post_consent",{})
    if not isinstance(allowed,dict):
        raise DispatchBlocked("Per-post consent registry invalid")
    result=[]
    for item in queue.get("per_account",[]):
        if item["platform"] in MANUAL:
            continue
        key=item["account_key"]
        consent=allowed.get(key,{})
        if not (consent.get("account_oauth_verified")
                and consent.get("developer_app_approved")
                and consent.get("creator_authorized_this_post")
                and isinstance(consent.get("approval_reference"),str)
                and len(consent["approval_reference"])>=8):
            continue
        if item.get("published_id") or item.get("published_url"):
            continue
        approved_time=consent.get("scheduled_at")
        try:
            dt=datetime.fromisoformat(approved_time)
        except (ValueError,TypeError):
            continue
        if dt.tzinfo is None or dt.astimezone(timezone.utc)>now.astimezone(timezone.utc):
            continue
        if dt.isoformat() not in item.get("planned_local_times",[]):
            continue
        # Approval is per account AND one time slot; no repeated fan-out.
        result.append((item,consent,dt))
    return result


def send(item, consent, file, sha):
    gateway=os.getenv("ONEFLOW_PUBLISHER_GATEWAY","")
    token=os.getenv("ONEFLOW_PUBLISHER_TOKEN","")
    hostname=os.getenv("ONEFLOW_PUBLISHER_HOSTNAME","")
    parsed=urlparse(gateway)
    if not gateway or parsed.scheme!="https" or parsed.hostname!=hostname or not hostname:
        raise DispatchBlocked("Explicit allowlisted HTTPS publisher gateway required")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("","/"):
        raise DispatchBlocked("Gateway URL must be bare trusted origin")
    if not token:
        raise DispatchBlocked("Publisher bearer credential not configured")
    idempotency=hashlib.sha256((sha+item["account_key"]+consent["scheduled_at"]).encode()).hexdigest()
    # Publisher gateway MUST recheck OAuth/app approval and authorization.
    # The content is a metadata handoff only; upload byte flow requires a separately
    # approved private media store/gateway. Public GitHub Actions never holds video.
    body=json.dumps({
      "platform":item["platform"],"account_key":item["account_key"],
      "approved_asset_sha256":sha,"media_source":"private-media-store",
      "scheduled_at":consent["scheduled_at"],"consent_ref":consent["approval_reference"],
      "title":item["content_brief"][:120],"ai_content_label":item["ai_content_label"],
      "idempotency_key":idempotency,
    },ensure_ascii=False).encode("utf8")
    req=Request(gateway.rstrip("/")+"/publish",data=body,method="POST",
       headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urlopen(req,timeout=45) as response:
            obj=json.loads(response.read(100000))
    except Exception:
        raise DispatchBlocked("Publisher gateway request failed; check provider before retry") from None
    if not isinstance(obj,dict):
        raise DispatchBlocked("Publisher receipt is invalid")
    status=obj.get("status")
    if status=="published" and obj.get("id") and obj.get("url"):
        return {"state":"PUBLISHED_RECEIPT_REPORTED","id":str(obj["id"]),"url":str(obj["url"]),
                "idempotency_key":idempotency}
    if status=="pending" and obj.get("id"):
        return {"state":"PENDING_CONFIRMATION","id":str(obj["id"]),
                "idempotency_key":idempotency}
    raise DispatchBlocked("Publisher returned no accepted receipt")


def dispatch(queue, approval, now, live=False):
    candidates=due_items(queue,approval,now)
    summary={"status":"OFFLINE_ELIGIBILITY_ONLY" if not live else "GATEWAY_HANDOFF_RESULTS",
             "due_eligible":len(candidates),"published":0,
             "pending":0,"results":[],"never_claims_earnings":True}
    if not live:
        return summary
    if not candidates:
        return summary
    media=verified_file(queue)
    for item,consent,_ in candidates:
        resp=send(item,consent,media,queue["asset"]["sha256"])
        summary["results"].append({"account_key":item["account_key"],**resp})
        if resp["state"]=="PUBLISHED_RECEIPT_REPORTED":
            summary["published"]+=1
        else: summary["pending"]+=1
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--queue",required=True)
    parser.add_argument("--consent-registry",required=True)
    parser.add_argument("--out",default="private-inputs/commercial-v3-dispatch-result.json")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--release-consent",action="store_true")
    args=parser.parse_args()
    if args.live and not args.release_consent:
        raise SystemExit("BLOCKED: --release-consent required for live gateway handoff")
    try:
        queue=json.loads(Path(args.queue).read_text(encoding="utf8"))
        consent=json.loads(Path(args.consent_registry).read_text(encoding="utf8"))
        result=dispatch(queue,consent,datetime.now(timezone.utc),live=args.live)
        destination=Path(args.out);destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
        print(json.dumps(result,ensure_ascii=False))
    except (DispatchBlocked,OSError,ValueError,KeyError) as exc:
        raise SystemExit("BLOCKED: "+str(exc)) from None


if __name__=="__main__":
    main()
