import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "integrations" / "video_adapters.py"
spec = importlib.util.spec_from_file_location("video_adapters", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class VideoAdapterTests(unittest.TestCase):
    def test_local_only(self):
        self.assertEqual(mod.validate_local_endpoint("http://127.0.0.1:8188"), "http://127.0.0.1:8188")
        for bad in ["https://api.openai.com:443", "http://8.8.8.8:8188", "http://example.com:8188", "file:///etc/passwd", "http://user:pass@localhost:8188"]:
            with self.assertRaises(ValueError):
                mod.validate_local_endpoint(bad)
    def test_comfy_validation(self):
        workflow = {"1": {"class_type": "KSampler", "inputs": {"seed": 7}}}
        self.assertEqual(mod.build_comfy_request(workflow), {"prompt": workflow})
        for bad in [{}, {"x": {"class_type": "a", "inputs": {}}}, {"1": {"class_type": "a"}}, []]:
            with self.assertRaises(ValueError):
                mod.validate_comfy_workflow(bad)
    def test_no_model_install(self):
        self.assertEqual(mod.PROJECTS["wan2.2"]["mode"], "model-not-installed")

if __name__ == "__main__":
    unittest.main()
