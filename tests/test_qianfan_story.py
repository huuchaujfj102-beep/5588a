"""Offline Qianfan adapter tests. Never contact or bill a remote provider."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.core import FlowError, create, describe, main
from oneflow.providers import ProviderError
from oneflow.qianfan import QIANFAN_CHAT_URL, storyboard


class QianfanStoryTests(unittest.TestCase):
    def setUp(self):
        self.story = {"kind": "qianfan", "model": "ernie-5.1", "max_tokens": 2048}
        self.cfg = {"story": self.story, "max_shots": 12}
        self.shots = [{"prompt": "Car accelerates in sunset", "sound": "Engine roaring"},
                      {"prompt": "Car passes the camera", "sound": "Fast whoosh"},
                      {"prompt": "Car flies beyond the cliff", "sound": "Jet acceleration"}]
        self.response = {"choices": [{"message": {"role": "assistant",
                                                   "content": json.dumps({"shots": self.shots})}}]}

    def test_offline_mode_refuses_qianfan_call(self):
        with patch("oneflow.qianfan.json_call") as call:
            with self.assertRaisesRegex(FlowError, "fees"):
                describe("一辆车启动，疾驰，腾空", 15, 3, self.cfg)
            with tempfile.TemporaryDirectory() as out:
                with self.assertRaisesRegex(FlowError, "fees"):
                    create("一辆车启动，疾驰，腾空", 15, "9:16", [], out, self.cfg)
            call.assert_not_called()

    def test_explicit_live_story_calls_fixed_official_endpoint(self):
        with patch("oneflow.qianfan.json_call", return_value=self.response) as call:
            shots, planner = describe("一辆车启动，疾驰，腾空", 15, 3, self.cfg,
                                      live_story=True)
        self.assertEqual(len(shots), 3)
        self.assertEqual(planner, "qianfan_live:ernie-5.1")
        self.assertIn("Engine roaring", shots[0]["sound"])
        args, kwargs = call.call_args
        self.assertEqual(args[0], QIANFAN_CHAT_URL)
        self.assertEqual(args[1], {"token_env": "QIANFAN_API_KEY"})
        self.assertEqual(args[2]["model"], "ernie-5.1")
        self.assertFalse(args[2]["stream"])
        self.assertEqual(len(args[2]["messages"]), 2)
        self.assertNotIn("QIANFAN_API_KEY", json.dumps(args[2]))

    def test_fenced_json_and_validation(self):
        content = chr(96) * 3 + "json\n" + json.dumps({"shots": self.shots}) + "\n" + chr(96) * 3
        response = {"choices": [{"message": {"content": content}}]}
        with patch("oneflow.qianfan.json_call", return_value=response):
            self.assertEqual(len(storyboard(self.story, "brief", 15, 3)), 3)

        malformed = [
            {"choices": [{"message": {"content": '{"shots": []}'}}]},
            {"choices": [{"message": {"content": '{"shots":[{"prompt":"a","sound":"x"}]}'}}]},
            {"choices": [{"message": {"content": "not json"}}]},
            {"choices": []},
            {"error": {"message": "this should never be printed"}},
        ]
        for item in malformed:
            with self.subTest(item=item), patch("oneflow.qianfan.json_call", return_value=item):
                with self.assertRaisesRegex(ProviderError, "expected JSON"):
                    storyboard(self.story, "brief", 15, 3)

    def test_model_and_limits_block_before_network(self):
        with patch("oneflow.qianfan.json_call") as call:
            for invalid in ["", "bad model name", "bad\nname", None]:
                with self.subTest(invalid=invalid):
                    with self.assertRaises(ProviderError):
                        storyboard({**self.story, "model": invalid}, "brief", 15, 3)
            with self.assertRaises(ProviderError):
                storyboard({**self.story, "max_tokens": 100000}, "brief", 15, 3)
            call.assert_not_called()

    def test_cli_live_plan_does_not_render_media(self):
        with tempfile.TemporaryDirectory() as root:
            cfgfile = Path(root) / "config.json"
            cfgfile.write_text(json.dumps(self.cfg), encoding="utf-8")
            out = io.StringIO()
            with patch("oneflow.qianfan.json_call", return_value=self.response) as call:
                with patch("oneflow.core.produce") as produce:
                    with contextlib.redirect_stdout(out):
                        status = main(["run", "--prompt", "Car races toward a cliff at sunset",
                                       "--seconds", "15", "--ratio", "9:16", "--out", root,
                                       "--config", str(cfgfile), "--live-plan"])
                    self.assertEqual(status, 0)
                    produce.assert_not_called()
                    self.assertEqual(call.call_count, 1)
            result = json.loads(out.getvalue())
            self.assertEqual(result["status"], "PLANNED")
            manifest = json.loads((Path(result["job"]) / "manifest.json").read_text())
            self.assertEqual(manifest["planner"], "qianfan_live:ernie-5.1")
            self.assertFalse((Path(result["job"]) / "final-draft.mp4").exists())

    def test_cli_offline_with_qianfan_config_does_not_spend(self):
        with tempfile.TemporaryDirectory() as root:
            cfgfile = Path(root) / "config.json"
            cfgfile.write_text(json.dumps(self.cfg), encoding="utf-8")
            with patch("oneflow.qianfan.json_call") as call:
                with contextlib.redirect_stderr(io.StringIO()):
                    status = main(["run", "--prompt", "Car races toward a cliff at sunset",
                                   "--seconds", "15", "--out", root, "--config", str(cfgfile)])
                self.assertEqual(status, 1)
                call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
