import os
import signal
import sys

from muban_shencha import shencha
from vllm.entrypoints.cli.main import main


def tuichu(bianhao, zhen):
    raise KeyboardInterrupt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, tuichu)
    cipan = None
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        if '--chat-template' not in sys.argv:
            raise RuntimeError('Claude-compatible Qwen chat template is required.')
        shencha(sys.argv[sys.argv.index('--chat-template') + 1])
        if os.environ.get('QWEN_DISK_CACHE_CONFIG'):
            from cipan_fuwu import qidong
            cipan = qidong(os.environ['QWEN_DISK_CACHE_CONFIG'])
    try:
        main()
    finally:
        if cipan is not None and cipan.poll() is None:
            cipan.terminate()
            try:
                cipan.wait(timeout=15)
            except Exception:
                cipan.kill()
                cipan.wait(timeout=5)
