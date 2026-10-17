# Environment Setup

[中文](setup.zh-CN.md)

## Reference Environment

| Component | Recorded value |
| --- | --- |
| GPUs | 2 × RTX 3090 24 GB, SM86 |
| Interconnect | No NVLink; CUDA peer access false; NCCL SHM |
| Driver | 550.78, `nvidia-smi` reports CUDA 12.4 |
| User-space CUDA | 12.9, runtime 12.9.79 |
| Linux / glibc | Linux x86_64, glibc 2.35 |
| Python | 3.13.12 |
| Torch / Triton | 2.13.0+cu129 / 3.7.1 |
| Effective vLLM | Complete 0.30.0+cu129 wheel plus the nine listed patches |
| FlashInfer / compressed-tensors | 0.6.18 / 0.18.0 |
| Transformers / xgrammar | 5.12.1 / 0.2.1 |
| Compiler | gcc-10, g++-10 |

The driver's advertised CUDA version and the CUDA libraries installed inside a Python environment are different things. This combination worked on the recorded host without changing the driver. Compatibility on another host needs verification. The launcher accepts `--cuda-home /path/to/cuda-12.9`; it does not install or change a driver.

The original base environment had vLLM **0.28 distribution metadata**. `PYTHONPATH` selected a complete, separately unpacked **0.30 runtime including its native libraries**. The recipe builder reproduces that runtime, rather than copying a few Python files over an installed package. [environment.json](../benchmarks/environment.json) preserves the discrepancy.

## Existing Environments

The published preparation and launch scripts were run on the recorded host with reused Python dependencies. The resulting model/runtime served real requests and a complete Claude Code Read-tool round. A subsequent round coincided with the experiment's 82°C temperature stop. See the [assembly record](../benchmarks/assembly-validation-20261017.json); this check does not validate a fresh dependency installation or sustained-load stability.

Reuse a compatible environment if available. Before installation, inspect versions with its own Python executable. Run every recipe command with that executable. The recorded dependency versions describe the working environment; they are not a validated fresh-install lock file.

The official 0.30 wheel requests `compressed-tensors==0.17.0` and `flashinfer-python==0.6.18.post1`. The measured reused environment contains 0.18.0 and 0.6.18 respectively. Do not present its package inventory as a resolver-consistent installation recipe.

## Official Wheel

Download the pinned official release asset. A local copy can be reused.

```bash
mkdir -p downloads
curl -fL --retry 3 \
  'https://github.com/vllm-project/vllm/releases/download/v0.30.0/vllm-0.30.0%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl' \
  -o downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
sha256sum downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

Expected SHA256:

```text
e98cb69659bfcfc849cf11ce0781a7161d40b02b51a6c3636924a5909f2aabcc
```

For users in China, the same release asset can be fetched through `https://ghfast.top/https://github.com/...`; verify the digest above. Python package downloads can use `https://pypi.tuna.tsinghua.edu.cn/simple`, and model downloads can use `https://hf-mirror.com`.

## Isolated Environment Installation

This path has **not** passed a clean-host installation run. It is provided to make the remaining reproduction gap explicit. Use an isolated environment; leave working installations intact.

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/python -m pip install \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
  --extra-index-url https://download.pytorch.org/whl/cu129 \
  downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

Then install LMCache from the archived source below. Native extensions need a compatible CUDA toolkit and compiler. If these versions cannot be installed on your host, attach a sanitized environment report to an issue; do not replace the working production environment to experiment.

## LMCache Source

The working build used an unchanged upstream source snapshot, not a numbered release. Download the exact snapshot from [release v0.1.0](https://github.com/YYTbit/qwen3.8-27b-3090/releases/tag/v0.1.0), asset `LMCache-dev-b026def84282.tar.gz`.

```text
SHA256 b026def84282947124f4997a7f640b9f7682411182dc5ea83485e663a7e37d9f
```

Extract outside the repository, or in an ignored directory, and install using the same Python environment as the server:

```bash
mkdir -p scratch/lmcache
tar -xzf downloads/LMCache-dev-b026def84282.tar.gz -C scratch/lmcache
python -m pip install --no-build-isolation scratch/lmcache/LMCache-dev \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

The local build identified itself as `0.0.0+qwen.local20261015`. That tag is provenance, not an upstream version to request from PyPI. The MP connector and `lmcache.cli.main server` are used unchanged.

## Checkpoint Preparation

The pinned target starts with an asymmetric AWQ4 body and BF16 heads. `prepare_model.py` copies it to a new directory and invokes the upstream `quant_heads_stream.py`. The source is preserved. Head and embedding quantization is symmetric INT8, group size 128; linear scales are FP16 and embedding scales BF16. MTP linears are INT8, although this DFlash profile does not use MTP.

The archived target configuration then supplies the same group assignments and YaRN factor 4 with original length 262,144. This sets a 1,048,576 limit; it does not prove accuracy or speed at that length. Quantizer backup files remain beside the prepared model for inspection and consume additional space.

The runtime builder checks the wheel and patch SHA256 values, uses `patch --fuzz=0`, and writes into a new directory. On the recorded host, all 2,683 Python sources from this build matched the archived working runtime.

Model preparation audit: [preparation-audit.json](../benchmarks/preparation-audit.json). All non-MTP tensors match the measured checkpoint in shape, dtype, and raw-byte SHA256. Three unused auxiliary MTP draft-head tensors are omitted; native DFlash2 does not use them. GPU integration scope is recorded in the audits.

## Server and Client Configuration

Follow the commands in the main README. Keep the selected GPUs free of unrelated workloads: the measured two-GPU profile uses about 23.3 GiB per GPU.

The launcher creates a local key and compilation/cache directories, then starts the server in the foreground. It sets process-local variables, binds to loopback, and writes no Claude settings. Use separate work directories and ports for independent servers. A server restart with the same prepared weights, runtime, and work directory retains its disk-cache namespace.
