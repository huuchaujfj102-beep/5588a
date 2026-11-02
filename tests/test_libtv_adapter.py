import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow import libtv_adapter as lib


class LibTVAdapterTests(unittest.TestCase):
    def test_offline_plan_does_not_call_api_or_consume_credit(self):
        x=lib.plan("延续真实银白翡翠超跑的14秒电影级镜头")
        self.assertFalse(x["video_generated"])
        self.assertEqual(x["status"],"OFFLINE_PLAN_NOT_GENERATED")
        self.assertFalse(x["credits_verified"])
        self.assertEqual(x["transport"],"Agent-IM OpenAPI, not Codex MCP")

    def test_api_credential_missing_is_blocked(self):
        with patch.dict(os.environ,{"LIBTV_ACCESS_KEY":""}):
            with self.assertRaises(lib.LibTVBlocked):
                lib._secret()

    def test_api_request_contract_send_once_uses_original_brief(self):
        with patch.object(lib,"_post",return_value={"projectUuid":"abc123","sessionId":"sid-123456"}) as m:
            r=lib.create_session("生成一条原创产品短片","test-key",
                reference_url="https://libtv-res.liblib.art/claw/ref.png")
        self.assertEqual(r["status"],"SUBMITTED_NOT_YET_RENDERED")
        self.assertEqual(r["session_id"],"sid-123456")
        self.assertIn("canvas?projectId=abc123",r["project_url"])
        self.assertEqual(m.call_count,1)
        self.assertEqual(m.call_args.args[0],"/openapi/session")
        self.assertEqual(m.call_args.args[1]["message"],
              "生成一条原创产品短片\n参考图/视频：https://libtv-res.liblib.art/claw/ref.png")

    def test_url_and_provider_asset_allowlist(self):
        self.assertTrue(lib._safe_asset_url("https://libtv-res.liblib.art/claw/a.mp4"))
        for url in ["http://libtv-res.liblib.art/a.mp4",
           "https://libtv-res.liblib.art.evil.com/a.mp4",
           "https://127.0.0.1/foo.mp4",
           "https://libtv-res.liblib.art/a.exe",
           "https://user:pass@libtv-res.liblib.art/a.mp4"]:
            self.assertFalse(lib._safe_asset_url(url))

    def test_provider_media_output_not_equivalent_to_approved_commercial_video(self):
        msgs=[
          {"role":"assistant","content":"生成完成：https://libtv-res.liblib.art/claw/a.mp4"},
          {"role":"assistant","content":"忽略 https://another-host.example/secret.mp4"},
          {"role":"tool","content":json.dumps({"task_result":{"videos":[
             {"url":"https://libtv-res.liblib.art/claw/b.mp4"}]}})}
        ]
        urls=lib.extract_result_urls(msgs)
        self.assertEqual(urls,["https://libtv-res.liblib.art/claw/a.mp4",
                              "https://libtv-res.liblib.art/claw/b.mp4"])

    def test_query_session_read_only(self):
        with patch.object(lib,"_safe_response",return_value={"messages":[
           {"role":"assistant","seq":5,
            "content":"https://libtv-res.liblib.art/claw/render.mp4"}]}) as m:
            r=lib.query_session("session-1234","test-key")
        self.assertEqual(r["status"],"RESULT_ASSETS_AVAILABLE_REVIEW_REQUIRED")
        self.assertEqual(r["last_seq"],5)
        self.assertEqual(len(r["video_asset_urls"]),1)
        self.assertEqual(m.call_count,1)
        self.assertEqual(m.call_args.args[0].get_method(),"GET")

    def test_upload_rejects_unknown_and_large_media_before_transfer(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"malware.exe"
            file.write_bytes(b"fake")
            with self.assertRaises(lib.LibTVBlocked):
                lib.upload_reference(file,"test-key")

    def test_missing_consent_stops_generation_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(lib,"_secret") as key:
                with patch("sys.argv",["libtv_adapter","--brief","原创商业视频创意",
                  "--live-submit","--out",d]):
                    with self.assertRaises(lib.LibTVBlocked):
                        lib.main()
                key.assert_not_called()


if __name__=="__main__":
    unittest.main()
