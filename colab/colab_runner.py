"""Colab adapter: append-only verified checkpoints; original evaluation stays pinned.

Only the host kernel release is excluded from resume identity. GPU, driver,
Python, installed packages, protocol and original source identity remain strict.
Run one notebook per backup directory. This is not a distributed writer.
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import tempfile
import uuid
import zipfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checkpoints(remote):
    markers = sorted(Path(remote).glob('*.ready.json'))
    entries = []
    for index, path in enumerate(markers, 1):
        entry = json.loads(path.read_text())
        if entry['sequence'] != index or not path.name.startswith(f'{index:06d}-'):
            raise RuntimeError('Checkpoint gap or concurrent writers; preserve Drive files and inspect.')
        if Path(entry['archive']).name != entry['archive']:
            raise ValueError('Unsafe checkpoint archive path')
        entries.append(entry)
    return entries


def restore(remote, local):
    local = Path(local)
    if local.exists():
        raise FileExistsError('Restore requires a fresh local directory; existing work is preserved.')
    entries = checkpoints(remote)
    local.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=local.parent) as td:
        stage = Path(td) / 'artifacts'
        stage.mkdir()
        for entry in entries:
            archive = Path(td) / 'checkpoint.zip'
            shutil.copyfile(Path(remote) / entry['archive'], archive)
            if sha(archive) != entry['sha256']:
                raise ValueError(f"Checkpoint checksum failed: {entry['archive']}")
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    relative = Path(info.filename)
                    if relative.is_absolute() or '..' in relative.parts or info.is_dir():
                        raise ValueError('Unsafe checkpoint entry')
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
            archive.unlink()
        stage.rename(local)
    print(f'Restored {len(entries)} verified checkpoints', flush=True)


class CheckpointStore:
    def __init__(self, local, remote):
        self.local, self.remote = Path(local), Path(remote)
        self.remote.mkdir(parents=True, exist_ok=True)
        self.sequence = len(checkpoints(self.remote))
        self.seen = {}

    def save(self):
        # Called synchronously after a complete sample, never from a background thread.
        changed, stamps = [], {}
        for path in sorted(self.local.rglob('*')):
            relative = path.relative_to(self.local)
            if any(part.startswith('.') for part in relative.parts) or not path.is_file():
                continue
            if path.is_symlink():
                raise ValueError('Artifact symlinks are not supported')
            stat = path.stat()
            stamps[str(relative)] = (stat.st_size, stat.st_mtime_ns)
            if self.seen.get(str(relative)) != stamps[str(relative)]:
                changed.append(path)
        if not changed:
            return
        if len(checkpoints(self.remote)) != self.sequence:
            raise RuntimeError('Another writer changed this backup directory. Stop the other notebook.')
        number = self.sequence + 1
        stem = f'{number:06d}-{uuid.uuid4().hex}'
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / (stem + '.zip')
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
                for path in changed:
                    z.write(path, str(path.relative_to(self.local)))
            checksum = sha(archive)
            destination = self.remote / archive.name
            shutil.copyfile(archive, destination)
            if sha(destination) != checksum:
                raise IOError('Drive checkpoint verification failed; local results are preserved.')
            marker = {'sequence': number, 'archive': archive.name, 'sha256': checksum}
            pending = self.remote / (stem + '.pending')
            pending.write_text(json.dumps(marker))
            os.replace(pending, self.remote / (stem + '.ready.json'))
        self.seen = stamps
        self.sequence = number
        print(f'DRIVE_BACKUP_OK checkpoint={number}', flush=True)



def install_raw_journal(engine, backend_class, local, run_id):
    """Save generated outputs before the scorer; never label this journal as scored."""
    from contextlib import closing

    prepare = engine.prepare_request
    generate = backend_class.generate_stream
    pending = {}

    def prepare_request(*args, **kwargs):
        request, record = prepare(*args, **kwargs)
        pending[request['sample_id']] = record
        return request, record

    def generate_stream(self, requests):
        with closing(generate(self, requests)) as stream:
            for output in stream:
                record = pending.pop(output['sample_id'])
                payload = record | output | {'journal_status': 'GENERATED_UNSCORED'}
                # These paths are outside run/samples; final scoring never consumes them implicitly.
                target = Path(local) / 'raw_journal' / run_id / (record['inference_id'] + '.json')
                target.parent.mkdir(parents=True, exist_ok=True)
                encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                            dir=target.parent, prefix='.pending-', delete=False) as stream_file:
                        temporary = Path(stream_file.name)
                        stream_file.write(encoded + '\n')
                        stream_file.flush()
                        os.fsync(stream_file.fileno())
                    os.link(temporary, target)  # Local disk: publish atomically without overwrite.
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                yield output

    engine.prepare_request = prepare_request
    backend_class.generate_stream = generate_stream


def validate_budget_2048(cfg, hw, baseline, original_validate):
    """Allow one named output-budget experiment, retaining every upstream guard."""
    import copy
    expected = copy.deepcopy(baseline)
    expected['protocol_id'] = 'mmmu-val-v8-2048'
    expected['generation']['max_new_tokens'] = 2048
    if cfg != expected:
        raise ValueError('2048 experiment may change only protocol_id and max_new_tokens')
    original_validate(baseline, hw)


def install_budget_2048_protocol():
    """Register a strict adapter extension without editing the pinned checkout."""
    import yaml
    import mmdl.runtime.contracts as contracts
    repo = Path(contracts.__file__).resolve().parents[3]
    baseline = yaml.safe_load((repo/'configs/eval/mmmu_val_v8.yaml').read_text())
    original_validate = contracts.validate_configs

    def validate(cfg, hw):
        if cfg.get('protocol_id') == 'mmmu-val-v8-2048':
            return validate_budget_2048(cfg, hw, baseline, original_validate)
        return original_validate(cfg, hw)

    contracts.validate_configs = validate


def preflight(repo, model_path, data_root, output, protocol=None):
    """Validate all pinned inputs on CPU, without constructing a GPU model."""
    import torch
    import yaml
    from transformers import AutoConfig, AutoProcessor
    from mmdl.evaluation.datasets.mmmu import load_validation, separate_sample
    from mmdl.evaluation.prompt import build_messages
    from mmdl.evaluation.backends.input_preparation import prepare_protocol_inputs
    from mmdl.runtime.artifacts import digest, write_json
    from mmdl.runtime.contracts import MODEL_REVISION

    torch.set_num_threads(4)
    repo, output = Path(repo), Path(output)
    cfg = yaml.safe_load(Path(protocol or repo / 'configs/eval/mmmu_val_v8.yaml').read_text())
    datasets, coverage = load_validation(Path(data_root))
    processor = AutoProcessor.from_pretrained(str(model_path), revision=MODEL_REVISION,
                                              local_files_only=True, trust_remote_code=False)
    model_config = AutoConfig.from_pretrained(str(model_path), revision=MODEL_REVISION,
                                             local_files_only=True, trust_remote_code=False)
    processor.image_processor.size = {'shortest_edge': cfg['image']['min_pixels'],
                                      'longest_edge': cfg['image']['max_pixels']}
    records = []
    for subject in sorted(datasets):
        for row in datasets[subject]:
            sample, images, _gold = separate_sample(row, subject)
            if len(images) > 5:
                raise ValueError(f"{sample['id']}: exceeds fixed vLLM image limit")
            messages = build_messages(sample, images, repo)
            item, processed = prepare_protocol_inputs(processor, model_config, messages, images, cfg['image'])
            if item['input_tokens'] + cfg['generation']['max_new_tokens'] > cfg['execution']['max_model_len']:
                raise ValueError(f"{sample['id']}: input plus output budget exceeds context")
            records.append({'id': sample['id'], 'subject': subject, 'images': len(images),
                            'question_type': sample['question_type'],
                            'input_tokens': item['input_tokens'], 'input_sha256': item['input_sha256']})
            del item, processed, messages, images
        print(f'INPUT_PREFLIGHT {len(records)}/900', flush=True)
    if len(records) != 900 or len({r['id'] for r in records}) != 900:
        raise ValueError('Input preflight did not cover exactly 900 unique samples')
    result = {'status': 'PASS', 'count': 900, 'coverage': coverage, 'protocol_sha256': digest(cfg),
              'adapter_sha256': sha(__file__), 'model_revision': MODEL_REVISION,
              'max_input_tokens': max(r['input_tokens'] for r in records),
              'max_images': max(r['images'] for r in records), 'records': records}
    write_json(output, result)
    return result


def run():
    import sys
    import mmdl.evaluation.engine as engine
    from mmdl.evaluation.cli import main
    from mmdl.runtime.artifacts import write_json

    install_budget_2048_protocol()
    local = Path(os.environ['MMDL_ARTIFACT_ROOT'])
    remote = Path(os.environ['MMDL_COLAB_BACKUP'])
    store = CheckpointStore(local, remote)
    original_identity = engine.environment_identity
    wrapper_hash = sha(__file__)
    session_id = uuid.uuid4().hex

    def identity(environment):
        write_json(local / 'colab_sessions' / f'{session_id}.json', {
            'environment': environment, 'adapter_sha256': wrapper_hash,
            'argv': sys.argv, 'resume_policy': 'ignore-host-kernel-release-only-v1',
        })
        result = original_identity(environment)
        result['platform'] = {'system': platform.system(), 'machine': platform.machine()}
        result['colab_adapter_sha256'] = wrapper_hash
        # Check compatibility before RunWriter, to give a useful error without bypassing it.
        if '--resume' in sys.argv:
            from mmdl.runtime.artifacts import digest
            run_id = sys.argv[sys.argv.index('--run-id') + 1]
            saved = json.loads((local / 'runs' / run_id / 'run_manifest.json').read_text())
            if saved['identity']['environment_sha256'] != digest(result):
                raise RuntimeError('Resume environment differs (GPU/driver/Python/packages/adapter). '
                                   'Use the same environment; do not merge different GPUs or delete checks.')
        return result

    from mmdl.evaluation.backends.vllm_backend import VLLMBackend
    run_id = sys.argv[sys.argv.index('--run-id') + 1]
    install_raw_journal(engine, VLLMBackend, local, run_id)

    original_writer = engine.RunWriter

    class DriveWriter(original_writer):
        def save(self, record):
            super().save(record)
            store.save()

    engine.environment_identity = identity
    engine.RunWriter = DriveWriter
    support = local / 'colab_support'
    support.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, support / 'colab_runner.py')
    try:
        main()
    finally:
        store.save()


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['preflight']:
        import argparse
        parser = argparse.ArgumentParser()
        for name in ('repo', 'model-path', 'data-root', 'output'):
            parser.add_argument('--' + name, required=True, type=Path)
        parser.add_argument('--protocol', type=Path)
        args = parser.parse_args(sys.argv[2:])
        preflight(args.repo, args.model_path, args.data_root, args.output, args.protocol)
    else:
        run()
