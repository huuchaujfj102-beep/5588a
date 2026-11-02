"""OneFlow Commercial V3.1: evidence-first competitor research to production handoff.

For public posts observed in a user-authorized browser session. NO crawling,
auto login, captcha handling, platform posting, or inference calls.
All browser observations remain unverified until an editor reviews their URLs.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from .commercial_v3 import requested_channels

DOMAINS = {
    "douyin": ("douyin.com", "iesdouyin.com"),
    "xiaohongshu": ("xiaohongshu.com",),
    "wechat_channels": ("channels.weixin.qq.com", "weixin.qq.com"),
    "kuaishou": ("kuaishou.com", "chenzhongtech.com"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "youtube": ("youtube.com", "youtu.be"),
    "tiktok": ("tiktok.com",),
    "instagram": ("instagram.com",),
    "facebook": ("facebook.com", "fb.watch"),
    "pinterest": ("pinterest.com",),
    "linkedin": ("linkedin.com",),
    "toutiao": ("toutiao.com",),
    "weibo": ("weibo.com", "weibo.cn"),
}
SIGNALS = {"none", "business_contact", "sponsored_post", "shop", "paid_product",
           "official_ad", "unknown"}
FORMAT = {"short_video", "long_video", "carousel", "image_post", "live_replay"}
QUERY_SUFFIXES = ["热门 创意 视频", "商业 广告 视频", "教程 制作 过程", "产品 展示 视频"]


class EvidenceError(ValueError):
    pass


def _date(value):
    try:
        v = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if v.tzinfo is None:
            raise ValueError()
        return v.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        raise EvidenceError("All observations need timezone-aware ISO timestamps") from None


def _safe_url(url, platform):
    if not isinstance(url, str) or len(url) > 1024:
        raise EvidenceError("Invalid/long evidence URL")
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if (p.scheme != "https" or p.username or p.password or p.port or
            not any(host == d or host.endswith("." + d) for d in DOMAINS[platform])):
        raise EvidenceError("Unsupported evidence URL host for " + platform)
    if p.query and any(k in p.query.lower() for k in ("token=", "cookie=", "session=", "auth=")):
        raise EvidenceError("Evidence URL contains access credentials")
    return url


def research_tasks(brief, selected):
    jobs = []
    for platform in selected:
        queries = [brief + " " + q for q in QUERY_SUFFIXES]
        jobs.append({
          "platform": platform,
          "task_status": "BROWSER_RESEARCH_NOT_EXECUTED",
          "scope": "Public competitor posts only, within user's permitted logged-in session",
          "queries": queries,
          "targets": {"unique_creators": 5, "recent_posts": 12,
                      "minimum_for_production_review": 5},
          "required_fields": ["url", "creator", "title", "published_at", "captured_at",
              "format", "hook", "structure", "metrics", "lead_signal"],
          "browser_steps": [
              "User signs in directly to the official platform; never share cookies/passwords",
              "Use authorized browser navigation and search; manually finish slider/CAPTCHA",
              "Open public posts, record URL, date, content structure and visible counts only",
              "Do not scrape private messages, follower lists, hidden APIs, or bulk-export profiles",
              "Research 5 distinct creators where available; note missing/hidden data",
              "Record original public link for each observation; do not infer revenue",
              "Human researcher reviews quality and exports the small JSON evidence dataset"
          ],
          "publishing_access": "NOT_IMPLIED_BY_BROWSER_LOGIN"
        })
    return jobs


def analyze(platform, observations, now=None):
    if platform not in DOMAINS:
        raise EvidenceError("Unknown platform")
    if not isinstance(observations, list) or len(observations) > 250:
        raise EvidenceError("Expected 0..250 observation records")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise EvidenceError("Now must be timezone aware")
    rows, seen = [], set()
    for i, item in enumerate(observations):
        if not isinstance(item, dict):
            raise EvidenceError("Observation record must be an object")
        source = _safe_url(item.get("url"), platform)
        if source in seen:
            raise EvidenceError("Duplicate post evidence URL")
        seen.add(source)
        creator = item.get("creator")
        if not isinstance(creator, str) or not (1 <= len(creator) <= 100):
            raise EvidenceError("Public creator display label required")
        pub = _date(item.get("published_at"))
        cap = _date(item.get("captured_at"))
        if pub > cap + timedelta(days=1) or cap > now + timedelta(days=2):
            raise EvidenceError("Inconsistent published/captured time")
        if item.get("format") not in FORMAT or item.get("lead_signal") not in SIGNALS:
            raise EvidenceError("Invalid format or monetization signal")
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            raise EvidenceError("Metrics must be a dict (empty if hidden)")
        checked = {}
        for m in ("views", "likes", "comments", "saves", "shares"):
            if m in metrics:
                if type(metrics[m]) is not int or metrics[m] < 0:
                    raise EvidenceError("Visible metrics must be nonnegative integers")
                checked[m] = metrics[m]
        for key in ("title", "hook", "structure"):
            if not isinstance(item.get(key), str) or not (1 <= len(item[key]) <= 500):
                raise EvidenceError("Missing public title, hook, or structure")
        signal = item["lead_signal"]
        lead_url = item.get("lead_evidence_url")
        if lead_url:
            # Lead details are an observation, not evidence of a sale or payout.
            _safe_url(lead_url, platform)
        er = None
        if checked.get("views", 0) > 0:
            er = round((checked.get("likes",0) + checked.get("comments",0) +
                checked.get("saves",0) + checked.get("shares",0)) /
                checked["views"], 4)
        rows.append({
            "url":source,"creator":creator,"title":item["title"],
            "format":item["format"],"hook":item["hook"],"structure":item["structure"],
            "published_at":pub.isoformat(),"captured_at":cap.isoformat(),
            "age_days_at_capture":max(0, (cap-pub).days),
            "metrics":checked,"observed_engagement_ratio":er,
            "lead_signal":signal,"lead_evidence_url":lead_url,
            "source_level":"USER_RECORDED_PUBLIC_BROWSER_OBSERVATION_NOT_INDEPENDENTLY_VERIFIED",
            "revenue_verified":False
        })
    recent = [r for r in rows if 0 <= (now-_date(r["published_at"])).days <= 45]
    creators = {r["creator"] for r in recent}
    status = "RESEARCH_READY_FOR_HUMAN_REVIEW" if len(recent)>=5 and len(creators)>=3 else "SAMPLE_INSUFFICIENT"
    by_format = dict(Counter(r["format"] for r in recent))
    hooks = [h for h,count in Counter(r["hook"] for r in recent).most_common(6)]
    business = [r["url"] for r in recent if r["lead_signal"] not in ("none","unknown")]
    return {
      "platform":platform,"status":status,
      "sample_total":len(rows),"recent_45d_posts":len(recent),
      "recent_unique_creators":len(creators),"format_counts":by_format,
      "observed_hooks":hooks,"monetization_signal_post_urls":business,
      "cautions":["Visible public metrics only; unknown views => no comparable ratio",
                  "A business link or sponsorship tag is NOT evidence of sales/profit",
                  "Browser observations remain subject to editorial verification",
                  "Public platform policies and API permissions must be checked separately"],
      "evidence":rows
    }


def build_handoff(brief, report):
    if report["status"] != "RESEARCH_READY_FOR_HUMAN_REVIEW":
        return {"status":"RESEARCH_GAP_BLOCKS_EVIDENCE_BASED_CREATIVE",
                "requested":"Collect >=5 recent posts across >=3 creators",
                "video_generated":False}
    hooks=report["observed_hooks"][:3]
    return {
      "status":"EDITORIAL_CREATIVE_DRAFT_REQUIRES_APPROVAL",
      "video_generated":False,"published":False,
      "market":report["platform"],"source_brief":brief,
      "research_post_urls":[r["url"] for r in report["evidence"]],
      "creative_directions":[
        {"hook_pattern":h,"instruction":"Invent a new ORIGINAL story; do not recreate, download or imitate exact competitors' footage"}
        for h in hooks],
      "oneflow_prompt":(
         brief + "。原创视频策划；参考已取证公开内容的叙事规律，"
         "不得复制他人镜头、台词或品牌；先锁定产品真实外观、商用许可、"
         "人物/物理空间一致性，前3秒明确钩子，展示产品价值，"
         "输出分镜、视觉参考、音效、剪辑及各平台差异版本。"
      ),
      "editor_gate":"VERIFY_EACH_URL_AND_APPROVE_REAL_CONTENT_BEFORE_RENDER"
    }


def write_outputs(brief, selected, out, observed_map=None, now=None):
    dest=Path(out)
    dest.mkdir(parents=True,exist_ok=True)
    tasks=research_tasks(brief,selected)
    (dest/"browser-research-tasks.json").write_text(
        json.dumps({"schema":"oneflow-commercial-v3.1.browser.v1","tasks":tasks},
                   ensure_ascii=False,indent=2),encoding="utf8")
    summaries=[]
    for platform in selected:
        report=analyze(platform,(observed_map or {}).get(platform,[]),now=now)
        summaries.append(report)
        (dest/(platform+"-evidence-report.json")).write_text(
            json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
        (dest/(platform+"-to-production.json")).write_text(
            json.dumps(build_handoff(brief,report),ensure_ascii=False,indent=2),
            encoding="utf8")
    return {"status":"RESEARCH_TASKS_READY_NOT_BROWSER_EXECUTED",
            "platforms":selected,
            "reports":[{"platform":r["platform"],"status":r["status"],
                        "public_posts":r["sample_total"]} for r in summaries]}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Browser research tasks and audited public evidence intake")
    parser.add_argument("--brief",required=True)
    parser.add_argument("--platform",action="append")
    parser.add_argument("--observations",help="private browser research JSON platform_id -> posts[]")
    parser.add_argument("--out",default="commercial-research-preview")
    args=parser.parse_args(argv)
    try:
        chosen,_=requested_channels(args.platform)
        if len(args.brief)<8 or len(args.brief)>3000:
            raise EvidenceError("Brief must be 8-3000 characters")
        data={}
        if args.observations:
            source=Path(args.observations)
            if not source.is_file() or source.stat().st_size > 1_000_000:
                raise EvidenceError("Missing/oversized research observations input")
            data=json.loads(source.read_text(encoding="utf8"))
            if not isinstance(data,dict) or set(data)-set(chosen):
                raise EvidenceError("Research JSON keys must match selected platform IDs")
        print(json.dumps(write_outputs(args.brief,chosen,args.out,data),ensure_ascii=False))
    except (ValueError,OSError,TypeError,EvidenceError) as err:
        print("RESEARCH_BLOCKED:",str(err))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
