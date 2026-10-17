import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


def get_status(config):
    api_key = Path(config['key_file']).read_text().strip()
    r = urllib.request.Request('http://127.0.0.1:%d/status' % config['http_port'],
                               headers={'Authorization': 'Bearer ' + api_key})
    with urllib.request.urlopen(r, timeout=3) as f:
        return json.load(f)


def start_cache(config_path):
    config = json.loads(Path(config_path).read_text())
    for port in (config['port'], config['http_port'], config['http_port'] + 1):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', port))
            except OSError as e:
                raise RuntimeError('A persistent cache port is already occupied: ' + str(port)) from e
    adapter = {'type': 'fs_native',
               'base_path': str(Path(config['root']) / config['namespace'] / 'objects'),
               'num_workers': 4, 'use_odirect': False,
               'max_capacity_gb': config['capacity_gb'],
               'eviction': {'eviction_policy': 'LRU'}}
    command = [sys.executable, '-m', 'lmcache.cli.main', 'server',
              '--host', '127.0.0.1', '--port', str(config['port']),
              '--http-host', '127.0.0.1', '--http-port', str(config['http_port']),
              '--prometheus-port', str(config['http_port'] + 1),
              '--disable-metrics', '--enable-extra-logging',
              '--http-api-key-file', config['key_file'],
              '--chunk-size', str(config['chunk_size']), '--separate-object-groups',
              '--max-workers', '4', '--l1-size-gb', str(config['l1_size_gb']),
              '--l1-use-lazy', '--eviction-policy', 'noop',
              '--l2-store-policy', 'skip_l1', '--l2-adapter', json.dumps(adapter)]
    environment = os.environ.copy()
    environment['LMCACHE_TRACK_USAGE'] = 'false'
    environment['LMCACHE_REQUEST_TELEMETRY_TYPE'] = 'noop'
    with Path(config['log']).open('a') as log:
        p = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, env=environment, close_fds=True)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if p.poll() is not None:
            raise RuntimeError('The disk KV backend exited; inspect ' + config['log'])
        try:
            if get_status(config).get('is_healthy'):
                return p
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    p.terminate()
    p.wait(timeout=10)
    raise RuntimeError('The disk KV backend did not become healthy; inspect ' + config['log'])
