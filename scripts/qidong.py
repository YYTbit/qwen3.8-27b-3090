import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys


def tianchong(x, duiying):
    if isinstance(x, dict):
        return {k: tianchong(v, duiying) for k, v in x.items()}
    if isinstance(x, list):
        return [tianchong(v, duiying) for v in x]
    if isinstance(x, str):
        if x.startswith('{'):
            try:
                return json.dumps(tianchong(json.loads(x), duiying))
            except ValueError:
                pass
        for k, v in duiying.items():
            x = x.replace(k, v)
    return x


def zhixing():
    p = argparse.ArgumentParser(description='Start the archived two-GPU recipe with process-local settings.')
    for n in ['runtime', 'target', 'draft', 'work-dir']:
        p.add_argument('--' + n, required=True, type=Path)
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--cache-port', type=int, default=8100)
    p.add_argument('--cache-http-port', type=int, default=8101)
    p.add_argument('--cuda-home', type=Path)
    p.add_argument('--numa-node', type=int)
    a = p.parse_args()
    gen = Path(__file__).resolve().parents[1]
    if len(a.gpus.split(',')) != 2:
        p.error('This measured profile uses exactly two GPUs.')
    for n in ['runtime', 'target', 'draft', 'work_dir']:
        setattr(a, n, getattr(a, n).resolve())
    if not (a.runtime / 'recipe-runtime.json').is_file():
        p.error('Build the runtime with scripts/zhunbei_yunxing.py first.')
    for m in [a.target, a.draft]:
        if not (m / 'config.json').is_file():
            p.error('Missing model config: ' + str(m))
    duankou = [a.port, a.cache_port, a.cache_http_port, a.cache_http_port + 1]
    if len(set(duankou)) != 4 or any(n < 1024 or n > 65535 for n in duankou):
        p.error('Use four distinct nonprivileged ports.')
    a.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    miyao = a.work_dir / 'api-key'
    if not miyao.exists():
        with miyao.open('x', opener=lambda f, flags: os.open(f, flags, 0o600)) as f:
            f.write(secrets.token_urlsafe(32) + '\n')
    if not miyao.read_text().strip():
        p.error('The API key file is empty.')
    moshi = json.loads((gen / 'configs/launch-template.json').read_text())
    qianming = hashlib.sha256()
    for f in [a.runtime / 'recipe-runtime.json', gen / 'configs/launch-template.json', gen / 'scripts/qwen-claude-template.jinja']:
        qianming.update(f.read_bytes())
    for m in [a.target, a.draft]:
        for f in sorted(m.glob('*.json')):
            qianming.update(f.read_bytes())
        for f in sorted(m.glob('*.safetensors')):
            z = f.stat()
            qianming.update(json.dumps([str(f), z.st_size, z.st_mtime_ns]).encode())
    cipan = json.loads((gen / 'configs/disk-cache-template.json').read_text())
    cipan.update(namespace='tp2-' + qianming.hexdigest()[:24], root=str(a.work_dir / 'kv-cache'), port=a.cache_port, http_port=a.cache_http_port, key_file=str(miyao), log=str(a.work_dir / 'lmcache.log'))
    cipan_wenjian = a.work_dir / 'disk-cache.json'
    cipan_wenjian.write_text(json.dumps(cipan, indent=2) + '\n')
    duiying = {'PYTHON_EXECUTABLE': sys.executable, 'RECIPE_FILES': str(gen / 'scripts'), 'TARGET_MODEL': str(a.target), 'DRAFT_MODEL': str(a.draft), 'PREPARED_VLLM_RUNTIME': str(a.runtime), 'DISK_CACHE_CONFIG': str(cipan_wenjian), 'GPU_A,GPU_B': a.gpus, 'READ_API_KEY_FROM_LOCAL_FILE': miyao.read_text().strip()}
    mingling = tianchong(moshi['argv'], duiying)
    mingling[mingling.index('--port') + 1] = str(a.port)
    zhuanhuan = json.loads(mingling[mingling.index('--kv-transfer-config') + 1])
    zhuanhuan['kv_connector_extra_config']['lmcache.mp.port'] = a.cache_port
    mingling[mingling.index('--kv-transfer-config') + 1] = json.dumps(zhuanhuan)
    huanjing = os.environ.copy()
    peizhi = tianchong(moshi['environment'], duiying)
    peizhi.pop('CUDA_HOME', None)
    if a.cuda_home:
        peizhi['CUDA_HOME'] = str(a.cuda_home.resolve())
    elif not huanjing.get('CUDA_HOME') and shutil.which('nvcc'):
        peizhi['CUDA_HOME'] = str(Path(shutil.which('nvcc')).resolve().parents[1])
    if not shutil.which('gcc-10') or not shutil.which('g++-10'):
        p.error('The archived profile needs gcc-10 and g++-10; see docs/setup.md.')
    peizhi['PYTHONPATH'] += os.pathsep + huanjing.get('PYTHONPATH', '')
    for n in ['NCCL_ALGO', 'NCCL_PROTO', 'NCCL_MIN_NCHANNELS', 'NCCL_MAX_NCHANNELS', 'NCCL_P2P_LEVEL', 'VLLM_DFLASH2_DISABLE_EAGLE_BLOCK_DROP']:
        huanjing.pop(n, None)
    for n in ['TMPDIR', 'TRITON_CACHE_DIR', 'TORCHINDUCTOR_CACHE_DIR', 'VLLM_CACHE_ROOT', 'CUDA_CACHE_PATH']:
        f = a.work_dir / n.lower()
        f.mkdir(exist_ok=True)
        peizhi[n] = str(f)
    huanjing.update(peizhi)
    if a.numa_node is not None:
        if not shutil.which('numactl'):
            p.error('numactl is required for --numa-node.')
        mingling = ['numactl', '--cpunodebind=' + str(a.numa_node), '--membind=' + str(a.numa_node)] + mingling
    print('API: http://127.0.0.1:' + str(a.port), flush=True)
    print('Key file: ' + str(miyao), flush=True)
    print('Cache namespace: ' + cipan['namespace'], flush=True)
    os.execvpe(mingling[0], mingling, huanjing)


if __name__ == '__main__':
    zhixing()
