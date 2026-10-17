import os
import signal
import sys

from template_validator import validate_template
from vllm.entrypoints.cli.main import main


def handle_shutdown(signal_number, frame):
    raise KeyboardInterrupt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_shutdown)
    cache_process = None
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        if '--chat-template' not in sys.argv:
            raise RuntimeError('Claude-compatible Qwen chat template is required.')
        validate_template(sys.argv[sys.argv.index('--chat-template') + 1])
        if os.environ.get('QWEN_DISK_CACHE_CONFIG'):
            from disk_cache import start_cache
            cache_process = start_cache(os.environ['QWEN_DISK_CACHE_CONFIG'])
    try:
        main()
    finally:
        if cache_process is not None and cache_process.poll() is None:
            cache_process.terminate()
            try:
                cache_process.wait(timeout=15)
            except Exception:
                cache_process.kill()
                cache_process.wait(timeout=5)
