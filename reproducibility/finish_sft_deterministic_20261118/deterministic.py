"""Diagnose fixed-input SDPA backward and repeat the frozen finish SFT deterministically.

The immutable original train function, data and inference implementation are reused.
Only numerical execution controls are changed. No new training targets or MMMU training.
"""
from __future__ import annotations
import argparse
from contextlib import nullcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback

CORE_SHA = '49e2126670434e0ca1960d758a2d08c8bd2664f59f57423fe55f9dcaccf5fffe'
JOB = 'finish-sft-deterministic-20261118'
SEED = 3407
HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / 'reproduce.py'
if not CORE_PATH.exists():
    CORE_PATH = HERE.parent / 'finish_sft_20261118/reproduce.py'
if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA:
    raise ValueError('Immutable original audit core differs')
_spec = importlib.util.spec_from_file_location('frozen_finish_repro', CORE_PATH)
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)


def emit(event, value):
    print('DETER_' + event + ' ' + json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def runtime_env(root):
    env = core.runtime_env(root)
    env.update(CUBLAS_WORKSPACE_CONFIG=':4096:8', PYTHONHASHSEED=str(SEED),
               OMP_NUM_THREADS='6', MKL_NUM_THREADS='6')
    return env


def configure(policy):
    import numpy as np
    import torch
    if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8' or os.environ.get('PYTHONHASHSEED') != str(SEED):
        raise ValueError('Deterministic environment must be set before starting the process')
    strict = policy != 'legacy'
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(strict, warn_only=False)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = strict
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = not strict  # Match the observed legacy setting in diagnosis.
    torch.backends.cuda.enable_flash_sdp(True)
    torch.backends.cuda.enable_mem_efficient_sdp(True)
    torch.backends.cuda.enable_math_sdp(True)
    torch.backends.cuda.enable_cudnn_sdp(True)
    if strict:
        torch.set_float32_matmul_precision('highest')
        torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
        torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
        torch.backends.cuda.allow_fp16_bf16_reduction_math_sdp(False)
    result = core.environment()
    result.update(policy=policy, deterministic_warn_only=torch.is_deterministic_algorithms_warn_only_enabled(),
                  torch_interop_threads=torch.get_num_interop_threads(),
                  cudnn_sdp=torch.backends.cuda.cudnn_sdp_enabled(),
                  fp16_reduced_precision_reduction=torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction,
                  bf16_reduced_precision_reduction=torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction,
                  math_sdp_low_precision_reduction=torch.backends.cuda.fp16_bf16_reduction_math_sdp_allowed())
    if strict and (not result['deterministic_algorithms'] or result['deterministic_warn_only']):
        raise ValueError('Strict deterministic algorithms were not enabled')
    return result


def backend_context(policy):
    if policy == 'strict_math':
        from torch.nn.attention import sdpa_kernel, SDPBackend
        return sdpa_kernel(SDPBackend.MATH)
    return nullcontext()


def relevant_ops(profiler):
    return [{'name': event.key, 'count': event.count} for event in profiler.key_averages()
            if any(word in event.key.lower() for word in ('scaled_dot_product', 'flash_attention', 'efficient_attention', 'cudnn_attention'))]


def sdpa_replay(captured, original_sdpa):
    """Only the deterministic flag is changed in the first two fixed-input arms."""
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    q, k, v = captured['qkv']
    dout = captured['dout']
    assert captured['kwargs'].get('dropout_p', captured['args'][1] if len(captured['args']) > 1 else 0.0) == 0
    original_flag = torch.are_deterministic_algorithms_enabled()
    result = {}
    fixed = core.tensor_fingerprint({'q': q, 'k': k, 'v': v, 'dout': dout})
    for name, deterministic, math_only in [('default_repeat', False, False),
                                           ('deterministic_flag', True, False),
                                           ('math_reference', True, True)]:
        runs, first_grads = [], None
        try:
            torch.use_deterministic_algorithms(deterministic, warn_only=False)
            for repeat in range(3):
                torch.manual_seed(SEED)
                inputs = [x.detach().clone(memory_format=torch.preserve_format).requires_grad_(True) for x in (q, k, v)]
                input_fp = core.tensor_fingerprint(dict(zip(('q', 'k', 'v'), inputs)) | {'dout': dout})
                if input_fp != fixed:
                    raise ValueError('SDPA replay input bits changed')
                ctx = sdpa_kernel(SDPBackend.MATH) if math_only else nullcontext()
                prof_ctx = torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) if repeat == 0 else nullcontext()
                with ctx, prof_ctx as profiler:
                    output = original_sdpa(*inputs, *captured['args'], **captured['kwargs'])
                    output_fp = core.tensor_fingerprint({'output': output})
                    gradients = torch.autograd.grad(output, inputs, grad_outputs=dout)
                torch.cuda.synchronize()
                gradient_fp = core.tensor_fingerprint(dict(zip(('dq', 'dk', 'dv'), gradients)))
                if first_grads is None:
                    first_grads = [g.detach().clone() for g in gradients]
                maximum = max(float((a.float() - b.float()).abs().max()) for a, b in zip(first_grads, gradients, strict=True))
                runs.append({'repeat': repeat, 'input_sha256': input_fp['sha256'],
                             'output_sha256': output_fp['sha256'], 'gradient_sha256': gradient_fp['sha256'],
                             'gradient_tensors': gradient_fp['tensors'], 'max_abs_gradient_delta_from_first': maximum,
                             'strides_preserved': [list(i.stride()) == list(s.stride()) for i, s in zip(inputs, (q, k, v), strict=True)]})
                if repeat == 0:
                    operators = relevant_ops(profiler)
                del output, gradients, inputs
            result[name] = {'deterministic_algorithms': deterministic, 'math_only': math_only,
                            'operators': operators, 'runs': runs,
                            'unique_outputs': len({r['output_sha256'] for r in runs}),
                            'unique_gradients': len({r['gradient_sha256'] for r in runs})}
        except Exception as error:
            result[name] = {'error': repr(error), 'traceback': traceback.format_exc(), 'runs': runs}
        finally:
            del first_grads
            torch.cuda.empty_cache()
    torch.use_deterministic_algorithms(original_flag, warn_only=False)
    return {'layer': captured['layer'], 'fixed_input': fixed,
            'qkv_shapes': [list(t.shape) for t in (q, k, v)],
            'qkv_strides': [list(t.stride()) for t in (q, k, v)],
            'original_qkv_strides': captured['original_strides'],
            'kwargs': {key: (core.tensor_fingerprint({key: value}) if isinstance(value, torch.Tensor) else value)
                       for key, value in captured['kwargs'].items()}, 'arms': result,
            'control': 'First two arms use identical tensors, incoming gradient, backend flags, CUBLAS workspace and seed; only deterministic_algorithms is toggled.'}


