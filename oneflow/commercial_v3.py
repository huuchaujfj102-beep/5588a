"""OneFlow Commercial V3: platform strategy + cost-aware publishing queue.

Produces a verified, offline, platform-specific runbook from one sentence.
Never fakes a posted video or treats a PR/CI plan as published content.
A separate, legitimately authorized publisher worker is required for posting.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CATALOG = Path(__file__).with_name("commercial_platforms.json")
CN_TZ = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc
BLOCKED_DOMESTIC = {"wechat_channels","xiaohongshu"}


class CommercialError(ValueError):
    pass


def platforms():
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows = source.get("platform_profiles", [])
    if not rows or len({x["id"] for x in rows}) != len(rows):
        raise CommercialError("Invalid platform catalog")
    return source, {x["id"]: x for x in rows}


def requested_channels(ids, stage="launch"):
    catalog, records = platforms()
    requested = list(dict.fromkeys(ids)) if ids else [
        x["id"] for x in catalog["platform_profiles"]
        if x["p0_accounts" if stage == "launch" else "p1_accounts"] > 0]
    invalid = set(requested) - set(records)
    if invalid:
        raise CommercialError("Unknown platform(s): " + ",".join(sorted(invalid)))
    return requested, records


def local_schedule(start, profile, frequency):
    """Suggested local calendar only, not optimal publishing time or actual platform schedule."""
    tz = CN_TZ if profile["market"] == "CN" else ZoneInfo("America/Los_Angeles")
    if start.tzinfo is None:
        raise CommercialError("Schedule requires a timezone-aware input")
    local = start.astimezone(tz)
    sample_times = profile["trial_local_times"]
    days = [0,2,4,6,1,3,5][:min(max(1,frequency),7)]
    planned = []
    for i, offset in enumerate(days):
        future = (local + timedelta(days=offset)).date()
        hour,minute=map(int,sample_times[i % len(sample_times)].split(":"))
        scheduled = datetime.combine(future,time(hour,minute),tzinfo=tz)
        if scheduled <= local:
            scheduled += timedelta(days=7)
        planned.append(scheduled.isoformat())
    return sorted(planned)


def make_queue(brief, start, channels=None, stage="launch", reviewer=None,
               source_video=None, master_sha=None, ai_label="含有AI生成内容",
               rights_attested=False):
    if not isinstance(brief,str) or not (8 <= len(brief.strip()) <= 3000):
        raise CommercialError("Provide a meaningful one-sentence brief (8-3000 chars)")
    if stage not in ("launch","expand"):
        raise CommercialError("stage must be launch or expand")
    if ai_label not in ("含有AI生成内容","含有虚构演绎内容","含有营销信息"):
        raise CommercialError("Select an applicable content label")
    if start.tzinfo is None:
        raise CommercialError("Schedule must include a timezone offset")
    selection, profiles = requested_channels(channels,stage)
    if source_video:
        file = Path(source_video)
        if not file.is_file() or file.suffix.lower() not in (".mp4",".mov",".webm"):
            raise CommercialError("Verified local MP4/MOV/WEBM required, never dummy placeholders")
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if master_sha and actual != master_sha.lower():
            raise CommercialError("Asset hash mismatch, approval invalid")
        master_sha = actual
    elif master_sha:
        raise CommercialError("Cannot claim a verified hash without the media file")
    if reviewer and not rights_attested:
        raise CommercialError("Signoff requires rights attestation")
    if reviewer and not source_video:
        raise CommercialError("Cannot approve a production without real media")
    rows = []
    for pid in selection:
        p = profiles[pid]
        count = p["p0_accounts" if stage=="launch" else "p1_accounts"]
        if count == 0:
            continue
        mode = p["posting_mode"]
        for index in range(1,count+1):
            account_key = f"{pid}-A{index:02d}"
            times = local_schedule(start,p,min(p["week_posts_per_account"],7))
            # All platforms initially NEED external authorization / manual confirmation.
            # Even with a vetted master, exact app-user OAuth and consent must be checked.
            if pid in BLOCKED_DOMESTIC:
                delivery="OFFICIAL_MANUAL_SCHEDULER"
            else:
                delivery="API_AUTHORIZATION_AND_APP_REVIEW_REQUIRED"
            rows.append({
                "account_key":account_key,"platform":pid,"brand":p["brands"][min(index-1,len(p["brands"])-1)],
                "content_brief":brief,"planned_local_times":times,
                "formats":p["formats"],"hook":p["anchor"],
                "launch_playbook":p["launch"],"first_30d_hypothesis":p["trial_30d_target"],
                "monetization":p["monetization"],
                "publisher_route":delivery,
                "api_docs":p["publish_docs"],
                "ai_content_label":ai_label,"required_checks":p["constraints"],
                "state":"PUBLISH_PACKAGE_ONLY" if reviewer else "NEEDS_ASSET_AND_HUMAN_REVIEW",
                "published_id":None,"published_url":None,"actual_metrics":None,
                "actual_cost_cny":None
            })
    return {
      "schema":"oneflow-commercial-v3.queue.v1",
      "created_at_utc":datetime.now(UTC).isoformat(),
      "status":"OFFLINE_PLAN_ONLY_NO_VIDEO_RENDER_NO_UPLOAD",
      "stage":stage,"brief":brief,
      "asset": {"local_path":str(Path(source_video).resolve()) if source_video else None,
                "sha256":master_sha,"rights_attested":bool(rights_attested),
                "reviewer":reviewer,"visual_review_verified":bool(reviewer and source_video and rights_attested)},
      "release_gate":"BLOCKED_UNTIL_PER_ACCOUNT_OAUTH_FINAL_CONSENT_AND_OFFICIAL_RECEIPT",
      "account_count":len(rows),"per_account":rows
    }


def write_queue(out, data):
    root=Path(out)
    root.mkdir(parents=True,exist_ok=True)
    (root/"commercial-v3-queue.json").write_text(
       json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
    lines=["# OneFlow Commercial V3 - platform operations", "",
      "STATUS: OFFLINE PLAN ONLY; NOT posted to any platform", "",
      "Brief: "+data["brief"], "",
      "Total accounts: "+str(data["account_count"]), ""]
    for p in data["per_account"]:
        lines += ["## "+p["account_key"]+" — "+p["brand"],"",
          "Content: "+p["formats"][0],"Hook: "+p["hook"],
          "Launch: "+p["launch_playbook"],
          "Times (LOCAL): "+", ".join(p["planned_local_times"]),
          "Publication: "+p["publisher_route"],
          "Conversion: "+" / ".join(p["monetization"]),
          "Official rules: "+p["api_docs"],""]
    (root/"commercial-v3-operations.md").write_text("\n".join(lines),encoding="utf8")
    return root


def main(argv=None):
    ap=argparse.ArgumentParser(description="One sentence -> all-platform operating plan; NO publishing")
    ap.add_argument("--brief",required=True)
    ap.add_argument("--stage",choices=("launch","expand"),default="launch")
    ap.add_argument("--platform",action="append")
    ap.add_argument("--start",default="2026-11-02T09:00:00+08:00")
    ap.add_argument("--source-video")
    ap.add_argument("--source-sha256")
    ap.add_argument("--reviewer")
    ap.add_argument("--rights-attested",action="store_true")
    ap.add_argument("--ai-label",default="含有AI生成内容")
    ap.add_argument("--out",default="commercial-v3-preview")
    args=ap.parse_args(argv)
    try:
        data=make_queue(args.brief,datetime.fromisoformat(args.start),
          channels=args.platform,stage=args.stage,reviewer=args.reviewer,
          source_video=args.source_video,master_sha=args.source_sha256,
          rights_attested=args.rights_attested,ai_label=args.ai_label)
        path=write_queue(args.out,data)
        print(json.dumps({"status":data["status"],"account_count":data["account_count"],
                          "out":str(path),"platforms":len(set(p["platform"] for p in data["per_account"]))},
                         ensure_ascii=False))
    except (CommercialError,OSError,ValueError) as exc:
        print("COMMERCIAL_V3_BLOCKED:",str(exc))
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
