import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


repository_root = Path(__file__).resolve().parents[1]
summary = json.loads((repository_root / 'benchmarks/history/summary.json').read_text())
output_dir = repository_root / 'docs/figures'
output_dir.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 11,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.titleweight': 'bold', 'axes.labelcolor': '#334155',
    'xtick.color': '#475569', 'ytick.color': '#475569',
    'svg.fonttype': 'none', 'pdf.fonttype': 42,
})


def save_figure(figure, basename):
    for output_format in ['svg', 'pdf', 'png']:
        p = output_dir / (basename + '.' + output_format)
        figure.savefig(p, dpi=180, facecolor='white')
        if output_format == 'svg':
            p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines()) + '\n')
    plt.close(figure)


prefill_bins = summary['prefill_decay']['record']['ranges']
labels = []
values = []
for x in prefill_bins:
    a, b = x['token_range']
    labels.append('{}-{}k'.format(a // 1000, round(b / 1000, 1) if b % 1000 else b // 1000))
    values.append(x['median_batch_tokens_per_s'])

figure, axes = plt.subplots(figsize=(10.2, 5.3))
figure.subplots_adjust(left=0.10, right=0.98, top=0.79, bottom=0.25)
figure.text(0.10, 0.93, 'Long-Context Prefill Scaling', fontsize=16, weight='bold')
figure.text(0.10, 0.865, 'vLLM 0.23 W4A8 PP2 | Median completed-batch prefill rate by processed-token range', color='#475569', fontsize=10)
axes.bar(range(len(values)), values, color=['#2563eb'] + ['#94a3b8'] * 5 + ['#0f766e'], width=0.67, zorder=3)
axes.set_xticks(range(len(values)))
axes.set_xticklabels(labels, fontsize=10)
axes.set_xlabel('Processed prompt tokens')
axes.set_ylabel('Input tokens / second')
axes.set_ylim(0, 2900)
axes.set_yticks([0, 500, 1000, 1500, 2000, 2500])
axes.grid(axis='y', color='#e2e8f0', zorder=0)
for i, v in enumerate(values):
    axes.text(i, v + 65, '{:,.0f}'.format(v), ha='center', fontsize=11, weight='bold')
figure.text(0.10, 0.105, 'Actual input: 520,761 tokens. First batch excluded. Bins contain 31, 32, 32, 32, 16, 16 and 8 batches.', fontsize=9, color='#475569')
figure.text(0.10, 0.058, 'The separate 3,437 tok/s early sampling window uses a different metric. Source: S038 in benchmarks/history.', fontsize=9, color='#475569')
save_figure(figure, 'prefill-decay')

layouts = summary['sglang_tp_pp']['layouts']
figure, axes = plt.subplots(figsize=(8.8, 4.9))
figure.subplots_adjust(left=0.11, right=0.97, top=0.77, bottom=0.25)
figure.text(0.11, 0.92, 'SGLang Parallelism Evaluation', fontsize=15, weight='bold')
figure.text(0.11, 0.85, 'SGLang 0.5.19 + MTP | 5,224 input / 4,096 output tokens | One run per layout', fontsize=10, color='#475569')
axes.barh([1, 0], [x['first_api_tokens_per_s'] for x in layouts], color=['#2563eb', '#0f766e'], height=0.5, zorder=3)
axes.set_yticks([1, 0])
axes.set_yticklabels([x['layout'] for x in layouts])
axes.set_xlim(0, 60)
axes.set_xticks([0, 10, 20, 30, 40, 50, 60])
axes.set_xlabel('Output tokens / second, including reasoning')
axes.grid(axis='x', color='#e2e8f0', zorder=0)
for y, x in zip([1, 0], layouts):
    axes.text(x['first_api_tokens_per_s'] + 0.8, y, '{:.2f}'.format(x['first_api_tokens_per_s']), va='center', weight='bold')
figure.text(0.11, 0.11, 'PP2: AWQ W4A16, FP8 KV, historical backports. Full TP2 launch recovery is incomplete.', fontsize=9, color='#475569')
figure.text(0.11, 0.06, 'First API phase only; later contexts diverge. Other configuration effects are not isolated. Source: S016.', fontsize=9, color='#475569')
save_figure(figure, 'sglang-layout')

original_results = json.loads((repository_root / 'benchmarks/results.json').read_text())
assembly_results = json.loads((repository_root / 'benchmarks/assembly-validation-20261017.json').read_text())
campaign_records = json.loads((repository_root / 'benchmarks/history/campaigns/D.json').read_text())
restoration_records = [v for v in campaign_records['sources'] if v['label'].startswith('research-20261017/final-production-replay')]
groups = [
    ('Archived\nselection', [v['stream_tokens_per_s'] for v in original_results['warm_runs']]),
    ('Archive\nrestoration 1', original_results['restoration_recheck_20261017']['warm_decode_tps']),
    ('Archive\nrestoration 2', [v['metrics']['clients'][0]['stream_tokens_per_s'] for v in restoration_records]),
    ('Separate public\nscript assembly', [v['stream_tokens_per_s'] for v in assembly_results['warm_runs']]),
]

figure, axes = plt.subplots(figsize=(10.2, 5.8))
figure.subplots_adjust(left=0.10, right=0.98, top=0.78, bottom=0.30)
figure.text(0.10, 0.93, 'Archive Restoration and Reconstruction', fontsize=16, weight='bold')
figure.text(0.10, 0.86, '18,649 input / 1,024 output tokens per stream | Three observations in each group', fontsize=10, color='#475569')
axes.axvspan(2.55, 3.45, color='#f1f5f9', zorder=0)
axes.axvline(2.5, color='#94a3b8', linestyle='--', linewidth=1)
for i, (_, v) in enumerate(groups):
    color = '#2563eb' if i == 0 else '#0f766e' if i < 3 else '#64748b'
    axes.scatter([i - 0.14, i, i + 0.14], v, s=65, color=color, edgecolors='white', linewidths=0.9, zorder=4)
    median_rate = statistics.median(v)
    axes.hlines(median_rate, i - 0.24, i + 0.24, color='#0f172a', linewidth=2.0, zorder=3)
    axes.text(i + 0.25, median_rate, '{:.2f}'.format(median_rate), fontsize=9.8, weight='bold', va='center')
axes.set_xlim(-0.5, 3.65)
axes.set_ylim(120, 170)
axes.set_yticks([120, 130, 140, 150, 160, 170])
axes.set_xticks(range(4))
axes.set_xticklabels([v[0] for v in groups])
axes.set_ylabel('Output tokens / second, including reasoning')
axes.grid(axis='y', color='#e2e8f0', zorder=0)
figure.text(0.10, 0.15, 'Dots: individual capped runs, including reasoning. Black segments: group medians. Three observations per group.', fontsize=9, color='#475569')
figure.text(0.10, 0.105, 'First three groups: 17,920 prefix hits. Separate assembly: 16,128 hits, fixed 10.5 GiB KV/card, smaller shared pool.', fontsize=9, color='#475569')
figure.text(0.10, 0.06, 'Sources: benchmarks/results.json, history {}, and assembly-validation-20261017.json.'.format('/'.join(v['source_id'] for v in restoration_records)), fontsize=9, color='#475569')
save_figure(figure, 'restoration-runs')

decision_cards = [
    ('01 / WORKLOAD', 'Workload Definition', 'Resumed Claude Code sessions\nImage and tool content\nShared inference service'),
    ('02 / GGUF', 'GGUF Compatibility', 'llama.cpp Q4_K_M trials\nNear-1M configured limits\nAllocation and timing records'),
    ('03 / PREFILL', 'Long-Context Prefill', 'vLLM 0.23 W4A8 PP2\n520k context scaling\nPrefix reuse and decode'),
    ('04 / PARALLELISM', 'Parallelism and Drafting', 'SGLang TP/PP and chunking\nMTP, DFlash2 and DFlash8\nPrecision and CUDA graphs'),
    ('05 / VERIFICATION', 'Verification Kernels', 'Native 0.28 and 0.30 trials\nMatched kernel comparisons\nArchived experimental branch'),
    ('06 / CONFIGURATION', 'Selected Runtime', 'Native vLLM + DFlash2\nNine unchanged public patches\n18.6k warm median: 153 tok/s'),
    ('07 / REPRODUCIBILITY', 'Restoration Validation', 'Archive restores: 151 / 146\nSeparate assembly: 145 tok/s\nText-prefix disk recovery'),
    ('08 / DEPLOYMENT', 'Client Integration', 'Multiple clients, one server\nPersistent prefix storage\nPinned setup and measurements'),
]
positions = [(0.02 + i * 0.25, 0.51) for i in range(4)] + [(0.02 + i * 0.25, 0.15) for i in [3, 2, 1, 0]]
figure, axes = plt.subplots(figsize=(13.4, 7.0))
figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
axes.set_xlim(0, 1)
axes.set_ylim(0, 1)
axes.axis('off')
axes.text(0.025, 0.94, 'Dual-GPU Evaluation Overview', fontsize=18, weight='bold')
axes.text(0.025, 0.885, 'Engine compatibility, context scaling, speculative decoding and deployment validation', fontsize=10.5, color='#475569')
for i, ((x, y), (tag, title, body)) in enumerate(zip(positions, decision_cards)):
    background, border = ('#f8fafc', '#cbd5e1')
    if i == 5:
        background, border = '#ecfdf5', '#059669'
    elif i == 6:
        background, border = '#f0fdfa', '#5eead4'
    elif i == 7:
        background, border = '#eff6ff', '#93c5fd'
    box = FancyBboxPatch((x, y), 0.215, 0.295, boxstyle='round,pad=0.007,rounding_size=0.012', facecolor=background, edgecolor=border, linewidth=1.7 if i == 5 else 1.1)
    axes.add_patch(box)
    axes.text(x + 0.013, y + 0.255, tag, fontsize=8.8, color='#166534' if i == 5 else '#64748b', weight='bold')
    axes.text(x + 0.013, y + 0.205, title, fontsize=11.2, color='#0f172a', weight='bold')
    axes.text(x + 0.013, y + 0.155, body, fontsize=10.3, color='#334155', va='top', linespacing=1.55)
for i in range(7):
    x, y = positions[i]
    a, b = positions[i + 1]
    if i < 3:
        arrow_start, arrow_end = (x + 0.223, y + 0.15), (a - 0.009, b + 0.15)
    elif i == 3:
        arrow_start, arrow_end = (x + 0.1075, y - 0.01), (a + 0.1075, b + 0.306)
    else:
        arrow_start, arrow_end = (x - 0.009, y + 0.15), (a + 0.223, b + 0.15)
    axes.add_patch(FancyArrowPatch(arrow_start, arrow_end, arrowstyle='-|>', color='#64748b', mutation_scale=12, linewidth=1.4))
axes.text(0.025, 0.065, 'Campaigns overlap. Each result is linked to its configuration and original measurement record.', fontsize=10, color='#475569')
axes.text(0.025, 0.026, 'Measured headline: 18,649 actual input tokens with a warm prefix; output rates include reasoning.', fontsize=10, color='#475569')
save_figure(figure, 'decision-trail')

(output_dir / 'figure-data.json').write_text(json.dumps({'decision_cards': decision_cards, 'prefill': prefill_bins,
    'sglang_layouts': layouts, 'restoration_groups': groups,
    'restoration_source_ids': [v['source_id'] for v in restoration_records]}, ensure_ascii=False, indent=2) + '\n')

print('Saved four history figures as SVG, PDF and PNG.')
