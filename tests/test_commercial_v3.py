import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from oneflow.commercial_v3 import make_queue, requested_channels, local_schedule, CommercialError
from oneflow.commercial_dispatch import dispatch, DispatchBlocked

START=datetime(2026,11,2,9,0,tzinfo=timezone(timedelta(hours=8)))


class CommercialV3Tests(unittest.TestCase):
    def test_platform_account_count_and_legal_publication_mode(self):
        x=make_queue("为一家中国智能硬件品牌制作可以国际传播的商业创意视频",START)
        self.assertEqual(x["account_count"],9)
        self.assertEqual(len(set(p["platform"] for p in x["per_account"])),8)
        self.assertEqual(x["status"],"OFFLINE_PLAN_ONLY_NO_VIDEO_RENDER_NO_UPLOAD")
        for item in x["per_account"]:
            self.assertIsNone(item["published_id"])
            self.assertIsNone(item["actual_metrics"])
            self.assertEqual(item["state"],"NEEDS_ASSET_AND_HUMAN_REVIEW")
            self.assertTrue(all(datetime.fromisoformat(t).tzinfo is not None for t in item["planned_local_times"]))
        routes={p["platform"]:p["publisher_route"] for p in x["per_account"]}
        self.assertEqual(routes["wechat_channels"],"OFFICIAL_MANUAL_SCHEDULER")
        self.assertEqual(routes["xiaohongshu"],"OFFICIAL_MANUAL_SCHEDULER")
        self.assertEqual(routes["youtube"],"API_AUTHORIZATION_AND_APP_REVIEW_REQUIRED")

    def test_expansion_has_later_channels(self):
        x=make_queue("制作AI工业未来视觉系列和品牌营销短片计划",START,stage="expand")
        self.assertEqual(x["account_count"],16)
        self.assertIn("facebook",set(p["platform"] for p in x["per_account"]))
        self.assertIn("toutiao",set(p["platform"] for p in x["per_account"]))

    def test_unknown_and_missing_rights_fail_closed(self):
        with self.assertRaises(CommercialError):
            make_queue("我要制作未来科幻超跑广告",START,channels=["does_not_exist"])
        with self.assertRaises(CommercialError):
            make_queue("我要制作未来科幻超跑广告",START,reviewer="Director")
        with self.assertRaises(CommercialError):
            make_queue("我要制作未来科幻超跑广告",START,master_sha="a"*64)

    def test_real_asset_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.mp4"
            path.write_bytes(b"simulated non-production fixture only")
            h=hashlib.sha256(path.read_bytes()).hexdigest()
            x=make_queue("设计新能源概念超跑后14秒广告成片",START,
                         source_video=str(path),master_sha=h,
                         rights_attested=True,reviewer="Test Reviewer",
                         channels=["douyin"])
            self.assertTrue(x["asset"]["visual_review_verified"])
            self.assertEqual(x["asset"]["sha256"],h)
            with self.assertRaises(CommercialError):
                make_queue("设计新能源概念超跑后14秒广告成片",START,
                     source_video=str(path),master_sha="b"*64)

    def test_dispatch_never_posts_without_per_item_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.mp4"
            path.write_bytes(b"test file")
            q=make_queue("原创智能硬件商业视频制作项目案例",START,
                 source_video=str(path),rights_attested=True,reviewer="Tester",
                 channels=["douyin","xiaohongshu"])
            x=dispatch(q,{"per_post_consent":{}},START+timedelta(days=7),live=False)
            self.assertEqual(x["due_eligible"],0)
            # Even approval for Xiaohongshu cannot enable unavailable public API.
            xhs=next(i for i in q["per_account"] if i["platform"]=="xiaohongshu")
            dt=xhs["planned_local_times"][0]
            consent={xhs["account_key"]:{
                "account_oauth_verified":True,"developer_app_approved":True,
                "creator_authorized_this_post":True,
                "approval_reference":"TEST-REFERENCE","scheduled_at":dt}}
            self.assertEqual(dispatch(q,{"per_post_consent":consent},
                               START+timedelta(days=7),live=False)["due_eligible"],0)

    def test_even_eligible_item_requires_trusted_gateway(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"video.mp4"
            path.write_bytes(b"content fixture")
            q=make_queue("原创智能硬件商业视频制作项目案例",START,
                 source_video=str(path),rights_attested=True,reviewer="Tester",channels=["youtube"])
            item=q["per_account"][0]
            consent={item["account_key"]:{
                "account_oauth_verified":True,"developer_app_approved":True,
                "creator_authorized_this_post":True,
                "approval_reference":"TEST-REF-1234",
                "scheduled_at":item["planned_local_times"][0]}}
            when=START+timedelta(days=7)
            self.assertEqual(dispatch(q,{"per_post_consent":consent},when)["due_eligible"],1)
            with self.assertRaises(DispatchBlocked):
                dispatch(q,{"per_post_consent":consent},when,live=True)


if __name__=="__main__":
    unittest.main()
