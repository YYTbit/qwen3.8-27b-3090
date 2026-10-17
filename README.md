# Qwen3.8-27B on Dual RTX 3090 GPUs

**[English](README.md) | [简体中文](README.zh-CN.md)**

A local Qwen3.8-27B deployment for Claude Code, built on **vLLM, native DFlash2, and public HyperQwen patches**. The selected configuration delivers **153 token/s median warm decode at 18.6k input tokens** on two RTX 3090s without NVLink. An independent archive restoration reproduced **151 token/s**.

[Setup](docs/setup.md) · [Performance Evaluation](docs/exploration.md) · [Measurements](docs/measurements.md) · [Cache](docs/cache.md) · [Releases](https://github.com/YYTbit/qwen3.8-27b-3090/releases)

## Features

- **Claude Code integration** through the native Anthropic endpoint, with text, image, and tool content support.
- **Native speculative decoding** with seven DFlash2 proposal tokens and standard rejection sampling.
- **GPU prefix caching and persistent disk cache** through upstream LMCache.
- **Independent service lifecycle** with multiple clients and process-local connection settings.
- **Pinned deployment configuration**, checkpoint preparation, ordered upstream patches, and an archived evaluation dataset.

## Performance

| Workload | Result | Measurement conditions |
| --- | --- | --- |
| Warm single stream | **153 token/s median** | 18,649 input; three runs of 1,024 output tokens |
| Independent archive restoration | **151 token/s median** | Same request and selected profile; three runs |
| Public-script reconstruction | **145 token/s median** | Same input; separate 10.5 GiB KV/card configuration |
| Five simultaneous streams | **56–69 token/s per stream** | Five running requests observed; four 1,024-token outputs and one 311-token tool call |
| Warm first thinking/text delta | **0.80–0.91 s** | Selected profile, single stream |
| Disk-cache reload after restart | **2.15 s** to first thinking/text delta | One verified text prefix; 16,128 external-cache tokens recovered |
| Complete Claude Code conversation | **104 / 138 token/s** | Two complete rounds with a successful Read tool call |

The single-stream result uses 17,920 cached prefix tokens and includes reasoning, with a 1,024-token output limit. Complete answers and tool round trips have separate measurements. [Individual runs](benchmarks/results.json) and the [reconstruction record](benchmarks/assembly-validation-20261017.json) retain the full conditions.

The archived configuration provides a **1,048,576-token per-request limit**, **five request slots**, and a **shared GPU KV pool of approximately 1.32M tokens**. The performance table reports the actual workloads measured; long-context evaluation is tracked in the roadmap.

## Configuration

| Component | Selected configuration |
| --- | --- |
| Hardware | 2 × RTX 3090 24 GB; no NVLink; CUDA peer access unavailable |
| Runtime | Official vLLM 0.30.0+cu129 wheel with nine unchanged HyperQwen patches |
| Target model | Abliterated AWQ4 body; INT8 embeddings and output head |
| Draft model | DFlash2 W4A16; seven speculative tokens; lookup disabled |
| Cache and state precision | INT4 target KV; BF16 draft KV; FP16 recurrent state |
| Execution | TP2; chunked prefill; GPU prefix caching; CPU model offload 0 |
| Persistent cache | Upstream LMCache disk storage with host staging during save/load |

The [evaluation report](docs/exploration.md) documents configuration selection across llama.cpp, SGLang, and vLLM, covering TP/PP, dynamic chunking, MTP/DFlash, precision, and cache persistence. The [archive](benchmarks/history/README.md) contains 247 source artifacts and 41 curated result rows with [configuration lineage](benchmarks/history/lineage.json).

![Dual-GPU evaluation overview](docs/figures/decision-trail.png)

## Quick Start

The recorded deployment uses Linux, two 24 GB RTX 3090s, and a CUDA 12.9 user-space environment, with approximately 23.3 GiB allocated per GPU. The [setup guide](docs/setup.md) covers driver compatibility, existing Python environments, and Chinese download mirrors. Deployment has been validated with reused dependencies; fresh-host installation remains a reproduction task.

```bash
git clone https://github.com/YYTbit/qwen3.8-27b-3090.git
cd qwen3.8-27b-3090
```

### Model Download

Download the pinned target and draft checkpoints. `HF_ENDPOINT` selects the Chinese mirror.

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download twolven/Qwen3.8-27B-abliterated-AWQ-MTP \
  --revision c2f5341e7c9a1c55e6d61cfc8e6d0ca897bd7443 --local-dir weights/base
hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
  --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 --local-dir weights/draft
```

### Model and Runtime Preparation

Run the following commands with the Python executable from a compatible environment. Model preparation copies the source checkpoint and invokes the upstream CPU quantizer; disk space is required for the prepared weights and quantizer backups.

```bash
python scripts/prepare_model.py --source weights/base --output weights/target-head8
python scripts/prepare_runtime.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

The builder verifies the pinned [wheel](configs/wheel-source.json) and patch hashes, then applies patches in order with `fuzz=0` in a separate runtime directory. The [checkpoint audit](benchmarks/preparation-audit.json) records matching shapes, dtypes, and raw-byte hashes for all non-MTP tensors. Three auxiliary MTP draft-head tensors are omitted from the DFlash2 checkpoint.

### Server Launch

```bash
python scripts/serve.py --runtime runtime/tp2 \
  --target weights/target-head8 --draft weights/draft \
  --work-dir .local --gpus 0,1 --port 8000
```

The server runs in the foreground and binds to `127.0.0.1:8000`. Initial kernel and graph compilation can take several minutes. Connect after `Application startup complete` appears. The local API key is stored in `.local/api-key`, and persistent KV objects are stored under `.local/kv-cache`. `Ctrl+C` releases the service's GPU allocation while retaining weights and disk cache.

The portable launcher reserves **10.5 GiB of KV storage per GPU**, producing a shared pool of approximately 1.23M tokens. The archived 153 token/s profile uses automatic sizing at 0.94 GPU utilization and a larger pool. Both retain the 1M context limit and five request slots. The KV budget is configurable with `--kv-cache-gib`.

For multi-socket hosts, inspect `nvidia-smi topo -m` and select a NUMA node with `--numa-node N` if appropriate. The recorded configuration disables P2P and custom all-reduce. See the [launch profile](configs/launch-template.json).

### Claude Code Connection

Run Claude Code in another terminal:

```bash
env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL=http://127.0.0.1:8000 \
  ANTHROPIC_AUTH_TOKEN="$(cat .local/api-key)" \
  claude --model qwen3.8-27b-uncensor
```

Connection settings apply to this process. Existing Claude Code and cc-switch configuration files are preserved. Multiple clients can share the independently managed server. Use an absolute key-file path when launching from another directory; client permissions remain controlled by Claude Code.

## Benchmarking

Save an Anthropic Messages request as a local JSON file and run:

```bash
python scripts/benchmark.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

The tool accepts loopback endpoints and records usage, timing, and a request digest. Conversation content remains local. The [measurement guide](docs/measurements.md) defines cold, GPU-warm, and disk-reloaded runs, per-stream throughput, and complete-client validation.

## Cache Persistence

GPU prefix caching reuses processed prefixes during engine operation. LMCache persists compatible KV and state objects for reuse after a restart. The configuration requests a **256 GiB LRU disk store with no TTL**. Cache identity includes the model, runtime, launch profile, and template.

One text-prefix unload/restart has been verified. Multi-day retention, multimodal persistence, and long-context quality are included in the roadmap. See [cache configuration and troubleshooting](docs/cache.md) for storage accounting and namespace details.

## Roadmap

- [x] Archive the selected profile and reproduce it through independent restorations.
- [x] Publish bilingual setup, checkpoint preparation, pinned patches, and measurement tools.
- [x] Publish engine evaluations, configuration lineage, and editable figures.
- [ ] Validate installation on a fresh host.
- [ ] Extend long-context and concurrent-client evaluation.
- [ ] Validate multimodal cache persistence, multi-day reuse, and INT4 KV quality.

## Contributing

Reproduction reports should include actual context length, output length, cache state, topology, and each stream's throughput. See the [reporting guide](CONTRIBUTING.md) and [issue tracker](https://github.com/YYTbit/qwen3.8-27b-3090/issues).

## License and Acknowledgments

[Apache-2.0](LICENSE). Model weights are distributed separately under their respective licenses.

Inference algorithms and kernels are provided by [vLLM](https://github.com/vllm-project/vllm), [HyperQwen](https://github.com/syv-ai/HyperQwen), [DFlash](https://github.com/z-lab/dflash), and [LMCache](https://github.com/LMCache/LMCache). See [third-party attribution](THIRD_PARTY.md).
