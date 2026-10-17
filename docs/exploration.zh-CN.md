# 双卡推理性能评测

**[English](exploration.md) | 简体中文**

本报告评测双 RTX 3090 上面向 Claude Code 的 Qwen3.8-27B 部署配置，涵盖 llama.cpp、SGLang 和 vLLM，重点分析 prefill 随上下文长度的变化、并行方式、投机解码、缓存持久化与并发服务。

选定配置采用 **vLLM 0.30、原生 DFlash2 和九个原样应用的 HyperQwen 公开补丁**。在 18,649 输入 token、热前缀缓存条件下，decode 中位数达到 **152.97 token/s**。两次独立归档恢复分别达到 **150.77** 和 **145.50 token/s**；公开脚本独立重建达到 **144.66 token/s**。

![双卡评测概览](figures/decision-trail.png)

## 评测设置

实测主机使用两张 24 GB RTX 3090，无 NVLink，CUDA peer access 不可用。工作负载包括真实 Claude Code 会话、工具调用和 Anthropic 请求回放。各组记录包含缓存状态、实际上下文、量化精度与输出上限。

[评测档案](../benchmarks/history/README.md)包含八个阶段的 247 份源文件摘录、236 个不同的原始 SHA256 及 41 行关键 CSV 结果。文件数量包含重叠汇总和嵌套报告。私有会话内容保留在本地，公开请求摘要与测量元数据。

| 评测组别 | 配置 | 评测范围 |
| --- | --- | --- |
| llama.cpp | GGUF Q4_K_M，部分使用 Q4_0 MTP 草稿 | 显存分配与短输入诊断 |
| SGLang TP/PP | 0.5.19 cu129，AWQ W4A16，MTP | 同提示观测与客户端接入 |
| SGLang 动态分块 | PP2，原生校准 | 校准与启动兼容性 |
| vLLM 长上下文 prefill | 0.23 cu129，W4A8，PP2，关闭投机 | 完整 520k 历史与分块预算 |
| vLLM MTP/DFlash | 0.23、0.28 及早期 0.30 分支 | 草稿长度、精度、计算图与对话完成情况 |
| 验证内核实验 | 历史原生 0.30 分支 | 同请求对照，独立归档 |
| 公开运行库候选 | 原生 0.30，packed INT4/MQ3D/W4A8 变体 | 完整配置筛选 |
| **选定配置** | **原生 0.30，九个公开补丁，batch 7167，block 1792** | **热缓存回放与独立恢复** |
| 公开脚本重建 | 相同公开算法，每卡 10.5 GiB KV | 权重与运行库重建 |

选定目标模型使用 AWQ4 主体、INT8 embedding 与输出头、INT4 目标 KV、BF16 草稿 KV 和 FP16 循环状态，DFlash2 草稿使用 W4A16。早期 W4A8 配置中的权重仍为 4bit，激活为 8bit。[配置归属](../benchmarks/history/lineage.json)记录各组差异。

## 框架兼容性

六份 llama.cpp 日志覆盖接近 1M 配置上限的 Q4_K_M 尝试，其中四份记录加载或分配错误。在 21 个提示 token、128 个输出 token 下，无 MTP 配置达到 **41.51 token/s**，MTP 配置达到 **17.23 token/s**，后者报告草稿接受率 0.921、平均发出长度 2.82。构建和启动信息部分留存，这组结果用于短输入诊断，详见 [L001 至 L006](../benchmarks/history/campaigns/L.json)。

客户端验收覆盖多模态加载、Anthropic 内容格式、工具执行和多轮完成情况。选定配置完成了 Read 工具调用与两轮完整 Claude Code 对话。[客户端结果](../benchmarks/results.json)与封顶吞吐回放分别记录。

## 长上下文 Prefill

### 分块预算

vLLM 0.23 W4A8 阶段在真实论文会话历史上比较 TP2、PP2 与静态分块预算。

| 配置 | 批次 token 预算 | 窗口完成 token | 窗口时长 | 窗口 prefill | 首个分块完成 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TP2 | 8,192 | 15,680 | 10.071 秒 | 1,557 token/s | 14.87 秒 |
| PP2 | 4,096 | 34,496 | 10.036 秒 | **3,437 token/s** | 11.81 秒 |
| PP2 | 6,272 | 31,360 | 10.042 秒 | 3,123 token/s | 12.92 秒 |

采样窗口从首个分块完成后开始。在这组条件下，4,096-token 预算的 PP2 获得最高初期窗口速度，随后用于完整长历史评测。

### 上下文长度影响

完成的请求包含 **520,761 个输入 token**。按已处理 token 区间统计，批次 prefill 中位数从首个 100k 区间的 **2,449 token/s** 降至末段的 **363 token/s**。

![520k 输入的 prefill 性能变化](figures/prefill-decay.png)

