# Measurement notes

The [exploration report](exploration.md) and [result lineage](../benchmarks/history/lineage.json) cover earlier engines and experimental branches. Their rates retain their original definitions and are attributed separately from the current profile below.

## What the headline measures

The original workload was a real Claude Code conversation with 18,649 input tokens. Its canonical SHA256 is recorded in [results.json](../benchmarks/results.json). The conversation is private and is not redistributed. The published numbers describe that workload; an exact public replay is unavailable.

For each completed stream:

```text
decode rate = (API output_tokens - 1) / (last thinking/text delta time - first thinking/text delta time)
```

This estimate uses streamed event arrival times, rather than a timestamp for every individual token. It includes reasoning. It excludes the wait before the first thinking/text delta. First answer text is measured separately. Three warm single-stream runs each produced 1,024 tokens and stopped at `max_tokens`, with no answer text yet.

Claude Code full-conversation rates use total output tokens and include gaps between tool calls and continuations. They are a different workload from a single capped stream. The latest restoration's two complete rounds generated 6,318 and 12,238 tokens at 133.36 and 117.29 token/s. The second round's first thinking delta arrived at 1.09 s, and answer text at 97.71 s. Do not label the first thinking delta as the completed answer latency.

## Cache state

The headline warm runs read 17,920 cached tokens and supplied 729 uncached tokens, about 96.1% prefix hits on that request. This does not establish 99% hits for arbitrary sessions.

The restart run recovered 16,128 tokens from external cache with no GPU prefix hits. It verified one text prefix after one unload. No multi-day or multimodal persistence claim follows from it.

## Concurrency

The original five-client measurement observed `max_running=5` at the engine. Four clients emitted 1,024 tokens; one emitted 311 tokens and stopped for tool use. Every client's rate is included. The range of 56–69 token/s is per stream, not an aggregate rate.

The included timing tool starts clients together. It does not query engine scheduling metrics, so its output explicitly says `running_concurrency_verified=false`. Submitted clients can queue; verify engine metrics separately when claiming actual concurrency. Five matching requests with a shared prefix also differ from five unrelated long conversations.

## Reproduce on your workload

1. Use the same model revisions, prepared checkpoint, runtime patches, sampling settings, and launch profile.
2. Supply your own Anthropic Messages JSON with `model`, `messages`, and `max_tokens`; retain tools, system content, and images when these are part of the workload.
3. Establish and label cold versus GPU-warm versus disk-reloaded cache state. A new cache namespace is required after model/runtime/TP changes.
4. Start with one client; then run five. Keep failures, cancellations, and early tool stops.
5. Check readable answers and successful tool execution in the actual client. A high token counter does not establish correct output.
6. Report input/output tokens, sampling, first thinking/text delta, first answer, each client's decode rate, peak GPU memory, and actual running requests.

`scripts/benchmark.py` saves metadata and a digest, not request or response text. It accepts local HTTP endpoints. Set `--ttft-limit 100` for a permitted cold run; warm acceptance checks use 10 s. A timeout closes that request. It does not shut down a shared server or establish that other clients were unaffected.

## Next measurement stage

- Actual 1M cold prefill within 100 s.
- Five concurrent 1M sessions, each decoding above 100 token/s.
- Multi-day cache retention and 99% hit rates across realistic conversations.
- Full long-context quality evaluation of the abliterated target and INT4 KV.

Record actual input length, cache state and each stream's rate for each new measurement. Historical request conditions remain in the exploration archive.

## Sampling record

The captured request uses adaptive thinking and omits temperature/top-p/top-k overrides. The checkpoint generation defaults are temperature 1.0, top-p 0.95, top-k 20 and repetition penalty 1.05, preserved in [generation-config.json](../configs/generation-config.json). Retain this distinction when comparing another client or server.
