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


def replay_request(client_id, a, payload, api_key, barrier):
    record = {'client': client_id, 'status': 'not_started', 'usage': {}, 'first_thinking_or_text_s': None, 'first_answer_s': None, 'last_delta_s': None, 'stop_reason': None, 'stream_tokens_per_s': None}
    request = urllib.request.Request(a.url.rstrip('/') + '/v1/messages', data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key, 'x-api-key': api_key, 'anthropic-version': '2023-06-01'})
    barrier.wait()
    start_time = time.monotonic()
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=a.ttft_limit) as f:
            record['http_status'] = f.status
            while True:
                elapsed = time.monotonic() - start_time
                remaining = (a.ttft_limit if record['first_thinking_or_text_s'] is None else a.total_limit) - elapsed
                if remaining <= 0:
                    raise TimeoutError
                f.fp.raw._sock.settimeout(remaining)
                line = f.readline()
                if not line:
                    break
                if not line.startswith(b'data: '):
                    continue
                event_data = line[6:].strip()
                if event_data == b'[DONE]':
                    break
                event = json.loads(event_data)
                elapsed = time.monotonic() - start_time
                event_type = event.get('type')
                if event_type == 'error':
                    record['status'] = 'api_error'
                    record['error_type'] = event.get('error', {}).get('type', 'unknown')
                    break
                if event_type == 'message_start':
                    record['usage'].update(event.get('message', {}).get('usage', {}))
                if event_type == 'message_delta':
                    record['usage'].update(event.get('usage', {}))
                    record['stop_reason'] = event.get('delta', {}).get('stop_reason')
                if event_type == 'content_block_delta':
                    delta = event.get('delta', {})
                    delta_type = delta.get('type')
                    if delta_type in ['thinking_delta', 'text_delta'] and (delta.get('thinking') or delta.get('text')):
                        if record['first_thinking_or_text_s'] is None:
                            record['first_thinking_or_text_s'] = elapsed
                        if delta_type == 'text_delta' and record['first_answer_s'] is None:
                            record['first_answer_s'] = elapsed
                        record['last_delta_s'] = elapsed
                if event_type == 'message_stop':
                    record['status'] = 'response_finished'
                    break
            if record['status'] == 'not_started':
                record['status'] = 'incomplete_stream'
    except (TimeoutError, socket.timeout):
        record['status'] = 'ttft_timeout' if record['first_thinking_or_text_s'] is None else 'total_timeout'
    except urllib.error.HTTPError as e:
        record['status'] = 'http_error'
        record['http_status'] = e.code
    except (OSError, ValueError, AttributeError) as e:
        record['status'] = 'client_error'
        record['error_type'] = type(e).__name__
    record['elapsed_s'] = time.monotonic() - start_time
    first_delta = record['first_thinking_or_text_s']
    last_delta = record['last_delta_s']
    output_tokens = record['usage'].get('output_tokens', 0)
    if record['status'] == 'response_finished' and first_delta is not None and last_delta > first_delta and output_tokens > 1:
        record['stream_tokens_per_s'] = (output_tokens - 1) / (last_delta - first_delta)
    return record


def main():
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
    payload = json.dumps(x, ensure_ascii=False).encode()
    api_key = a.key_file.read_text().strip()
    barrier = threading.Barrier(a.concurrency)
    with ThreadPoolExecutor(max_workers=a.concurrency) as executor:
        results = list(executor.map(lambda i: replay_request(i, a, payload, api_key, barrier), range(1, a.concurrency + 1)))
    summary = {'request_sha256': hashlib.sha256(payload).hexdigest(), 'request_text_saved': False, 'includes_reasoning': True, 'measurement': '(output_tokens - 1) / (last thinking/text delta - first thinking/text delta)', 'requested_concurrency': a.concurrency, 'running_concurrency_verified': False, 'clients': results}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    for r in results:
        print(json.dumps({k: r[k] for k in ['client', 'status', 'first_thinking_or_text_s', 'first_answer_s', 'stream_tokens_per_s']}))


if __name__ == '__main__':
    main()
