# Community posts

English and Chinese versions of the measured deployment story. The live bilingual club-3090 post is linked below. Implementation, data organization and writing used AI assistance, disclosed in the community post.

## Publication status

| Community | Status | Link / next step |
| --- | --- | --- |
| club-3090, Show and tell | Existing public post; publication receipt tracks its latest verified body | [Discussion #1715](https://github.com/noonghunna/club-3090/discussions/1715) |
| V2EX | Not posted | An authenticated account/session is needed |
| Reddit, r/LocalLLaMA | Not posted | An authenticated account/session and posting eligibility are needed |

The exploration archive expands the existing post, with result attribution and failed paths. No duplicate promotion thread is needed.

## 中文

### 标题

双3090把Qwen接进Claude Code：从llama.cpp、SGLang一路试到原生vLLM+DFlash2，18.6k热缓存约150 token/s

### 正文

我想把本地Qwen接进平时的Claude Code工作流：回到已有长会话就能继续，多开几个终端也能共用服务。手边是3090，没有NVLink，这台机器的CUDA peer access也不可用。

最初遇到的情况很直接。模型已经加载，显存已经占了，下一条消息仍然要等很久。为了弄清楚慢在哪里，我们陆续尝试了llama.cpp、SGLang、vLLM，以及TP/PP、动态分块、MTP、DFlash2/8、KV精度和磁盘缓存。最后保留的是vLLM原生DFlash2加公开HyperQwen补丁。

项目：[YYTbit/qwen3.8-27b-3090](https://github.com/YYTbit/qwen3.8-27b-3090)

[完整中文探索过程](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/exploration.zh-CN.md) · [配置归属与数据](https://github.com/YYTbit/qwen3.8-27b-3090/tree/main/benchmarks/history)

这次把历史记录也整理出来了：八个阶段、247份留存证据文件的脱敏摘录、236个不同的原始SHA256和41行关键CSV记录。报告与汇总存在重叠，这个数量指文件。每组结果标明所属配置，早期自改内核的成绩也保留其分支身份。

其中几次测量改变了后续的选择。

- **初期prefill好看，长历史后段仍会很慢。** 早期vLLM W4A8 PP2的观察窗口达到3437 token/s；实际跑完520,761-token历史后，末段批次速度中位数为363，冷首token约797秒。
- **高缓存命中也要继续测下一轮。** 同一个旧PP2配置的后续输入命中约99.8%的前缀，首token仍需约13至14秒，decode为18至19 token/s。
- **动态分块需要看实际执行结果。** SGLang原生动态分块在校准阶段失败，没有真实请求速度；另一条记录的汇总字段与实际启动参数冲突，档案中已注明。SGLang同首轮提示的TP/PP观测也附完整条件和参数缺失项。
- **能恢复，才方便继续做实验。** 最终双卡配置独立归档，后续从归档恢复并重放，保留了逐次重测结果。公开脚本又重建了一份独立权重与运行库。

最终保留的方案是完整官方vLLM 0.30 CUDA12.9 wheel、九个原样公开HyperQwen补丁、原生DFlash2和上游LMCache。目标主体AWQ4、embedding/输出头INT8，草稿W4A16，目标KV为INT4。推理CPU offload为0，磁盘缓存保存与回载经过主机内存暂存。

| 最终配方相关实测 | 结果 |
| --- | --- |
| 18,649输入、热单路、三次各1,024输出 | 中位 **152.97 token/s** |
| 独立归档恢复，同请求三次 | 中位 **150.77 token/s** |
| 后续再次恢复，同请求三次 | 中位 **145.50 token/s** |
| 公开脚本重建，另设每卡10.5GiB KV | 热三轮中位 **144.66 token/s** |
| 最终双卡五请求回放，观测到五路运行 | **逐路56.47至69.04 token/s** |
| 一次实际卸载重启 | 外部缓存回载16,128个文本前缀token，首思考/文本约2.15秒 |

标题单路数据命中17,920 token，约96.1%，速度含思考，三个1,024输出都在正文出现前封顶。五路中四路输出1,024，一路311 token后请求工具。完整Read工具往返和两轮Claude Code对话另外验收，逐次结果、首正文时间和独立重测都在仓库。

**标题成绩来自本机18.6k热缓存交互。** 启动器配置1M单请求上限与五个槽位，使用约1.32M-token共享KV池。更长上下文、更多客户端和多日缓存的测量列入后续复现计划。

不同阶段的输入、精度和运行库存在差异，因此宣传中的约150只引用最终配方的对应记录。算法与内核归属vLLM、HyperQwen、DFlash、LMCache及相关上游；这个仓库整理本机的组合、准备过程、恢复方式和选择依据。安装说明提供固定版本、已有环境复用方式以及中国镜像入口。

如果你有相似配置，欢迎带上实际上下文、缓存、互联和逐路速度复现。希望这份记录能帮助后续部署时更快判断哪些条件值得继续试。有帮助的话，欢迎Star收藏，也欢迎补充不同机器的结果。

## English

### Title

Qwen3.8-27B on two 3090s: the llama.cpp, SGLang and vLLM/DFlash2 experiments behind ~150 tok/s at 18.6k warm context

### Post

I wanted local Qwen to fit my usual Claude Code workflow: return to a long conversation, send the next message, and let several terminals share one server. The machine has RTX 3090s, no NVLink, and no working CUDA peer access.

The model could be loaded and occupying VRAM while the next turn still took minutes. Working through that led us through llama.cpp, SGLang, vLLM, TP/PP, native dynamic chunking, MTP, DFlash2/8, KV precision and disk-cache reloads. The retained dual-GPU configuration uses native vLLM DFlash2 and public HyperQwen patches.

Repo: [YYTbit/qwen3.8-27b-3090](https://github.com/YYTbit/qwen3.8-27b-3090)

[Full decision trail](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/exploration.md) · [Result lineage and data](https://github.com/YYTbit/qwen3.8-27b-3090/tree/main/benchmarks/history)

I've now archived the history too: eight campaigns, sanitized extracts of 247 surviving evidence artifacts, 236 distinct original SHA256 digests, and 41 curated CSV rows. Nested stages and summaries overlap, so those are file counts. Each result is mapped to its configuration, including the older custom-kernel branches that were later retired.

A few observations changed the direction:

- **Early prefill did not predict late prefill.** An older vLLM W4A8 PP2 profile reached 3,437 input tok/s in an early sampling window. In a completed 520,761-token history, the late-bin median fell to 363 tok/s and cold first token took about 797 seconds.
- **A cache hit was not enough to establish usable next-turn speed.** The same old PP2 profile's follow-ups reused about 99.8% of the prefix, but first token still took 13–14 seconds and decode ran at 18–19 tok/s.
- **Native dynamic chunking needed an actual completion check.** SGLang's calibration failed before the real request. Another launch summary's dynamic-chunk flag disagreed with its actual arguments; the archive records the correction. Same-first-prompt TP/PP observations retain their configuration gaps.
- **Restoration needed its own measurements.** The selected profile was archived, restored and replayed, including independent reruns. The public scripts then assembled a separate checkpoint/runtime.

The retained stack is the complete official vLLM 0.30 CUDA12.9 wheel with nine unchanged public HyperQwen patches, native DFlash2 and upstream LMCache. The target body is AWQ4, embeddings/output head are INT8, the draft is W4A16 and target KV is INT4. Model CPU offload is zero; disk KV save/load uses host staging.

| Selected-profile evidence | Result |
| --- | --- |
| 18,649 input, one warm stream, three 1,024-output runs | **152.97 tok/s median** |
| Independent archive restoration, same three-run request | **150.77 tok/s median** |
| Later restoration, same three-run request | **145.50 tok/s median** |
| Public-script assembly, separate 10.5 GiB KV/card budget | **144.66 tok/s median warm** |
| Five replay requests, five running observed | **56.47–69.04 tok/s per stream** |
| One actual unload/restart | 16,128 text-prefix tokens recovered externally; first thinking/text at 2.15 s |

The headline single-stream runs reused 17,920 prefix tokens, about 96.1%. Rates include reasoning, and all three capped runs stopped before answer text. Four five-client streams emitted 1,024 tokens; one requested a tool after 311. Complete Read-tool round trips and two real Claude Code turns were checked separately. Individual runs, first-answer timings and independent reruns are linked in the repository.

**The measured headline uses the local 18.6k warm interactive profile.** The launcher configures a 1M per-request limit and five slots with a shared KV pool of about 1.32M tokens. Additional long-context, multi-client and multi-day cache measurements are on the reproduction roadmap.

Inputs, precision and runtimes differ across the history. The ~150 headline belongs to the selected profile's measurements. Credit for algorithms/kernels goes to vLLM, HyperQwen, DFlash, LMCache and the relevant upstream projects; this repository packages the host-specific preparation, selection, restoration and evidence. English/Chinese setup docs include pinned sources, environment reuse and Chinese download mirrors.

I'd welcome reproductions with actual context length, cache state, topology and each stream's rate. I hope the decision trail helps others choose the next useful experiment on similar hardware. Star the repo if you'd like to follow the work, or add a result from your machine.
