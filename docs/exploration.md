# Dual-GPU Performance Evaluation

**English | [简体中文](exploration.zh-CN.md)**

This report evaluates Qwen3.8-27B serving configurations on two RTX 3090 GPUs for Claude Code workloads. The evaluation covers llama.cpp, SGLang, and vLLM, with measurements of prefill scaling, parallelism, speculative decoding, cache persistence, and concurrent serving.

The selected configuration combines **vLLM 0.30, native DFlash2, and nine unchanged public HyperQwen patches**. At 18,649 input tokens with a warm prefix, it achieved **152.97 token/s median decode**. Two independent archive restorations achieved **150.77** and **145.50 token/s**; a separate public-script reconstruction achieved **144.66 token/s**.

![Dual-GPU evaluation overview](figures/decision-trail.png)

## Evaluation Setup

The host has two 24 GB RTX 3090s without NVLink or CUDA peer access. Workloads include real Claude Code conversations, tool calls, and replayed Anthropic requests. Cache state, actual context length, precision, and output limits are recorded for each result family.

The [evaluation archive](../benchmarks/history/README.md) contains 247 source artifacts across eight campaigns, 236 distinct original SHA256 digests, and 41 curated CSV rows. Artifact counts include overlapping summaries and nested reports. Private conversation content is excluded; request fingerprints and measurement metadata are retained.

| Evaluation group | Configuration | Evaluation scope |
| --- | --- | --- |
| llama.cpp | GGUF Q4_K_M; optional Q4_0 MTP draft | Allocation and short-input diagnostics |
| SGLang TP/PP | 0.5.19 cu129, AWQ W4A16, MTP | Same-prompt observations and client integration |
| SGLang dynamic chunking | PP2 with native calibration | Calibration and startup compatibility |
| vLLM long-context prefill | 0.23 cu129, W4A8, PP2, speculation disabled | Completed 520k history and chunk-size evaluation |
| vLLM MTP/DFlash | 0.23/0.28 and early 0.30 branches | Draft length, precision, graph modes, and client completion |
| Verification kernel experiments | Historical native 0.30 branch | Matched controls; archived experimental branch |
| Public runtime candidates | Native 0.30, packed INT4/MQ3D/W4A8 variants | Complete-profile selection |
| **Selected configuration** | **Native 0.30, nine public patches, batch 7167, block 1792** | **Warm replay and independent restoration** |
| Public-script reconstruction | Same public algorithms; 10.5 GiB KV/card | Checkpoint and runtime reconstruction |

The selected target uses an AWQ4 body, INT8 embeddings/output head, INT4 target KV, BF16 draft KV, and FP16 recurrent state. Its DFlash2 draft uses W4A16. In earlier W4A8 trials, weights remain 4-bit and activations use 8-bit precision. [Configuration lineage](../benchmarks/history/lineage.json) records these distinctions.

## Engine Compatibility

Six llama.cpp logs cover early Q4_K_M trials with near-1M configured context limits. Four record loading or allocation errors. At 21 prompt tokens and 128 output tokens, the no-MTP trial reached **41.51 token/s**, while an MTP trial reached **17.23 token/s**, with reported draft acceptance of 0.921 and mean emitted length of 2.82. Recovered build and launch metadata is partial. These measurements serve as short-input diagnostics ([L001–L006](../benchmarks/history/campaigns/L.json)).

Client validation covered multimodal loading, Anthropic content formats, tool execution, and multi-round completion. The selected profile completed a Read tool call and two full Claude Code rounds. [Client results](../benchmarks/results.json) are recorded separately from output-capped throughput replays.

## Long-Context Prefill

### Chunk-Size Evaluation

The vLLM 0.23 W4A8 campaign compared TP2, PP2, and static chunk budgets on a real paper-writing history.

| Configuration | Batch-token budget | Tokens completed in window | Window duration | Window prefill rate | First completed chunk |
| --- | ---: | ---: | ---: | ---: | ---: |
| TP2 | 8,192 | 15,680 | 10.071 s | 1,557 token/s | 14.87 s |
| PP2 | 4,096 | 34,496 | 10.036 s | **3,437 token/s** | 11.81 s |
| PP2 | 6,272 | 31,360 | 10.042 s | 3,123 token/s | 12.92 s |

Sampling windows begin after the first completed chunk. Under these conditions, PP2 with a 4,096-token budget produced the highest early-window rate and was selected for the completed long-history evaluation.

### Context Scaling

The completed request contained **520,761 input tokens**. Median completed-batch prefill rates decreased from **2,449 token/s** in the first 100k-token range to **363 token/s** in the final range.

![Prefill scaling across a 520k-token input](figures/prefill-decay.png)

