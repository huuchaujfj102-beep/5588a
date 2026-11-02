"""MuseSteamer Air API contract tests, completely offline and non-billable.

Sources: https://cloud.baidu.com/doc/qianfan-api/s/Amg0lgcx4
         https://cloud.baidu.com/doc/qianfan-api/s/Bmg0ma4hf
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.qianfan_media import (
    MUSE_ENDPOINT, MUSE_MODEL, MediaTaskError, submit, task_status, wait_for_task,
)
from oneflow.qianfan_i2v import plan, submit_once, resume
from oneflow.core import FlowError, load_json


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def answer(data):
    return FakeResponse(json.dumps(data).encode("utf-8"))


class MuseSteamerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _plan(self, **kw):
        defaults = dict(
            brief="同一辆超跑立即起步，沿夕阳公路加速前进",
            first_frame="https://example.com/approved-vehicle.png",
            seconds=5, model=MUSE_MODEL, resolution="720p",
            sound="synthetic", out_root=self.root,
            enable_watermark=False, platforms=("douyin",),
        )
        defaults.update(kw)
        return plan(**defaults)

    def test_no_paid_generation_without_confirm(self):
        with patch("oneflow.qianfan_i2v.submit") as billable:
            job = self._plan()
            self.assertEqual(load_json(job / "manifest.json")["status"], "PLANNED")
            self.assertEqual(load_json(job / "manifest.json")["qianfan_i2v"]["estimated_model_cost_rmb"], 1.0)
            with self.assertRaisesRegex(FlowError, "confirm-paid"):
                submit_once(job)
            billable.assert_not_called()

    def test_muse_uses_dedicated_endpoint_schema_without_vq_extras(self):
        requests = []
        def fake(req, timeout):
            requests.append(req)
            return answer({"id": "as-abcd", "task_id": "task123"})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "test-only"}):
            result = submit("video", model=MUSE_MODEL, prompt="车轮转动向前冲",
                            image_url="https://example.com/car.png",
                            resolution="720p", duration=5, allow_paid=True,
                            transport=fake)
        self.assertEqual(result["task_id"], "task123")
        self.assertEqual(result["status"], "created")
        self.assertEqual(len(requests), 1)
        req = requests[0]
        self.assertEqual(req.full_url, MUSE_ENDPOINT)
        self.assertEqual(req.get_method(), "POST")
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], MUSE_MODEL)
        self.assertEqual(payload["content"][0], {"type": "text", "text": "车轮转动向前冲"})
        self.assertEqual(payload["content"][1]["image_url"]["url"], "https://example.com/car.png")
        self.assertEqual(payload["duration"], 5)
        self.assertFalse(payload["watermark"])
        self.assertFalse(payload["prompt_extend"])
        self.assertNotIn("model_parameters", payload)
        self.assertNotIn("resolution", payload)
        self.assertNotIn("type", payload)

    def test_air_status_and_download_field(self):
        urls = []
        def fake(req, timeout):
            urls.append((req.get_method(), req.full_url))
            return answer({"task_id": "task123", "model": MUSE_MODEL,
                           "status": "succeeded",
                           "content": {"video_url": "https://cdn.example.com/clip.mp4"}})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "test-only"}):
            got = task_status("video", "task123", model=MUSE_MODEL, transport=fake)
        self.assertEqual(got["status"], "succeeded")
        self.assertEqual(got["result_urls"], ["https://cdn.example.com/clip.mp4"])
        self.assertEqual(urls, [("GET", MUSE_ENDPOINT + "?task_id=task123")])

    def test_air_pending_polling_never_reposts(self):
        count = 0
        requests = []
        def fake(req, timeout):
            nonlocal count
            count += 1
            requests.append(req.get_method())
            return answer({"status": "running" if count == 1 else "succeeded",
                           "content": {"video_url": "https://cdn.example.com/x.mp4"} if count > 1 else {}})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "test-only"}):
            got = wait_for_task("video", "task123", model=MUSE_MODEL, attempts=2,
                                delay=0, sleep_fn=lambda _: None, transport=fake)
        self.assertEqual(got["status"], "succeeded")
        self.assertEqual(requests, ["GET", "GET"])

    def test_bad_air_configuration_rejected_before_network(self):
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "test-only"}):
            with patch("oneflow.qianfan_media._safe_open") as net:
                for changes in ({"duration": 4}, {"audio": True},
                                {"image_url": "http://example.com/car.png"}):
                    settings = dict(model=MUSE_MODEL, prompt="car drives",
                                    image_url="https://example.com/car.png",
                                    duration=5, resolution="720p", audio=False,
                                    allow_paid=True)
                    settings.update(changes)
                    with self.assertRaises(MediaTaskError):
                        submit("video", **settings)
                net.assert_not_called()
        with self.assertRaisesRegex(FlowError, "exactly 5"):
            self._plan(seconds=4)
        with self.assertRaisesRegex(FlowError, "requires VQ3"):
            self._plan(sound="embedded")

    def test_air_single_paid_post_and_uncertain_no_retry(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit", return_value={
                "task_id": "good_task", "status": "created"}) as paid:
            submit_once(job, confirm_paid=True)
            self.assertEqual(paid.call_count, 1)
            self.assertEqual(paid.call_args.kwargs["model"], MUSE_MODEL)
            with self.assertRaisesRegex(FlowError, "already attempted"):
                submit_once(job, confirm_paid=True)
        job2 = self._plan(brief="另一辆虚构超跑沿赛道行驶")
        with patch("oneflow.qianfan_i2v.submit",
                   side_effect=MediaTaskError("Qianfan API HTTP 403")) as paid:
            with self.assertRaises(MediaTaskError):
                submit_once(job2, confirm_paid=True)
            with self.assertRaisesRegex(FlowError, "already attempted"):
                submit_once(job2, confirm_paid=True)
            self.assertEqual(paid.call_count, 1)


    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg/FFprobe required for real CPU-only assembly test")
    def test_muse_succeeded_finalizes_real_local_mp4_and_douyin_package(self):
        job = self._plan()
        with patch("oneflow.qianfan_i2v.submit", return_value={
                "task_id": "muse123", "status": "created"}):
            submit_once(job, confirm_paid=True)

        def fake_download(url, target):
            target = Path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=5",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target),
            ], check=True, capture_output=True, timeout=90)
            return target

        with patch("oneflow.qianfan_media.wait_for_task", return_value={
                "task_id": "muse123", "status": "succeeded",
                "result_urls": ["https://cdn.example.com/muse.mp4"]}):
            result = resume(job, fetcher=fake_download, watermark=False)
        self.assertEqual(result, "AWAITING_HUMAN_REVIEW")
        manifest = load_json(job / "manifest.json")
        self.assertEqual(manifest["qianfan_i2v"]["status"], "FINALIZED")
        self.assertTrue((job / manifest["render"]).exists())
        self.assertTrue((job / "release-package" / "douyin.json").exists())
        self.assertEqual(load_json(job / "qc.json")["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
