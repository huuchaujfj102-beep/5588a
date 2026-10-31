import json
import tempfile
import unittest
from pathlib import Path

from oneflow.core import FlowError, load_json
from oneflow.request_runner import package, validate, srt_timestamp


def sample():
    return {
        "title": "童话短片",
        "brief": "白雪公主和七个小矮人在森林里结识、战胜困境并成为朋友。",
        "seconds": 15,
        "ratio": "9:16",
        "platforms": [],
        "characters": {"白雪公主": "黑发，绯红披风，靛蓝长裙，服装不随镜头变化。",
                       "七个矮人": "七位不同服装和工具的成年矿工，不增减人数。"},
        "shots": [
            {"seconds": 5, "visual": "幽暗森林", "motion": "公主向前走", "camera": "稳定跟拍",
             "sound": "枝叶沙沙", "narration": "她逃进森林。"},
            {"seconds": 5, "visual": "发现木屋", "motion": "轻敲房门", "camera": "慢推镜头",
             "sound": "木门敲击", "narration": "一盏灯指引了她。"},
            {"seconds": 5, "visual": "七位矿工团聚", "motion": "众人微笑", "camera": "缓慢拉远",
             "sound": "壁炉微响", "narration": "她找到了朋友。"}
        ]
    }


class StoryRequestTests(unittest.TestCase):
    def test_exactly_timed_story_package(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = package(sample(), Path(directory))
            manifest = load_json(folder / "manifest.json")
            self.assertEqual(manifest["status"], "PLANNED")
            self.assertEqual(manifest["seconds"], 15)
            self.assertEqual(sum(x["seconds"] for x in manifest["shots"]), 15)
            self.assertEqual(len(manifest["shots"]), 3)
            self.assertTrue((folder / "character-bible.md").exists())
            self.assertTrue((folder / "narration.json").exists())
            self.assertTrue((folder / "rendering-checklist.md").exists())
            self.assertTrue((folder / "subtitles.srt").exists())
            self.assertTrue((folder / "audio-cues.json").exists())
            self.assertTrue((folder / "edit-decision-list.json").exists())
            self.assertTrue((folder / "release-drafts.json").exists())
            self.assertEqual(manifest["offline_handoff"]["subtitles"], "subtitles.srt")
            subtitles = (folder / "subtitles.srt").read_text(encoding="utf8")
            self.assertIn("00:00:00,000 --> 00:00:05,000", subtitles)
            self.assertIn("00:00:10,000 --> 00:00:15,000", subtitles)
            self.assertIn("她找到了朋友。", subtitles)
            from film_audit.audit import check_srt
            self.assertEqual(check_srt(folder / "subtitles.srt"), [])
            narration = load_json(folder / "audio-cues.json")
            self.assertEqual(narration["status"], "SCRIPT_ONLY_NO_AUDIO")
            self.assertEqual(len(narration["shots"]), 3)
            self.assertIsNone(narration["shots"][0]["narration_audio"])
            edit = load_json(folder / "edit-decision-list.json")
            self.assertIsNone(edit["shots"][0]["source_video"])
            self.assertEqual(edit["duration_seconds"], 15)
            drafts = load_json(folder / "release-drafts.json")
            self.assertFalse(drafts["publish_automatically"])
            self.assertIn("douyin", drafts["profiles"])
            self.assertIn("youtube", drafts["profiles"])
            self.assertTrue(all(x["status"] == "DRAFT_NOT_PUBLISHED"
                                for x in drafts["profiles"].values()))
            self.assertIn("七位不同服装", manifest["shots"][1]["visual_prompt"])
            self.assertEqual(manifest["shots"][2]["narration"], "她找到了朋友。")
            self.assertFalse((folder / "final-draft.mp4").exists())

    def test_srt_timestamp_is_exact(self):
        self.assertEqual(srt_timestamp(0), "00:00:00,000")
        self.assertEqual(srt_timestamp(60), "00:01:00,000")
        self.assertEqual(srt_timestamp(3605), "01:00:05,000")
        with self.assertRaises(FlowError):
            srt_timestamp(-1)

    def test_empty_bible_rejected(self):
        doc = sample()
        doc["characters"] = {}
        with self.assertRaisesRegex(FlowError, "character bible"):
            validate(doc)

    def test_silent_wrong_number_of_shots_rejected(self):
        doc = sample()
        doc["shots"] = doc["shots"][:2]
        with self.assertRaisesRegex(FlowError, "exactly"):
            validate(doc)

    def test_wrong_duration_rejected(self):
        doc = sample()
        doc["shots"][1]["seconds"] = 4
        with self.assertRaisesRegex(FlowError, "sum"):
            validate(doc)

    def test_missing_voiceover_text_rejected(self):
        doc = sample()
        doc["shots"][0]["narration"] = ""
        with self.assertRaisesRegex(FlowError, "missing required"):
            validate(doc)


if __name__ == "__main__":
    unittest.main()
