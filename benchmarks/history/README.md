# Exploration data

**[English report](../../docs/exploration.md) | [中文报告](../../docs/exploration.zh-CN.md)**

This archive contains **247 surviving source artifacts, 236 distinct original SHA256 digests, eight campaigns, and 41 curated CSV rows**. These are artifact counts. Reports, nested stages and later summaries overlap, so they are not counts of independent experiments or statistical replicates.

## Start here

| File | Contents |
| --- | --- |
| [summary.json](summary.json) | Curated conditions, individual measurements, failures, matched controls and selected-profile evidence |
| [lineage.json](lineage.json) | Explicit attribution of every result family; selected profile, retired custom branches and separate assemblies |
| [cases.csv](cases.csv) | Flat export of 41 key observations, with scope, metric definition and source ID |
| [configurations.json](configurations.json) | Recovered historical SGLang flags, including the dynamic-chunking metadata correction |
| [manifest.json](manifest.json) | Original source IDs, byte sizes, SHA256 and dataset locations |
| [curation-audit.json](curation-audit.json) | Source-digest, attribution, median, link and privacy checks performed before publication |
| [L.json](campaigns/L.json) | Six surviving llama.cpp server logs, extracted timing/allocation records |
| [E.json](campaigns/E.json) | Two early exploratory timing streams, including 22 general and 93 short-decode records |
| [S.json](campaigns/S.json) | 39 SGLang/vLLM 0.23 reports and launch records from October 10 |
| [T.json](campaigns/T.json) | Four earlier SGLang integration records |
| [P.json](campaigns/P.json) | 42 vLLM/speculation/precision reports from October 15 |
| [A.json](campaigns/A.json) | 11 isolated baseline/shared-verification reports |
| [B.json](campaigns/B.json) | 16 real five-client and 120k-history reports |
| [D.json](campaigns/D.json) | 127 matched-control, native DFlash, recovery, restoration and dual-GPU restoration reports |

## Reading the records

Every source has a stable ID within this snapshot, a logical label, an original-byte SHA256 and a `metrics` tree. The original source files remain private. Numeric, boolean and null fields are retained with selected categorical fields; prompts, outputs, credentials, session/message IDs, environment dumps and private absolute paths are excluded. This is a measurement extract, not a byte-identical raw-log release. Source fingerprints identify the private original; they do not make its workload publicly replayable.

The current recipe's complete pinned launch remains in [launch-template.json](../../configs/launch-template.json). Historical launch recovery is partial, and some old trials used local compatibility adaptations or custom kernels. Archiving their results does not install those branches or make them part of the selected nine-public-patch profile.

## Curation decisions

- `S013`: SGLang native dynamic-chunk calibration failed before any real request. Its speed is unmeasured, represented by missing/null rates.
- The static PP launch summary inherited `native_dynamic_chunking=true`. Its actual argument list lacks `--enable-dynamic-chunking`, and its performance report says false. [Recovered flags](configurations.json) preserve both facts; the curated report labels that run static.
- `S016`: use the first API phase for the TP2/PP2 observation. Both have 5,224 input and 4,096 output tokens. Complete TP2 launch recovery is unavailable, so other configuration effects are unresolved. Subsequent continuation inputs differ.
- `S036`: the completed 520k-history rates are from **vLLM W4A8 PP2**, even though a later SGLang report quotes them as historical references.
- `S038`: prefill decay uses medians of completed-batch rates within processed-token ranges, excluding the first batch. The 3,437 token/s early-window measurement is a different metric.
- `D001`: historical matched custom-kernel controls are retained, including a candidate with output differences. They are not the final public recipe.
- `E`: exact configuration linkage is incomplete. Some tiny-prompt/synthetic diagnostics report misleadingly high rates, including a 64-output warmup at 877 token/s. These are excluded from accepted results and all promotional claims. They are kept here to make the exclusion visible.
- Historical API-phase rates often use `N / delta_time`; current capped replays use `(N-1) / delta_time`. Values are preserved as reported. The difference matters particularly for very short outputs.
- Historical API-phase event times are relative to the complete client turn. Continuation first-delta timestamps are not per-request TTFT, so their CSV `ttft_s` cells are left empty.
- `max_tokens` can stop during reasoning. A completed HTTP stream is not evidence of a completed answer. `max_running=5` is distinct from submitting five clients or configuring five slots.
- Missing performance is not zero performance. A canceled first-token gate yields no decode sample. Post-cancellation survivor rates do not establish sustained five-stream throughput.

## Rebuild the figures

With an existing Matplotlib environment:

```bash
python scripts/render_figures.py
```

This reads the archived JSON and redraws the decision diagram plus three measurement figures. It sends no inference requests. SVG and PDF exports accompany the README-compatible PNGs in [docs/figures](../../docs/figures).

An [editable PowerPoint and PDF collection](../../docs/figures/README.md) is also included.
