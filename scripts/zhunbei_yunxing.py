import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def zhi(lujing):
    h = hashlib.sha256()
    with lujing.open('rb') as f:
        for kuai in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(kuai)
    return h.hexdigest()


def zhixing():
    p = argparse.ArgumentParser(description='Build an isolated vLLM runtime from the pinned official wheel.')
    p.add_argument('--wheel', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    gen = Path(__file__).resolve().parents[1]
    peizhi = json.loads((gen / 'configs/patches.json').read_text())
    if zhi(a.wheel) != peizhi['wheel_sha256']:
        p.error('The wheel SHA256 differs from the measured release.')
    if a.output.exists():
        p.error('The output already exists. Choose a new directory.')
    if not shutil.which('patch'):
        p.error('GNU patch is required.')
    for xiang in peizhi['patch_order']:
        if zhi(gen / 'patches' / xiang['name']) != xiang['sha256']:
            p.error('Patch SHA256 mismatch: ' + xiang['name'])
    a.output = a.output.resolve()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    linshi = Path(tempfile.mkdtemp(prefix=a.output.name + '.building-', dir=a.output.parent))
    try:
        with zipfile.ZipFile(a.wheel) as f:
            for n in f.namelist():
                if n.startswith('vllm/') or '.dist-info/' in n:
                    f.extract(n, linshi)
        for xiang in peizhi['patch_order']:
            mingling = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-d', str(linshi / 'vllm'), '-i', str(gen / 'patches' / xiang['name'])]
            subprocess.run(mingling + ['--dry-run'], check=True)
            subprocess.run(mingling, check=True)
        jilu = {'wheel_sha256': peizhi['wheel_sha256'], 'patch_order': peizhi['patch_order'], 'python_sources': {str(f.relative_to(linshi)): zhi(f) for f in sorted((linshi / 'vllm').rglob('*.py'))}}
        (linshi / 'recipe-runtime.json').write_text(json.dumps(jilu, indent=2) + '\n')
        linshi.rename(a.output)
    except BaseException:
        print('Incomplete build retained for inspection: ' + str(linshi))
        raise
    print('Runtime ready: ' + str(a.output))


if __name__ == '__main__':
    zhixing()
