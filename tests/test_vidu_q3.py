import argparse
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from oneflow import vidu_q3 as v


class ViduQ3Tests(unittest.TestCase):
    def test_text10_and_15(self):
        for sec in (10, 15):
            body = v.build_payload("text2video", "Supercar speeds forwards", sec, "720p")
            self.assertEqual(body["model"], "viduq3-pro")
            self.assertEqual(body["duration"], sec)
            self.assertEqual(body["aspect_ratio"], "9:16")
            self.assertTrue(body["audio"])
            self.assertFalse(body["off_peak"])

    def test_bad_duration_and_missing_frame_are_preflight_only(self):
        with self.assertRaises(v.ViduError):
            v.build_payload("text2video", "A real road", 20, "720p")
        with self.assertRaises(v.ViduError):
            v.build_payload("img2video", "A real road", 10, "720p")
        with self.assertRaises(v.ViduError):
            v.build_payload("text2video", "A real road", 10, "720p", "unused.png")

    def test_local_png_frame_encoded_with_correct_mime(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "S01.png"
            header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
            p.write_bytes(header + (640).to_bytes(4, "big") + (640).to_bytes(4, "big") + b"\x08\x02" + b"0" * 120)
            payload = v.build_payload("img2video", "Same car accelerating", 15, "720p", str(p))
            self.assertEqual(len(payload["images"]), 1)
            self.assertTrue(payload["images"][0].startswith("data:image/png;base64,"))
            self.assertNotIn("aspect_ratio", payload)

    def test_dry_run_sends_no_paid_request_and_needs_no_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="generate", mode="text2video", prompt="Supercar accelerating",
                                      seconds=10, resolution="720p", first_frame=None,
                                      confirm_paid=False, out=tmp, poll_attempts=1, poll_seconds=0,
                                      task_id=None)
            with patch.dict("os.environ", {}, clear=True), patch.object(v, "api_request", side_effect=AssertionError("network attempted")):
                v.run(args)
            manifest = json.loads((Path(tmp) / "vidu-status.json").read_text())
            self.assertEqual(manifest["state"], "PLANNED")
            self.assertEqual(manifest["billable_post_count"], 0)

    def test_authorized_generate_submits_once_and_queries_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="generate", mode="text2video", prompt="Supercar accelerating",
                                      seconds=10, resolution="720p", first_frame=None,
                                      confirm_paid=True, out=tmp, poll_attempts=1, poll_seconds=0,
                                      task_id=None)
            requests = []
            def fake_api(method, path, **kwargs):
                requests.append((method, path))
                if path == "/ent/v2/credits":
                    return {"remains": [{"type": "metered", "credit_remain": 1000}]}
                return {"task_id": "test-task-123", "state": "created"} if method == "POST" else {
                    "id": "test-task-123", "state": "success",
                    "creations": [{"url": "https://example.org/film.mp4"}]}
            with patch.dict("os.environ", {"VIDU_API_KEY": "safe-demo-key"}, clear=True), \
                 patch.object(v, "api_request", side_effect=fake_api), \
                 patch.object(v, "download_video", side_effect=lambda u,p: Path(p).write_bytes(b"MP4")), \
                 patch.object(v, "probe_mp4", return_value={"duration": 10.0}), \
                 patch.object(v, "render_portrait", return_value={"duration": 10.0, "width": 1080, "height": 1920, "has_audio": True}):
                v.run(args)
            self.assertEqual(requests, [("GET", "/ent/v2/credits"),
                                        ("POST", "/ent/v2/text2video"),
                                        ("GET", "/ent/v2/tasks/test-task-123/creations")])
            manifest = json.loads((Path(tmp) / "vidu-status.json").read_text())
            self.assertEqual(manifest["state"], "DELIVERED")
            self.assertEqual(manifest["billable_post_count"], 1)
            self.assertNotIn("safe-demo-key", json.dumps(manifest))
            self.assertNotIn("example.org", json.dumps(manifest))

    def test_timeout_submission_is_uncertain_and_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="generate", mode="text2video", prompt="Supercar accelerating",
                                      seconds=15, resolution="720p", first_frame=None,
                                      confirm_paid=True, out=tmp, poll_attempts=1, poll_seconds=0,
                                      task_id=None)
            calls = []
            def fail(method, path, **kwargs):
                calls.append(method)
                if path == "/ent/v2/credits":
                    return {"remains": [{"credit_remain": 1000}]}
                raise v.ViduError("Vidu transport/timeout; POST acceptance UNKNOWN")
            with patch.dict("os.environ", {"VIDU_API_KEY": "safe-demo-key"}, clear=True), \
                 patch.object(v, "api_request", side_effect=fail):
                with self.assertRaises(v.ViduError):
                    v.run(args)
            self.assertEqual(calls, ["GET", "POST"])
            manifest = json.loads((Path(tmp) / "vidu-status.json").read_text())
            self.assertEqual(manifest["state"], "POST_ACCEPTANCE_UNKNOWN")
            self.assertEqual(manifest["billable_post_count"], 1)
            self.assertIsNone(manifest["task_id"])

    def test_resume_only_queries_no_paid_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="resume", mode="text2video", prompt="ignored",
                                      seconds=15, resolution="720p", first_frame=None,
                                      confirm_paid=False, out=tmp, poll_attempts=1, poll_seconds=0,
                                      task_id="existing-123")
            with patch.dict("os.environ", {"VIDU_API_KEY": "safe-demo-key"}, clear=True), \
                 patch.object(v, "api_request", side_effect=lambda method, path, **kw: {"id": "existing-123", "state": "processing"}) as mocked:
                with self.assertRaises(v.ViduError):
                    v.run(args)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(mocked.call_args.args[:2], ("GET", "/ent/v2/tasks/existing-123/creations"))
            manifest = json.loads((Path(tmp) / "vidu-status.json").read_text())
            self.assertEqual(manifest["billable_post_count"], 0)
            self.assertEqual(manifest["task_id"], "existing-123")

    def test_401_does_not_disclose_provider_body(self):
        def reject(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, "invalid-token secret-token", {}, io.BytesIO(b"secret-token"))
        with self.assertRaises(v.ViduError) as ctx:
            v.api_request("POST", "/ent/v2/text2video", key="secret-token", payload={"prompt":"safe"}, opener=reject)
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn("secret-token", str(ctx.exception))

    def test_provider_400_reports_documented_code_not_secret(self):
        for code in ("CreditInsufficient", "ModelUnavailable", "FieldInvalid", "FieldUnwanted"):
            response_body = json.dumps({
                "reason": code,
                "message": "invalid field: duration; TOKEN_PRIVATE_SHOULD_NOT_LEAK"
            }).encode()
            def reject(req, timeout):
                raise urllib.error.HTTPError(req.full_url, 400, "private", {},
                                            io.BytesIO(response_body))
            with self.assertRaises(v.ViduError) as ctx:
                v.api_request("POST", "/ent/v2/text2video",
                              key="TOKEN_PRIVATE_SHOULD_NOT_LEAK",
                              payload={"model": "viduq3-pro"}, opener=reject)
            self.assertIn("provider_code=" + code, str(ctx.exception))
            self.assertNotIn("TOKEN_PRIVATE_SHOULD_NOT_LEAK", str(ctx.exception))
            self.assertNotIn("invalid field", str(ctx.exception))

    def test_malicious_provider_body_must_never_be_logged(self):
        detail = v.safe_http_diagnostic(json.dumps({
            "reason": "SHOULD_NOT_BE_PRINTED",
            "message": "private email and API credentials plus password"
        }).encode())
        self.assertEqual(detail, "provider_code=not_exposed")

    def test_credit_preflight_is_get_only_no_paid_post(self):
        import contextlib
        captured = io.StringIO()
        observed = []
        def safe_api(method, path, **kw):
            observed.append((method, path))
            return {"remains": [{"type":"test","credit_remain":0}]}
        with patch.dict("os.environ", {"VIDU_API_KEY":"test-only"}, clear=True), \
             patch.object(v, "api_request", side_effect=safe_api), \
             contextlib.redirect_stdout(captured):
            v.run(argparse.Namespace(action="preflight"))
        self.assertEqual(observed, [("GET", "/ent/v2/credits")])
        self.assertIn("credit_status=zero", captured.getvalue())
        self.assertNotIn("test-only", captured.getvalue())

    def test_15s_credit_budget_is_300_at_720p(self):
        self.assertEqual(v.CREDITS_PER_SECOND["720p"] * 15, 300)

    def test_insufficient_credits_cannot_submit_billable_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="generate", mode="text2video",
                                      prompt="Dark silver hypercar racing on sunset road",
                                      seconds=15, resolution="720p", first_frame=None,
                                      confirm_paid=True, out=tmp, poll_attempts=1,
                                      poll_seconds=0, task_id=None)
            calls = []
            def credits_only(method, path, **kw):
                calls.append((method, path))
                if method != "GET":
                    raise AssertionError("Unexpected POST")
                return {"remains": [{"credit_remain": 299}]}
            with patch.dict("os.environ", {"VIDU_API_KEY": "test-key"}, clear=True), \
                 patch.object(v, "api_request", side_effect=credits_only):
                with self.assertRaisesRegex(v.ViduError, "No paid POST sent"):
                    v.run(args)
            self.assertEqual(calls, [("GET", "/ent/v2/credits")])
            manifest = json.loads((Path(tmp) / "vidu-status.json").read_text())
            self.assertEqual(manifest["billable_post_count"], 0)
            self.assertEqual(manifest["state"], "BLOCKED_BEFORE_POST")
            self.assertEqual(manifest["estimated_credits"], 300)

    def test_credit_balance_unknown_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="generate", mode="text2video",
                                      prompt="Dark silver hypercar racing on sunset road",
                                      seconds=15, resolution="720p", first_frame=None,
                                      confirm_paid=True, out=tmp, poll_attempts=1,
                                      poll_seconds=0, task_id=None)
            with patch.dict("os.environ", {"VIDU_API_KEY":"test-key"}, clear=True), \
                 patch.object(v, "api_request", return_value={"remains": []}) as caller:
                with self.assertRaises(v.ViduError):
                    v.run(args)
            self.assertEqual(caller.call_count, 1)
            self.assertEqual(json.loads((Path(tmp) / "vidu-status.json").read_text())["billable_post_count"], 0)

    def test_wrong_provider_duration_is_rejected_even_with_real_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(action="resume", mode="text2video",
                                      prompt="not used", seconds=15, resolution="720p",
                                      first_frame=None, confirm_paid=False, out=tmp,
                                      poll_attempts=1, poll_seconds=0, task_id="existing-123")
            with patch.dict("os.environ", {"VIDU_API_KEY":"test-key"}, clear=True), \
                 patch.object(v, "api_request", return_value={
                     "state": "success", "creations": [{"url":"https://example.org/video.mp4"}]}), \
                 patch.object(v, "download_video", side_effect=lambda url,p: Path(p).write_bytes(b"MP4")), \
                 patch.object(v, "probe_mp4", return_value={"duration": 7.0}):
                with self.assertRaisesRegex(v.ViduError, "duration unexpected"):
                    v.run(args)

    def test_parse_official_remains_credits(self):
        data = {"remains": [
            {"type":"test", "credit_remain":150},
            {"type":"metered", "credit_remain":200}
        ], "packages": [{"credit_remain":350}]}
        self.assertEqual(v.parse_credit_snapshot(data), (350, "remains"))

    def test_parse_new_remaining_credits_string_values(self):
        data = {"remaining_credits": [
            {"type":"test", "credit_remain":"120"},
            {"type":"metered", "credit_remain":"180"}
        ]}
        self.assertEqual(v.parse_credit_snapshot(data), (300, "remaining_credits"))

    def test_empty_remaining_credits_falls_back_to_official_remains(self):
        data = {"remaining_credits":[],
                "remains":[{"type":"metered", "credit_remain":400}]}
        self.assertEqual(v.parse_credit_snapshot(data), (400, "remains"))

    def test_active_packages_fallback_without_double_count(self):
        data = {"packages":[{"type":"metered", "credit_remain":290},
                            {"type":"test", "credit_remain":15}]}
        self.assertEqual(v.parse_credit_snapshot(data), (305, "packages"))

    def test_empty_resource_lists_mean_zero_not_unknown(self):
        self.assertEqual(v.parse_credit_snapshot({"remains":[], "packages":[]}),
                         (0, "empty_resources"))

    def test_unknown_and_malformed_values_fail_closed(self):
        for data in ({}, {"remains":[{"credit_remain":"UNDEFINED"}]},
                     {"remains":[{"credit_remain":True}]},
                     {"remains":[{"credit_remain":-1}]},
                     {"remains":[{"credit_remain":"not a number"}]}):
            amount, reason = v.parse_credit_snapshot(data)
            self.assertIsNone(amount)
            self.assertTrue(reason)

    def test_concurrency_only_without_credit_is_unknown(self):
        self.assertEqual(v.parse_credit_snapshot({
            "remains":[{"type":"concurrent","concurrency_limit":1}]
        }), (None, "unrecognized_schema"))

    def test_readonly_preflight_prints_schema_without_exact_credit_value(self):
        import contextlib
        sink = io.StringIO()
        with patch.dict("os.environ", {"VIDU_API_KEY":"safe-test"}, clear=True), \
             patch.object(v, "api_request", return_value={
                 "remaining_credits":[],
                 "remains":[{"type":"metered","credit_remain":400}]}), \
             contextlib.redirect_stdout(sink):
            v.credits_preflight()
        self.assertIn("credits_sufficient_for_15s_720p=YES", sink.getvalue())
        self.assertIn("response_schema=remains", sink.getvalue())
        self.assertNotIn("400", sink.getvalue())
        self.assertNotIn("safe-test", sink.getvalue())

    def test_api_uses_token_header_and_correct_url(self):
        seen = []
        def fake(req, timeout):
            seen.append((req.full_url, req.get_header("Authorization"), req.get_method()))
            return io.BytesIO(b'{"task_id":"example-123","state":"created"}')
        result = v.api_request("POST", "/ent/v2/text2video", key="safe-test", payload={"model":"viduq3-pro"}, opener=fake)
        self.assertEqual(result["task_id"], "example-123")
        self.assertEqual(seen, [("https://api.vidu.com/ent/v2/text2video", "Token safe-test", "POST")])


if __name__ == "__main__":
    unittest.main()
