import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description='Prepare a separate head8 checkpoint using the unmodified HyperQwen CPU script.')
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.source = a.source.resolve()
    a.output = a.output.resolve()
    repository_root = Path(__file__).resolve().parents[1]
    if a.output.exists() or a.source == a.output or a.source in a.output.parents:
        p.error('Choose a new output directory outside the source checkpoint.')
    if not (a.source / 'model.safetensors.index.json').is_file():
        p.error('The source checkpoint needs model.safetensors.index.json.')
    config = json.loads((a.source / 'config.json').read_text())
    quantization = config.get('quantization_config', {})
    if quantization.get('quant_method') != 'compressed-tensors' or 'group_0' not in quantization.get('config_groups', {}):
        p.error('Use the pinned compressed-tensors AWQ source in configs/model-sources.json.')
    shutil.copytree(a.source, a.output, ignore=shutil.ignore_patterns('.*', '*.bak*', '*.tmp', '*.log', '__pycache__'))
    environment = os.environ.copy()
    environment['CUDA_VISIBLE_DEVICES'] = ''
    environment.setdefault('OMP_NUM_THREADS', '4')
    subprocess.run([sys.executable, '-B', str(repository_root / 'third_party/hyperqwen/prepare/quant_heads_stream.py'), str(a.output), '--mtp-bits', '8'], env=environment, check=True)
    shutil.copy2(repository_root / 'configs/target-config.json', a.output / 'config.json')
    provenance = {'base': json.loads((repository_root / 'configs/model-sources.json').read_text())['base_target'], 'quantizer': json.loads((repository_root / 'third_party/hyperqwen/provenance.json').read_text()), 'config_sha256': hashlib.sha256((a.output / 'config.json').read_bytes()).hexdigest(), 'source_modified': False, 'cpu_only_preparation': True}
    (a.output / 'recipe-preparation.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Prepared checkpoint: ' + str(a.output))
    print('Original checkpoint preserved. Quantizer backups remain in the output directory.')


if __name__ == '__main__':
    main()
