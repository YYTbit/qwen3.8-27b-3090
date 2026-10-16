import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
import urllib.error
import urllib.request


def qingqiu(bianhao, a, zhengwen, miyao, tongbu):
    jilu = {'client': bianhao, 'status': 'not_started', 'usage': {}, 'first_thinking_or_text_s': None, 'first_answer_s': None, 'last_delta_s': None, 'stop_reason': None, 'stream_tokens_per_s': None}
    xinxi = urllib.request.Request(a.url.rstrip('/') + '/v1/messages', data=zhengwen, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + miyao, 'x-api-key': miyao, 'anthropic-version': '2023-06-01'})
    tongbu.wait()
    kaishi = time.monotonic()
    try:
        daikai = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with daikai.open(xinxi, timeout=a.ttft_limit) as f:
            jilu['http_status'] = f.status
            while True:
                xianzai = time.monotonic() - kaishi
                shengyu = (a.ttft_limit if jilu['first_thinking_or_text_s'] is None else a.total_limit) - xianzai
                if shengyu <= 0:
                    raise TimeoutError
                f.fp.raw._sock.settimeout(shengyu)
                hang = f.readline()
                if not hang:
                    break
                if not hang.startswith(b'data: '):
                    continue
                shuju = hang[6:].strip()
                if shuju == b'[DONE]':
                    break
                xiang = json.loads(shuju)
                xianzai = time.monotonic() - kaishi
                leixing = xiang.get('type')
                if leixing == 'error':
                    jilu['status'] = 'api_error'
                    jilu['error_type'] = xiang.get('error', {}).get('type', 'unknown')
                    break
                if leixing == 'message_start':
                    jilu['usage'].update(xiang.get('message', {}).get('usage', {}))
                if leixing == 'message_delta':
                    jilu['usage'].update(xiang.get('usage', {}))
                    jilu['stop_reason'] = xiang.get('delta', {}).get('stop_reason')
                if leixing == 'content_block_delta':
                    bianhua = xiang.get('delta', {})
                    leibie = bianhua.get('type')
                    if leibie in ['thinking_delta', 'text_delta'] and (bianhua.get('thinking') or bianhua.get('text')):
                        if jilu['first_thinking_or_text_s'] is None:
                            jilu['first_thinking_or_text_s'] = xianzai
                        if leibie == 'text_delta' and jilu['first_answer_s'] is None:
                            jilu['first_answer_s'] = xianzai
                        jilu['last_delta_s'] = xianzai
                if leixing == 'message_stop':
                    jilu['status'] = 'response_finished'
                    break
            if jilu['status'] == 'not_started':
                jilu['status'] = 'incomplete_stream'
    except (TimeoutError, socket.timeout):
        jilu['status'] = 'ttft_timeout' if jilu['first_thinking_or_text_s'] is None else 'total_timeout'
    except urllib.error.HTTPError as e:
        jilu['status'] = 'http_error'
        jilu['http_status'] = e.code
    except (OSError, ValueError, AttributeError) as e:
        jilu['status'] = 'client_error'
        jilu['error_type'] = type(e).__name__
    jilu['elapsed_s'] = time.monotonic() - kaishi
    shou = jilu['first_thinking_or_text_s']
    wei = jilu['last_delta_s']
    shuliang = jilu['usage'].get('output_tokens', 0)
    if jilu['status'] == 'response_finished' and shou is not None and wei > shou and shuliang > 1:
        jilu['stream_tokens_per_s'] = (shuliang - 1) / (wei - shou)
    return jilu


def zhixing():
    p = argparse.ArgumentParser(description='Replay your own Anthropic request against a loopback endpoint; save timing metadata.')
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--key-file', required=True, type=Path)
    p.add_argument('--request', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--concurrency', type=int, default=1)
    p.add_argument('--ttft-limit', type=float, default=10)
    p.add_argument('--total-limit', type=float, default=120)
    a = p.parse_args()
    from urllib.parse import urlparse
    u = urlparse(a.url)
    if u.scheme != 'http' or u.hostname not in ['127.0.0.1', 'localhost', '::1'] or u.username or u.password:
        p.error('Use a local HTTP endpoint. This script does not send requests to paid providers.')
    if not 1 <= a.concurrency <= 5 or a.ttft_limit <= 0 or a.total_limit < a.ttft_limit:
        p.error('Use 1 to 5 clients and positive deadlines with total-limit >= ttft-limit.')
    if a.output.exists():
        p.error('Choose a new output file.')
    x = json.loads(a.request.read_text())
    x['stream'] = True
    zhengwen = json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    miyao = a.key_file.read_text().strip()
    tongbu = threading.Barrier(a.concurrency)
    with ThreadPoolExecutor(max_workers=a.concurrency) as chi:
        jieguo = list(chi.map(lambda i: qingqiu(i, a, zhengwen, miyao, tongbu), range(1, a.concurrency + 1)))
    zongjie = {'request_sha256': hashlib.sha256(zhengwen).hexdigest(), 'request_text_saved': False, 'includes_reasoning': True, 'measurement': '(output_tokens - 1) / (last thinking/text delta - first thinking/text delta)', 'requested_concurrency': a.concurrency, 'running_concurrency_verified': False, 'clients': jieguo}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(zongjie, f, indent=2)
        f.write('\n')
    for r in jieguo:
        print(json.dumps({k: r[k] for k in ['client', 'status', 'first_thinking_or_text_s', 'first_answer_s', 'stream_tokens_per_s']}))


if __name__ == '__main__':
    zhixing()
