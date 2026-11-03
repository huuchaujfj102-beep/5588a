"""Evidence-informed platform-native creative briefs. No scraping or paid generation.

Editorial hypotheses, not undocumented algorithm rules or guaranteed viral scores.
"""
import argparse
import json
from pathlib import Path

PROFILES = {
 "douyin": {
  "name": "抖音", "duration": 15, "ratio": "9:16",
  "goal": "strong initial retention, shares, follow intent",
  "style": "spectacle and rapid visual reveal",
  "hook": "0-1s: the most powerful acceleration shot immediately; no logo intro",
  "beats": [
   "0-3s: strongest driving action, engine hits, wheel spin clearly visible",
   "3-10s: one surprising continuous low-angle acceleration tracking shot",
   "10-15s: decisive payoff and short original question inviting discussion"
  ],
  "editing": "fast opening, high-impact cuts only when spatially coherent, physical sound before music",
  "title_pattern": "这台未来超跑，起步那一秒有多狠？",
  "metrics": ["3s retention", "average watch time", "completion", "shares", "follows per 1000 plays"],
  "benchmarks": ["罗老师说车", "超哥超车"],
  "sources": ["https://trust.douyin.com/algorithm/", "https://www.chanmama.com/open/authorFansRank.html?cat=%E6%B1%BD%E8%BD%A6&day=202610&type=month"]
 },
 "xiaohongshu": {
  "name": "小红书", "duration": 22, "ratio": "9:16",
  "goal": "search relevance, saves, high-intent follows",
  "style": "visual craft breakdown and useful AI-making process",
  "hook": "0-2s: clear cover/claim 'AI超跑视频怎么做出真实速度感？'",
  "beats": [
   "0-5s: show the finished frame and the exact problem solved",
   "5-15s: original keyframe → wheel motion → road parallax comparison, annotated with real methods",
   "15-22s: show 3 practical production lessons and final polished shot"
  ],
  "editing": "readable overlays, proof of process, restrained sound, no false performance specs",
  "title_pattern": "AI超跑电影感怎么做？3个镜头技巧｜附流程",
  "metrics": ["saves per 1000 impressions", "search impressions", "profile visits", "quality comments", "follows"],
  "benchmarks": ["舒甜的车", "阿鑫撸车屋", "小李爱洗车"],
  "sources": ["https://www.qian-gua.com/rank/category/1/30/20261001/97.html", "https://toobigdata.com/mkt/3899.html"]
 },
 "shipinhao": {
  "name": "视频号", "duration": 27, "ratio": "9:16",
  "goal": "social sharing, meaningful discussion, trusted account follows",
  "style": "mini documentary with human-friendly narration or informative captions",
  "hook": "0-3s: an easy-to-understand statement about why this speed shot feels real",
  "beats": [
   "0-7s: reveal cinematic supercar moment with accessible context",
   "7-20s: explain how design, camera and audio create an illusion of speed",
   "20-27s: emotionally satisfying outro worthy of sharing in a friend group"
  ],
  "editing": "slightly calmer readable rhythm, narrative continuity, avoid manipulative share-bait",
  "title_pattern": "一段未来超跑短片，为什么能拍出电影里的速度感",
  "metrics": ["shares per 1000 views", "comments", "completion", "follows"],
  "benchmarks": ["1号车盟", "工程师说车", "齐宇时间"],
  "sources": ["https://youwant.cn/rank/blogger/1/20261010/13.html"]
 },
 "kuaishou": {
  "name": "快手", "duration": 25, "ratio": "9:16",
  "goal": "authenticity, active discussions, sustained followers",
  "style": "direct, personable craftsmanship reveal; fewer flashy transitions",
  "hook": "0-2s: '这车从静止到冲出去，我把镜头拆开给你看'",
  "beats": [
   "0-6s: straightforward before/after of still versus moving car",
   "6-18s: show tangible wheel rotation, acceleration and production method",
   "18-25s: strongest moving shot and concrete question for fellow enthusiasts"
  ],
  "editing": "honest workshop feel, prominent natural/synthetic disclosed engine sound, clear readable subtitles",
  "title_pattern": "一张图让超跑真正跑起来，关键看这3处",
  "metrics": ["average watch time", "comments", "follower conversion", "repeat viewers"],
  "benchmarks": ["曹野", "玩车女神", "车哥测评"],
  "sources": ["https://www.scribd.com/document/941779136/2025%25E5%25B9%25B4%25E5%25BF%25AB%25E6%2589%258B%25E6%25B1%25BD%25E8%25BD%25A6%25E8%25A1%258C%25E4%25B8%259A%25E6%258A%25A5%25E5%2591%258A-%25E7%25A3%2581%25E5%258A%259B%25E5%25BC%2595%25E6%2593%258E"]
 },
 "youtube": {
  "name": "YouTube Shorts", "duration": 28, "ratio": "9:16",
  "goal": "chose-to-view, engaged views, retention and subscribers",
  "style": "international visual storytelling with concise English screen text",
  "hook": "0-1s: immediate high-speed payoff, caption 'One frame. Real motion?'",
  "beats": [
   "0-7s: a visually novel launch with precise car consistency",
   "7-20s: two clear escalation beats with original explanation of motion physics",
   "20-28s: impressive repeatable payoff and distinctive original creator perspective"
  ],
  "editing": "original English narration or readable captions; no reuse-only platform exports; no borrowed music",
  "title_pattern": "Can AI Make a Supercar Actually Move? | Cinematic Motion Test",
  "metrics": ["chose to view", "engaged views", "average percentage viewed", "subscribers gained"],
  "benchmarks": ["Donut", "carwow", "Supercar Blondie"],
  "sources": ["https://support.google.com/youtube/answer/12942217?co=YOUTUBE._YTVideoType%3Dshorts", "https://support.google.com/youtube/blog/470890423/prioritizing-original-content-on-shorts?hl=en"]
 }
}
ORDER = ("douyin", "xiaohongshu", "shipinhao", "kuaishou", "youtube")


