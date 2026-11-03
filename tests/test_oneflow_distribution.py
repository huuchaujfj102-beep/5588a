"""No-network tests for five-platform OneFlow delivery handoff."""
import tempfile
import unittest
from pathlib import Path

from oneflow.core import FlowError, config, create, digest, load_json, save_json
from oneflow.distribution import TARGETS, build_delivery_kit


class FivePlatformDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = create(
            "Same graphite supercar accelerates through sunset, no dialogue",
            5, "9:16", list(TARGETS), self.tmp.name, config()
        )
        clip = self.root / "final-draft.mp4"
        clip.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"x" * 512)
        manifest = load_json(self.root / "manifest.json")
        manifest["render"] = clip.name
        manifest["status"] = "AWAITING_HUMAN_REVIEW"
        save_json(self.root / "manifest.json", manifest)
        save_json(self.root / "qc.json", {
            "status": "REVIEW_REQUIRED", "video_sha256": digest(clip)
        })

    def test_five_packages_all_unpublished(self):
        result = build_delivery_kit(self.root)
        self.assertEqual(result["published_count"], 0)
        self.assertEqual(len(result["targets"]), 5)
        self.assertEqual({x["platform"] for x in result["targets"]}, set(TARGETS))
        for platform in TARGETS:
            pkg = load_json(self.root / "delivery-kit" / (platform + ".json"))
            self.assertEqual(pkg["publication_status"], "NOT_SUBMITTED")
            self.assertEqual(pkg["human_review_status"], "PENDING")
            self.assertIsNone(pkg["official_post_id"])
            self.assertIsNone(pkg["official_post_url"])
            self.assertEqual(pkg["video_sha256"], result["video_sha256"])
        self.assertEqual(load_json(self.root / "delivery-kit" / "report.json"), result)

    def test_tampered_media_is_rejected(self):
        (self.root / "final-draft.mp4").write_bytes(b"y" * 600)
        with self.assertRaisesRegex(FlowError, "hash changed"):
            build_delivery_kit(self.root)

    def test_pending_video_does_not_create_fake_handoff(self):
        manifest = load_json(self.root / "manifest.json")
        manifest["status"] = "VIDEO_PENDING"
        save_json(self.root / "manifest.json", manifest)
        with self.assertRaisesRegex(FlowError, "audited MP4"):
            build_delivery_kit(self.root)
        self.assertFalse((self.root / "delivery-kit").exists())

    def test_missing_platform_fails_closed(self):
        manifest = load_json(self.root / "manifest.json")
        manifest["platforms"] = ["douyin"]
        save_json(self.root / "manifest.json", manifest)
        with self.assertRaisesRegex(FlowError, "Five target"):
            build_delivery_kit(self.root)


if __name__ == "__main__":
    unittest.main()
