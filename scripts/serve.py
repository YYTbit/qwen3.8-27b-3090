import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys


def expand_placeholders(x, replacements):
    if isinstance(x, dict):
        return {k: expand_placeholders(v, replacements) for k, v in x.items()}
    if isinstance(x, list):
        return [expand_placeholders(v, replacements) for v in x]
    if isinstance(x, str):
        if x.startswith('{'):
            try:
                return json.dumps(expand_placeholders(json.loads(x), replacements))
            except ValueError:
                pass
        for k, v in replacements.items():
            x = x.replace(k, v)
    return x


def main():
    p = argparse.ArgumentParser(description='Start the archived two-GPU recipe with process-local settings.')
    for n in ['runtime', 'target', 'draft', 'work-dir']:
        p.add_argument('--' + n, required=True, type=Path)
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--cache-port', type=int, default=8100)
    p.add_argument('--cache-http-port', type=int, default=8101)
    p.add_argument('--kv-cache-gib', type=float, default=10.5)
    p.add_argument('--cuda-home', type=Path)
    p.add_argument('--numa-node', type=int)
    a = p.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    if len(a.gpus.split(',')) != 2:
        p.error('This measured profile uses exactly two GPUs.')
    if not 9.5 <= a.kv_cache_gib <= 11.5:
        p.error('Use a per-GPU KV budget between 9.5 and 11.5 GiB; verify total device memory.')
    for n in ['runtime', 'target', 'draft', 'work_dir']:
        setattr(a, n, getattr(a, n).resolve())
    if not (a.runtime / 'recipe-runtime.json').is_file():
        p.error('Build the runtime with scripts/prepare_runtime.py first.')
    for m in [a.target, a.draft]:
        if not (m / 'config.json').is_file():
            p.error('Missing model config: ' + str(m))
    ports = [a.port, a.cache_port, a.cache_http_port, a.cache_http_port + 1]
    if len(set(ports)) != 4 or any(n < 1024 or n > 65535 for n in ports):
        p.error('Use four distinct nonprivileged ports.')
    a.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = a.work_dir / 'api-key'
    if not key_path.exists():
        with open(key_path, 'x', opener=lambda f, flags: os.open(f, flags, 0o600)) as f:
            f.write(secrets.token_urlsafe(32) + '\n')
    if not key_path.read_text().strip():
        p.error('The API key file is empty.')
    launch_profile = json.loads((repository_root / 'configs/launch-template.json').read_text())
    cache_fingerprint = hashlib.sha256()
    cache_fingerprint.update(json.dumps({'kv_cache_gib': a.kv_cache_gib}).encode())
    for f in [a.runtime / 'recipe-runtime.json', repository_root / 'configs/launch-template.json', repository_root / 'scripts/qwen-claude-template.jinja']:
        cache_fingerprint.update(f.read_bytes())
    for m in [a.target, a.draft]:
        for f in sorted(m.glob('*.json')):
            cache_fingerprint.update(f.read_bytes())
        for f in sorted(m.glob('*.safetensors')):
            z = f.stat()
            cache_fingerprint.update(json.dumps([str(f), z.st_size, z.st_mtime_ns]).encode())
    cache_config = json.loads((repository_root / 'configs/disk-cache-template.json').read_text())
    cache_config.update(namespace='tp2-' + cache_fingerprint.hexdigest()[:24], root=str(a.work_dir / 'kv-cache'), port=a.cache_port, http_port=a.cache_http_port, key_file=str(key_path), log=str(a.work_dir / 'lmcache.log'))
    cache_config_path = a.work_dir / 'disk-cache.json'
    cache_config_path.write_text(json.dumps(cache_config, indent=2) + '\n')
    replacements = {'PYTHON_EXECUTABLE': sys.executable, 'RECIPE_FILES': str(repository_root / 'scripts'), 'TARGET_MODEL': str(a.target), 'DRAFT_MODEL': str(a.draft), 'PREPARED_VLLM_RUNTIME': str(a.runtime), 'DISK_CACHE_CONFIG': str(cache_config_path), 'GPU_A,GPU_B': a.gpus, 'READ_API_KEY_FROM_LOCAL_FILE': key_path.read_text().strip()}
    command = expand_placeholders(launch_profile['argv'], replacements)
    command += ['--kv-cache-memory-bytes', str(int(a.kv_cache_gib * 2 ** 30))]
    command[command.index('--port') + 1] = str(a.port)
    transfer_config = json.loads(command[command.index('--kv-transfer-config') + 1])
    transfer_config['kv_connector_extra_config']['lmcache.mp.port'] = a.cache_port
    command[command.index('--kv-transfer-config') + 1] = json.dumps(transfer_config)
    environment = os.environ.copy()
    overrides = expand_placeholders(launch_profile['environment'], replacements)
    overrides.pop('CUDA_HOME', None)
    if a.cuda_home:
        overrides['CUDA_HOME'] = str(a.cuda_home.resolve())
    elif not environment.get('CUDA_HOME') and shutil.which('nvcc'):
        overrides['CUDA_HOME'] = str(Path(shutil.which('nvcc')).resolve().parents[1])
    if not shutil.which('gcc-10') or not shutil.which('g++-10'):
        p.error('The archived profile needs gcc-10 and g++-10; see docs/setup.md.')
    overrides['PYTHONPATH'] += os.pathsep + environment.get('PYTHONPATH', '')
    for n in ['NCCL_ALGO', 'NCCL_PROTO', 'NCCL_MIN_NCHANNELS', 'NCCL_MAX_NCHANNELS', 'NCCL_P2P_LEVEL', 'VLLM_DFLASH2_DISABLE_EAGLE_BLOCK_DROP', 'VLLM_MARLIN_INPUT_DTYPE', 'VLLM_MARLIN_INT8_INCLUDE_RE', 'VLLM_MARLIN_INT8_EXCLUDE_RE', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
        environment.pop(n, None)
    overrides['NO_PROXY'] = overrides['no_proxy'] = '127.0.0.1,localhost,::1'
    cuda = overrides.get('CUDA_HOME', environment.get('CUDA_HOME'))
    if cuda:
        overrides['PATH'] = str(Path(cuda) / 'bin') + os.pathsep + environment.get('PATH', '')
    for n in ['TMPDIR', 'TRITON_CACHE_DIR', 'TORCHINDUCTOR_CACHE_DIR', 'VLLM_CACHE_ROOT', 'CUDA_CACHE_PATH']:
        f = a.work_dir / n.lower()
        f.mkdir(exist_ok=True)
        overrides[n] = str(f)
    environment.update(overrides)
    if a.numa_node is not None:
        if not shutil.which('numactl'):
            p.error('numactl is required for --numa-node.')
        command = ['numactl', '--cpunodebind=' + str(a.numa_node), '--membind=' + str(a.numa_node)] + command
    print('API: http://127.0.0.1:' + str(a.port), flush=True)
    print('Key file: ' + str(key_path), flush=True)
    print('Cache namespace: ' + cache_config['namespace'], flush=True)
    os.execvpe(command[0], command, environment)


if __name__ == '__main__':
    main()
