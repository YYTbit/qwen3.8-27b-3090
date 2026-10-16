# Four-GPU experiments

[中文](four-gpu.zh-CN.md)

These candidates use four RTX 3090s, TP4, native DFlash2, a 1,048,576 configured context limit, five request slots, INT4 target KV, and zero CPU model offload. Total device memory is limited to 17 GiB per physical GPU. The host has no NVLink or CUDA peer access, and NCCL uses host shared memory.

The workload is the same real 18,649-token Claude Code history. Each stream has a 1,024-token output cap, includes reasoning, and uses a 10-second warm first-token deadline. The context configuration is not an actual 1M input measurement.

| Candidate | Warm single-stream median | Completed clients out of five | Observed rates of completed streams | Max requests running |
| --- | --- | --- | --- | --- |
| W4A8, standard sampling | 85.84 tok/s | 4 | 33.79–45.29 tok/s | 5 |
| W4A8 + native batch-sharded sampling | 82.28 tok/s | 4 | 37.80–43.27 tok/s | 5 |
| W4A8 + native per-worker NUMA binding | 68.08 tok/s | 2 | 40.93–45.52 tok/s | 4 |

Unfinished clients were canceled at the first-token deadline. The completed streams therefore spend part of their output window with fewer clients running. **These ranges do not establish successful sustained five-stream performance.** Every completed client in this table generated 1,024 tokens. [Machine-readable records](../benchmarks/four-gpu-20261017.json) retain the individual results.

All three candidates were rejected as defaults. Peak total GPU memory remained below 15.25 GiB per card, with no observed critical Xid event. Low memory usage or low board power does not by itself establish an engine defect or predict a speed gain.

## Native features checked

vLLM's [batch-sharded sampling](https://docs.vllm.ai/en/stable/cli/serve/) is disabled by default. The Qwen implementation provides `compute_logits_local`; all four workers confirmed activation. It reduces replicated vocabulary sampling through an all-to-all exchange, but did not improve this workload.

The same official release supports per-worker NUMA binding. GPU nodes were detected as `[0, 0, 1, 1]`, and the worker bindings were confirmed. An initial launch failed because an unpacked upstream `numa_wrapper.sh` lost its executable permission. Restoring the official wheel's mode `0755`, with unchanged file content, resolved startup. The public runtime builder now preserves wheel file modes.

[Block verification](https://github.com/vllm-project/vllm/pull/46781) is also present in Model Runner V2 as `rejection_sample_method=block`. It is a candidate for a later controlled run; no local result is claimed here.

## Two replicas

Native DP2 × TP2 can avoid a four-rank tensor-parallel group. It needs two model copies and two KV pools. The current TP2 model/draft load is about 9.2 GiB per card. A 1M target INT4 KV cache requires at least another 8 GiB per card before scales, recurrent state, and workspaces. The existing profile therefore cannot be duplicated under a 17 GiB cap while preserving 1M capacity.

Reducing the experimental context limit could diagnose the topology benefit, but it would be a different configuration. It would not complete the 1M target. CPU model offload is outside this recipe's inference profile.

The validated dual-GPU profile remains the reference. A replacement needs readable output, successful real Claude Code turns, measured per-stream concurrency, and the required memory/context scope.
