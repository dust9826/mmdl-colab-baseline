"""CPU-only regressions for data preservation and notebook cleanup. No GPU/downloads."""
import ast
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adapter', ROOT/'colab/colab_runner.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
NOTEBOOK = json.loads((ROOT/'colab/L4_MMMU.ipynb').read_text())


class ColabTests(unittest.TestCase):
    def test_notebook_syntax_and_exact_embedded_adapter(self):
        notebooks = [NOTEBOOK]
        budget_notebook = ROOT/'colab/L4_MMMU_2048.ipynb'
        if budget_notebook.exists():
            notebooks.append(json.loads(budget_notebook.read_text()))
        runner_source = (ROOT/'colab/colab_runner.py').read_text()
        for notebook in notebooks:
            for i, cell in enumerate(notebook['cells']):
                if cell['cell_type'] == 'code':
                    ast.parse(''.join(cell['source']), filename=f'cell-{i}')
                    self.assertFalse(cell['outputs'])
            tree = ast.parse(''.join(notebook['cells'][8]['source']))
            self.assertEqual(ast.literal_eval(tree.body[0].value), runner_source)

    def test_2048_budget_accepts_only_named_output_limit_change(self):
        import copy

        baseline = {
            'protocol_id': 'mmmu-val-v8',
            'generation': {'max_new_tokens': 32768, 'temperature': 0.7, 'top_p': 0.8},
            'execution': {'max_model_len': 40960, 'batch_size': 2},
            'image': {'min_pixels': 1003520, 'max_pixels': 4014080},
            'parser': 'team-final-answer-v8',
            'model': {'id': 'Qwen/Qwen3-VL-4B-Instruct', 'revision': 'pinned'},
            'dataset': {'revision': 'pinned', 'expected_total': 900},
        }
        baseline_before = copy.deepcopy(baseline)
        candidate = copy.deepcopy(baseline)
        candidate['protocol_id'] = 'mmmu-val-v8-2048'
        candidate['generation']['max_new_tokens'] = 2048
        hw = {'name': 'colab_gpu'}
        calls = []

        def original_validate(cfg, passed_hw):
            calls.append((cfg, passed_hw))

        adapter.validate_budget_2048(candidate, hw, baseline, original_validate)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], baseline)
        self.assertIs(calls[0][1], hw)
        self.assertEqual(baseline, baseline_before)

        drift_paths = (
            ('protocol_id',),
            ('image', 'max_pixels'),
            ('execution', 'max_model_len'),
            ('generation', 'temperature'),
            ('parser',),
            ('model', 'revision'),
            ('dataset', 'revision'),
            ('generation', 'max_new_tokens'),
        )
        for path in drift_paths:
            with self.subTest(path=path):
                invalid = copy.deepcopy(candidate)
                section = invalid
                for key in path[:-1]:
                    section = section[key]
                key = path[-1]
                section[key] = 'changed' if isinstance(section[key], str) else section[key] + 1
                with self.assertRaisesRegex(ValueError, 'only protocol_id and max_new_tokens'):
                    adapter.validate_budget_2048(invalid, hw, baseline, original_validate)
        self.assertEqual(len(calls), 1, 'invalid protocol drift must not reach upstream validation')

    def test_incremental_restore_ignores_unpublished_uploads_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); local = root/'local'; remote = root/'remote'; local.mkdir()
            (local/'sample').write_text('first')
            store = adapter.CheckpointStore(local, remote); store.save()
            (local/'sample').write_text('second'); store.save()
            (remote/'orphan.zip').write_bytes(b'interrupted upload')
            adapter.restore(remote, root/'restored')
            self.assertEqual((root/'restored/sample').read_text(), 'second')
            with self.assertRaises(FileExistsError): adapter.restore(remote, root/'restored')
            next(remote.glob('000001-*.zip')).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'): adapter.restore(remote, root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_raw_response_survives_scorer_exception_and_backup(self):
        class Backend:
            def generate_stream(self, requests):
                for request in requests:
                    yield {'sample_id': request['sample_id'], 'raw_response': 'unscored answer',
                           'generated_token_ids': [1, 2], 'finish_reason': 'stop'}
        engine = SimpleNamespace(prepare_request=lambda: (
            {'sample_id': 'validation_Accounting_1'},
            {'id': 'validation_Accounting_1', 'inference_id': 'attempt1', 'answer': 'B', 'prompt': 'Q'}))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); local = root/'local'; remote = root/'remote'
            adapter.install_raw_journal(engine, Backend, local, 'job-evaluation')
            def requests(): yield engine.prepare_request()[0]
            with self.assertRaisesRegex(ValueError, 'parser failed'):
                with closing(Backend().generate_stream(requests())) as stream:
                    for _output in stream:
                        path = local/'raw_journal/job-evaluation/attempt1.json'
                        self.assertTrue(path.exists())  # Durable BEFORE the scorer sees the output.
                        raise ValueError('parser failed')
            adapter.CheckpointStore(local, remote).save()
            adapter.restore(remote, root/'restored')
            row = json.loads((root/'restored/raw_journal/job-evaluation/attempt1.json').read_text())
            self.assertEqual(row['raw_response'], 'unscored answer')
            self.assertEqual(row['generated_token_ids'], [1, 2])
            self.assertEqual(row['journal_status'], 'GENERATED_UNSCORED')
            self.assertNotIn('correct', row)
            self.assertFalse(list(local.rglob('.pending-*')))

    def lifecycle(self, fail_phase=None, backup_fail=False):
        source = ''.join(NOTEBOOK['cells'][15]['source']).replace('RUN_FULL = False', 'RUN_FULL = True', 1)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/'colab_support').mkdir()
            events = []; backup_calls = []
            def call(args, **kwargs):
                label = 'rescore' if 'scripts/rescore.sh' in args else (
                    'validate' if 'scripts.validate_run' in args else (
                    'validate_rescore' if 'scripts.validate_rescore' in args else 'preflight'))
                events.append(label)
                if label == fail_phase: raise ValueError(label)
            def evaluate(*args):
                events.append('inference')
                if fail_phase == 'inference': raise ValueError('inference')
                path = root/'runs/job-evaluation'; path.mkdir(parents=True)
                (path/'summary.json').write_text('{"status":"COMPLETE"}')
            class Store:
                def __init__(self, *args): pass
                def save(self):
                    backup_calls.append('save'); events.append('backup')
                    if backup_fail: raise OSError('backup unavailable')
            colab = SimpleNamespace(runtime=SimpleNamespace(unassign=lambda: events.append('disconnect')))
            scope = dict(LOCAL=root, REMOTE=root/'remote', JOB_ID='job', PYTHON='python', RUNNER='runner',
                REPO=ROOT, Path=Path, json=json, os=SimpleNamespace(environ={'HF_HOME': str(root),
                'MMDL_DATA_ROOT': str(root)}), call=call, evaluate=evaluate,
                backup=SimpleNamespace(CheckpointStore=Store))
            with patch.dict(sys.modules, {'google': SimpleNamespace(colab=colab), 'google.colab': colab}):
                try: exec(compile(source, 'full-run-cell', 'exec'), scope)
                except (ValueError, OSError): pass
            state = json.loads((root/'colab_support/lifecycle.json').read_text())
            return events, state

    def test_success_backs_up_after_validation_then_disconnects(self):
        events, state = self.lifecycle()
        self.assertEqual(state['status'], 'COMPLETE')
        self.assertEqual(events[-3:], ['validate_rescore', 'backup', 'disconnect'])

    def test_failures_back_up_and_disconnect_without_claiming_completion(self):
        for phase in ('preflight', 'inference', 'validate', 'rescore', 'validate_rescore'):
            with self.subTest(phase=phase):
                events, state = self.lifecycle(phase)
                self.assertEqual(state['status'], 'FAILED')
                self.assertEqual(events[-2:], ['backup', 'disconnect'])

    def test_backup_failure_keeps_runtime_alive(self):
        events, state = self.lifecycle(backup_fail=True)
        self.assertEqual(state['status'], 'FAILED')
        self.assertNotIn('disconnect', events)

    def test_preflight_rejects_context_overflow_and_image_limit(self):
        cfg = {'image': {'min_pixels': 1, 'max_pixels': 2},
               'generation': {'max_new_tokens': 32768}, 'execution': {'max_model_len': 40960}}
        rows = [{'id': str(i), 'question_type': 'open', 'subject': 'fixture'} for i in range(900)]
        size = {'tokens': 8192, 'images': 1}
        saved = []
        modules = {
            'torch': SimpleNamespace(set_num_threads=lambda _: None),
            'yaml': SimpleNamespace(safe_load=lambda _: cfg),
            'transformers': SimpleNamespace(
                AutoProcessor=SimpleNamespace(from_pretrained=lambda *a, **k: SimpleNamespace(image_processor=SimpleNamespace())),
                AutoConfig=SimpleNamespace(from_pretrained=lambda *a, **k: SimpleNamespace())),
            'mmdl.evaluation.datasets.mmmu': SimpleNamespace(
                load_validation=lambda _: ({'fixture': rows}, {}),
                separate_sample=lambda row, subject: (row, [object()]*size['images'], {'answer': 'gold'})),
            'mmdl.evaluation.prompt': SimpleNamespace(build_messages=lambda *a: []),
            'mmdl.evaluation.backends.input_preparation': SimpleNamespace(
                prepare_protocol_inputs=lambda *a: ({'input_tokens': size['tokens'], 'input_sha256': 'hash'}, [])),
            'mmdl.runtime.artifacts': SimpleNamespace(digest=lambda _: 'hash', write_json=lambda p,v: saved.append(v)),
            'mmdl.runtime.contracts': SimpleNamespace(MODEL_REVISION='pinned'),
        }
        with tempfile.TemporaryDirectory() as td, patch.dict(sys.modules, modules):
            root = Path(td); (root/'configs/eval').mkdir(parents=True)
            (root/'configs/eval/mmmu_val_v8.yaml').write_text('fixture')
            result = adapter.preflight(root, root, root, root/'out')
            self.assertEqual(result['count'], 900)
            self.assertEqual(result['max_input_tokens'], 8192)
            size['tokens'] = 8193
            with self.assertRaisesRegex(ValueError, 'context'): adapter.preflight(root, root, root, root/'out')
            size.update(tokens=8192, images=6)
            with self.assertRaisesRegex(ValueError, 'image limit'): adapter.preflight(root, root, root, root/'out')
            self.assertEqual(len(saved), 1)  # Failure must not publish a passing report.


if __name__ == '__main__': unittest.main()
