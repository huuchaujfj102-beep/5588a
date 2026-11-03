"""Seven-clip Muse orchestration tests: NO network and NO provider billing."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.core import FlowError, load_json, save_json
from oneflow.muse_35s import SEGMENTS, TOTAL_SECONDS, make_35s, _bridge_prompt


class Muse35sTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.frame = self.base / "first.png"
        self.frame.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"x" * 120)
        self.idea = "One graphite silver supercar races down a sunset mountain road"

    def test_no_consent_means_zero_submissions(self):
        with patch("oneflow.muse_35s.i2v.submit_once") as submit:
            with self.assertRaisesRegex(FlowError, "confirm-seven-paid"):
                make_35s(self.idea, self.frame, self.base / "out")
            submit.assert_not_called()

    def test_all_seven_prompts_unique_and_short(self):
        prompts = [_bridge_prompt(n, self.idea) for n in range(1, 8)]
        self.assertEqual(len(set(prompts)), 7)
        self.assertTrue(all(len(prompt) <= 925 for prompt in prompts))
        self.assertIn("CONTINUE", prompts[1] if "CONTINUE" in prompts[1] else prompts[1].replace("Continue", "CONTINUE"))

    def test_seven_sequential_real_frame_handoffs_mocked(self):
        calls = []
        def submitted(job, *, confirm_paid):
            self.assertTrue(confirm_paid)
            calls.append(job)
            m = load_json(job / "manifest.json")
            m["qianfan_i2v"]["task_id"] = "task" + str(len(calls))
            m["qianfan_i2v"]["status"] = "created"
            save_json(job / "manifest.json", m)

        def completed(job):
            m = load_json(job / "manifest.json")
            m["status"] = "AWAITING_HUMAN_REVIEW"
            m["qianfan_i2v"]["status"] = "FINALIZED"
            save_json(job / "manifest.json", m)
            media = job / "media"
            media.mkdir(exist_ok=True)
            (media / "S01-qianfan-raw.mp4").write_bytes(b"video" * 150)
            (media / "original-engine-synth.wav").write_bytes(b"audio" * 150)
            return "AWAITING_HUMAN_REVIEW"

        def tail(video, output):
            self.assertTrue(Path(video).is_file())
            Path(output).write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"t" * 200)

        def portrait(raw, output):
            Path(output).write_bytes(b"portrait" * 100)
            return Path(output)

        def joined(film, manifest, cfg):
            self.assertEqual(len(manifest["shots"]), 7)
            self.assertEqual(sum(s["seconds"] for s in manifest["shots"]), 35)
            self.assertEqual(manifest["ratio"], "9:16")
            out = film / "final-draft.mp4"
            out.write_bytes(b"final movie" * 100)
            return out

        def qc(film, manifest, cfg, movie):
            save_json(film / "qc.json", {"status": "REVIEW_REQUIRED"})
            return {"status": "REVIEW_REQUIRED"}

        with patch("oneflow.muse_35s.i2v.submit_once", side_effect=submitted), \
             patch("oneflow.muse_35s.i2v.resume", side_effect=completed), \
             patch("oneflow.muse_35s.last_frame", side_effect=tail) as tail_fn, \
             patch("oneflow.muse_35s._portrait_from_square", side_effect=portrait) as portrait_fn, \
             patch("oneflow.muse_35s.assemble", side_effect=joined), \
             patch("oneflow.muse_35s.audit", side_effect=qc), \
             patch("oneflow.muse_35s.i2v._watermark_mp4"):
            out = self.base / "out"
            film = make_35s(self.idea, self.frame, out, confirm_seven_paid=True)
        self.assertEqual(len(calls), SEGMENTS)
        self.assertEqual(tail_fn.call_count, SEGMENTS - 1)
        self.assertEqual(portrait_fn.call_count, SEGMENTS)
        progress = load_json(out / "progress.json")
        self.assertEqual(progress["expected_total_seconds"], TOTAL_SECONDS)
        self.assertEqual(progress["publication_status"], "NOT_SUBMITTED")
        self.assertEqual([p["task_id"] for p in progress["parts"]],
                         ["task" + str(i) for i in range(1, 8)])
        self.assertEqual(load_json(film / "manifest.json")["source_provenance"]["real_end_frame_bridge_count"], 6)
        self.assertEqual(load_json(film / "manifest.json")["status"], "AWAITING_HUMAN_REVIEW")
        self.assertTrue((film / "release-package" / "douyin.json").is_file())

    def test_failure_midstream_halts_without_duplicate_post(self):
        calls = []
        def fail_at_third(job, *, confirm_paid):
            calls.append(job)
            if len(calls) == 3:
                raise FlowError("Provider uncertain")
            m = load_json(job / "manifest.json")
            m["qianfan_i2v"]["task_id"] = "task" + str(len(calls))
            save_json(job / "manifest.json", m)

        def done(job):
            m = load_json(job / "manifest.json")
            m["status"] = "AWAITING_HUMAN_REVIEW"
            save_json(job / "manifest.json", m)
            media = job / "media"
            media.mkdir(exist_ok=True)
            (media / "S01-qianfan-raw.mp4").write_bytes(b"video" * 150)
            return "AWAITING_HUMAN_REVIEW"

        def tail(src, dest):
            Path(dest).write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"x" * 200)
        root = self.base / "work"
        with patch("oneflow.muse_35s.i2v.submit_once", side_effect=fail_at_third), \
             patch("oneflow.muse_35s.i2v.resume", side_effect=done), \
             patch("oneflow.muse_35s.last_frame", side_effect=tail):
            with self.assertRaisesRegex(FlowError, "Provider uncertain"):
                make_35s(self.idea, self.frame, root, confirm_seven_paid=True)
        self.assertEqual(len(calls), 3)
        ledger = load_json(root / "progress.json")
        self.assertEqual(len(ledger["parts"]), 3)
        self.assertEqual(ledger["parts"][2]["state"], "SUBMISSION_UNCERTAIN")
        self.assertEqual(ledger["status"], "STOPPED_RECONCILE_BILLING")
        with patch("oneflow.muse_35s.i2v.submit_once") as submit:
            with self.assertRaisesRegex(FlowError, "do NOT restart"):
                make_35s(self.idea, self.frame, root, confirm_seven_paid=True)
            submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