The plot excludes the first batch and groups completed-batch rates by processed-token range. The earlier 3,437 token/s value uses a separate window statistic. End-to-end cold prefill averaged **654 token/s**, with a client-visible first token at **797.10 s**. Sources: `S038` and `S036` in [campaign S](../benchmarks/history/campaigns/S.json).

| Turn | Actual input | Engine cached tokens | Prefix hit rate | Client first token | Decode |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cold | 520,761 | 0 | 0% | 797.10 s | 21.48 token/s |
| Follow-up 1 | 523,234 | 522,144 | 99.79% | 12.91 s | 18.38 token/s |
| Follow-up 2 | 525,005 | 523,712 | 99.75% | 14.07 s | 18.79 token/s |

These measurements describe the historical **W4A8 PP2 configuration with speculation disabled**. Prefix reuse reduced follow-up latency, while long-context decode remained a separate performance constraint. Cache hits were confirmed by the engine; the historical Anthropic adapter reported zero cache tokens in its usage fields.

## Parallelism and Dynamic Chunking

SGLang native dynamic chunking was evaluated with PP2. Calibration fitted a negative quadratic coefficient after 128 samples and terminated before request execution (`S013`). A separate static PP2 gate processed 16,384 tokens in a 10.025 s observation window, approximately **1,634 token/s**, before cancellation. Its summary inherited a dynamic-chunking flag that was absent from the launch arguments; [recovered configuration records](../benchmarks/history/configurations.json) identify it as static chunking.

A later SGLang MTP evaluation used the same initial paper prompt, with **5,224 input and 4,096 output tokens** per first API phase.

![SGLang parallelism evaluation](figures/sglang-layout.png)

| Layout | First-phase decode | First thinking/text delta | Client completion |
| --- | ---: | ---: | --- |
| TP2 | **49.57 token/s** | 4.42 s | Complete, with continuation |
| PP2 | 28.97 token/s | 5.51 s | Complete, with continuation |

Dynamic chunking was disabled for these measurements. The recovered PP2 launch used AWQ W4A16, FP8 E5M2 KV, a 65,536-token limit, and historical backports with compatibility adaptations. TP2 launch metadata is partial. The figure therefore reports one observation per layout under their recorded configurations; continuation contexts subsequently diverged. Source `S016` retains all API phases and timing definitions.

## Speculative Decoding

### Draft and Precision Evaluation

The initial vLLM 0.23 campaign evaluated MTP proposal lengths, greedy and probabilistic drafting, attention backends, graph modes, recurrent-state precision, and DFlash variants.

| Candidate | First-phase input | First-phase decode | Client outcome |
| --- | ---: | ---: | --- |
| MTP1, FlashInfer, FP8 KV, greedy draft | 5,199 | 24.49 token/s | Incomplete; graph fallback observed |
| MTP3, Triton INT8 KV, greedy draft | 5,199 | 42.66 token/s | Complete |
| MTP3, Triton INT8 KV, probabilistic draft | 5,203 | 59.47 token/s | Complete |
| MTP5, Triton INT8 KV, greedy draft | 5,199 | 42.71 token/s | Complete, with continuation |
| DFlash2 with INT8 heads | 5,204 | 80.57 token/s | Complete |
| DFlash2 with FP16 recurrent state, October 15 | 5,175 | 82.23 token/s | Complete |

This matrix records complete candidate configurations, with differences in input, precision, and draft integration. DFlash8 and several W4A8 candidates terminated before a completed API phase. Full records are available in [summary.json](../benchmarks/history/summary.json) and campaigns [S](../benchmarks/history/campaigns/S.json) and [P](../benchmarks/history/campaigns/P.json).

Subsequent native 0.28/0.30 client campaigns exceeded 100 token/s on short paper questions and extended testing to longer conversations. The archived **89.97 token/s** observation used **37,208 context tokens**.

### Verification Kernel Experiments

A historical native 0.30 branch evaluated shared-verification kernels with matched 18,649-token requests.

| Historical configuration | Runs | Median decode | Median step time |
| --- | ---: | ---: | ---: |
| Lookup enabled | 3 | 123.14 token/s | 24.83 ms |
| Lookup disabled | 3 | 135.13 token/s | 24.89 ms |
| Lookup disabled, NCCL LL | 3 | 134.11 token/s | 25.01 ms |
| Initial shared verification | 3 | 147.87 token/s | 23.51 ms |
| Shared verification confirmation | 6 | 140.84 token/s | 24.56 ms |
| Shared verification, eight warps | 4 | 141.70 token/s | 23.75 ms |

The first three eight-warp outputs matched the lookup-disabled references, with paired throughput increases of approximately 4.7–4.9%. A greedy 512-token check also matched. Another candidate produced output differences; correctness records are retained in `D001`.

