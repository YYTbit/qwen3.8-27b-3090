# Qwen3.8-27B on 2 × RTX 3090

**[English](README.md) | [简体中文](README.zh-CN.md)**

A local Claude Code serving recipe using vLLM's native DFlash2 path and public HyperQwen patches. On two RTX 3090s without NVLink or CUDA peer access, a real 18.6k-token conversation reached **153 token/s median warm decode**. An independent restoration rerun reached **151 token/s**.

The repository includes the measured launch profile, ordered upstream patches, checkpoint preparation, persistent-cache setup, and timing records. The target is an abliterated AWQ4 checkpoint with INT8 embeddings and output head; the draft is DFlash2 W4A16.

**[Read the dual-GPU exploration story](docs/exploration.md):** llama.cpp, SGLang, TP/PP, dynamic chunking, MTP/DFlash, KV precision and cache reloads. The [archive](benchmarks/history/README.md) contains 247 surviving evidence artifacts and 41 curated result rows, with [explicit result-to-profile mapping](benchmarks/history/lineage.json).

## Results

| Workload | Result | Scope |
| --- | --- | --- |
| 18,649 input tokens, one warm stream | **153 token/s median**, three runs | 1,024 output tokens per run, including reasoning |
| Same profile restored from archive | **151 token/s median**, three runs | 143–161 token/s |
| Checkpoint/runtime assembled with the published scripts | **145 token/s median**, three warm runs | 10.5 GiB KV/card; 18,649 input tokens; reused Python dependencies |
| Five simultaneous streams | **56–69 token/s per stream** | Engine observed five running; four 1,024-token outputs and one 311-token tool call |
| Warm time to first thinking/text delta | **0.80–0.91 s** | First streamed reasoning/text |
| One unload/restart with disk cache | **2.15 s** to first thinking/text delta | 16,128 external-cache tokens recovered; one verified text prefix |
| Real Claude Code, complete two-round conversation | **104 / 138 token/s** | Read tool succeeded; both rounds ended normally |

Individual runs and restoration measurements are in [benchmarks/results.json](benchmarks/results.json). Rates include reasoning, with a 1,024-token output cap for the headline replays. Complete Claude Code answers and tool round trips are measured separately. The workload is a real private conversation from the recorded host.

The [public-script assembly](benchmarks/assembly-validation-20261017.json) uses a separate 1.23M-token shared KV pool. Warm first thinking/text took 2.07–2.08 s with 16,128 cached tokens. A real Claude Code round completed a Read tool call and an answer at 136 token/s; answer text began at 37.68 s. The linked record includes the complete run conditions.

**Measured headline: 18,649 actual input tokens with a warm prefix.** The archived launcher configures a 1,048,576-token per-request limit and five request slots, backed by a shared GPU KV pool of about 1.32M tokens. Further long-context and multi-client measurements are on the reproduction roadmap.

## Why this configuration

The long-history runs changed what needed measuring. An earlier vLLM W4A8 PP2 configuration reached a 3,437 token/s early prefill window, but completed-batch medians fell to 363 token/s near the end of a real 520k input. Its follow-ups hit about 99.8% of the prefix and still decoded at 18–19 token/s. Those results belong to that earlier profile.

SGLang layout observations, native dynamic-chunk calibration failures, speculation/precision trials and matched historical kernel controls are retained in the [decision trail](docs/exploration.md). The selected profile returns to native DFlash2 and nine unchanged public patches, with its own repeat and restoration evidence. Historical custom-kernel results remain separately labeled. Cross-engine conditions differ, so this repository makes no general framework speedup claim.

![The decision trail behind the retained dual-3090 profile](docs/figures/decision-trail.png)

## Stack

- vLLM **0.30.0+cu129**, complete official wheel plus **nine unmodified public HyperQwen patches**.
- Native DFlash2, seven speculative tokens, standard rejection sampling. Lookup drafting is disabled.
- AWQ4 target body, INT8 embedding and `lm_head`, W4A16 draft, INT4 target KV, BF16 draft KV.
- Tensor parallelism across two GPUs, chunked prefill, GPU prefix caching, upstream LMCache disk storage.
- Native Anthropic endpoint and a Claude-compatible chat template for text, images, and tool content.
- GPU-resident model inference, `--cpu-offload-gb 0`. Disk KV storage uses host staging during save/load.

