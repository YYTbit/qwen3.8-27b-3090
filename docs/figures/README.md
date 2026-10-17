# Evaluation Figures

**[English report](../exploration.md) | [中文报告](../exploration.zh-CN.md)**

Four figures summarize the dual-GPU evaluation, covering configuration selection, long-context prefill, SGLang parallelism, and archive restoration. The report tables provide configuration details and measurement conditions.

| Figure | Preview | Vector exports |
| --- | --- | --- |
| Evaluation overview | [PNG](decision-trail.png) | [SVG](decision-trail.svg), [PDF](decision-trail.pdf) |
| Long-context prefill scaling | [PNG](prefill-decay.png) | [SVG](prefill-decay.svg), [PDF](prefill-decay.pdf) |
| SGLang parallelism evaluation | [PNG](sglang-layout.png) | [SVG](sglang-layout.svg), [PDF](sglang-layout.pdf) |
| Archive restoration and reconstruction | [PNG](restoration-runs.png) | [SVG](restoration-runs.svg), [PDF](restoration-runs.pdf) |

Download the [four-page PDF collection](dual-gpu-exploration.pdf) and [editable PowerPoint](dual-gpu-exploration.pptx). The presentation contains four slides built from editable shapes and text, with no embedded raster images. [Figure data](figure-data.json) is generated from the published measurement records and editorial decision cards.

## Figure Generation

With Matplotlib installed:

```bash
python scripts/render_figures.py
```

To regenerate the editable presentation, use an environment with `python-pptx`:

```bash
python scripts/export_figures_pptx.py
```

The presentation export used `python-pptx==1.0.2`, `lxml==5.3.0` and `XlsxWriter==3.2.0`. These are documentation dependencies, independent of the inference environment. Package downloads can use `https://pypi.tuna.tsinghua.edu.cn/simple`.

Headline rates use an actual 18,649-token warm-prefix workload and include reasoning. The assembly uses a separate KV budget. The SGLang comparison retains its partial launch recovery in the caption and data. All points and ranges come from the linked records.