def build(idea, niche="ai_supercar"):
    if not isinstance(idea, str) or not 4 <= len(idea.strip()) <= 6000:
        raise ValueError("Idea must be 4-6000 characters")
    if niche != "ai_supercar":
        raise ValueError("This version only has researched AI supercar niche profiles")
    variants = {}
    for key in ORDER:
        p = PROFILES[key]
        variants[key] = {
            "platform": p["name"], "original_idea": idea.strip(), "duration_seconds": p["duration"],
            "ratio": p["ratio"], "primary_goal": p["goal"], "distinctive_style": p["style"],
            "opening_hook": p["hook"], "scene_plan": p["beats"],
            "editing_and_sound": p["editing"], "suggested_title": p["title_pattern"],
            "performance_metrics": p["metrics"], "research_accounts_to_study": p["benchmarks"],
            "source_urls": p["sources"], "release_status": "NOT_GENERATED",
            "publication_status": "NOT_SUBMITTED",
            "creative_prompt": (
                "Create an ORIGINAL platform-native video about: " + idea.strip() +
                ". Structure: " + " | ".join(p["beats"]) +
                ". Style: " + p["style"] + ". Editing: " + p["editing"] +
                ". Keep the SAME car identity across all shots. No impossible physics, "
                "no cloned voices, no unlicensed footage, no false technical claims."
            )
        }
    return {
        "schema": "oneflow-platform-native-strategy-v1", "status": "EDITORIAL_RESEARCH_DRAFT",
        "niche": niche, "viral_guarantee": False,
        "basis": "Platform-specific test hypotheses plus documented ranking/creator examples; account metrics require ongoing validation.",
        "content_variants": variants
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = build(args.idea)
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    (root / "strategy.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for key, data in result["content_variants"].items():
        (root / (key + "-creative-brief.json")).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared five distinct ORIGINAL video scripts, not generated or published any videos.")


if __name__ == "__main__":
    main()
