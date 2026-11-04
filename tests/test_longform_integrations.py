"""Offline integration tests. Never use paid API keys or generate media."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.longform import (
    LongformError, make_plan, connection, store_plan, attach_asset,
    load_timeline, build_render_payload, public_https
)
from oneflow.longform_renderer import submit, prepare_submission
from oneflow.longform_plugins import local_model_command, lip_sync_command, local_execute


class FakeResponse:
    def __init__(self, data):
        self.body = io.BytesIO(json.dumps(data).encode("utf-8"))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size=-1):
        return self.body.read(size)


class LongformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = connection(self.root / "longform.sqlite")
        self.addCleanup(self.db.close)
        self.plan = make_plan("雨夜借灯", "原创国风悬疑故事：雨夜旧灯笼引出一段家书往事")
        store_plan(self.db, self.plan)

    def bind_all(self):
        for s in self.plan["scenes"]:
            for shot in s["shots"]:
                attach_asset(self.db, shot["id"], "image",
                             "https://media.example.com/approved-art.png",
                             "license-proof-20261104")

    def test_7min_episode_has_exact_420_seconds_and_stable_ids(self):
        self.assertEqual(self.plan["seconds"], 420)
        self.assertEqual(len(self.plan["scenes"]), 7)
        self.assertEqual(sum(s["seconds"] for s in self.plan["scenes"]), 420)
        self.assertGreaterEqual(self.plan["shots_count"], 40)
        self.assertTrue(all(0 < h["seconds"] <= 12
                            for s in self.plan["scenes"] for h in s["shots"]))
        self.assertEqual(self.plan["id"], make_plan(
            "雨夜借灯", "原创国风悬疑故事：雨夜旧灯笼引出一段家书往事")["id"])
        self.assertEqual(self.plan["status"], "PLANNED_OFFLINE_NOT_RENDERED")

    def test_20min_episode_plans_chapters_without_mutating_shortflow(self):
        long = make_plan("国风长篇", "原创国风故事20分钟篇章规划", 1200)
        self.assertEqual(len(long["scenes"]), 16)
        self.assertEqual({s["chapter_no"] for s in long["scenes"]}, {1, 2, 3, 4})
        self.assertEqual(sum(s["seconds"] for s in long["scenes"]), 1200)
        self.assertLessEqual(long["shots_count"], 200)

    def test_rejects_invalid_durations_scene_beats_and_plan_overwrites(self):
        with self.assertRaises(LongformError):
            make_plan("错误", "适当长度的故事", 1201)
        with self.assertRaises(LongformError):
            make_plan("错误", "适当长度的故事", 420, scene_beats=["only one"])
        self.assertFalse(store_plan(self.db, self.plan))
        changed = dict(self.plan, brief="modified")
        with self.assertRaisesRegex(LongformError, "revised plan"):
            store_plan(self.db, changed)

    def test_asset_license_and_https_required(self):
        shot = self.plan["scenes"][0]["shots"][0]["id"]
        for url in ("http://example.com/p.png", "https://localhost/a.png",
                    "https://127.0.0.1/a.png", "https://10.0.0.1/private",
                    "https://user:password@example.com/a.png"):
            with self.assertRaises(LongformError, msg=url):
                attach_asset(self.db, shot, "image", url, "license-proof")
        with self.assertRaises(LongformError):
            attach_asset(self.db, shot, "image", "https://example.com/a.png", "")
        attach_asset(self.db, shot, "image", "https://example.com/a.png", "license-proof")
        with self.assertRaisesRegex(LongformError, "Immutable"):
            attach_asset(self.db, shot, "image", "https://example.com/b.png", "license-proof")

    def test_export_refuses_missing_media(self):
        with self.assertRaisesRegex(LongformError, "rights-reviewed"):
            load_timeline(self.db, self.plan["id"])

    def test_7min_render_payloads_are_offline_and_structurally_sound(self):
        self.bind_all()
        timeline = load_timeline(self.db, self.plan["id"])
        self.assertEqual(timeline["seconds"], 420)
        self.assertEqual(sum(len(s["shots"]) for s in timeline["scenes"]),
                         self.plan["shots_count"])
        shotstack = build_render_payload(timeline, "shotstack")
        clips = shotstack["timeline"]["tracks"][0]["clips"]
        self.assertEqual(len(clips), self.plan["shots_count"])
        self.assertEqual(sum(c["length"] for c in clips), 420)
        self.assertEqual(clips[0]["start"], 0)
        self.assertEqual(clips[-1]["start"] + clips[-1]["length"], 420)
        j2v = build_render_payload(timeline, "json2video")
        self.assertEqual(len(j2v["scenes"]), 7)
        self.assertEqual(sum(s["duration"] for s in j2v["scenes"]), 420)
        for s in j2v["scenes"]:
            self.assertEqual(s["elements"][-1]["start"] +
                             s["elements"][-1]["duration"], s["duration"])

    def test_paid_call_requires_explicit_approval_and_quote(self):
        self.bind_all()
        payload = build_render_payload(load_timeline(self.db, self.plan["id"]), "shotstack")
        with self.assertRaisesRegex(LongformError, "confirm-paid"):
            submit(self.db,self.plan["id"],"shotstack",payload,
                   quote_rmb=4,budget_cap_rmb=10)
        with self.assertRaisesRegex(LongformError, "quote"):
            submit(self.db,self.plan["id"],"shotstack",payload,
                   confirm_paid=True,quote_rmb=15,budget_cap_rmb=10)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM render_jobs").fetchone()[0],0)

    def test_external_payload_tampering_blocked(self):
        self.bind_all()
        payload = build_render_payload(load_timeline(self.db,self.plan["id"]),"shotstack")
        payload["timeline"]["tracks"][0]["clips"][0]["asset"]["src"] = "https://evil.example.net/a.png"
        with self.assertRaisesRegex(LongformError, "differs"):
            prepare_submission(self.db,self.plan["id"],"shotstack",payload,
                               confirm_paid=True,quote_rmb=2,budget_cap_rmb=10)

    def test_fake_cloud_submit_records_receipt_and_duplicate_prevention(self):
        self.bind_all()
        payload = build_render_payload(load_timeline(self.db,self.plan["id"]),"json2video")
        calls = []
        def fake_open(req, timeout=30):
            calls.append(req)
            return FakeResponse({"project":"p-safe-test-id"})
        r=submit(self.db,self.plan["id"],"json2video",payload,confirm_paid=True,
                 quote_rmb=2,budget_cap_rmb=10,api_key="mock-not-real",
                 opener=fake_open)
        self.assertEqual(r["status"],"SUBMITTED_NOT_PUBLISHED")
        self.assertEqual(r["remote_id"],"p-safe-test-id")
        self.assertEqual(len(calls),1)
        self.assertIn("api.json2video.com",calls[0].full_url)
        with self.assertRaisesRegex(LongformError,"Duplicate"):
            submit(self.db,self.plan["id"],"json2video",payload,confirm_paid=True,
                   quote_rmb=2,budget_cap_rmb=10,api_key="mock-not-real",
                   opener=fake_open)
        self.assertEqual(len(calls),1)

    def test_no_api_key_blocks_without_external_request(self):
        self.bind_all()
        payload=build_render_payload(load_timeline(self.db,self.plan["id"]),"shotstack")
        with patch.dict("os.environ",{"SHOTSTACK_API_KEY":""}):
            with self.assertRaisesRegex(LongformError,"Missing SHOTSTACK_API_KEY"):
                submit(self.db,self.plan["id"],"shotstack",payload,confirm_paid=True,
                       quote_rmb=2,budget_cap_rmb=10)

    def test_local_plugins_only_plan_commands_by_default(self):
        model_root=self.root / "svi"
        (model_root / "scripts/test").mkdir(parents=True)
        (model_root / "scripts/test/svi_2.0.sh").write_text("#!/bin/sh\n",encoding="utf-8")
        cmd=local_model_command("svi",model_root)
        result=local_execute(cmd)
        self.assertEqual(result["status"],"PLAN_ONLY")
        with self.assertRaisesRegex(LongformError,"license-checked"):
            local_execute(cmd,execute=True)
        audio=self.root/"voice.wav"
        audio.write_bytes(b"RIFF")
        binary=self.root/"rhubarb"
        binary.write_bytes(b"synthetic test binary")
        cmd=lip_sync_command(audio,self.root/"mouth.json",binary=str(binary))
        self.assertIn("phonetic",cmd)
        self.assertEqual(cmd[-1],str(audio))


if __name__=="__main__":
    unittest.main()