class FirstGradientCaptured(Exception):
    pass


def execute_training(root, name, policy, probe=False, replay=False):
    import peft
    import torch
    import torch.nn.functional as functional
    import run_pilot
    environment = configure(policy)
    artifacts = root / 'artifacts'
    core.write(artifacts / (name + '-control.json'), environment)
    rows = core.read(root / 'source/train.json')
    row_map = {r['id']: r for r in rows}
    order = []
    for epoch in range(2):
        ids = list(row_map)
        random.Random(SEED + epoch).shuffle(ids)
        order.extend(ids)
    state = {'calls': [], 'inputs': {}, 'logits': [], 'active': None, 'inside_attention': False}
    captured = {}
    original_get = peft.get_peft_model
    original_clip = torch.nn.utils.clip_grad_norm_
    original_logp = run_pilot.completion_logp
    original_sdpa = functional.scaled_dot_product_attention
    handles = []

    def observe_logits(module, args, output):
        if state['active'] is not None and state['active'] < 4:
            state['logits'].append({'call': state['active'], **core.tensor_fingerprint({'logits': output})})

    def observe_model(*args, **kwargs):
        model = original_get(*args, **kwargs)
        base = model.get_base_model()
        handles.append(base.lm_head.register_forward_hook(observe_logits))
        if replay:
            attention = base.model.language_model.layers[0].self_attn
            def enter(module, args): state['inside_attention'] = True
            def leave(module, args, output): state['inside_attention'] = False
            handles.extend([attention.register_forward_pre_hook(enter), attention.register_forward_hook(leave)])
        state['model'] = model
        return model

    def observe_logp(model, base, batch, tokens):
        index = len(state['calls'])
        sid = order[index]
        state['active'] = index
        if sid not in state['inputs']:
            state['inputs'][sid] = core.tensor_fingerprint({key: value for key, value in batch.items() if isinstance(value, torch.Tensor)})
        if batch['input_ids'][0].tolist()[-len(row_map[sid]['draft_ids']):] != row_map[sid]['draft_ids'] or tokens != row_map[sid]['tail_ids']:
            raise ValueError('Frozen draft/target ordering changed')
        logp = original_logp(model, base, batch, tokens)
        state['calls'].append({'call': index, 'id': sid, 'loss': float(-logp.mean().detach()),
                               **core.tensor_fingerprint({'logp': logp})})
        state['active'] = None
        return logp

    def observe_sdpa(q, k, v, *args, **kwargs):
        output = original_sdpa(q, k, v, *args, **kwargs)
        if replay and state['inside_attention'] and not captured and q.requires_grad:
            captured.update(layer='model.language_model.layers.0.self_attn',
                            original_strides=[list(x.stride()) for x in (q,k,v)],
                            qkv=tuple(x.detach().clone(memory_format=torch.preserve_format) for x in (q, k, v)),
                            args=tuple(x.detach().clone() if isinstance(x, torch.Tensor) else x for x in args),
                            kwargs={key: value.detach().clone() if isinstance(value, torch.Tensor) else value for key, value in kwargs.items()})
            def incoming(gradient):
                if 'dout' not in captured: captured['dout'] = gradient.detach().clone(memory_format=torch.preserve_format)
            handles.append(output.register_hook(incoming))
        return output

    def stop_before_update(parameters, *args, **kwargs):
        norm = original_clip(parameters, *args, **kwargs)
        state['norm'] = float(norm)
        raise FirstGradientCaptured()

    peft.get_peft_model = observe_model
    run_pilot.completion_logp = observe_logp
    if replay: functional.scaled_dot_product_attention = observe_sdpa
    if probe: torch.nn.utils.clip_grad_norm_ = stop_before_update
    profile = torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) if replay else nullcontext()
    error = None
    try:
        with backend_context(policy), profile as profiler:
            try:
                core.train(root, name)
            except FirstGradientCaptured:
                if not probe: raise
        if replay:
            if 'dout' not in captured:
                raise ValueError('Actual decoder SDPA incoming gradient not captured')
            core.write(artifacts / 'diagnosis/actual-model-operators.json', relevant_ops(profiler))
            core.write(artifacts / 'diagnosis/sdpa-replay.json', sdpa_replay(captured, original_sdpa))
    except BaseException as exc:
        error = exc
        core.write(artifacts / name / 'error.json', {'error': repr(exc), 'traceback': traceback.format_exc()})
    finally:
        peft.get_peft_model = original_get
        run_pilot.completion_logp = original_logp
        functional.scaled_dot_product_attention = original_sdpa
        torch.nn.utils.clip_grad_norm_ = original_clip
        for handle in handles: handle.remove()
        core.write(artifacts / name / 'forward-trace.json', {key: state[key] for key in ('calls', 'inputs', 'logits')})
    if error is not None: raise error
    if probe:
        trace = core.read(artifacts / name / 'numerical_trace.json')
        if len(state['calls']) != 4 or len(trace['gradients_before_clip']) != 1:
            raise ValueError('Preflight must stop at the first four-example gradient, before optimizer.step')
        report = {'name': name, 'policy': policy, 'optimizer_updates': 0, 'backward_examples': 4,
                  'initial_sha256': trace['initial']['sha256'],
                  'gradient_sha256': trace['gradients_before_clip'][0]['sha256'],
                  'gradient_norm': state['norm'], 'ids': [c['id'] for c in state['calls']],
                  'logp_sha256': [c['sha256'] for c in state['calls']],
                  'logits_sha256': [c['sha256'] for c in state['logits']],
                  'input_sha256': {key: value['sha256'] for key, value in state['inputs'].items()}}
        core.write(artifacts / name / 'probe.json', report)
        emit('FIRST_GRADIENT', report)
    elif len(state['calls']) != 96 or len(state['inputs']) != 48:
        raise ValueError('Full training forward coverage changed')
    emit('TRAIN_STAGE_SAVED', {'name': name, 'policy': policy, 'probe': probe, 'forward_calls': len(state['calls'])})


