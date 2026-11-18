"""Evaluate the already verified finish-SFT adapter; never train or select weights.

Resume only the missing original window38; fresh full SFT900. Frozen MMMU/P0/V8 and identical windows. No new training.
The notebook persists verified incremental output packets through the sidebar.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
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

CORE_SHA = '49e2126670434e0ca1960d758a2d08c8bd2664f59f57423fe55f9dcaccf5fffe'
ADAPTER_SHA = '90f0afaf72f22c622fd7e533514b02efd0b650d07589ff5773f6864b952188f8'
JOB = 'finish-sft-deterministic-full-20261119'
HERE = Path(__file__).resolve().parent
if hashlib.sha256((HERE / 'reproduce.py').read_bytes()).hexdigest() != CORE_SHA:
    raise ValueError('Frozen evaluation core changed')
spec = importlib.util.spec_from_file_location('frozen_finish_core', HERE / 'reproduce.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def emit(event, value):
    print('EVAL900_' + event + ' ' + json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def runtime_env(root):
    env = core.runtime_env(root)
    env.update(CUBLAS_WORKSPACE_CONFIG=':4096:8', PYTHONHASHSEED='3407',
               OMP_NUM_THREADS='6', MKL_NUM_THREADS='6')
    return env


def prepare(root):
    import run_pilot
    from safetensors.torch import load_file
    import torch
    out = root / 'restored/A'
    if core.sha(out / 'sft/adapter/adapter_model.safetensors') != ADAPTER_SHA:
        raise ValueError('Not the already verified deterministic adapter')
    weights = load_file(out / 'sft/adapter/adapter_model.safetensors')
    observed = core.tensor_fingerprint(weights)
    if observed != core.read(out / 'final_tensors.json') or len(weights) != 144:
        raise ValueError('Restored actual 144 tensor identities differ')
    if not all(torch.isfinite(w).all() for w in weights.values()):
        raise ValueError('Non-finite restored weights')
    locations = core.read(root / 'artifacts/setup/locations.json')
    core.write(out / 'model.json', {'snapshot': locations[core.MODEL]['snapshot']})
    run_pilot.merge_stage(root / 'source', out, ('sft',))
    actual = {p.name: core.sha(p) for p in (out / 'merged/sft').glob('*.safetensors')}
    expected = {k: v for k, v in core.read(out / 'merged_files.json').items() if k.endswith('.safetensors')}
    if not actual or actual != expected:
        raise ValueError('Merged inference weight bytes differ from verified 24-item run')
    core.write(root / 'artifacts/adapter-identity.json', {'adapter_sha256': ADAPTER_SHA,
        'tensor_count': len(weights), 'all_tensors_match': True, 'merged_weight_hashes': actual,
        'merged_weight_bytes_match_previous': True, 'new_training_updates': 0})
    emit('ADAPTER_VERIFIED', {'adapter_sha256': ADAPTER_SHA, 'tensors': 144, 'new_updates': 0})


def make_inputs(root, processor, cfg):
    from mmdl.evaluation.datasets.mmmu import load_validation, separate_sample
    from mmdl.evaluation.prompt import build_messages
    from mmdl.evaluation.backends.input_preparation import prepare_protocol_inputs
    from mmdl.runtime.artifacts import digest
    from mmdl.runtime.contracts import sample_seed
    protocol = core.read(root / 'source/protocol.json')
    locations = core.read(root / 'artifacts/setup/locations.json')
    datasets, _ = load_validation(Path(locations['MMMU/MMMU']['data_root']))
    locked = core.read(root / 'source/eval_lock.json')
    by_id = {r['id']: (subject, r) for subject, rows in datasets.items() for r in rows}
    if len(by_id) != 900 or sorted(by_id) != [r['id'] for r in locked]:
        raise ValueError('Missing/duplicate/changed MMMU IDs')
    rows, prompts = [], []
    for lock in locked:
        subject, raw = by_id[lock['id']]
        sample, images, gold = separate_sample(raw, subject)
        messages = build_messages(sample, images, root / 'MMDL')
        prepared, processed = prepare_protocol_inputs(processor, cfg, messages, images, protocol['image'])
        observed = {'id': sample['id'], 'subject': subject, 'input_sha256': prepared['input_sha256'],
            'actual_engine_prompt_token_ids_sha256': digest(prepared['prompt_token_ids']),
            'seed': sample_seed(3407, sample['id']), 'input_tokens': prepared['input_tokens']}
        if any(observed[k] != lock[k] for k in observed) or prepared['input_tokens'] + 2048 > 12288:
            raise ValueError('Frozen P0/image/seed/prompt/context changed: ' + sample['id'])
        rows.append(sample | gold | observed)
        prompts.append({'prompt': prepared['chat_prompt'], 'multi_modal_data': {'image': processed}})
    return protocol, rows, prompts


def infer(root, arm):
    import run_pilot
    from transformers import AutoConfig, AutoProcessor
    from vllm import SamplingParams
    from mmdl.runtime.artifacts import digest
    from mmdl.evaluation.final_answer_parser_v8 import score_response
    if arm not in ('base', 'sft'):
        raise ValueError('Unknown evaluation arm')
    out = root / 'artifacts'
    core.write(out / f'{arm}-environment.json', core.environment())
    base = Path(core.read(out / 'setup/locations.json')[core.MODEL]['snapshot'])
    path = base if arm == 'base' else root / 'restored/A/merged/sft'
    processor = AutoProcessor.from_pretrained(path, local_files_only=True, use_fast=True)
    cfg = AutoConfig.from_pretrained(path, local_files_only=True)
    protocol = core.read(root / 'source/protocol.json')
    size = {'shortest_edge': protocol['image']['min_pixels'], 'longest_edge': protocol['image']['max_pixels']}
    processor.image_processor.size = size
    protocol, rows, prompts = make_inputs(root, processor, cfg)
    extra = {'logits_processors': ['experiment:FinishCue']} if arm == 'base' else {}
    llm = run_pilot.engine(path, {'size': size, 'do_resize': False}, 8, 12288,
        max(len(p['multi_modal_data']['image']) for p in prompts), **extra)
    g = protocol['generation']
    prior_files = sorted((out / 'responses').glob(f'{arm}-*.json'))
    if arm == 'sft' and prior_files:
        raise ValueError('SFT900 was not previously started; no rerun allowed')
    prior = [r for p in prior_files for r in core.read(p)['rows']]
    if arm == 'base' and (len(prior_files) != 37 or len(prior) != 888):
        raise ValueError('Exactly the verified 37 original windows must exist')
    for i, r in enumerate(prior):
        if any(r[k] != rows[i][k] for k in ('id','input_sha256','actual_engine_prompt_token_ids_sha256','seed')):
            raise ValueError('Resumed sample lock changed')
        grade = score_response(r['raw_response'], r['question_type'], r['options'], r['answer'], r['finish_reason'], question=r['question'])
        if any(r[k] != grade[k] for k in grade):
            raise ValueError('Restored V8 grade changed')
    seen = {r['id'] for r in prior}
    generation_seconds = sum(core.read(p)['generation_seconds'] for p in prior_files)
    correct = sum(r['correct'] for r in prior)
    emit('RESUME', {'arm':arm,'preserved_windows':len(prior_files),'preserved_n':len(prior)})
    for number, start in enumerate(range(0, 900, 24), 1):
        if number <= len(prior_files):
            continue
        group = rows[start:start+24]
        params = [SamplingParams(n=1, seed=r['seed'], max_tokens=2048,
            temperature=g['temperature'], top_p=g['top_p'], top_k=g['top_k'],
            repetition_penalty=g['repetition_penalty'], presence_penalty=g['presence_penalty']) for r in group]
        tick = time.monotonic()
        outputs = llm.generate(prompts[start:start+24], params, use_tqdm=False)
        seconds = time.monotonic() - tick
        generation_seconds += seconds
        records = []
        for row, output in zip(group, outputs, strict=True):
            result, = output.outputs
            if (row['id'] in seen or not output.finished or not 0 < len(result.token_ids) <= 2048
                or result.finish_reason not in ('stop', 'length')
                or digest(list(output.prompt_token_ids)) != row['actual_engine_prompt_token_ids_sha256']):
                raise ValueError('Invalid, duplicate or changed inference: ' + row['id'])
            seen.add(row['id'])
            grade = score_response(result.text, row['question_type'], row['options'], row['answer'],
                                   result.finish_reason, question=row['question'])
            metric_names = ('arrival_time','first_scheduled_time','first_token_time','finished_time',
                            'time_in_queue','scheduler_time','model_forward_time','model_execute_time')
            metrics = {k: getattr(output.metrics, k, None) for k in metric_names} if output.metrics else None
            records.append(row | grade | {'arm': arm, 'raw_response': result.text,
                'token_ids': list(result.token_ids), 'generated_tokens': len(result.token_ids),
                'finish_reason': result.finish_reason, 'stop_reason': result.stop_reason,
                'request_id': ('continuation:' + output.request_id) if arm == 'base' else output.request_id,
                'engine_request_id': output.request_id, 'process': 'continuation', 'metrics': metrics,
                'window': number, 'window_generation_seconds': seconds,
                'hit_cap': len(result.token_ids) == 2048, 'route': 'free'})
        correct += sum(r['correct'] for r in records)
        core.write(out / 'responses' / f'{arm}-{number:03d}.json', {'arm': arm, 'window': number,
            'generation_seconds': seconds, 'rows': records})
        progress = {'arm': arm, 'n': len(seen), 'target': 900, 'correct': correct,
                    'windows': number, 'generation_seconds': generation_seconds}
        core.write(out / f'{arm}-progress.json', progress)
        emit('PROGRESS', progress)
        # Disk is incremental per window; verified own-Drive output backup every six windows.
        if number % 6 == 0 or len(seen) == 900:
            label = f'{arm}_{number:03d}'
            emit('CHECKPOINT_REQUEST', {'stage': label})
            if input().strip() != 'CHECKPOINT_VERIFIED':
                raise ValueError('Checkpoint was not externally verified')
    if len(seen) != 900:
        raise ValueError('Incomplete inference')
    emit('ARM_COMPLETE', progress)


def collect(root, arm):
    files = sorted((root / 'artifacts/responses').glob(f'{arm}-*.json'))
    if len(files) != 38:
        raise ValueError('Incomplete response windows')
    records = [r for p in files for r in core.read(p)['rows']]
    if len(records) != 900 or len({r['id'] for r in records}) != 900:
        raise ValueError('Missing/duplicate response IDs')
    return records


def compare(root):
    from mmdl.evaluation.final_answer_parser_v8 import score_response
    from run_full import SCORE_FIELDS
    arms = {arm: collect(root, arm) for arm in ('base','sft')}
    locked = core.read(root / 'source/eval_lock.json')
    for arm, rows in arms.items():
        for r, lock in zip(rows, locked, strict=True):
            if any(r[k] != lock[k] for k in lock):
                raise ValueError('Saved response identity differs: ' + r['id'])
            grade = score_response(r['raw_response'], r['question_type'], r['options'], r['answer'],
                                   r['finish_reason'], question=r['question'])
            if any(r[k] != grade[k] for k in SCORE_FIELDS):
                raise ValueError('Independent V8 regrade mismatch')
    result = {'status':'COMPLETE', 'arms': {a: {'n':900, 'correct':sum(r['correct'] for r in rs),
        'generated_tokens':sum(r['generated_tokens'] for r in rs),
        'hit_cap':sum(r['hit_cap'] for r in rs),
        'no_parse':sum(r['parse_status'] != 'PARSED' for r in rs),
        'generation_seconds':core.read(root / f'artifacts/{a}-progress.json')['generation_seconds']}
        for a,rs in arms.items()}, 'independent_v8_regrades':1800,
        'adapter_sha256':ADAPTER_SHA, 'new_training_updates':0,
        'conditions':{'cap':2048,'engine_seed':3407,'request_seed':'per_sample_sha256_v1',
            'MP':0,'window':24,'max_num_seqs':8,'context':12288,'parser':'pinned V8',
            'forced_cue':False,'fresh_process_per_arm':True}}
    core.write(root / 'artifacts/comparison.json', result)
    emit('COMPLETE', result)


def launch(bundle, adapter_bundle, root, backup, release, max_seconds=18000, resume_bundle=None):
    root = Path(root)
    root.mkdir(exist_ok=False)
    out = root / 'artifacts'
    out.mkdir()
    env = runtime_env(root)
    deadline = time.monotonic() + max_seconds
    watchdog = threading.Timer(max_seconds + 180, release)
    watchdog.daemon = True
    watchdog.start()
    stage = 'restore'
    success = False

    def run(label, args, cap):
        nonlocal stage
        stage = label
        timeout = min(cap, deadline - time.monotonic())
        if timeout <= 0:
            raise TimeoutError(label)
        emit('PHASE', {'stage':label,'remaining_seconds':round(deadline-time.monotonic())})
        logfile = out / 'logs' / (label + '.log')
        logfile.parent.mkdir(exist_ok=True)
        with logfile.open('x') as log, subprocess.Popen([str(x) for x in args], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors='replace', start_new_session=True, bufsize=1) as proc:
            def stop():
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try: proc.wait(timeout=15)
                    except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL)
            timer = threading.Timer(timeout,stop)
            timer.daemon = True
            timer.start()
            try:
                for line in proc.stdout:
                    log.write(line)
                    if line.startswith(('EVAL900_','REPRO_','PREF_')):
                        log.flush()
                        print(line,end='',flush=True)
                    if line.startswith('EVAL900_CHECKPOINT_REQUEST '):
                        checkpoint = json.loads(line.split(' ',1)[1])['stage']
                        backup(out,checkpoint)
                        proc.stdin.write('CHECKPOINT_VERIFIED\n')
                        proc.stdin.flush()
                code = proc.wait()
                if code:
                    print(logfile.read_text()[-5000:],flush=True)
                    raise RuntimeError(f'{label} exited {code}')
            finally:
                timer.cancel()
                stop()

    try:
        gpu = subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total',
                                      '--format=csv,noheader'],text=True,timeout=15).strip()
        if '\n' in gpu or 'NVIDIA L4' not in gpu or shutil.disk_usage(root).free < 60*2**30:
            raise ValueError('One L4 and 60 GiB free disk required: '+gpu)
        core.unpack(bundle,root/'source')
        with zipfile.ZipFile(adapter_bundle) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or z.testzip() is not None:
                raise ValueError('Duplicate or corrupt adapter bundle')
            for name in names:
                p=Path(name)
                if p.is_absolute() or '..' in p.parts or name.endswith('/'):
                    raise ValueError('Unsafe adapter bundle member')
                dest=root/'restored'/p
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read(name))
        core.write(out/'driver.json',{'status':'RUNNING','gpu':gpu,'start_unix':time.time(),
                   'max_seconds':max_seconds,'adapter_sha256':ADAPTER_SHA,'new_training_updates':0})
        if resume_bundle is None:
            raise ValueError('Explicit verified888 recovery bundle required')
        with zipfile.ZipFile(resume_bundle) as z:
            manifest=json.loads(z.read('_resume_manifest.json'))
            assert manifest['n']==888 and manifest['initial_source_sha256']=='bd8ff39a7dbbdb33755107a243960b27507ed9d20849052903a667c4eaae2d50'
            assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
            assert set(z.namelist())==set(manifest['files'])|{'_resume_manifest.json'}
            for name, expected in manifest['files'].items():
                p=Path(name)
                assert not p.is_absolute() and '..' not in p.parts
                assert name.startswith(('responses/base-','receipts/')) or name=='base-progress.json'
                raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==expected
                dest=out/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            core.write(out/'resume-provenance.json',manifest | {'bundle_sha256':core.sha(resume_bundle),
                'caveat':'Original first888 preserved; original last12 in a new process. SFT900 one fresh process. Seed alone does not prove batch invariance.'})
        core.write(out/'source-manifest.json',{'evaluation_source_sha256':core.sha(__file__),
            'core_sha256':CORE_SHA,'frozen_bundle_sha256':core.BUNDLE_SHA,
            'adapter_bundle_sha256':core.sha(adapter_bundle),'adapter_sha256':ADAPTER_SHA})
        run('clone',['git','clone','--quiet','https://github.com/jang2296/MMDL.git',root/'MMDL'],180)
        run('pin',['git','-C',root/'MMDL','checkout','--detach',core.COMMIT],30)
        run('uv',[sys.executable,'-m','pip','install','--quiet','uv'],180)
        run('venv',['uv','venv','--python','3.12.3',root/'env'],300)
        python=root/'env/bin/python'
        run('pip',['uv','pip','install','--python',python,'pip==25.2'],120)
        run('packages',[python,'-m','pip','install','--disable-pip-version-check',
            '-r',root/'MMDL/env/requirements-vllm.lock'],1800)
        run('project',['uv','pip','install','--python',python,'--no-deps','-e',root/'MMDL'],120)
        run('environment',[python,HERE/'reproduce.py','environment',root],120)
        run('download',[python,'-m','mmdl.data.download','--skip-pro','--cache',root/'hf',
            '--data-root',root/'data','--artifact-root',out],1800)
        run('adapter',[python,__file__,'prepare',root],600)
        backup(out,'prepared')
        for arm in ('base','sft'):
            run('infer_'+arm,[python,__file__,'infer',root,arm],1800 if arm=='base' else 14400)
        run('compare',[python,__file__,'compare',root],180)
        backup(out,'comparison')
        success=True
    finally:
        old=core.read(out/'driver.json') if (out/'driver.json').exists() else {}
        core.write(out/'driver.json',old|{'status':'COMPLETE' if success else 'FAILED',
            'last_stage':stage,'end_unix':time.time()})
        try: backup(out,'final')
        finally:
            watchdog.cancel()
            emit('RELEASE_REQUEST',{'unix':time.time()})
            release()


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','infer','compare'])
    p.add_argument('root',type=Path)
    p.add_argument('arm',nargs='?')
    args=p.parse_args()
    if args.stage=='infer': infer(args.root,args.arm)
    else: globals()[args.stage](args.root)
