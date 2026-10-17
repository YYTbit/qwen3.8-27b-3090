# Project Announcement

Bilingual project summary for the existing [club-3090 discussion](https://github.com/noonghunna/club-3090/discussions/1715). Publication metadata is recorded in [community-publication.json](community-publication.json).

## Publication Status

| Community | Status | Reference |
| --- | --- | --- |
| club-3090, Show and tell | Published | [Discussion #1715](https://github.com/noonghunna/club-3090/discussions/1715) |
| V2EX | Pending authenticated session | Unpublished |
| Reddit, r/LocalLLaMA | Pending authentication and posting eligibility | Unpublished |

## English

### Qwen3.8-27B on Dual RTX 3090 GPUs

A local Qwen3.8-27B deployment for Claude Code is available with **153 tok/s median warm decode at 18.6k input tokens** on two RTX 3090s, without NVLink or CUDA peer access. It uses **native vLLM DFlash2, nine unchanged HyperQwen patches, and upstream LMCache**.

[Repository](https://github.com/YYTbit/qwen3.8-27b-3090) · [Performance Evaluation](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/exploration.md) · [Setup](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/setup.md) · [Data](https://github.com/YYTbit/qwen3.8-27b-3090/tree/main/benchmarks/history)

#### Performance

| Evaluation | Result |
| --- | --- |
| Selected profile, three warm runs | **152.97 tok/s median** |
| Independent archive restorations | **150.77 / 145.50 tok/s median** |
| Public-script reconstruction | **144.66 tok/s median** |
| Five running replay streams | **56.47–69.04 tok/s per stream** |
| Text-prefix recovery after restart | **16,128 cached tokens; 2.15 s to first thinking/text delta** |

The single-stream replays use 18,649 input tokens, 17,920 cached tokens, and 1,024 output tokens per run, including reasoning. The reconstruction uses a separate 10.5 GiB KV/card budget and 16,128 cache hits. Five-stream results include four 1,024-token outputs and one 311-token tool call. Complete Claude Code conversations and successful Read-tool round trips have separate records.

#### Configuration

The target has an abliterated AWQ4 body with INT8 embeddings/output head. The W4A16 DFlash2 draft proposes seven tokens; target KV uses INT4 and draft KV uses BF16. Model inference remains on GPU, with CPU model offload set to zero. Disk-cache save/load uses host staging.

The archived launcher configures a 1,048,576-token per-request limit and five slots, backed by a shared GPU KV pool of approximately 1.32M tokens. Reported throughput corresponds to the measured 18.6k warm workload. Service management is independent of Claude Code, and connection settings apply to each client process.

#### Evaluation Archive

The deployment was selected through evaluations of **llama.cpp, SGLang, and vLLM**, covering TP/PP, static and dynamic chunking, MTP/DFlash, quantization, CUDA graphs, and cache persistence.

The long-history campaign measured an earlier vLLM W4A8 PP2 profile across a complete 520k input, identifying substantial context-dependent prefill decay. Subsequent experiments examined parallelism and speculative decoding, followed by whole-profile selection and independent restoration. The report links each result to its runtime and workload, with historical kernel experiments retained as a separate branch.

The archive contains **247 source artifacts, 236 distinct original SHA256 digests, and 41 curated result rows**. Counts refer to files, including overlapping reports. Four figures, eight tables, editable PowerPoint slides, and PDF exports accompany the bilingual report.

#### Reproducibility

The repository includes pinned checkpoints and patches, model/runtime preparation scripts, launch profiles, cache configuration, and a local timing tool. Setup documentation supports existing Python environments and Chinese download mirrors. Further evaluation covers fresh-host installation, longer contexts, concurrent conversations, and multi-day cache reuse.

Reproduction reports are welcome through [GitHub Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues), with actual context length, cache state, hardware topology, and per-stream throughput.

Inference algorithms and kernels are provided by vLLM, HyperQwen, DFlash, LMCache, and the relevant upstream projects. Deployment tooling, data curation, and documentation were prepared with AI assistance.

## 简体中文

### Qwen3.8-27B 双 RTX 3090 部署与性能评测

面向 Claude Code 的本地 Qwen3.8-27B 部署方案已公开。在无 NVLink、CUDA peer access 不可用的双 RTX 3090 上，18.6k 输入、热缓存单路 decode 中位数达到 **153 token/s**。方案采用 **vLLM 原生 DFlash2、九个原样应用的 HyperQwen 公开补丁和上游 LMCache**。

[项目仓库](https://github.com/YYTbit/qwen3.8-27b-3090) · [性能评测](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/exploration.zh-CN.md) · [环境配置](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/setup.zh-CN.md) · [数据档案](https://github.com/YYTbit/qwen3.8-27b-3090/tree/main/benchmarks/history)

#### 性能表现

| 评测组别 | 结果 |
| --- | --- |
| 选定配置，三次热缓存回放 | 中位数 **152.97 token/s** |
| 两次独立归档恢复 | 中位数 **150.77 / 145.50 token/s** |
| 公开脚本重建 | 中位数 **144.66 token/s** |
| 五路回放请求同时运行 | **逐路 56.47 至 69.04 token/s** |
| 重启后文本前缀回载 | **16,128 个缓存 token，首个思考或文本增量 2.15 秒** |

单路回放为 18,649 输入、17,920 命中，每次输出 1,024 token，包含思考。重建组采用独立的每卡 10.5 GiB KV 预算，命中 16,128 token。五路中四路输出 1,024 token，一路 311 token 后调用工具。完整 Claude Code 会话和 Read 工具往返另有记录。

#### 部署配置

目标模型采用去拒绝版本的 AWQ4 主体，embedding 与输出头为 INT8。W4A16 DFlash2 草稿提出七个 token，目标 KV 为 INT4，草稿 KV 为 BF16。模型推理位于 GPU，CPU 模型卸载为零，磁盘缓存保存与回载使用主机内存暂存。

归档启动器配置 1,048,576-token 单请求上限、五个槽位和约 1.32M-token 共享 GPU KV 池，公开吞吐对应实测 18.6k 热缓存工作负载。服务管理与 Claude Code 独立，连接设置限定于各客户端进程。

#### 评测档案

配置筛选覆盖 **llama.cpp、SGLang 和 vLLM**，包括 TP/PP、静态与动态分块、MTP/DFlash、量化、CUDA graph 及缓存持久化。

长历史阶段使用早期 vLLM W4A8 PP2 配置完成 520k 输入，记录 prefill 随上下文增长的明显衰减。后续评测转向并行方式与投机解码，再进行完整配置筛选及独立恢复。报告为各项结果标注运行库与工作负载，历史内核实验单独归档。

档案包含 **247 份源文件摘录、236 个不同的原始 SHA256 和 41 行关键结果**，文件数量包含重叠报告。双语评测报告配有四张图、八张表、可编辑 PowerPoint 和 PDF。

#### 复现资料

仓库提供固定模型与补丁、权重和运行库准备脚本、启动配置、缓存配置及本地测量工具。环境说明支持复用已有 Python 环境，并提供中国镜像。后续评测覆盖干净主机安装、更长上下文、并发会话与多日缓存复用。

欢迎通过 [GitHub Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues)提交复现，附实际上下文、缓存状态、硬件互联与逐路吞吐。

推理算法与内核来自 vLLM、HyperQwen、DFlash、LMCache 及相关上游项目。部署工具、数据整理和文档使用了 AI 辅助。