def preflights_match(root, policy):
    left, right = [core.read(root / 'artifacts' / f'preflight_{policy}_{i}/probe.json') for i in (1, 2)]
    keys = ['initial_sha256', 'gradient_sha256', 'gradient_norm', 'ids', 'logp_sha256', 'logits_sha256', 'input_sha256']
    return {key: left[key] == right[key] for key in keys}


def compare(root):
    import torch
    from safetensors.torch import load_file
    from mmdl.evaluation.final_answer_parser_v8 import score_response
    out = root / 'artifacts'
    training = [core.read(out / name / 'training.json') for name in ('A', 'B')]
    traces = [core.read(out / name / 'numerical_trace.json') for name in ('A', 'B')]
    forwards = [core.read(out / name / 'forward-trace.json') for name in ('A', 'B')]
    controls = [core.read(out / (name + '-control.json')) for name in ('A', 'B')]
    assert controls[0] == controls[1]
    assert training[0]['epoch_orders'] == training[1]['epoch_orders']
    assert all(t['train_sha256'] == core.TRAIN_SHA and t['arms']['sft']['updates'] == 24 for t in training)
    weights = [load_file(out / name / 'sft/adapter/adapter_model.safetensors') for name in ('A', 'B')]
    assert set(weights[0]) == set(weights[1])
    tensors = []
    for key, value in weights[0].items():
        delta = (value.double() - weights[1][key].double()).abs()
        tensors.append({'name': key, 'equal': torch.equal(value, weights[1][key]),
                        'max_abs': float(delta.max()), 'mean_abs': float(delta.mean())})
    steps = [{'step': x['step'], 'loss_equal': x['loss'] == y['loss'],
              'gradient_norm_equal': x['gradient_norm'] == y['gradient_norm'],
              'gradient_sha256_equal': u['sha256'] == v['sha256']}
             for x, y, u, v in zip(training[0]['steps'], training[1]['steps'],
                                   traces[0]['gradients_before_clip'], traces[1]['gradients_before_clip'], strict=True)]
    inference = [core.read(out / 'inference' / (name + '.json')) for name in ('A_1', 'B_1')]
    rows = []
    regraded = 0
    for left, right in zip(inference[0]['rows'], inference[1]['rows'], strict=True):
        assert all(left[k] == right[k] for k in ('id', 'input_sha256', 'actual_engine_prompt_token_ids_sha256', 'seed'))
        for r in (left, right):
            grade = score_response(r['raw_response'], r['question_type'], r['options'], r['answer'], r['finish_reason'], question=r['question'])
            assert all(r[key] == grade[key] for key in ('correct','parsed_answer','parse_status','extraction_rule','extraction_evidence','extraction_status'))
            regraded += 1
        rows.append({'id': left['id'], 'raw_equal': left['raw_response'] == right['raw_response'],
                     'tokens_equal': left['token_ids'] == right['token_ids'],
                     'finish_equal': (left['finish_reason'], left['stop_reason']) == (right['finish_reason'], right['stop_reason']),
                     'parsed_answer_equal': left['parsed_answer'] == right['parsed_answer'],
                     'left_correct': left['correct'], 'right_correct': right['correct'],
                     'left_tokens': left['generated_tokens'], 'right_tokens': right['generated_tokens']})
    assert len(rows) == len({r['id'] for r in rows}) == 24
    merged = [core.read(out / name / 'merged_files.json') for name in ('A','B')]
    merged_weight_equal = {key: value == merged[1].get(key) for key, value in merged[0].items() if key.endswith('.safetensors')}
    result = {'status':'COMPARISON_COMPLETE', 'policy':core.read(out/'control.json'),
              'initial_tensors_equal': traces[0]['initial'] == traces[1]['initial'],
              'all_inputs_equal': forwards[0]['inputs'] == forwards[1]['inputs'],
              'all_forward_logps_equal': forwards[0]['calls'] == forwards[1]['calls'],
              'first4_full_logits_equal': forwards[0]['logits'] == forwards[1]['logits'],
              'equal_final_tensors':sum(r['equal'] for r in tensors), 'total_tensors':len(tensors),
              'adapter_file_sha256': [t['arms']['sft']['adapter_sha256'] for t in training],
              'tensor_differences':tensors, 'steps':steps, 'merged_weight_files_equal':merged_weight_equal,
              'independent_v8_regrades':regraded,
              'inference_exact':sum(r['raw_equal'] and r['tokens_equal'] and r['finish_equal'] for r in rows),
              'same_parsed_answer':sum(r['parsed_answer_equal'] for r in rows),
              'scores':[i['correct'] for i in inference], 'rows':rows,
              'scope':'Two full trainings on frozen48; original first Accounting24 request window; two fresh inference processes, 2048/P0/V8/MP0. No full900 or cross-platform guarantee.'}
    result['determinism_confirmed'] = (result['initial_tensors_equal'] and result['all_inputs_equal']
        and result['all_forward_logps_equal'] and result['first4_full_logits_equal']
        and result['equal_final_tensors'] == result['total_tensors'] == 144
        and all(all(s[k] for k in ('loss_equal','gradient_norm_equal','gradient_sha256_equal')) for s in steps)
        and bool(merged_weight_equal) and all(merged_weight_equal.values()) and result['inference_exact'] == 24)
    core.write(out/'comparison.json',result)
    emit('COMPLETE',{key:result[key] for key in ('status','determinism_confirmed','initial_tensors_equal','equal_final_tensors','total_tensors','inference_exact','scores')})


