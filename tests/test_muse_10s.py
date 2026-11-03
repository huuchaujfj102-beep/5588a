"""No paid provider calls: the entire two-part orchestrator is mocked."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from oneflow.core import load_json
from oneflow.muse_10s import make_10s, FlowError


class Muse10sTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.frame = self.base / "start.png"
        self.frame.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"a" * 120)

    def test_requires_explicit_consent_for_two_paid_tasks(self):
        with patch("oneflow.muse_10s.i2v.submit_once") as submit:
            with self.assertRaisesRegex(FlowError, "confirm-two-paid"):
                make_10s("supercar racing", str(self.frame), self.base / "out")
            submit.assert_not_called()

    def test_mocked_two_sequential_tasks_and_handoff(self):
        out = self.base / "out"
        counter = []
        def fake_submit(job, *, confirm_paid=False):
            self.assertTrue(confirm_paid)
            counter.append(job)
        def fake_resume(job):
            from oneflow.core import save_json
            m = load_json(job / "manifest.json")
            m["qianfan_i2v"]["task_id"] = "simulated-" + str(len(counter))
            m["status"] = "AWAITING_HUMAN_REVIEW"
            save_json(job / "manifest.json", m)
            (job / "media").mkdir(exist_ok=True)
            (job / "media" / "S01-qianfan-raw.mp4").write_bytes(b"test raw clip" * 100)
            (job / "media" / "original-engine-synth.wav").write_bytes(b"test audio" * 100)
            return "AWAITING_HUMAN_REVIEW"
        def fake_tail(video, png):
            self.assertTrue(Path(video).exists())
            Path(png).write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"x" * 90)
        def fake_assemble(job, manifest, cfg):
            self.assertEqual(len(manifest["shots"]), 2)
            self.assertEqual(sum(s["seconds"] for s in manifest["shots"]), 10)
            output = job / "final-draft.mp4"
            output.write_bytes(b"movie" * 100)
            return output
        def fake_audit(job, manifest, cfg, video):
            from oneflow.core import save_json
            save_json(job / "qc.json", {"status": "REVIEW_REQUIRED"})
            return {"status": "REVIEW_REQUIRED"}

        with patch("oneflow.muse_10s.i2v.submit_once", side_effect=fake_submit), \
             patch("oneflow.muse_10s.i2v.resume", side_effect=fake_resume), \
             patch("oneflow.muse_10s.last_frame", side_effect=fake_tail), \
             patch("oneflow.muse_10s.assemble", side_effect=fake_assemble), \
             patch("oneflow.muse_10s.audit", side_effect=fake_audit), \
             patch("oneflow.muse_10s.i2v._watermark_mp4"):
            movie = make_10s("One silver supercar speeds forward", str(self.frame),
                             out, confirm_two_paid=True)
        self.assertEqual(len(counter), 2)
        manifest = load_json(movie / "manifest.json")
        self.assertEqual(manifest["seconds"], 10)
        self.assertTrue(manifest["source_provenance"]["not_native_10s"])
        self.assertEqual(manifest["source_provenance"]["two_real_muse_tasks"],
                         ["simulated-1", "simulated-2"])
        self.assertEqual(manifest["status"], "AWAITING_HUMAN_REVIEW")
        self.assertEqual(load_json(out / "progress.json")["publication_status"], "NOT_SUBMITTED")
        self.assertTrue((out / "S02-tail.png").is_file())
        self.assertTrue((movie / "release-package" / "douyin.json").is_file())

    def test_do_not_restart_nonempty_root(self):
        out = self.base / "out"
        out.mkdir()
        (out / "progress.json").write_text("already started")
        with patch("oneflow.muse_10s.i2v.submit_once") as submit:
            with self.assertRaisesRegex(FlowError, "already exists"):
                make_10s("Supercar launches immediately", str(self.frame), out,
                         confirm_two_paid=True)
            submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
