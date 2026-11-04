"""SVI Wan2.2 bootstrap safety: OFFLINE tests, never download weights."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runpod_svi" / "install.sh"
REV = "bab066229ea530a09587bed52c41ed6089bd509f"


class SviInstallTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["bash","-n",str(SCRIPT)],check=True)

    def test_pinned_wan22_revision_and_separate_environment(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("svi_wan22", source)
        self.assertIn(REV, source)
        self.assertIn("python3.10", source)
        self.assertIn("torch==2.7.1", source)
        self.assertIn("flash_attn==2.8.0.post2", source)
        self.assertIn("SVI_VENV", source)
        self.assertIn("Wan-AI/Wan2.2-I2V-A14B", source)
        self.assertNotIn("Wan2.2-TI2V-5B", source)

    def test_gpu_runtime_requires_opt_in_without_touching_network(self):
        env = dict(os.environ)
        env.pop("SVI_APPROVE_GPU_BILLING",None)
        p=subprocess.run(["bash",str(SCRIPT),"runtime"],capture_output=True,text=True,
                         env=env,timeout=10)
        self.assertEqual(p.returncode,2)
        self.assertIn("GPU billing not approved",p.stderr)

    def test_model_download_requires_gpu_approval(self):
        env = dict(os.environ)
        env.pop("SVI_APPROVE_GPU_BILLING",None)
        p=subprocess.run(["bash",str(SCRIPT),"weights"],capture_output=True,text=True,
                         env=env,timeout=10)
        self.assertEqual(p.returncode,2)
        self.assertIn("GPU billing not approved",p.stderr)

    def test_unknown_mode_does_not_install(self):
        p=subprocess.run(["bash",str(SCRIPT),"unverified"],capture_output=True,text=True,
                         timeout=10)
        self.assertEqual(p.returncode,2)
        self.assertIn("Supported modes",p.stderr)

    def test_two_approved_model_adapters_exist(self):
        source=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("high_noise_lora_v2.0.safetensors",source)
        self.assertIn("low_noise_lora_v2.0.safetensors",source)
        self.assertIn("SVI_MODEL_LICENSE_CHECKED",source)
        self.assertIn("SVI_APPROVE_DOWNLOAD",source)
        self.assertIn("180 GiB",source)


if __name__ == "__main__":
    unittest.main()
