import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from oneflow.commercial_research import (
    analyze, build_handoff, research_tasks, write_outputs, EvidenceError
)
from oneflow.commercial_campaign import build_campaign, CampaignError

NOW=datetime.now(timezone.utc).replace(microsecond=0)
START=datetime(2026,11,2,9,0,tzinfo=timezone(timedelta(hours=8)))
BRIEF="制作原创未来汽车与中国智能硬件商业广告，通过公开视频对标调研后生成多平台视频"


def records(count=5):
    items=[]
    for i in range(count):
        items.append({
          "url":"https://www.xiaohongshu.com/explore/testpost"+str(i),
          "creator":"Creator"+str(i%3),
          "title":"AI工业广告构思"+str(i),
          "published_at":(NOW-timedelta(days=3+i)).isoformat(),
          "captured_at":NOW.isoformat(),
          "format":"short_video" if i%2==0 else "image_post",
          "hook":"产品开箱反差" if i%2==0 else "制作过程拆解",
          "structure":"前3秒产品钩子→实拍/AI制作对比→结尾成果",
          "metrics":{"likes":50+i,"comments":3+i},
          "lead_signal":"business_contact" if i==0 else "unknown"
        })
    return items


class ResearchTests(unittest.TestCase):
    def test_research_plan_uses_only_public_manual_session(self):
        job=research_tasks(BRIEF,["xiaohongshu"])[0]
        self.assertEqual(job["task_status"],"BROWSER_RESEARCH_NOT_EXECUTED")
        self.assertIn("CAPTCHA"," ".join(job["browser_steps"]))
        self.assertEqual(job["publishing_access"],"NOT_IMPLIED_BY_BROWSER_LOGIN")

    def test_evidence_is_not_economic_proof(self):
        r=analyze("xiaohongshu",records(),now=NOW)
        self.assertEqual(r["status"],"RESEARCH_READY_FOR_HUMAN_REVIEW")
        self.assertEqual(r["recent_45d_posts"],5)
        self.assertEqual(r["recent_unique_creators"],3)
        self.assertEqual(len(r["monetization_signal_post_urls"]),1)
        self.assertTrue(all(not i["revenue_verified"] for i in r["evidence"]))
        self.assertIsNone(r["evidence"][0]["observed_engagement_ratio"])
        handoff=build_handoff(BRIEF,r)
        self.assertEqual(handoff["status"],"EDITORIAL_CREATIVE_DRAFT_REQUIRES_APPROVAL")
        self.assertFalse(handoff["video_generated"])
        self.assertIn("原创",handoff["oneflow_prompt"])

    def test_missing_or_old_data_blocks_evidence_based_claims(self):
        self.assertEqual(analyze("xiaohongshu",records(2),now=NOW)["status"],"SAMPLE_INSUFFICIENT")
        o=records()
        for r in o:
            r["published_at"]=(NOW-timedelta(days=180)).isoformat()
        self.assertEqual(analyze("xiaohongshu",o,now=NOW)["status"],"SAMPLE_INSUFFICIENT")

    def test_wrong_platform_and_secret_urls_blocked(self):
        o=records()
        o[0]["url"]="https://example.com/x"
        with self.assertRaises(EvidenceError):
            analyze("xiaohongshu",o,now=NOW)
        o=records()
        o[0]["url"]+="?token=secret"
        with self.assertRaises(EvidenceError):
            analyze("xiaohongshu",o,now=NOW)
        o=records()
        o[1]["url"]=o[0]["url"]
        with self.assertRaises(EvidenceError):
            analyze("xiaohongshu",o,now=NOW)

    def test_one_sentence_without_browser_does_not_fake_posts_or_video(self):
        with tempfile.TemporaryDirectory() as root:
            c=build_campaign(BRIEF,None,START,root)
            self.assertEqual(c["campaign_status"],"BROWSER_RESEARCH_REQUIRED")
            self.assertEqual(c["accounts_planned"],9)
            self.assertEqual(c["posted_to_platforms"],0)
            self.assertEqual(c["real_videos_generated"],0)
            self.assertTrue((Path(root)/"research"/"xiaohongshu-evidence-report.json").is_file())
            self.assertTrue((Path(root)/"schedules"/"commercial-v3-queue.json").is_file())

    def test_research_needs_human_approval_before_storyboard(self):
        with tempfile.TemporaryDirectory() as root:
            data={"xiaohongshu":records()}
            r=build_campaign(BRIEF,["xiaohongshu"],START,root,evidence=data)
            self.assertEqual(r["campaign_status"],"EVIDENCE_REVIEW_REQUIRED")
            self.assertEqual(r["jobs"],[])
            with self.assertRaises(CampaignError):
                build_campaign(BRIEF,["xiaohongshu"],START,root,
                  evidence=data,research_approved=True)

    def test_reviewed_evidence_creates_real_offline_storyboard_not_media(self):
        with tempfile.TemporaryDirectory() as root:
            data={"xiaohongshu":records()}
            r=build_campaign(BRIEF,["xiaohongshu"],START,root,evidence=data,
                 research_approved=True,editor="审核编辑",seconds=15)
            self.assertEqual(r["campaign_status"],"EDITORIAL_STORYBOARDS_CREATED_NOT_RENDERED")
            self.assertEqual(len(r["jobs"]),1)
            self.assertEqual(r["real_videos_generated"],0)
            p=Path(r["jobs"][0]["job_dir"])
            self.assertTrue((p/"manifest.json").is_file())
            m=json.loads((p/"manifest.json").read_text())
            self.assertEqual(m["seconds"],15)
            self.assertEqual(m["status"],"PLANNED")


if __name__=="__main__":
    unittest.main()
