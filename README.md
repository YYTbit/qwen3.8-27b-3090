# Qwen3.8-27B on 2 × RTX 3090

**[English](README.md) | [简体中文](README.zh-CN.md)**

A local Claude Code serving recipe using vLLM's native DFlash2 path and public HyperQwen patches. On two RTX 3090s without NVLink or CUDA peer access, a real 18.6k-token conversation reached **153 token/s median warm decode**. An independent restoration rerun reached **151 token/s**.

The repository includes the measured launch profile, ordered upstream patches, checkpoint preparation, persistent-cache setup, and timing records. The target is an abliterated AWQ4 checkpoint with INT8 embeddings and output head; the draft is DFlash2 W4A16.

## Results

| Workload | Result | Scope |
| --- | --- | --- |
| 18,649 input tokens, one warm stream | **153 token/s median**, three runs | 1,024 output tokens per run, including reasoning |
| Same profile restored from archive | **151 token/s median**, three runs | 143–161 token/s |
| Five simultaneous streams | **56–69 token/s per stream** | Engine observed five running; four 1,024-token outputs and one 311-token tool call |
| Warm time to first thinking/text delta | **0.80–0.91 s** | Not time to the final answer |
| One unload/restart with disk cache | **2.15 s** to first thinking/text delta | 16,128 external-cache tokens recovered; one verified text prefix |
| Real Claude Code, complete two-round conversation | **104 / 138 token/s** | Read tool succeeded; both rounds ended normally |
| 120k-token cold input with images | No first token within 100 s | Canceled at the deadline |

Full records, including the later restoration conversation and failed targets, are in [benchmarks/results.json](benchmarks/results.json). Rates include thinking tokens. The three headline runs reached `max_tokens` before answer text appeared. These are local observations on a private workload, not a public leaderboard or a quality evaluation.

**1M is the configured context limit. Actual 1M performance, five streams each above 100 token/s, and multi-day 99% cache hits remain unverified.** The shared GPU KV pool is about 1.32M tokens; five slots do not provide five independent resident 1M contexts.

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
python scripts/zhunbei_moxing.py --source weights/base --output weights/target-head8
python scripts/zhunbei_yunxing.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

The [wheel source](configs/wheel-source.json) pins its official URL and SHA256. The runtime builder verifies the wheel and patches and applies them with `fuzz=0` in a new directory.

Model preparation audit: [preparation-audit.json](benchmarks/preparation-audit.json). All non-MTP tensors match the measured checkpoint in shape, dtype, and raw-byte SHA256. Three unused auxiliary MTP draft-head tensors are omitted; native DFlash2 does not use them. See the audit files for the validated scope.

### 3. Start the model

```bash
python scripts/qidong.py --runtime runtime/tp2 \
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
python scripts/cesu.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

See [measurement details](docs/measurements.md) for cold versus warm runs, per-stream reporting, and correctness checks. A private request fingerprint is published with the original results; the underlying conversation is excluded.

## Cache and long-context limits

GPU prefix cache avoids repeated prefill while the engine stays loaded. LMCache saves compatible KV/state objects to disk and can reload them after an unload. The recipe has no configured TTL and requests a 256 GiB LRU disk store. The upstream store's accounting across restarts is incomplete, so this is not a strict cross-restart capacity guarantee.

Cache reuse depends on an identical prefix, model/runtime layout, and available cached blocks. Abliteration does not imply a safety or intelligence guarantee. Long-context quality and the effect of INT4 KV need separate evaluation.

Image inputs can use the multimodal model, but the verified restart result covers text. Multimodal disk-cache reuse, multi-day retention, independent 1M sessions, and 1M cold-prefill latency have not passed end-to-end validation. See [cache behavior and troubleshooting](docs/cache.md).

## Roadmap

- [x] Archive and restore the dual-GPU profile and retain measured results.
- [x] Publish bilingual documentation, public patch hashes, model preparation, and a local timing tool.
- [ ] Validate installation from a fresh environment on another host.
- [ ] Improve four-GPU, five-stream performance within **17 GiB per GPU**.
- [ ] Validate long-context performance, multimodal persistence, and multi-day cache reuse.

See the [four-GPU experiment report](docs/four-gpu.md) for rejected W4A8, batch-sharded sampling, and NUMA candidates, including individual stream results.

## Contributing

Reproductions on other machines are welcome. Include actual context length, output length, cache state, topology, and each stream's speed. [Reporting guide](CONTRIBUTING.md) · [Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues)

## License

[Apache-2.0](LICENSE). Model weights are downloaded separately under their respective licenses. [Third-party attribution](THIRD_PARTY.md).
