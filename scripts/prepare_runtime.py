import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description='Build an isolated vLLM runtime from the pinned official wheel.')
    p.add_argument('--wheel', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    patch_config = json.loads((repository_root / 'configs/patches.json').read_text())
    if sha256_file(a.wheel) != patch_config['wheel_sha256']:
        p.error('The wheel SHA256 differs from the measured release.')
    if a.output.exists():
        p.error('The output already exists. Choose a new directory.')
    if not shutil.which('patch'):
        p.error('GNU patch is required.')
    for patch_record in patch_config['patch_order']:
        if sha256_file(repository_root / 'patches' / patch_record['name']) != patch_record['sha256']:
            p.error('Patch SHA256 mismatch: ' + patch_record['name'])
    a.output = a.output.resolve()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix=a.output.name + '.building-', dir=a.output.parent))
    try:
        with zipfile.ZipFile(a.wheel) as f:
            for n in f.namelist():
                if n.startswith('vllm/') or '.dist-info/' in n:
                    path = Path(f.extract(n, build_dir))
                    file_mode = (f.getinfo(n).external_attr >> 16) & 0o777
                    if file_mode:
                        path.chmod(file_mode)
        for patch_record in patch_config['patch_order']:
            command = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-d', str(build_dir / 'vllm'), '-i', str(repository_root / 'patches' / patch_record['name'])]
            subprocess.run(command + ['--dry-run'], check=True)
            subprocess.run(command, check=True)
        manifest = {'wheel_sha256': patch_config['wheel_sha256'], 'patch_order': patch_config['patch_order'], 'python_sources': {str(f.relative_to(build_dir)): sha256_file(f) for f in sorted((build_dir / 'vllm').rglob('*.py'))}}
        (build_dir / 'recipe-runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
        build_dir.rename(a.output)
    except BaseException:
        print('Incomplete build retained for inspection: ' + str(build_dir))
        raise
    print('Runtime ready: ' + str(a.output))


if __name__ == '__main__':
    main()
