# Measurement Methodology

This document defines metrics for the selected deployment. Earlier engine and branch measurements retain their original definitions in the [evaluation report](exploration.md) and [configuration lineage](../benchmarks/history/lineage.json).

## Workload

The reference request is a real Claude Code conversation containing **18,649 input tokens**. Its canonical SHA256 is recorded in [results.json](../benchmarks/results.json). Private conversation content is excluded from the public archive. Reproduction on other hosts uses a locally supplied Anthropic Messages request.

## Timing Metrics

Single-stream decode throughput is calculated as:

```text
decode rate = (API output_tokens - 1) / (last thinking/text delta time - first thinking/text delta time)
```

The estimate uses streamed event arrival times and includes reasoning. Time before the first thinking/text delta is reported separately. The three headline warm runs each produced 1,024 tokens and reached the output limit during reasoning.

| Metric | Definition |
| --- | --- |
| First thinking/text delta | Time from request submission to the first streamed reasoning or text content |
| First answer | Time from request submission to the first answer-text content |
| Stream decode rate | API output tokens over the interval between first and last content deltas, as defined above |
| Complete-conversation rate | Total output tokens over a client turn, including tool and continuation gaps |

Complete Claude Code turns are measured separately. The latest restoration generated 6,318 and 12,238 tokens at 133.36 and 117.29 token/s. In the second round, the first thinking delta arrived at 1.09 s and the first answer text at 97.71 s.

## Cache State

The reference warm runs used **17,920 cached tokens and 729 uncached tokens**, approximately 96.1% prefix hits. Cache state is classified as cold, GPU-warm, or disk-reloaded.

The recorded restart recovered 16,128 tokens from external cache with zero GPU prefix hits. This measurement covers one text prefix after one unload. Multi-day and multimodal persistence are separate evaluation tasks.

## Concurrency

The selected five-request replay observed `max_running=5`. Four streams emitted 1,024 tokens; one emitted 311 tokens and stopped for tool use. Reported **56–69 token/s** rates are per stream, with all five clients included. Requests shared a prefix.

The timing tool submits clients together and records `running_concurrency_verified=false`, since engine scheduling metrics require separate collection. Reports should include submitted, running, and waiting requests, with per-stream and aggregate rates labeled explicitly.

## Reproduction Procedure

1. Match model revisions, checkpoint preparation, runtime patches, sampling settings, and launch profile.
2. Provide an Anthropic Messages JSON containing `model`, `messages`, and `max_tokens`, together with any system content, tools, or images.
3. Record cache state. Use a separate cache namespace after changes to the model, runtime, or parallelism.
4. Collect single-client and concurrent measurements, including cancellations and tool stops.
5. Validate readable answers and successful tool execution in Claude Code.
6. Report actual input/output tokens, first thinking/text delta, first answer, per-stream throughput, peak GPU memory, and running-request counts.

`scripts/benchmark.py` records timing, usage, and a request digest for loopback endpoints. Conversation text is excluded. `--ttft-limit 100` permits a cold-run deadline; warm checks use 10 s. Timeouts close the corresponding request while the shared server remains running.

## Sampling Configuration

The captured request uses adaptive thinking without temperature, top-p, or top-k overrides. The checkpoint defaults are temperature 1.0, top-p 0.95, top-k 20, and repetition penalty 1.05, recorded in [generation-config.json](../configs/generation-config.json). Reproductions should identify both request-level overrides and model defaults.

## Evaluation Roadmap

- Actual 1M-token cold prefill within 100 s.
- Five concurrent 1M sessions with per-stream decode above 100 token/s.
- Multi-day cache retention and realistic-session prefix hit rates above 99%.
- Long-context quality evaluation of the abliterated target and INT4 KV.
