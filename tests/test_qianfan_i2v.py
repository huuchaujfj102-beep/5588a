"""Offline and CPU-only Qianfan OneFlow I2V tests. No billed requests."""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.core import FlowError, config, load_json
from oneflow.qianfan_i2v import (
    _image_data_uri, _fetch_video, build_prompt, plan, resume, submit_once,
)
from oneflow.qianfan_media import MediaTaskError


class QianfanI2VTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _plan(self, **options):
        defaults = dict(brief="超跑从静止立即启动、车轮转动并在夕阳公路上加速疾驰",
                        first_frame="https://example.com/public-supercar.png",
                        out_root=self.root, model="VQ2-Turbo",
                        sound="synthetic", enable_watermark=False)
        defaults.update(options)
        return plan(**defaults)

    def test_plan_never_pays_and_tracks_reference(self):
        with patch("oneflow.qianfan_i2v.submit") as paid:
            job = self._plan(platforms=("douyin", "youtube"))
            data = load_json(job / "manifest.json")
            self.assertEqual(data["status"], "PLANNED")
            self.assertEqual(len(data["shots"]), 1)
            self.assertIsNone(data["qianfan_i2v"]["task_id"])
            self.assertEqual(data["qianfan_i2v"]["source"]["mode"], "remote_public")
            self.assertEqual(data["qianfan_i2v"]["estimated_model_cost_rmb"], 1.25)
            self.assertEqual(data["platforms"], ["douyin", "youtube"])
            paid.assert_not_called()

    def test_native_10_and_15_second_single_shot_plans(self):
        for seconds, model in ((10, "VQ2-Turbo"), (10, "VQ3-Turbo"),
                               (15, "VQ3-Turbo"), (15, "VQ3-Pro"), (15, "VQ4")):
            with self.subTest(seconds=seconds, model=model):
                job = self._plan(seconds=seconds, model=model)
                m = load_json(job / "manifest.json")
                self.assertEqual(len(m["shots"]), 1)
                self.assertEqual(m["shots"][0]["seconds"], seconds)
                self.assertTrue(m["native_single_clip"])
                self.assertEqual(m["qianfan_i2v"]["status"], "PLANNED")
                self.assertIsNone(m["qianfan_i2v"]["task_id"])

    def test_invalid_long_model_fails_before_paid_submit(self):
        for seconds, model in ((15, "VQ2-Turbo"), (15, "musesteamer-air-i2v"),
                               (10, "musesteamer-air-i2v")):
            with self.subTest(seconds=seconds, model=model):
                with patch("oneflow.qianfan_i2v.submit") as paid:
                    with self.assertRaises(FlowError):
                        self._plan(seconds=seconds, model=model)
                    paid.assert_not_called()

    def test_one_15s_task_only_no_stitched_paid_requests(self):
        job = self._plan(seconds=15, model="VQ3-Turbo", sound="embedded")
        response = {"task_id": "native15abc", "status": "created"}
        with patch("oneflow.qianfan_i2v.submit", return_value=response) as paid:
            submit_once(job, confirm_paid=True)
            paid.assert_called_once()
            self.assertEqual(paid.call_args.kwargs["duration"], 15)
            self.assertTrue(paid.call_args.kwargs["audio"])
            with self.assertRaises(FlowError):
                submit_once(job, confirm_paid=True)

    def test_explicit_paid_is_required(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit") as paid:
            with self.assertRaisesRegex(FlowError, "confirm-paid"):
                submit_once(job)
            paid.assert_not_called()
        self.assertEqual(load_json(job / "manifest.json")["status"], "PLANNED")

    def test_paid_submit_only_once_and_task_persisted(self):
        job = self._plan()
        response = {"task_id": "video123", "status": "created", "model": "VQ2-Turbo"}
        with patch("oneflow.qianfan_i2v.submit", return_value=response) as paid:
            submit_once(job, confirm_paid=True)
            self.assertEqual(paid.call_count, 1)
            self.assertEqual(paid.call_args.kwargs["prompt"].count("accelerates fast"), 1)
            self.assertEqual(paid.call_args.kwargs["audio"], False)
            self.assertTrue(paid.call_args.kwargs["allow_paid"])
            with self.assertRaisesRegex(FlowError, "already attempted"):
                submit_once(job, confirm_paid=True)
            paid.assert_called_once()
        data = load_json(job / "manifest.json")
        self.assertEqual(data["qianfan_i2v"]["task_id"], "video123")
        self.assertEqual(data["status"], "VIDEO_PENDING")

    def test_uncertain_submit_never_auto_resubmits(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit", side_effect=MediaTaskError("HTTP 403")) as paid:
            with self.assertRaises(MediaTaskError):
                submit_once(job, confirm_paid=True)
            with self.assertRaisesRegex(FlowError, "already attempted"):
                submit_once(job, confirm_paid=True)
            self.assertEqual(paid.call_count, 1)
        data = load_json(job / "manifest.json")
        self.assertEqual(data["qianfan_i2v"]["status"], "SUBMISSION_UNCERTAIN")
        self.assertIsNone(data["qianfan_i2v"]["task_id"])

    def test_resume_without_known_id_cannot_post(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit") as paid:
            with self.assertRaisesRegex(FlowError, "No confirmed task ID"):
                resume(job)
            paid.assert_not_called()

    def test_resume_pending_has_no_paid_post(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit", return_value={
                "task_id": "vid124", "status": "created"}):
            submit_once(job, confirm_paid=True)
        with patch("oneflow.qianfan_media.wait_for_task", return_value={
                "task_id": "vid124", "status": "processing", "result_urls": []}):
            self.assertEqual(resume(job), "VIDEO_PENDING")
        self.assertEqual(load_json(job / "manifest.json")["status"], "VIDEO_PENDING")

    def test_local_reference_data_uri_keeps_bytes_private(self):
        png = self.root / "first.png"
        png.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"x" * 100)
        encoded = _image_data_uri(png)
        self.assertTrue(encoded.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(encoded.split(",", 1)[1]), png.read_bytes())
        job = self._plan(first_frame=str(png))
        manifest = load_json(job / "manifest.json")
        self.assertEqual(manifest["qianfan_i2v"]["source"]["mode"], "local")
        self.assertNotIn("base64", (job / "manifest.json").read_text())

    def test_url_guardrails_and_motion(self):
        for value in ["http://example.com/a.jpg",
                      "https://example.com/private.jpg?token=secret",
                      "javascript:alert(1)"]:
            with self.subTest(value=value):
                with self.assertRaises(FlowError):
                    self._plan(first_frame=value)
        p = build_prompt("超跑启动、加速、飞驰")
        self.assertIn("ROTATE", p)
        self.assertIn("FORWARD", p)
        self.assertIn("no morphing", p)

    def test_embedded_audio_model_selection(self):
        with self.assertRaisesRegex(FlowError, "requires VQ3"):
            self._plan(sound="embedded")
        job = self._plan(sound="embedded", model="VQ3-Turbo")
        with patch("oneflow.qianfan_i2v.submit", return_value={
                "task_id": "v123", "status": "created"}) as paid:
            submit_once(job, confirm_paid=True)
            self.assertEqual(paid.call_args.kwargs["audio"], True)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg and FFprobe required for actual CPU-only media test")
    def test_real_synthetic_clip_audit_and_release_package(self):
        # Run the actual "造镜者" drifting watermark filter, too.
        job = self._plan(platforms=("douyin",), enable_watermark=True)
        with patch("oneflow.qianfan_i2v.submit", return_value={
                "task_id": "vid125", "status": "created"}):
            submit_once(job, confirm_paid=True)
        def fake_download(url, path):
            path = Path(path)
            path.parent.mkdir(exist_ok=True, parents=True)
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-f", "lavfi", "-i",
                 "color=c=black:s=320x180:r=24:d=5.3",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
                check=True, timeout=60, capture_output=True)
            return path
        completed = {"task_id": "vid125", "status": "success",
                     "result_urls": ["https://cdn.example.com/video.mp4"]}
        with patch("oneflow.qianfan_media.wait_for_task", return_value=completed):
            status = resume(job, fetcher=fake_download)
        self.assertEqual(status, "AWAITING_HUMAN_REVIEW")
        d = load_json(job / "manifest.json")
        self.assertEqual(d["approval"], None)
        self.assertTrue((job / d["render"]).is_file())
        self.assertTrue((job / "release-package" / "douyin.json").is_file())
        self.assertEqual(load_json(job / "qc.json")["status"], "REVIEW_REQUIRED")
        self.assertEqual(d["qianfan_i2v"]["status"], "FINALIZED")
        with patch("oneflow.qianfan_i2v.submit") as paid:
            self.assertEqual(resume(job), "AWAITING_HUMAN_REVIEW")
            paid.assert_not_called()


if __name__ == "__main__":
    unittest.main()