图中剔除首个批次，对各区间内完成批次的速度取中位数；前述 3,437 token/s 使用独立窗口统计。冷请求端到端 prefill 平均约 **654 token/s**，客户端首 token 为 **797.10 秒**。数据来自 [S 阶段](../benchmarks/history/campaigns/S.json)的 S038 与 S036。

| 轮次 | 实际输入 | 引擎命中 token | 前缀命中率 | 客户端首 token | Decode |
| --- | ---: | ---: | ---: | ---: | ---: |
| 冷请求 | 520,761 | 0 | 0% | 797.10 秒 | 21.48 token/s |
| 后续第 1 轮 | 523,234 | 522,144 | 99.79% | 12.91 秒 | 18.38 token/s |
| 后续第 2 轮 | 525,005 | 523,712 | 99.75% | 14.07 秒 | 18.79 token/s |

这些测量属于历史 **W4A8 PP2、关闭投机解码**配置。前缀复用缩短了后续轮次延迟，长上下文 decode 仍是独立的性能约束。引擎确认缓存命中，当时的 Anthropic 适配器在用量字段中报告零缓存 token。

## 并行方式与动态分块

SGLang 原生动态分块使用 PP2 评测。128 个样本的校准得到负二次项系数，在请求执行前终止，记录为 S013。另一组静态 PP2 在 10.025 秒观察窗口处理 16,384 token，约 **1,634 token/s**，随后取消。该组汇总继承了动态分块标记，实际启动命令未包含对应参数，[配置记录](../benchmarks/history/configurations.json)据此归类为静态分块。

后续 SGLang MTP 评测使用相同的首轮论文提示，每个首轮 API 阶段均为 **5,224 输入、4,096 输出 token**。

![SGLang 并行方式评测](figures/sglang-layout.png)

| 并行方式 | 首阶段 decode | 首个思考或文本增量 | 客户端完成情况 |
| --- | ---: | ---: | --- |
| TP2 | **49.57 token/s** | 4.42 秒 | 完成，包含续接 |
| PP2 | 28.97 token/s | 5.51 秒 | 完成，包含续接 |

这组测量关闭动态分块。留存的 PP2 配置使用 AWQ W4A16、FP8 E5M2 KV、65,536-token 上限及历史回移补丁与兼容适配，TP2 启动信息部分留存。因此，图中分别报告两组既有配置的一次观测，后续续接上下文也已分化。S016 保留全部 API 阶段与计时定义。

## 投机解码

### 草稿与精度评测

早期 vLLM 0.23 阶段评测 MTP 长度、贪心和概率草稿、attention 后端、计算图模式、循环状态精度及 DFlash 变体。

| 候选配置 | 首阶段输入 | 首阶段 decode | 客户端结果 |
| --- | ---: | ---: | --- |
| MTP1，FlashInfer，FP8 KV，贪心草稿 | 5,199 | 24.49 token/s | 未完成，发生计算图回退 |
| MTP3，Triton INT8 KV，贪心草稿 | 5,199 | 42.66 token/s | 完成 |
| MTP3，Triton INT8 KV，概率草稿 | 5,203 | 59.47 token/s | 完成 |
| MTP5，Triton INT8 KV，贪心草稿 | 5,199 | 42.71 token/s | 完成，包含续接 |
| DFlash2 与 INT8 头部 | 5,204 | 80.57 token/s | 完成 |
| DFlash2 与 FP16 循环状态，10 月 15 日 | 5,175 | 82.23 token/s | 完成 |

矩阵记录完整候选配置，其输入、精度和草稿接入存在差异。DFlash8 与部分 W4A8 候选在完整 API 阶段形成前终止。完整记录见 [summary.json](../benchmarks/history/summary.json)、[S 阶段](../benchmarks/history/campaigns/S.json)和 [P 阶段](../benchmarks/history/campaigns/P.json)。

后续原生 0.28/0.30 客户端阶段在短论文问题上超过 100 token/s，并扩展到更长的完整会话。档案中的 **89.97 token/s** 观测对应 **37,208 个上下文 token**。

### 验证内核实验

历史原生 0.30 分支使用相同的 18,649-token 请求，评测共享验证内核。

| 历史配置 | 次数 | Decode 中位数 | 每步耗时中位数 |
| --- | ---: | ---: | ---: |
| 开启 lookup | 3 | 123.14 token/s | 24.83 毫秒 |
| 关闭 lookup | 3 | 135.13 token/s | 24.89 毫秒 |
| 关闭 lookup，NCCL LL | 3 | 134.11 token/s | 25.01 毫秒 |
| 初版共享验证 | 3 | 147.87 token/s | 23.51 毫秒 |
| 共享验证复核 | 6 | 140.84 token/s | 24.56 毫秒 |
| 共享验证，eight warps | 4 | 141.70 token/s | 23.75 毫秒 |

