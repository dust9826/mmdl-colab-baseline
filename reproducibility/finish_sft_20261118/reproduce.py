"""Frozen finish-SFT repeatability audit; no new data selection or score tuning.

Standard-library bootstrap. GPU stages run inside the original pinned venv.
The 24-item probe is the original first complete request window, not a score estimate.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile

COMMIT = 'f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1'
MODEL = 'Qwen/Qwen3-VL-4B-Instruct'
REVISION = 'ebb281ec70b05090aa6165b016eac8ec08e71b17'
TRAIN_SHA = '1ca52b224f3c03dfae2d3297d9bfc8a0e563936afc117293e9d5f2e65cc09070'
BUNDLE_SHA = '0bc1895db561eca1440e820bdbfb067d256ad7a847342e22c4e96f6ded56fb98'
JOB = 'finish-sft-repro-20261118'
EXPECTED = {'torch': '2.8.0+cu128', 'vllm': '0.11.0', 'transformers': '4.57.1',
            'peft': '0.17.1', 'pillow': '11.3.0', 'qwen-vl-utils': '0.0.14'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.pending')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def emit(event, obj):
    print('REPRO_' + event + ' ' + json.dumps(obj, ensure_ascii=False, allow_nan=False), flush=True)


def unpack(bundle, destination):
    if sha(bundle) != BUNDLE_SHA:
        raise ValueError('Frozen bundle SHA256 mismatch')
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    with zipfile.ZipFile(bundle) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError('Duplicate ZIP members or CRC mismatch')
        for name in names:
            p = Path(name)
            if p.is_absolute() or '..' in p.parts or name.endswith('/'):
                raise ValueError('Unsafe ZIP member')
            target = destination / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    manifest = read(destination / 'manifest.json')
    actual = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*')
              if p.is_file() and p.name != 'manifest.json'}
    if actual != manifest['files'] or sha(destination / 'train.json') != TRAIN_SHA:
        raise ValueError('Frozen file coverage/hash mismatch')
    rows = read(destination / 'train.json')
    candidates = read(destination / 'training/candidates.json')
    if len(rows) != 48 or len({r['id'] for r in rows}) != 48:
        raise ValueError('Expected exactly the original selected 48 examples')
    by_id = {r['id']: r for r in candidates}
    for row in rows:
        if any(row[k] != v for k, v in by_id[row['id']].items()):
            raise ValueError('Changed training selection')
        if len(row['draft_ids']) != row['prefix_tokens'] or len(row['tail_ids']) != row['supervised_tokens']:
            raise ValueError('Stored token coverage mismatch')
        if row['draft_tokens'] != 2048 or row['draft_finish_reason'] != 'length':
            raise ValueError('Changed teacher draft criteria')
        if not 512 <= len(row['draft_ids']) <= 1920 or len(row['draft_ids']) + len(row['tail_ids']) > 2048:
            raise ValueError('Invalid training token budget')
        expected = {g: sum((a - b if row['family'] == 'stock' else
                            a * b - rest[0] if row['family'] == 'invoice' else a * b)
                           for a, b, *rest in values)
                    for g, values in row['original_values'].items()}
        if expected != row['group_subtotals'] or sum(expected.values()) != int(row['answer']):
            raise ValueError('Independent training arithmetic verification failed')
    lock = read(destination / 'eval_lock.json')
    if len(lock) != 900 or len({r['id'] for r in lock}) != 900:
        raise ValueError('Evaluation identity lock must contain exactly 900 unique IDs')
    train_ids = {r['id'] for r in rows}
    if train_ids & {r['id'] for r in lock}:
        raise ValueError('Training/evaluation ID overlap')
    return manifest


def runtime_env(root):
    env = os.environ.copy()
    env.update(PYTHONPATH=str(root / 'source') + os.pathsep + str(root / 'MMDL') +
               os.pathsep + str(root / 'MMDL/src'), HF_HOME=str(root / 'hf'),
               MMDL_DATA_ROOT=str(root / 'data'), MMDL_ARTIFACT_ROOT=str(root / 'artifacts'),
               TOKENIZERS_PARALLELISM='false', PYTHONUNBUFFERED='1', CUDA_VISIBLE_DEVICES='0',
               VLLM_ENABLE_V1_MULTIPROCESSING='0')
    if 'VLLM_BATCH_INVARIANT' in env:
        raise ValueError('vLLM 0.11.0 does not support batch invariance')
    # Preserve the historical numerical path. Do not silently replace SDPA or enable strict kernels.
    return env


def environment():
    from importlib.metadata import version
    import platform
    import torch
    versions = {name: version(name) for name in EXPECTED}
    if versions != EXPECTED or sys.version_info[:3] != (3, 12, 3):
        raise ValueError(f'Pinned environment mismatch: {versions} / {sys.version}')
    if torch.cuda.device_count() != 1 or 'L4' not in torch.cuda.get_device_name(0):
        raise ValueError('This audit requires one NVIDIA L4')
    return {'packages': versions, 'python': sys.version, 'platform': platform.platform(),
            'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                                            '--format=csv,noheader'], text=True).strip(),
            'cuda': torch.version.cuda, 'cudnn': torch.backends.cudnn.version(),
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'cudnn_deterministic': torch.backends.cudnn.deterministic,
            'cudnn_benchmark': torch.backends.cudnn.benchmark,
            'tf32_matmul': torch.backends.cuda.matmul.allow_tf32,
            'tf32_cudnn': torch.backends.cudnn.allow_tf32,
            'sdpa_flash': torch.backends.cuda.flash_sdp_enabled(),
            'sdpa_mem_efficient': torch.backends.cuda.mem_efficient_sdp_enabled(),
            'sdpa_math': torch.backends.cuda.math_sdp_enabled(),
            'torch_threads': torch.get_num_threads(),
            'environment_flags': {k: os.environ.get(k) for k in (
                'VLLM_ENABLE_V1_MULTIPROCESSING', 'VLLM_BATCH_INVARIANT', 'CUBLAS_WORKSPACE_CONFIG',
                'PYTHONHASHSEED', 'NVIDIA_TF32_OVERRIDE')}}


def tensor_fingerprint(tensors):
    import torch
    rows = []
    for name, tensor in sorted(tensors.items()):
        value = tensor.detach().cpu().contiguous()
        rows.append({'name': name, 'shape': list(value.shape), 'dtype': str(value.dtype),
                     'sha256': hashlib.sha256(value.view(torch.uint8).numpy().tobytes()).hexdigest()})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'sha256': digest, 'tensors': rows}


def train(root, name):
    import peft
    import torch
    from peft import get_peft_model_state_dict
    import prior_finish
    out = root / 'artifacts' / name
    out.mkdir(exist_ok=False)
    shutil.copy2(root / 'source/train.json', out / 'train.json')
    shutil.copytree(root / 'artifacts/setup', out / 'setup')
    write(out / 'environment.json', environment())
    initial = {}
    gradients = []
    original_get = peft.get_peft_model
    original_clip = torch.nn.utils.clip_grad_norm_

    def capture_model(*args, **kwargs):
        model = original_get(*args, **kwargs)
        initial.update(tensor_fingerprint(get_peft_model_state_dict(model)))
        return model

    def capture_clip(parameters, *args, **kwargs):
        parameters = list(parameters)
        stamp = tensor_fingerprint({str(i): p.grad for i, p in enumerate(parameters) if p.grad is not None})
        gradients.append({'step': len(gradients) + 1, **stamp})
        return original_clip(parameters, *args, **kwargs)

    peft.get_peft_model = capture_model
    torch.nn.utils.clip_grad_norm_ = capture_clip
    try:
        prior_finish.train(root / 'source/training', out)
    finally:
        peft.get_peft_model = original_get
        torch.nn.utils.clip_grad_norm_ = original_clip
        write(out / 'numerical_trace.json', {'initial': initial, 'gradients_before_clip': gradients,
              'instrumentation': 'CPU copies for hashing; no tensor mutation or RNG consumption'})
    report = read(out / 'training.json')
    if (report['examples'], report['arms']['sft']['updates'], report['arms']['sft']['supervised_tokens']) != (48, 24, 7610):
        raise ValueError('Original 48-example/24-update/7610-target-token coverage changed')
    if report['train_sha256'] != TRAIN_SHA:
        raise ValueError('Training data changed')
    from safetensors.torch import load_file
    write(out / 'final_tensors.json', tensor_fingerprint(load_file(out / 'sft/adapter/adapter_model.safetensors')))
    emit('TRAIN_SAVED', {'replica': name, 'adapter_sha256': report['arms']['sft']['adapter_sha256'],
                         'updates': 24, 'examples': 48})


def merge(root, name):
    import run_pilot
    out = root / 'artifacts' / name
    locations = read(root / 'artifacts/setup/locations.json')
    write(out / 'model.json', {'snapshot': locations[MODEL]['snapshot']})
    run_pilot.merge_stage(root / 'source', out, ('sft',))
    # The exact merged inference weights are fingerprinted; only adapters are backed up remotely.
    write(out / 'merged_files.json', {p.name: sha(p) for p in sorted((out / 'merged/sft').iterdir()) if p.is_file()})


def inputs(root, processor, config):
    from mmdl.evaluation.datasets.mmmu import load_validation, separate_sample
    from mmdl.evaluation.prompt import build_messages
    from mmdl.evaluation.backends.input_preparation import prepare_protocol_inputs
    from mmdl.runtime.artifacts import digest
    from mmdl.runtime.contracts import sample_seed
    protocol = read(root / 'source/protocol.json')
    data = Path(read(root / 'artifacts/setup/locations.json')['MMMU/MMMU']['data_root'])
    datasets, _ = load_validation(data)
    expected = read(root / 'source/eval_lock.json')[:24]
    by_id = {row['id']: (subject, row) for subject, rows in datasets.items() for row in rows}
    if sorted(by_id) != [r['id'] for r in read(root / 'source/eval_lock.json')]:
        raise ValueError('Pinned dataset ID/order changed')
    rows, prompts = [], []
    for lock in expected:
        subject, row = by_id[lock['id']]
        sample, images, gold = separate_sample(row, subject)
        messages = build_messages(sample, images, root / 'MMDL')
        prepared, processed = prepare_protocol_inputs(processor, config, messages, images, protocol['image'])
        observed = {'id': sample['id'], 'subject': subject, 'input_sha256': prepared['input_sha256'],
                    'actual_engine_prompt_token_ids_sha256': digest(prepared['prompt_token_ids']),
                    'seed': sample_seed(3407, sample['id']), 'input_tokens': prepared['input_tokens']}
        if any(observed[k] != lock[k] for k in observed):
            raise ValueError(f"Frozen P0/seed/image/prompt changed: {sample['id']}")
        if prepared['input_tokens'] + 2048 > 12288:
            raise ValueError('Fixed context exceeded')
        rows.append(sample | gold | observed)
        prompts.append({'prompt': prepared['chat_prompt'], 'multi_modal_data': {'image': processed}})
    return protocol, rows, prompts


def infer(root, name):
    import run_pilot
    from transformers import AutoConfig, AutoProcessor
    from vllm import SamplingParams
    from mmdl.runtime.artifacts import digest
    from mmdl.evaluation.final_answer_parser_v8 import score_response
    artifacts = root / 'artifacts'
    write(artifacts / 'inference' / f'{name}-environment.json', environment())
    base = Path(read(artifacts / 'setup/locations.json')[MODEL]['snapshot'])
    replica = name.split('_')[0]
    model = base if replica == 'base' else artifacts / replica / 'merged/sft'
    processor = AutoProcessor.from_pretrained(model, local_files_only=True, use_fast=True)
    cfg = AutoConfig.from_pretrained(model, local_files_only=True)
    settings = read(root / 'source/protocol.json')
    size = {'shortest_edge': settings['image']['min_pixels'], 'longest_edge': settings['image']['max_pixels']}
    processor.image_processor.size = size
    protocol, rows, prompts = inputs(root, processor, cfg)
    # Original base engine loaded this dormant processor; base requests have no cue extra_args.
    extra = {'logits_processors': ['experiment:FinishCue']} if replica == 'base' else {}
    llm = run_pilot.engine(model, {'size': size, 'do_resize': False}, 8, 12288,
                          max(len(p['multi_modal_data']['image']) for p in prompts), **extra)
    g = protocol['generation']
    params = [SamplingParams(n=1, seed=r['seed'], max_tokens=2048, temperature=g['temperature'],
              top_p=g['top_p'], top_k=g['top_k'], repetition_penalty=g['repetition_penalty'],
              presence_penalty=g['presence_penalty']) for r in rows]
    tick = time.monotonic()
    outputs = llm.generate(prompts, params, use_tqdm=False)
    seconds = time.monotonic() - tick
    results = []
    for row, output in zip(rows, outputs, strict=True):
        result, = output.outputs
        if not output.finished or digest(list(output.prompt_token_ids)) != row['actual_engine_prompt_token_ids_sha256']:
            raise ValueError('Actual vLLM input prompt identity changed')
        grade = score_response(result.text, row['question_type'], row['options'], row['answer'],
                               result.finish_reason, question=row['question'])
        if not 0 < len(result.token_ids) <= 2048:
            raise ValueError('Response validation failed')
        results.append(row | grade | {'raw_response': result.text, 'token_ids': list(result.token_ids),
                       'generated_tokens': len(result.token_ids), 'finish_reason': result.finish_reason,
                       'stop_reason': result.stop_reason})
    report = {'name': name, 'count': 24, 'window': 24, 'max_num_seqs': 8, 'context': 12288,
              'cap': 2048, 'generation_seconds': seconds, 'engine_seed': 3407,
              'correct': sum(r['correct'] for r in results), 'total_tokens': sum(r['generated_tokens'] for r in results),
              'rows': results}
    write(artifacts / 'inference' / f'{name}.json', report)
    emit('INFERENCE_SAVED', {k: v for k, v in report.items() if k != 'rows'})


def compare(root):
    from safetensors.torch import load_file
    from mmdl.evaluation.final_answer_parser_v8 import score_response
    from run_full import SCORE_FIELDS
    import torch
    artifacts = root / 'artifacts'
    # Re-open saved raw outputs in a separate process and regrade all 120 responses.
    regraded = 0
    for name in ('base_1', 'base_2', 'A_1', 'A_2', 'B_1'):
        report = read(artifacts / 'inference' / (name + '.json'))
        if len(report['rows']) != 24 or len({r['id'] for r in report['rows']}) != 24:
            raise ValueError('Incomplete or duplicate inference response coverage')
        for row in report['rows']:
            grade = score_response(row['raw_response'], row['question_type'], row['options'], row['answer'],
                                   row['finish_reason'], question=row['question'])
            if any(row[k] != grade[k] for k in SCORE_FIELDS):
                raise ValueError('Independent saved-response V8 regrade mismatch')
            regraded += 1
    a, b = (read(artifacts / n / 'training.json') for n in ('A', 'B'))
    ta, tb = (read(artifacts / n / 'numerical_trace.json') for n in ('A', 'B'))
    weights = [load_file(artifacts / n / 'sft/adapter/adapter_model.safetensors') for n in ('A', 'B')]
    if set(weights[0]) != set(weights[1]) or a['epoch_orders'] != b['epoch_orders']:
        raise ValueError('Replicas have different tensor sets or example orders')
    tensor_differences = []
    for name, left in weights[0].items():
        right = weights[1][name]
        delta = (left.double() - right.double()).abs()
        tensor_differences.append({'name': name, 'equal': torch.equal(left, right),
                                  'max_abs': float(delta.max()), 'mean_abs': float(delta.mean())})
    steps = [{'step': x['step'], 'loss_delta': y['loss'] - x['loss'],
              'gradient_norm_delta': y['gradient_norm'] - x['gradient_norm'],
              'gradient_hash_equal': u['sha256'] == v['sha256']}
             for x, y, u, v in zip(a['steps'], b['steps'], ta['gradients_before_clip'],
                                   tb['gradients_before_clip'], strict=True)]

    def paired(left_name, right_name):
        left, right = (read(artifacts / 'inference' / (n + '.json')) for n in (left_name, right_name))
        pairs = []
        for x, y in zip(left['rows'], right['rows'], strict=True):
            if any(x[k] != y[k] for k in ('id', 'input_sha256', 'actual_engine_prompt_token_ids_sha256', 'seed')):
                raise ValueError('Paired inference input mismatch')
            pairs.append({'id': x['id'], 'tokens_equal': x['token_ids'] == y['token_ids'],
                          'raw_equal': x['raw_response'] == y['raw_response'],
                          'finish_equal': (x['finish_reason'], x['stop_reason']) == (y['finish_reason'], y['stop_reason']),
                          'left_correct': x['correct'], 'right_correct': y['correct'],
                          'left_tokens': x['generated_tokens'], 'right_tokens': y['generated_tokens']})
        return {'left': left_name, 'right': right_name,
                'exact_responses': sum(r['tokens_equal'] and r['raw_equal'] and r['finish_equal'] for r in pairs),
                'left_correct': left['correct'], 'right_correct': right['correct'], 'rows': pairs}

    result = {'status': 'PROBE_COMPLETE', 'training_examples': 48, 'updates_per_replica': 24,
              'train_sha256': TRAIN_SHA, 'bundle_sha256': BUNDLE_SHA,
              'initial_tensors_equal': ta['initial']['sha256'] == tb['initial']['sha256'],
              'adapter_bytes_equal': a['arms']['sft']['adapter_sha256'] == b['arms']['sft']['adapter_sha256'],
              'adapter_A_sha256': a['arms']['sft']['adapter_sha256'],
              'adapter_B_sha256': b['arms']['sft']['adapter_sha256'],
              'independent_v8_regrades': regraded,
              'final_equal_tensors': sum(d['equal'] for d in tensor_differences),
              'tensor_differences': tensor_differences, 'steps': steps,
              'inference': [paired('base_1', 'base_2'), paired('A_1', 'A_2'), paired('A_1', 'B_1')],
              'scope': 'Original first complete 24-item window. Five independent fresh processes. No claim of full-900 or batch invariance.',
              'limitations': ['The original 493-point adapter is unavailable.',
                  'Two training replicas with one seed do not estimate multi-seed uncertainty.',
                  'The first 24-item window is a determinism probe, not a representative accuracy sample.',
                  'No strict deterministic kernels or attention implementation changes were introduced.']}
    write(artifacts / 'comparison.json', result)
    emit('COMPLETE', {k: result[k] for k in ('status', 'initial_tensors_equal', 'adapter_bytes_equal', 'final_equal_tensors')}
         | {'inference_exact': [p['exact_responses'] for p in result['inference']]})


def launch(bundle, root, backup=None, release=None, max_seconds=2 * 3600):
    """Colab host orchestrator. backup must persist and read-back verify stage artifacts."""
    root, bundle = Path(root), Path(bundle)
    root.mkdir(exist_ok=False)
    artifacts = root / 'artifacts'
    artifacts.mkdir()
    deadline = time.monotonic() + max_seconds
    success = False
    stage = 'unpack'
    if release is None or backup is None:
        raise ValueError('Colab launch requires explicit verified backup and release callbacks')
    watchdog = threading.Timer(max_seconds + 180, release)
    watchdog.daemon = True
    watchdog.start()
    env = runtime_env(root)

    def run(label, args, cap=None):
        nonlocal stage
        stage = label
        emit('PHASE', {'stage': label, 'remaining_seconds': round(deadline - time.monotonic())})
        timeout = min(deadline - time.monotonic(), cap or max_seconds)
        if timeout <= 0:
            raise TimeoutError(label)
        log_path = artifacts / 'logs' / (label + '.log')
        log_path.parent.mkdir(exist_ok=True)
        with log_path.open('x') as log, subprocess.Popen([str(x) for x in args], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace',
                start_new_session=True, bufsize=1) as proc:
            def stop():
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
            timer = threading.Timer(timeout, stop)
            timer.daemon = True
            timer.start()
            try:
                for line in proc.stdout:
                    log.write(line)
                    if line.startswith(('REPRO_', 'FULL_', 'PREF_')):
                        log.flush()
                        print(line, end='', flush=True)
                code = proc.wait()
                if code:
                    print(log_path.read_text()[-4500:], flush=True)
                    raise RuntimeError(f'{label} exited {code}')
            finally:
                timer.cancel()
                stop()
        backup(artifacts, label)

    try:
        gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                                       '--format=csv,noheader'], text=True, timeout=15).strip()
        if '\n' in gpu or 'NVIDIA L4' not in gpu or shutil.disk_usage(root).free < 60 * 2**30:
            raise RuntimeError('Require one L4 and 60 GiB free disk: ' + gpu)
        manifest = unpack(bundle, root / 'source')
        write(artifacts / 'source_manifest.json', manifest)
        shutil.copy2(__file__, artifacts / 'reproduce.py')
        shutil.copy2(bundle, artifacts / 'frozen_bundle.zip')
        write(artifacts / 'driver.json', {'status': 'RUNNING', 'gpu': gpu, 'start_unix': time.time(),
                                         'max_seconds': max_seconds})
        backup(artifacts, 'before_model_download')
        run('clone', ['git', 'clone', '--quiet', 'https://github.com/jang2296/MMDL.git', root / 'MMDL'], 180)
        run('pin', ['git', '-C', root / 'MMDL', 'checkout', '--detach', COMMIT], 30)
        run('uv', [sys.executable, '-m', 'pip', 'install', '--quiet', 'uv'], 180)
        run('venv', ['uv', 'venv', '--python', '3.12.3', root / 'env'], 300)
        python = root / 'env/bin/python'
        run('pip', ['uv', 'pip', 'install', '--python', python, 'pip==25.2'], 120)
        run('packages', [python, '-m', 'pip', 'install', '--disable-pip-version-check',
                         '-r', root / 'MMDL/env/requirements-vllm.lock'], 1800)
        run('project', ['uv', 'pip', 'install', '--python', python, '--no-deps', '-e', root / 'MMDL'], 120)
        run('environment', [python, __file__, 'environment', root], 120)
        run('download', [python, '-m', 'mmdl.data.download', '--skip-pro', '--cache', root / 'hf',
                          '--data-root', root / 'data', '--artifact-root', artifacts], 1800)
        for name in ('A', 'B'):
            run('train_' + name, [python, __file__, 'train', root, name], 900)
            run('merge_' + name, [python, __file__, 'merge', root, name], 300)
        for name in ('base_1', 'base_2', 'A_1', 'A_2', 'B_1'):
            run('infer_' + name, [python, __file__, 'infer', root, name], 900)
        run('compare', [python, __file__, 'compare', root], 120)
        success = True
    finally:
        old = read(artifacts / 'driver.json') if (artifacts / 'driver.json').exists() else {}
        write(artifacts / 'driver.json', old | {'status': 'COMPLETE' if success else 'FAILED',
                                               'last_stage': stage, 'end_unix': time.time()})
        try:
            backup(artifacts, 'final')
            emit('FINAL_BACKUP_VERIFIED', {'status': 'COMPLETE' if success else 'FAILED'})
        except BaseException as error:
            write(artifacts / 'backup_failure.json', {'status': 'BACKUP_NEEDS_ATTENTION',
                  'stage': stage, 'error': str(error), 'compute_complete': success})
            emit('BACKUP_NEEDS_ATTENTION', {'stage': stage, 'error': str(error)})
            raise
        finally:
            watchdog.cancel()
            emit('RELEASE_REQUEST', {'unix': time.time()})
            release()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['audit', 'environment', 'train', 'merge', 'infer', 'compare'])
    p.add_argument('path', type=Path)
    p.add_argument('name', nargs='?')
    a = p.parse_args()
    if a.stage == 'audit':
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            m = unpack(a.path, Path(d) / 'bundle')
            emit('AUDIT_PASS', {'files': len(m['files']), 'train_examples': 48, 'locked_eval_ids': 900,
                                'training_uses_mmmu': False})
    elif a.stage == 'environment':
        write(a.path / 'artifacts/environment.json', environment())
        for entry in read(a.path / 'source/scorer_source.json')['files']:
            if sha(a.path / 'MMDL' / entry['path']) != entry['sha256']:
                raise ValueError('Pinned V8 scoring source changed: ' + entry['path'])
    elif a.stage in ('train', 'merge', 'infer'):
        globals()[a.stage](a.path, a.name)
    else:
        compare(a.path)


if __name__ == '__main__':
    main()
