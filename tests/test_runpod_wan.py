import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runpod_wan.smoke import SmokeError, build_command, run


class WanSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wan = self.root / "Wan2.2"
        self.model = self.root / "model"
        self.wan.mkdir()
        self.model.mkdir()
        (self.wan / "generate.py").write_text("print('fake')", encoding="utf8")
        (self.model / "config.json").write_text("{}", encoding="utf8")
        self.image = self.root / "approved.png"
        self.image.write_bytes(b"not a real png but enough for offline parser test")
        self.prompt_file = self.root / "prompt.txt"
        self.prompt_file.write_text("Original fantasy shot; controlled motion", encoding="utf8")
        self.output = self.root / "output.mp4"

    def command(self, seconds=5, output=None):
        return build_command(self.wan, self.model, self.image,
                             "Original fantasy shot", output or self.output,
                             seconds, 456)

    def test_native_wan_task_is_exactly_one_approved_clip(self):
        cmd = self.command(5)
        for flag, value in (("--task", "ti2v-5B"),
                            ("--frame_num", "121"),
                            ("--size", "704*1280"),
                            ("--offload_model", "True"),
                            ("--base_seed", "456")):
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--t5_cpu", cmd)
        self.assertIn("--image", cmd)

    def test_three_seconds_has_seventy_three_frames(self):
        cmd = self.command(3)
        self.assertEqual(cmd[cmd.index("--frame_num") + 1], "73")

    def test_dry_run_does_not_call_gpu(self):
        args = argparse.Namespace(
          wan_root=str(self.wan), model_dir=str(self.model), image=str(self.image),
          prompt_file=str(self.prompt_file), output=str(self.output),
          seconds=5, seed=456, dry_run=True, approved_image=False, confirm_gpu_spend=False)
        with patch("runpod_wan.smoke.subprocess.run",
                   side_effect=AssertionError("dry run must not execute")):
            report = run(args)
        self.assertEqual(report["status"], "DRY_RUN")
        self.assertFalse(self.output.exists())

    def test_preapproval_halts_billable_gpu_generation(self):
        args = argparse.Namespace(
          wan_root=str(self.wan), model_dir=str(self.model), image=str(self.image),
          prompt_file=str(self.prompt_file), output=str(self.output),
          seconds=5, seed=456, dry_run=False, approved_image=False, confirm_gpu_spend=True)
        with self.assertRaisesRegex(SmokeError, "Human approval"):
            run(args)

    def test_text_only_mode_is_supported_without_image(self):
        cmd = build_command(self.wan, self.model, None, "Forest at dawn",
                            self.output, 5, 123)
        self.assertNotIn("--image", cmd)
        self.assertEqual(cmd[cmd.index("--task") + 1], "ti2v-5B")

    def test_explicit_gpu_spend_confirmation_is_required(self):
        args = argparse.Namespace(
          wan_root=str(self.wan), model_dir=str(self.model), image=None,
          prompt_file=str(self.prompt_file), output=str(self.output),
          seconds=5, seed=456, dry_run=False, approved_image=False, confirm_gpu_spend=False)
        with self.assertRaisesRegex(SmokeError, "confirmed"):
            run(args)

    def test_fail_missing_weights(self):
        with self.assertRaisesRegex(SmokeError, "checkpoint"):
            build_command(self.wan, self.root / "missing", self.image,
                          "original shot", self.output, 5, 1)

    def test_fail_output_overwrite(self):
        self.output.write_bytes(b"existing")
        with self.assertRaisesRegex(SmokeError, "already exists"):
            self.command()

    def test_fail_missing_image(self):
        with self.assertRaisesRegex(SmokeError, "approved PNG"):
            build_command(self.wan, self.model, self.root / "missing.png",
                          "original shot", self.output, 5, 1)

    def test_fail_long_generation_before_spending(self):
        with self.assertRaisesRegex(SmokeError, "3-5 seconds"):
            self.command(30)


if __name__ == "__main__":
    unittest.main()