eight-warps 配置的前三次输出与关闭 lookup 的参考结果一致，配对吞吐提高约 4.7% 至 4.9%；greedy 512-token 检查也一致。另一个候选出现输出差异，正确性记录保留在 D001。

该实验分支与选定的公开补丁运行库分别归档。当时完整 Claude Code 轮次的 153.56/150.03 token/s，以及 120k 上下文的 75.34 token/s，均保留原分支归属。

## 运行库配置

最终筛选使用完整官方 vLLM 0.30 wheel 和公开 HyperQwen 补丁序列，候选覆盖 packed INT4、MQ3D 子集、W4A8 激活及 W4A16 草稿配置。

| 运行库候选 | 缓存与测量条件 | Decode | 筛选状态 |
| --- | --- | ---: | --- |
| Packed INT4，冷请求 | 18,649 输入，1,024 输出，开启 profiling | 32.73 token/s | 基线 |
| Packed INT4，热请求 | 16,128 命中，1,024 输出，开启 profiling | 24.10 token/s | 基线 |
| MQ3D 补丁子集，热请求 | 同来源历史，1,024 输出，开启 profiling | 58.84 / 92.21 token/s | 候选 |
| W4A8 激活，热请求 | 同来源历史，16,128 命中，1,024 输出 | 139.24 / 133.91 / 123.32 token/s | 候选 |
| W4A16，batch 3583 | 同来源历史，三次热请求，各 1,024 输出 | 中位数 149.18 token/s | 早期配置 |
| **W4A16，batch 7167** | **17,920 命中，三次各 1,024 输出** | **中位数 152.97 token/s** | **选定配置** |

每行代表一组完整运行配置，档案记录相应的草稿精度、补丁选择、缓存状态和 profiling 条件，组件效果由对应的独立对照说明。

选定配置使用七个原生 DFlash2 投机 token、标准拒绝采样、关闭 lookup、FP16 循环状态、GPU 前缀缓存与上游 LMCache。九个补丁均为原样应用的公开上游补丁。[运行库审计](../benchmarks/runtime-audit.json)、[权重审计](../benchmarks/preparation-audit.json)和[启动配置](../configs/launch-template.json)共同标识公开版本。

## 复现与缓存持久化

![归档恢复与重建测量](figures/restoration-runs.png)

| 评测组别 | 热缓存 decode 中位数 | 条件 |
| --- | ---: | --- |
| 原始归档 | **152.97 token/s** | 18,649 输入，17,920 命中，三次各 1,024 输出 |
| 第一次归档恢复 | **150.77 token/s** | 恢复后回放相同请求 |
| 第二次归档恢复 | **145.50 token/s** | 第二个独立恢复会话 |
| 公开脚本重建 | **144.66 token/s** | 新建权重与运行库，复用依赖，每卡 10.5 GiB KV |

图中包含十二个观测点，每组三次。重建组命中 16,128 token，共享 KV 池较小，作为独立配置报告。封顶吞吐测量包含思考，完整回答与首正文延迟见[测量方法](measurements.md)。

一次独立卸载重启从磁盘回载 **16,128 个文本前缀 token**，GPU 前缀命中为零。首个思考或文本增量为 **2.15 秒**，该次 decode 为 **161.83 token/s**。[缓存文档](cache.md)说明命名空间、存储容量与保留配置。

## 并发服务

选定 TP2 配置观测到**五路请求同时运行**，**逐路速度为 56.47 至 69.04 token/s**。四路输出 1,024 token，一路输出 311 token 后请求工具，五路共享会话前缀。

早期五客户端 Claude Code 阶段也观测到五路生成，四个客户端完成两轮，一个达到实验截止时间。四个完整五路的十秒窗口，**合计吞吐为 234.9 至 258.4 token/s**。这些合计窗口与选定配置的逐路结果分别记录在[档案](../benchmarks/history/summary.json)中。

其他历史评测包括子块对齐、更大 prefill 缓冲和多 API 进程的长历史接入，其配置身份与请求条件保留在阶段数据中。

## 总结

公开配置在双 RTX 3090 上实现约 **150 token/s 热缓存单路 decode**，并提供独立恢复记录、Claude Code 接入及重启后文本前缀回载验证。启动器配置 1M 单请求上限与五个请求槽位，共享约 1.32M-token GPU KV 池。后续评测覆盖更长的实际输入、并发会话、多日缓存保留和长上下文质量。

推理实现来自 [vLLM](https://github.com/vllm-project/vllm)、[HyperQwen](https://github.com/syv-ai/HyperQwen)、[DFlash](https://github.com/z-lab/dflash) 和 [LMCache](https://github.com/LMCache/LMCache)；早期评测使用 [SGLang](https://github.com/sgl-project/sglang) 与 [llama.cpp](https://github.com/ggml-org/llama.cpp)。本仓库提供部署配置、重建脚本、客户端接入与测量档案。复现提交方式见[贡献指南](../CONTRIBUTING.md)。
