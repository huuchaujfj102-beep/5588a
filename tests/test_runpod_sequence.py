"""Guard the real Runpod workflow from falsely claiming CUDA rendering on GitHub CPU."""
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunpodSequenceTests(unittest.TestCase):
    def test_sequence_has_three_stages_in_order(self):
        data = (ROOT / "runpod_wan" / "run_sequence.sh").read_text(encoding="utf-8")
        self.assertLess(data.index("WAN_DOWNLOAD=1 bash runpod_wan/bootstrap.sh"),
                        data.index("--dry-run"))
        self.assertLess(data.index("--dry-run"), data.index("--confirm-gpu-spend"))
        self.assertIn('test -s "$OUTPUT"', data)

    def test_manual_trigger_does_not_provision_gpu(self):
        content = (ROOT / ".github" / "workflows" / "runpod-wan-gpu-render.yml").read_text(encoding="utf8")
        self.assertIn("workflow_dispatch", content)
        self.assertIn("approve_gpu_billing:", content)
        self.assertIn("default: false", content)
        self.assertIn("runs-on: [self-hosted, linux, x64, runpod-wan22]", content)
        self.assertIn("environment: runpod-paid-gpu", content)
        self.assertNotIn("podFindAndDeployOnDemand", content)
        self.assertNotIn("api.runpod.io/graphql", content)

    def test_no_approval_fails_without_gpu_or_network(self):
        process = subprocess.run(
            ["bash", str(ROOT / "runpod_wan" / "run_sequence.sh")],
            cwd=ROOT, capture_output=True, text=True, timeout=8,
            env={**os.environ, "WAN_CONFIRM_GPU_COST": "false"})
        self.assertEqual(process.returncode, 2)
        self.assertIn("user must explicitly opt in", process.stderr)

    def test_static_bash_syntax(self):
        for path in ("runpod_wan/bootstrap.sh", "runpod_wan/run_sequence.sh"):
            proc = subprocess.run(["bash", "-n", str(ROOT / path)],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