Algorithms and kernels come from [vLLM](https://github.com/vllm-project/vllm), [HyperQwen](https://github.com/syv-ai/HyperQwen), [DFlash](https://github.com/z-lab/dflash), and [LMCache](https://github.com/LMCache/LMCache). See [upstream attribution](THIRD_PARTY.md).

## Quick start

This is a measured recipe for Linux, two 24 GB RTX 3090s, and a compatible CUDA 12.9 user-space environment. Each GPU used about 23.3 GiB on the recorded host. **Read [environment setup](docs/setup.md) first**: the original environment was reused, and a clean-machine dependency install has not been validated.

```bash
git clone https://github.com/YYTbit/qwen3.8-27b-3090.git
cd qwen3.8-27b-3090
```

### 1. Download the pinned checkpoints

Use an existing compatible environment or the setup guide. Hugging Face downloads can use the Chinese mirror.

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download twolven/Qwen3.8-27B-abliterated-AWQ-MTP \
  --revision c2f5341e7c9a1c55e6d61cfc8e6d0ca897bd7443 --local-dir weights/base
hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
  --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 --local-dir weights/draft
```

### 2. Prepare a separate checkpoint and runtime

Use the Python executable from your compatible environment. The model step copies the source before running the upstream CPU quantizer. Allow space for the new checkpoint and its backups.

```bash
python scripts/prepare_model.py --source weights/base --output weights/target-head8
python scripts/prepare_runtime.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

The [wheel source](configs/wheel-source.json) pins its official URL and SHA256. The runtime builder verifies the wheel and patches and applies them with `fuzz=0` in a new directory.

Model preparation audit: [preparation-audit.json](benchmarks/preparation-audit.json). All non-MTP tensors match the measured checkpoint in shape, dtype, and raw-byte SHA256. Three unused auxiliary MTP draft-head tensors are omitted; native DFlash2 does not use them. See the audit files for the validated scope.

### 3. Start the model

```bash
python scripts/serve.py --runtime runtime/tp2 \
  --target weights/target-head8 --draft weights/draft \
  --work-dir .local --gpus 0,1 --port 8000
```

Keep this process running. The first start compiles kernels and graphs and can take several minutes; wait for `Application startup complete` before connecting. The API binds to `127.0.0.1:8000`; a random local API key is written to `.local/api-key`. Persistent KV files live under `.local/kv-cache`. `Ctrl+C` stops the server and its cache worker; it retains the weights and disk cache on storage.

The portable launcher pins KV storage to **10.5 GiB per GPU** to leave workspace headroom. The archived measurement used automatic sizing at 0.94 GPU utilization; its original arguments remain in the launch template. Both configurations keep the 1M limit and five slots, with different shared pool capacities. `--kv-cache-gib` controls the portable budget.

For a multi-socket host, inspect `nvidia-smi topo -m` and optionally pass `--numa-node N`. The measured profile disables P2P and custom all-reduce. See the [complete launch profile](configs/launch-template.json).

### 4. Connect Claude Code

Run Claude Code in a second terminal:

```bash
env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL=http://127.0.0.1:8000 \
  ANTHROPIC_AUTH_TOKEN="$(cat .local/api-key)" \
  claude --model qwen3.8-27b-uncensor
```

These environment variables apply to that process. The launcher writes no Claude Code or cc-switch configuration. Service startup and Claude sessions are independent, so several clients can use one server. Run the command from the repository or use an absolute key-file path when working elsewhere. Normal Claude Code permissions remain under your control.

## Measure your own workload

Export a shareable Anthropic Messages request as a local JSON file. The timing tool accepts loopback endpoints and saves usage/timing metadata without prompt or response text.

```bash
python scripts/benchmark.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

See [measurement details](docs/measurements.md) for cold versus warm runs, per-stream reporting, and correctness checks. A private request fingerprint is published with the original results; the underlying conversation is excluded.

## Caching and context configuration

GPU prefix cache avoids repeated prefill while the engine stays loaded. LMCache saves compatible KV/state objects to disk and reloads them after an unload. The recipe requests a 256 GiB LRU disk store without a configured TTL. [Cache notes](docs/cache.md) describe namespace identity, capacity accounting and restart behavior.

Cache reuse depends on an identical prefix, model/runtime layout, and available cached blocks. The reproduction roadmap includes long-context quality and INT4 KV evaluation.

The model accepts image inputs. The recorded restart measurement covers a text prefix; multimodal disk-cache reuse and multi-day retention are included in the next validation stage. See [cache behavior and troubleshooting](docs/cache.md).

## Roadmap

- [x] Archive and restore the dual-GPU profile and retain measured results.
- [x] Publish bilingual documentation, public patch hashes, model preparation, and a local timing tool.
- [x] Publish the exploration archive, configuration lineage, failed paths and bilingual decision story.
- [ ] Validate installation from a fresh environment on another host.
- [ ] Validate long-context performance, multimodal persistence, and multi-day cache reuse.

## Contributing

Reproductions on other machines are welcome. Include actual context length, output length, cache state, topology, and each stream's speed. [Reporting guide](CONTRIBUTING.md) · [Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues)

## License

[Apache-2.0](LICENSE). Model weights are downloaded separately under their respective licenses. [Third-party attribution](THIRD_PARTY.md).
