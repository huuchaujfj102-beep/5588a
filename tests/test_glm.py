import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from film_audit.glm import review, usage_cost, validate_bundle, validate_review

BUNDLE = {'rules': '角色与服装锁定，禁止新增。', 'shots': [
    {'shot_id': 'S01', 'text': '角色甲穿深蓝袍服，右手持盏。'},
    {'shot_id': 'S02', 'text': '角色甲穿白色衣服，右手持盏。'}]}
BASELINE = {'status': 'FAIL', 'issues': [{'severity': 'blocker', 'code': 'MISSING_LEDGER'}]}


def response(findings=None):
    value = {'findings': findings or [], 'summary': '需人工复核', 'limitations': ['未检查画面']}
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}],
            'usage': {'prompt_tokens': 1000, 'completion_tokens': 100,
                      'prompt_tokens_details': {'cached_tokens': 500}}}


class GLMTests(unittest.TestCase):
    def test_dry_run_never_calls_network(self):
        def forbidden(*args):
            self.fail('Dry run invoked network')
        result = review(BUNDLE, BASELINE, transport=forbidden)
        self.assertEqual(result['mode'], 'dry_run')
        self.assertEqual(result['estimated_cost_usd'], 0)
        self.assertEqual(len(result['planned_stages']), 3)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_fail_closed(self):
        self.assertEqual(review(BUNDLE, BASELINE, live=True)['status'], 'ERROR')

    @patch.dict(os.environ, {'RUNPOD_API_KEY': 'unit-test-only'})
    def test_three_stages_preserve_baseline(self):
        original = copy.deepcopy(BASELINE)
        calls = []
        def fake(messages, key):
            calls.append(json.loads(messages[1]['content']))
            return response()
        result = review(BUNDLE, BASELINE, live=True, transport=fake)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(calls[2]['prior_reviews']), 2)
        self.assertEqual(BASELINE, original)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertAlmostEqual(result['estimated_cost_usd'], .0020955)

    def test_cost_with_and_without_cache(self):
        self.assertAlmostEqual(usage_cost({'prompt_tokens': 1000000, 'completion_tokens': 1000000}), 3.19)
        self.assertIsNone(usage_cost({}))
        self.assertIsNone(usage_cost({'prompt_tokens': 1, 'completion_tokens': 0,
                                     'prompt_tokens_details': {'cached_tokens': 2}}))

    def test_reject_hallucinated_evidence_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            validate_review({'findings': [{'shot_id': 'S01', 'severity': 'warning',
                'evidence': '不存在的证据', 'message': 'x', 'suggestion': 'y'}],
                'summary': '', 'limitations': []}, {'S01': '深蓝袍服'})
        bad = copy.deepcopy(BUNDLE)
        bad['shots'][1]['shot_id'] = 'S01'
        with self.assertRaises(ValueError):
            validate_bundle(bad)

    @patch.dict(os.environ, {'RUNPOD_API_KEY': 'unit-test-only'})
    def test_truncated_output_stops_and_records_cost(self):
        def fake(*args):
            value = response()
            value['choices'][0]['finish_reason'] = 'length'
            return value
        result = review(BUNDLE, BASELINE, live=True, transport=fake)
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(len(result['stages']), 1)
        self.assertGreater(result['estimated_cost_usd'], 0)

    @patch.dict(os.environ, {'RUNPOD_API_KEY': 'unit-test-only'})
    def test_model_blocker_requires_failure(self):
        finding = {'shot_id': 'S02', 'severity': 'blocker', 'evidence': '白色衣服',
                   'message': '服装冲突', 'suggestion': '核对母版'}
        result = review(BUNDLE, BASELINE, live=True, transport=lambda *args: response([finding]))
        self.assertEqual(result['status'], 'FAIL')

    @patch.dict(os.environ, {'RUNPOD_API_KEY': 'unit-test-only'})
    def test_malformed_json_stops(self):
        def fake(*args):
            value = response()
            value['choices'][0]['message']['content'] = 'not json'
            return value
        self.assertEqual(review(BUNDLE, BASELINE, live=True, transport=fake)['status'], 'ERROR')

    @patch.dict(os.environ, {'RUNPOD_API_KEY': 'unit-test-only'})
    def test_network_failure_and_invalid_envelope_fail_closed(self):
        calls = []
        def failed(*args):
            calls.append(1)
            raise ValueError('connection failed')
        self.assertEqual(review(BUNDLE, BASELINE, live=True, transport=failed)['status'], 'ERROR')
        self.assertEqual(len(calls), 1)
        self.assertEqual(review(BUNDLE, BASELINE, live=True, transport=lambda *args: [])['status'], 'ERROR')

    def test_cli_preserves_blocker_and_exits_on_missing_key(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, output = root/'input.json', root/'report.json'
            source.write_text(json.dumps(BUNDLE), encoding='utf8')
            ledger = root/'assets.csv'
            ledger.write_text('asset_id,source,license,proof,usage_scope\n1,own,owned,receipt,video\n')
            env = dict(os.environ)
            env.pop('RUNPOD_API_KEY', None)
            command = [sys.executable, '-m', 'film_audit.audit', '--glm-input', str(source),
                       '--output', str(output), '--assets', str(root/'absent.csv')]
            run = subprocess.run(command, capture_output=True, env=env)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(json.loads(output.read_text())['status'], 'FAIL')
            command[-1] = str(ledger)
            run = subprocess.run(command + ['--glm-live'], capture_output=True, env=env)
            self.assertEqual(run.returncode, 1)
            report = json.loads(output.read_text())
            self.assertEqual(report['status'], 'REVIEW_REQUIRED')
            self.assertEqual(report['glm_review']['status'], 'ERROR')
