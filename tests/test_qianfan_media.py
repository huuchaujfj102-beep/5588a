import io
import json
import os
import unittest
from unittest.mock import patch
from oneflow.qianfan_media import submit, MediaTaskError, IMAGE_ENDPOINT, VIDEO_ENDPOINT

class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

class MediaTests(unittest.TestCase):
    def test_no_paid_opt_in_no_network(self):
        with patch("urllib.request.urlopen") as call:
            for kind,model in (("image","o1-base"),("video","qianfan-video-latest")):
                with self.assertRaisesRegex(MediaTaskError,"allow_paid"):
                    submit(kind,prompt="supercar",model=model)
            call.assert_not_called()

    def test_image_submission_mock(self):
        captured=[]
        def fake(req,timeout):
            captured.append(req)
            return Response(json.dumps({"code":0,"data":{"task_id":"test-123","task_status":"submitted"}}).encode())
        with patch.dict(os.environ,{"QIANFAN_API_KEY":"fake-test-only"}):
            result=submit("image",prompt="red supercar",model="o1-base",
                          allow_paid=True,transport=fake)
        self.assertEqual(result["task_id"],"test-123")
        self.assertEqual(captured[0].full_url,IMAGE_ENDPOINT)
        payload=json.loads(captured[0].data)
        self.assertEqual(payload["type"],"omni")
        self.assertEqual(payload["model_parameters"]["n"],1)

    def test_video_is_safely_blocked_until_schema_confirmed(self):
        with patch.dict(os.environ,{"QIANFAN_API_KEY":"fake-test-only"}):
            with patch("urllib.request.urlopen") as call:
                with self.assertRaisesRegex(MediaTaskError,"awaiting verification"):
                    submit("video",prompt="slow cinematic movement",
                        model="qianfan-video-latest",
                        image_url="https://example.com/car.png",allow_paid=True)
                call.assert_not_called()

    def test_bad_inputs_never_send(self):
        with patch("urllib.request.urlopen") as call,patch.dict(os.environ,{"QIANFAN_API_KEY":"fake"}):
            with self.assertRaises(MediaTaskError):
                submit("video",prompt="car",model="qianfan-video-latest",
                       image_url="http://example.com/car.png",allow_paid=True)
            with self.assertRaises(MediaTaskError):
                submit("image",prompt="car",model="invalid",allow_paid=True)
            call.assert_not_called()

if __name__=="__main__":
    unittest.main()
