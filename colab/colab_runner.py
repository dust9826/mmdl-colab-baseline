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


def run():
    import sys
    import mmdl.evaluation.engine as engine
    from mmdl.evaluation.cli import main
    from mmdl.runtime.artifacts import write_json

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
    run()
