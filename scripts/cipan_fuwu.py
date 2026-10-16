import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


def zhuangtai(peizhi):
    miyao = Path(peizhi['key_file']).read_text().strip()
    r = urllib.request.Request('http://127.0.0.1:%d/status' % peizhi['http_port'],
                               headers={'Authorization': 'Bearer ' + miyao})
    with urllib.request.urlopen(r, timeout=3) as f:
        return json.load(f)


def qidong(wenjian):
    peizhi = json.loads(Path(wenjian).read_text())
    for duankou in (peizhi['port'], peizhi['http_port'], peizhi['http_port'] + 1):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', duankou))
            except OSError as e:
                raise RuntimeError('A persistent cache port is already occupied: ' + str(duankou)) from e
    shipei = {'type': 'fs_native',
               'base_path': str(Path(peizhi['root']) / peizhi['namespace'] / 'objects'),
               'num_workers': 4, 'use_odirect': False,
               'max_capacity_gb': peizhi['capacity_gb'],
               'eviction': {'eviction_policy': 'LRU'}}
    canshu = [sys.executable, '-m', 'lmcache.cli.main', 'server',
              '--host', '127.0.0.1', '--port', str(peizhi['port']),
              '--http-host', '127.0.0.1', '--http-port', str(peizhi['http_port']),
              '--prometheus-port', str(peizhi['http_port'] + 1),
              '--disable-metrics', '--enable-extra-logging',
              '--http-api-key-file', peizhi['key_file'],
              '--chunk-size', str(peizhi['chunk_size']), '--separate-object-groups',
              '--max-workers', '4', '--l1-size-gb', str(peizhi['l1_size_gb']),
              '--l1-use-lazy', '--eviction-policy', 'noop',
              '--l2-store-policy', 'skip_l1', '--l2-adapter', json.dumps(shipei)]
    huanjing = os.environ.copy()
    huanjing['LMCACHE_TRACK_USAGE'] = 'false'
    huanjing['LMCACHE_REQUEST_TELEMETRY_TYPE'] = 'noop'
    with Path(peizhi['log']).open('a') as log:
        p = subprocess.Popen(canshu, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, env=huanjing, close_fds=True)
    jiezhi = time.monotonic() + 90
    while time.monotonic() < jiezhi:
        if p.poll() is not None:
            raise RuntimeError('The disk KV backend exited; inspect ' + peizhi['log'])
        try:
            if zhuangtai(peizhi).get('is_healthy'):
                return p
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    p.terminate()
    p.wait(timeout=10)
    raise RuntimeError('The disk KV backend did not become healthy; inspect ' + peizhi['log'])
