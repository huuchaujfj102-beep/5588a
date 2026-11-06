"""Offline assertions at provider boundaries, not claims of visual correctness."""
import argparse
import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.image_generation import ImageFlowError, build_prompt, build_plan, execute
from oneflow import cloudflare_free_image as cloudflare, ovh_free_image as ovh
from oneflow import fal_image
from oneflow.continuity_rules import negative_constraints, RULE_VERSION


class Response:
    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, maximum):
        return self.raw[:maximum]


def image_args(root, **overrides):
    values = dict(brief='水墨动漫人物，题字“造镜者”，横幅', request_file=None,
                  shot='S01', seed=6, width=1344, height=768, output=root,
                  dry_run=True, approve_one_image=False, approve_free_test=False,
                  confirm_workers_free=False, steps=4)
    values.update(overrides)
    return argparse.Namespace(**values)


class ImageRulesTransportTests(unittest.TestCase):
    def test_user_style_text_and_ratio_not_overridden_by_template(self):
        brief='水墨动漫人物，题字“造镜者”，16:9横幅'
        with tempfile.TemporaryDirectory() as root:
            plan=execute(image_args(root, brief=brief))
        self.assertIn(brief, plan['prompt'])
        self.assertNotIn('9:16', plan['prompt'])
        self.assertNotIn('photorealistic cinematic still', plan['prompt'])
        self.assertNotIn('No captions, logos, watermarks', plan['prompt'])
        self.assertEqual(plan['rule_version'], RULE_VERSION)
        self.assertEqual(plan['negative_prompt_mode'], 'inline')
        self.assertFalse(plan['negative_prompt_field_transmitted'])

    def test_structural_negatives_are_in_actual_inline_prompt(self):
        prompt=build_prompt('吕洞宾背负大剑，手持拂尘，完整站立')
        self.assertIn(negative_constraints(), prompt)

    def test_source_whitespace_and_newlines_are_preserved(self):
        brief='  第一行原文\n第二行题字  '
        self.assertIn(brief,build_prompt(brief))

    def test_provider_length_limit_is_checked_in_both_dry_and_live_paths(self):
        for provider in (cloudflare, ovh):
            for dry in (True, False):
                with self.subTest(provider=provider.__name__, dry=dry):
                    with tempfile.TemporaryDirectory() as root:
                        args=image_args(root, brief='x'*2048, dry_run=dry,
                                        approve_free_test=True, confirm_workers_free=True)
                        with self.assertRaises(ImageFlowError):
                            if provider is cloudflare:
                                provider.execute(args, account_id='a'*32, token='fake',
                                    opener=lambda *a, **k: self.fail('unexpected network'))
                            else:
                                provider.execute(args,
                                    transport=lambda *a, **k: self.fail('unexpected network'))
                        self.assertFalse(Path(root, 'S01.png').exists())

    def test_compact_rules_fit_without_truncating_user_brief(self):
        brief='画中题字'+('青'*1200)
        full=build_prompt(brief)
        compact=build_prompt(brief,max_chars=2048)
        self.assertGreater(len(full),2048)
        self.assertLessEqual(len(compact),2048)
        self.assertIn(brief,compact)
        self.assertIn(negative_constraints(),compact)

    def test_cloudflare_transmits_inline_constraints_without_invented_fields(self):
        prompt=build_prompt('吕洞宾背负大剑，手持拂尘，站立', max_chars=2048)
        captured=[]
        def transport(request, timeout):
            captured.append(json.loads(request.data))
            raw=json.dumps({'success':True, 'result':{
                'image':base64.b64encode(b'x'*400).decode()}}).encode()
            return Response(raw)
        cloudflare.infer_once(prompt, 'a'*32, 'fake', opener=transport)
        self.assertEqual(set(captured[0]), {'prompt', 'steps'})
        self.assertIn(negative_constraints(), captured[0]['prompt'])

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
    def test_ovh_transmits_plan_negatives_instead_of_old_car_defaults(self):
        captured=[]
        def transport(request, timeout):
            captured.append(json.loads(request.data))
            return Response(b'x'*400)
        with tempfile.TemporaryDirectory() as root:
            args=image_args(root, dry_run=False, approve_free_test=True)
            planned=ovh.execute(image_args(root))
            with self.assertRaisesRegex(ImageFlowError, 'decodable'):
                ovh.execute(args, transport=transport)
        self.assertEqual(captured[0]['negative_prompt'], planned['negative_prompt'])
        self.assertEqual(planned['negative_prompt_mode'], 'separate')
        self.assertTrue(planned['negative_prompt_field_supported'])
        self.assertFalse(planned['negative_prompt_field_transmitted'])
        self.assertNotIn('duplicate cars', captured[0]['negative_prompt'])
        self.assertNotIn('cartoon', captured[0]['negative_prompt'])

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
    def test_hf_provider_receives_compiled_prompt(self):
        from PIL import Image
        captured=[]
        class FakeHF:
            def __init__(self, **kwargs):
                pass
            def text_to_image(self, **kwargs):
                captured.append(kwargs)
                return Image.new('RGB',(1344,768))
        with tempfile.TemporaryDirectory() as root:
            report=execute(image_args(root,dry_run=False,approve_one_image=True),
                           token='fake',client_cls=FakeHF)
        self.assertIn(negative_constraints(), captured[0]['prompt'])
        self.assertNotIn('negative_prompt', captured[0])
        self.assertEqual(captured[0]['prompt'],report['prompt'])

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
    def test_fal_provider_receives_compiled_prompt(self):
        captured=[]
        def submit(model, arguments):
            captured.append(arguments)
            return {'images': []}
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ImageFlowError,'exactly one'):
                fal_image.execute(image_args(root,dry_run=False,approve_one_image=True),
                                  token='fake',submit=submit)
        self.assertIn(negative_constraints(), captured[0]['prompt'])
        self.assertNotIn('negative_prompt', captured[0])

    def test_malformed_story_fails_before_compilation_or_model_call(self):
        with patch('oneflow.image_generation.safe_request_path',return_value=Path('unused')):
            with patch('pathlib.Path.read_text',return_value=json.dumps({'shots':[{'visual':'有效场景'}]})):
                with self.assertRaisesRegex(ImageFlowError,'visual, motion and camera'):
                    build_prompt(request_file='unused')


if __name__=='__main__':
    unittest.main()
