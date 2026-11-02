"""All Qianfan media tests are mock-only: no network, no model charges."""
import io
import json
import os
import unittest
from unittest.mock import patch
from oneflow.qianfan_media import (
    IMAGE_ENDPOINT, VIDEO_ENDPOINT, MediaTaskError,
    submit, task_status, wait_for_task,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def json_response(value):
    return FakeResponse(json.dumps(value).encode("utf-8"))


class MediaTests(unittest.TestCase):
    def test_no_paid_opt_in_no_network(self):
        with patch("urllib.request.urlopen") as call:
            for kind, model in (("image", "o1-base"), ("video", "VQ2-Turbo")):
                with self.assertRaisesRegex(MediaTaskError, "allow_paid"):
                    submit(kind, prompt="supercar", model=model)
            call.assert_not_called()

    def test_image_submission_schema(self):
        calls = []
        def fake(req, timeout):
            calls.append(req)
            return json_response({"code": 0, "data": {
                "task_id": "image123", "task_status": "submitted"}})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
            result = submit("image", prompt="red concept supercar", model="o1-base",
                            allow_paid=True, transport=fake)
        self.assertEqual(result["task_id"], "image123")
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(calls[0].full_url, IMAGE_ENDPOINT)
        payload = json.loads(calls[0].data)
        self.assertEqual(payload["type"], "omni")
        self.assertEqual(payload["model_parameters"]["n"], 1)
        self.assertEqual(payload["model_parameters"]["aspect_ratio"], "9:16")

    def test_video_submission_uses_actual_vq_schema(self):
        calls = []
        def fake(req, timeout):
            calls.append(req)
            return json_response({"task_id": "video123", "status": "created",
                                  "model": "VQ2-Turbo"})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
            result = submit("video", prompt="Supercar accelerates away",
                            model="VQ2-Turbo",
                            image_url="https://example.com/car.png", duration=5,
                            resolution="720p", allow_paid=True, transport=fake)
        self.assertEqual(result["task_id"], "video123")
        self.assertEqual(result["status"], "created")
        self.assertEqual(calls[0].full_url, VIDEO_ENDPOINT)
        payload = json.loads(calls[0].data)
        self.assertEqual(payload["type"], "img2video")
        self.assertEqual(payload["model_parameters"]["images"],
                         ["https://example.com/car.png"])
        self.assertEqual(payload["model_parameters"]["duration"], 5)
        self.assertFalse(payload["model_parameters"]["audio"])
        self.assertFalse(payload["model_parameters"]["is_rec"])
        self.assertNotIn("settings", payload["model_parameters"])
        self.assertNotIn("aspect_ratio", payload["model_parameters"])

    def test_bad_inputs_never_send(self):
        with patch("urllib.request.urlopen") as call:
            with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
                options = [
                    ("image", {"model": "invalid"}),
                    ("image", {"model": "o1-base", "resolution": "8k"}),
                    ("video", {"model": "qianfan-video-latest",
                               "image_url": "https://example.com/a.png"}),
                    ("video", {"model": "VQ2-Turbo",
                               "image_url": "http://example.com/a.png"}),
                    ("video", {"model": "VQ2-Turbo",
                               "image_url": "https://example.com/a.png", "duration": 17}),
                ]
                for kind, opts in options:
                    with self.subTest(kind=kind, opts=opts):
                        with self.assertRaises(MediaTaskError):
                            submit(kind, prompt="car", allow_paid=True, **opts)
            call.assert_not_called()

    def test_status_image_success(self):
        def fake(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            self.assertIn("task_id=img123", req.full_url)
            return json_response({"code": 0, "data": {
                "task_id": "img123", "task_status": "succeed",
                "task_result": {"images": [
                    {"url": "https://cdn.example.com/frame.png", "index": 0}]}}})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
            result = task_status("image", "img123", transport=fake)
        self.assertEqual(result["status"], "succeed")
        self.assertEqual(result["result_urls"],
                         ["https://cdn.example.com/frame.png"])

    def test_status_video_success(self):
        def fake(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            self.assertIn("task_id=vid123", req.full_url)
            self.assertIn("model=VQ2-Turbo", req.full_url)
            return json_response({"id": "vid123", "status": "success",
                                  "creations": [
                                      {"id": "x", "url": "https://cdn.example.com/clip.mp4"}]})
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
            result = task_status("video", "vid123", model="VQ2-Turbo",
                                 transport=fake)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result_urls"],
                         ["https://cdn.example.com/clip.mp4"])

    def test_bounded_poll_without_resubmission(self):
        responses = iter([
            {"code": 0, "data": {"task_status": "submitted"}},
            {"code": 0, "data": {"task_status": "processing"}},
            {"code": 0, "data": {"task_status": "succeed",
                                "task_result": {"images": [
                                    {"url": "https://cdn.example.com/ok.jpg"}]}}},
        ])
        verbs = []
        def fake(req, timeout):
            verbs.append(req.get_method())
            return json_response(next(responses))
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-test-only"}):
            result = wait_for_task("image", "img123", attempts=3, delay=0,
                                   sleep_fn=lambda _: None, transport=fake)
        self.assertEqual(result["status"], "succeed")
        self.assertEqual(verbs, ["GET", "GET", "GET"])

    def test_transport_failures_do_not_leak_secret(self):
        def fake(req, timeout):
            raise ValueError("private API key fake-super-secret")
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "fake-super-secret"}):
            with self.assertRaises(MediaTaskError) as caught:
                task_status("image", "img123", transport=fake)
        self.assertNotIn("fake-super-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
