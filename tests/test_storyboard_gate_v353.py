import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from oneflow.storyboard_gate_v353 import verify_storyboard, StoryboardGateError

class G3STests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name in ("script.csv","coast.png","style.png","BX05.png","yugu.png"):
            (self.root/name).write_bytes(name.encode())
        def ref(name):
            return {"path":name,"sha256":hashlib.sha256(name.encode()).hexdigest()}
        self.m=dict(
            storyboard_schema="oneflow-g3s-v3.5.3",shot_id="S06-04",
            source_script_ref="48-shot screenplay line S06-04",
            scene_id="COAST", camera_axis="seaside south-facing",
            shot_size="side full shot",camera_move="slow tracking",
            transition="hard cut",lighting_contract="cloudy north",
            action_trajectory="donkey walks on true reef",
            physical_contact="four hoof contact",
            continuity_to_prior="same storm sea and direction",
            editing_purpose="reveal safe evacuation",
            visual_description="true reef, false bridge, intact donkey",
            narrative_emotion="urgent controlled",
            original_dialogue="—",
            spatial_anchors=["reef A","left breakwater"],
            script_asset=ref("script.csv"),scene_asset=ref("coast.png"),
            style_asset=ref("style.png"),cast=["BX05"],
            subject_assets=[dict(ref("BX05.png"),id="BX05")],
            prop_assets=[dict(ref("yugu.png"),id="fish_drum")],
            collage=False,text_overlay=False,mode="epic_live_action")
    def test_valid_metadata_not_visual_proof(self):
        result=verify_storyboard(self.m,self.root,"S06-04")
        self.assertFalse(result["visual_identity_verified"])
        self.assertFalse(result["script_semantics_verified"])
    def test_shot_mismatch(self):
        with self.assertRaisesRegex(StoryboardGateError,"requested shot"):
            verify_storyboard(self.m,self.root,"S06-03")
    def test_absent_actor_asset(self):
        self.m["subject_assets"]=[]
        with self.assertRaisesRegex(StoryboardGateError,"locked portrait"):
            verify_storyboard(self.m,self.root)
    def test_bad_prop_hash(self):
        self.m["prop_assets"][0]["sha256"]="0"*64
        with self.assertRaisesRegex(StoryboardGateError,"SHA mismatch"):
            verify_storyboard(self.m,self.root)
    def test_missing_anchor(self):
        self.m["spatial_anchors"]=[]
        with self.assertRaisesRegex(StoryboardGateError,"spatial anchors"):
            verify_storyboard(self.m,self.root)
    def test_collage(self):
        self.m["collage"]=True
        with self.assertRaisesRegex(StoryboardGateError,"collage"):
            verify_storyboard(self.m,self.root)
    def test_env_shot_no_cast(self):
        self.m["cast"]=[]
        self.m["subject_assets"]=[]
        self.m["prop_assets"]=[]
        self.assertEqual(verify_storyboard(self.m,self.root)["shot_id"],"S06-04")
    def test_env_no_prop(self):
        self.m["cast"]=[]
        self.m["subject_assets"]=[]
        with self.assertRaisesRegex(StoryboardGateError,"environment"):
            verify_storyboard(self.m,self.root)
    def test_short_drama_mode_limit(self):
        self.m["mode"]="short_drama"
        self.m["shot_duration_seconds"]=5
        with self.assertRaisesRegex(StoryboardGateError,"1-3s"):
            verify_storyboard(self.m,self.root)
    def test_epic_film_duration(self):
        self.m["shot_duration_seconds"]=9
        self.assertEqual(verify_storyboard(self.m,self.root)["status"],"G3S_METADATA_PREFLIGHT_ONLY")
    def test_bad_scene_hash(self):
        self.m["scene_asset"]["sha256"]="0"*64
        with self.assertRaisesRegex(StoryboardGateError,"SHA mismatch"):
            verify_storyboard(self.m,self.root)
    def test_missing_action(self):
        self.m["action_trajectory"]=""
        with self.assertRaisesRegex(StoryboardGateError,"action_trajectory"):
            verify_storyboard(self.m,self.root)

if __name__=="__main__":
    unittest.main()
