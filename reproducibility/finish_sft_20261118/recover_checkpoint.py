"""Decode a sidebar-visible checkpoint; verify CRC, coverage and every member SHA256."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile


def recover(text_path, directory):
    text = Path(text_path).read_text()
    starts = list(re.finditer(r'^REPRO_CHECKPOINT_BEGIN (\{[^\n]+\})$', text, re.M))
    chosen = None
    for number, match in enumerate(starts):
        header = json.loads(match[1])
        section = text[match.end():starts[number+1].start() if number+1 < len(starts) else len(text)]
        seq = header['sequence']
        if re.search(r'^REPRO_CHECKPOINT_END '+str(seq)+r'\s*$', section, re.M):
            chosen = header, section
    if chosen is None:
        raise ValueError('No complete checkpoint in visible output')
    header, section = chosen
    seq = header['sequence']
    if (not isinstance(seq, int) or seq < 1 or header['stage'] not in ('train_A','train_B','compare','final')
            or Path(header['archive']).name != header['archive']
            or not re.fullmatch(r'[a-f0-9]{64}',header['sha256'])
            or not 0 < header['bytes'] <= 128*1024*1024
            or not 0 < header['chunks'] <= 8192):
        raise ValueError('Invalid checkpoint header')
    chunks = re.findall(r'^REPRO_CHECKPOINT_DATA '+str(seq)+r' (\d+) ([A-Za-z0-9+/=]+)$',section,re.M)
    if [int(i) for i,_ in chunks] != list(range(header['chunks'])):
        raise ValueError('Missing, repeated or reordered base64 chunks')
    data=base64.b64decode(''.join(chunk for _,chunk in chunks),validate=True)
    if len(data) != header['bytes'] or hashlib.sha256(data).hexdigest() != header['sha256']:
        raise ValueError('Checkpoint size/SHA256 mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist()
        if (len(names)>10000 or sum(i.file_size for i in z.infolist())>512*1024*1024
                or any(i.flag_bits & 1 for i in z.infolist())):
            raise ValueError('Oversized or encrypted checkpoint')
        if len(names)!=len(set(names)) or z.testzip() is not None:
            raise ValueError('Duplicate members or ZIP CRC failure')
        manifest=json.loads(z.read('_checkpoint_manifest.json'))
        if (manifest['sequence']!=seq or manifest['stage']!=header['stage']
                or set(names)!=set(manifest['files'])|{'_checkpoint_manifest.json'}
                or len(manifest['files'])!=header['payload_files']):
            raise ValueError('Checkpoint manifest coverage mismatch')
        for info in z.infolist():
            path=Path(info.filename)
            if (path.is_absolute() or path.drive or '..' in path.parts or '\\' in info.filename
                    or info.is_dir() or stat.S_ISLNK(info.external_attr>>16)):
                raise ValueError('Unsafe checkpoint path or symlink')
            if info.filename in manifest['files']:
                if hashlib.sha256(z.read(info)).hexdigest()!=manifest['files'][info.filename]:
                    raise ValueError('Member SHA256 mismatch: '+info.filename)
        directory=Path(directory)
        directory.mkdir(parents=True,exist_ok=True)
        packet_dir=directory/f'{seq:06d}-{header["stage"]}'
        packet_dir.mkdir(exist_ok=False)
        archive=packet_dir/header['archive']
        archive.write_bytes(data)
        payload=packet_dir/'payload'
        for info in z.infolist():
            destination=payload/info.filename
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(z.read(info))
        (packet_dir/'verified-header.json').write_text(json.dumps(header,indent=2)+'\n')
    result={'sequence':seq,'stage':header['stage'],'archive':str(archive),'bytes':len(data),
            'sha256':header['sha256'],'files':header['payload_files'],'crc_and_all_member_sha_pass':True,
            'manifest':str(payload/'_checkpoint_manifest.json')}
    for arm in ('A','B'):
        training=payload/arm/'training.json'
        if training.exists():
            report=json.loads(training.read_bytes())
            result['training_'+arm]={k:report[k] for k in ('seed','examples','epochs','train_sha256')}
            result['training_'+arm].update(report['arms']['sft'])
    (packet_dir/'recovery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('visible_text',type=Path)
    parser.add_argument('output_directory',type=Path)
    args=parser.parse_args()
    print(json.dumps(recover(args.visible_text,args.output_directory),ensure_ascii=False,indent=2))