def launch(bundle, root, backup, release, max_seconds=10800):
    root, bundle = Path(root), Path(bundle)
    root.mkdir(exist_ok=False)
    artifacts = root/'artifacts'
    artifacts.mkdir()
    deadline=time.monotonic()+max_seconds
    env=runtime_env(root)
    stage='setup'
    success=False
    watchdog=threading.Timer(max_seconds+180,release);watchdog.daemon=True;watchdog.start()

    def run(label,args,cap=1800,allowed_failure=False):
        nonlocal stage
        stage=label
        emit('PHASE',{'stage':label,'remaining_seconds':round(deadline-time.monotonic())})
        timeout=min(cap,deadline-time.monotonic())
        if timeout<=0:raise TimeoutError(label)
        log_path=artifacts/'logs'/(label+'.log');log_path.parent.mkdir(exist_ok=True)
        with log_path.open('x') as log, subprocess.Popen([str(x) for x in args],env=env,stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,text=True,errors='replace',start_new_session=True,bufsize=1) as proc:
            def stop():
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
            timer=threading.Timer(timeout,stop);timer.daemon=True;timer.start()
            try:
                for line in proc.stdout:
                    log.write(line)
                    if line.startswith(('DETER_','REPRO_','FULL_','PREF_')):log.flush();print(line,end='',flush=True)
                code=proc.wait()
                if code:
                    print(log_path.read_text()[-4500:],flush=True)
                    if not allowed_failure:raise RuntimeError(f'{label} exited {code}')
            finally:timer.cancel();stop()
        return code==0

    try:
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        if '\n' in gpu or 'NVIDIA L4' not in gpu or shutil.disk_usage(root).free<60*2**30:raise RuntimeError('Require one L4 and60GiB free: '+gpu)
        manifest=core.unpack(bundle,root/'source')
        core.write(artifacts/'source_manifest.json',manifest)
        shutil.copy2(__file__,artifacts/'deterministic.py');shutil.copy2(CORE_PATH,artifacts/'reproduce.py')
        core.write(artifacts/'driver.json',{'status':'RUNNING','gpu':gpu,'start_unix':time.time(),'max_seconds':max_seconds})
        run('clone',['git','clone','--quiet','https://github.com/jang2296/MMDL.git',root/'MMDL'],180)
        run('pin',['git','-C',root/'MMDL','checkout','--detach',core.COMMIT],30)
        run('uv',[sys.executable,'-m','pip','install','--quiet','uv'],180)
        run('venv',['uv','venv','--python','3.12.3',root/'env'],300)
        python=root/'env/bin/python'
        run('pip',['uv','pip','install','--python',python,'pip==25.2'],120)
        run('packages',[python,'-m','pip','install','--disable-pip-version-check','-r',root/'MMDL/env/requirements-vllm.lock'],1800)
        run('project',['uv','pip','install','--python',python,'--no-deps','-e',root/'MMDL'],120)
        run('environment',[python,CORE_PATH,'environment',root],120)
        run('download',[python,'-m','mmdl.data.download','--skip-pro','--cache',root/'hf','--data-root',root/'data','--artifact-root',artifacts],1800)
        run('diagnostic_legacy',[python,__file__,'probe',root,'diagnostic_legacy','legacy','--replay'],900)
        selected=None
        attempts=[]
        for policy in ('strict_auto','strict_math'):
            passed=True
            for i in (1,2):
                name=f'preflight_{policy}_{i}'
                if not run(name,[python,__file__,'probe',root,name,policy],900,allowed_failure=True):
                    passed=False;break
            matches=preflights_match(root,policy) if passed else {}
            attempts.append({'policy':policy,'completed':passed,'matches':matches})
            if passed and all(matches.values()):selected=policy;break
            emit('PREFLIGHT_POLICY_REJECTED',attempts[-1])
        control={'selected':selected,'attempts':attempts,'seed':SEED,'CUBLAS_WORKSPACE_CONFIG':':4096:8',
                 'PYTHONHASHSEED':str(SEED),'threads':6,'strict_warn_only':False,
                 'training_data_sha256':core.TRAIN_SHA,'immutable_core_sha256':CORE_SHA,
                 'changed_condition':'Strict deterministic kernels/precision controls; original frozen48 and train objective unchanged.'}
        core.write(artifacts/'control.json',control)
        backup(artifacts,'diagnosis')
        if selected is None:raise RuntimeError('Neither strict policy passed the full first-gradient cross-process check')
        for name in ('A','B'):
            run('train_'+name,[python,__file__,'train',root,name,selected],1800)
            backup(artifacts,'train_'+name)
            run('merge_'+name,[python,__file__,'merge',root,name,selected],300)
        for name in ('A_1','B_1'):
            run('infer_'+name,[python,__file__,'infer',root,name],900)
        run('compare',[python,__file__,'compare',root],120)
        backup(artifacts,'compare')
        success=True
    finally:
        previous=core.read(artifacts/'driver.json') if (artifacts/'driver.json').exists() else {}
        core.write(artifacts/'driver.json',previous|{'status':'COMPLETE' if success else 'FAILED','last_stage':stage,'end_unix':time.time()})
        try:
            backup(artifacts,'final')
            emit('FINAL_BACKUP_VERIFIED',{'status':'COMPLETE' if success else 'FAILED'})
        except BaseException as error:
            core.write(artifacts/'backup_failure.json',{'stage':stage,'error':repr(error),'compute_complete':success})
            emit('BACKUP_NEEDS_ATTENTION',{'stage':stage,'error':repr(error)})
            raise
        finally:
            watchdog.cancel();emit('RELEASE_REQUEST',{'unix':time.time()});release()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['probe','train','merge','infer','compare'])
    parser.add_argument('root',type=Path)
    parser.add_argument('name',nargs='?')
    parser.add_argument('policy',nargs='?',choices=['legacy','strict_auto','strict_math'])
    parser.add_argument('--replay',action='store_true')
    args=parser.parse_args()
    if args.stage in ('probe','train'):
        execute_training(args.root,args.name,args.policy,probe=args.stage=='probe',replay=args.replay)
    elif args.stage=='merge':
        configure(args.policy)
        core.merge(args.root,args.name)
    elif args.stage=='infer':core.infer(args.root,args.name)
    else:compare(args.root)


if __name__=='__main__':main()
