# Evaluation Dataset

**[English report](../../docs/exploration.md) | [中文报告](../../docs/exploration.zh-CN.md)**

The archive contains **247 source artifacts, 236 distinct original SHA256 digests, eight campaigns, and 41 curated CSV rows**. Artifact counts include overlapping reports and nested stages; statistical replication is recorded per measurement group.

## Dataset Index

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

## Record Format

Each source has a snapshot-stable ID, logical label, original-byte SHA256, and `metrics` tree. Extracts retain numeric, boolean, null, and selected categorical fields. Original files and private conversation content remain local. Source fingerprints identify the original records; public reproduction uses independently supplied workloads.

The selected configuration is pinned in [launch-template.json](../../configs/launch-template.json). Historical launch metadata is partially recovered. Compatibility adaptations, experimental kernels, and the selected nine-public-patch profile have separate entries in [lineage.json](lineage.json).

## Curation Rules

- `S013`: SGLang native dynamic-chunk calibration failed before any real request. Its speed is unmeasured, represented by missing/null rates.
- The static PP launch summary inherited `native_dynamic_chunking=true`. Its actual argument list lacks `--enable-dynamic-chunking`, and its performance report says false. [Recovered flags](configurations.json) preserve both facts; the curated report labels that run static.
- `S016`: use the first API phase for the TP2/PP2 observation. Both have 5,224 input and 4,096 output tokens. Complete TP2 launch recovery is unavailable, so other configuration effects are unresolved. Subsequent continuation inputs differ.
- `S036`: the completed 520k-history rates are from **vLLM W4A8 PP2**, even though a later SGLang report quotes them as historical references.
- `S038`: prefill decay uses medians of completed-batch rates within processed-token ranges, excluding the first batch. The 3,437 token/s early-window measurement is a different metric.
- `D001`: historical custom-kernel controls include output-equality checks and a candidate with output differences. These records belong to the archived experimental branch.
- `E`: configuration linkage is incomplete. Tiny-prompt and synthetic diagnostics, including a 64-output warmup at 877 token/s, are classified as diagnostic records and excluded from accepted performance summaries.
- Historical API-phase rates often use `N / delta_time`; current capped replays use `(N-1) / delta_time`. Values are preserved as reported. The difference matters particularly for very short outputs.
- Historical API-phase event times are relative to the complete client turn. Continuation first-delta timestamps are not per-request TTFT, so their CSV `ttft_s` cells are left empty.
- Output-capped streams, complete answers, configured slots, submitted clients, and engine-observed running requests are recorded as separate fields.
- Canceled first-token gates use null decode values. Sustained concurrent measurements require the stated number of active streams throughout the measurement window.

## Figure Generation

With an existing Matplotlib environment:

```bash
python scripts/render_figures.py
```

The renderer reads the archived JSON and generates the evaluation overview and three measurement figures. PNG previews, SVG, and PDF exports are available in [docs/figures](../../docs/figures).

An [editable PowerPoint and PDF collection](../../docs/figures/README.md) is also included.