This experimental branch is archived separately from the selected public-patch runtime. Its complete Claude Code rates of 153.56/150.03 token/s and its 120k-context rate of 75.34 token/s retain that branch attribution.

## Runtime Configuration

The final selection used the complete official vLLM 0.30 wheel and public HyperQwen patch sequence. Candidate configurations covered packed INT4, an MQ3D subset, W4A8 activations, and W4A16 drafting.

| Runtime candidate | Cache and measurement conditions | Decode | Selection status |
| --- | --- | ---: | --- |
| Packed INT4, cold | 18,649 input; 1,024 output; profiling enabled | 32.73 token/s | Baseline |
| Packed INT4, warm | 16,128 cache hits; 1,024 output; profiling enabled | 24.10 token/s | Baseline |
| MQ3D patch subset, warm | Same source history; 1,024 output; profiling enabled | 58.84 / 92.21 token/s | Candidate |
| W4A8 activations, warm | Same source history; 16,128 hits; 1,024 output | 139.24 / 133.91 / 123.32 token/s | Candidate |
| W4A16, batch 3583 | Same source history; three warm 1,024-token outputs | Median 149.18 token/s | Earlier configuration |
| **W4A16, batch 7167** | **17,920 hits; three 1,024-token outputs** | **Median 152.97 token/s** | **Selected** |

Each row represents a complete runtime profile. Draft precision, patch selection, cache state, and profiling conditions are recorded in the archive. Component-level effects are documented by their corresponding controls.

The selected profile uses seven native DFlash2 speculative tokens, standard rejection sampling, lookup disabled, FP16 recurrent state, GPU prefix caching, and upstream LMCache. All nine patches are unchanged public upstream patches. The [runtime audit](../benchmarks/runtime-audit.json), [checkpoint audit](../benchmarks/preparation-audit.json), and [launch profile](../configs/launch-template.json) identify the published configuration.

## Reproducibility and Cache Persistence

![Archive restoration and reconstruction measurements](figures/restoration-runs.png)

| Evaluation | Median warm decode | Conditions |
| --- | ---: | --- |
| Original archive | **152.97 token/s** | 18,649 input; 17,920 cache hits; three 1,024-token outputs |
| Archive restoration 1 | **150.77 token/s** | Same request replayed after restoration |
| Archive restoration 2 | **145.50 token/s** | Second independent recovery session |
| Public-script reconstruction | **144.66 token/s** | Rebuilt checkpoint/runtime; reused dependencies; 10.5 GiB KV/card |

The figure includes all twelve observations, with three runs per group. The reconstruction used 16,128 cache hits and a smaller shared KV pool, and is reported as a separate configuration. Capped throughput runs include reasoning; complete answers and first-answer latency are documented in the [measurement guide](measurements.md).

A separate unload/restart recovered **16,128 text-prefix tokens from disk**, with zero GPU prefix hits. The first thinking/text delta arrived at **2.15 s**, and that run decoded at **161.83 token/s**. [Cache documentation](cache.md) describes namespace identity, storage capacity, and retention settings.

## Concurrent Serving

The selected TP2 profile observed **five running replay requests**, with **56.47–69.04 token/s per stream**. Four requests emitted 1,024 tokens; one emitted 311 tokens before requesting a tool. The requests shared a conversation prefix.

An earlier five-client Claude Code campaign also observed all five generating. Four clients completed two rounds, and one reached the experiment deadline. Four ten-second windows with all five active produced **234.9–258.4 token/s aggregate throughput**. These aggregate windows and the selected profile's per-stream results have separate records in the [archive](../benchmarks/history/summary.json).

Additional historical evaluations covered sub-block alignment, larger prefill buffers, and multiple API-server processes for long-history admission. Their configuration identities and request conditions are preserved in the campaign data.

## Summary

The published configuration provides a measured dual-3090 deployment with approximately **150 token/s warm single-stream decode**, independent restoration evidence, Claude Code integration, and verified text-prefix recovery after restart. Its launcher supports a 1M per-request context limit and five slots backed by a shared GPU KV pool of approximately 1.32M tokens. Further evaluation covers longer actual inputs, concurrent conversations, multi-day cache retention, and long-context quality.

Inference implementations come from [vLLM](https://github.com/vllm-project/vllm), [HyperQwen](https://github.com/syv-ai/HyperQwen), [DFlash](https://github.com/z-lab/dflash), and [LMCache](https://github.com/LMCache/LMCache); earlier evaluations used [SGLang](https://github.com/sgl-project/sglang) and [llama.cpp](https://github.com/ggml-org/llama.cpp). This repository provides the deployment configuration, reconstruction scripts, client integration, and measurement archive. See the [contribution guide](../CONTRIBUTING.md) for reproduction reports.
