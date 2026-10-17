# Community post drafts

English and Chinese versions of the same deployment story. These drafts have not been posted to external communities. AI assistance was used to prepare them; review the destination's current submission and disclosure rules before posting.

## 中文

### 标题

把 Qwen3.8-27B 接进 Claude Code：双3090，18.6k热缓存约150 token/s，配方已开源

### 正文

我平时在 Claude Code 里处理长任务，有时会同时开几个终端。手边有3090，就想把 Qwen3.8-27B 接进这套工作流。希望用起来很直接：一个模型服务供多个会话连接，需要时启动，关闭某个终端后，其他会话还能继续用。

最初卡住我的，是回到已有会话后发下一条消息。模型已经加载，显存也占了，但历史一长，请求仍然要等很久。工具返回的内容还触发过接口错误，重启服务后又要确认缓存能否接着用。每次换一组参数，都要重新回到日常使用的场景里试一遍。

后来我固定用同一份真实 Claude Code 会话来验证，检查工具能否完整返回，再看热缓存解码、五路请求和卸载后的缓存回载。跑通的一组双卡配置单独归档，准备权重、构建运行库和启动服务的过程也整理成了脚本。现在把这份配方开源出来，方便有相似配置的人照着试，也方便下一次直接恢复。

项目：[YYTbit/qwen3.8-27b-3090](https://github.com/YYTbit/qwen3.8-27b-3090)

**这次的硬件是两张24GB RTX 3090，没有NVLink，CUDA peer access也不可用。** 使用 vLLM 0.30 原生 DFlash2、HyperQwen 公开补丁和 LMCache。目标模型为去拒绝版 AWQ4，embedding 和输出头采用INT8，草稿为DFlash2 W4A16，目标KV为INT4。模型推理的CPU offload设为0，磁盘缓存保存和回载会经过主机内存暂存。

在18,649-token真实历史上，目前记录的结果是：

| 场景 | 结果 |
| --- | --- |
| 热缓存单路，三轮各输出1,024 token | 中位 **153 token/s**，三轮范围148–159 |
| 从独立归档恢复后重测，同样三轮 | 中位 **151 token/s** |
| 用公开脚本新建权重和运行库，复用Python依赖 | 热缓存三轮中位 **145 token/s**，每轮1,024输出 |
| 五路同时发起的API回放 | **每路56–69 token/s**；引擎观测到五路运行 |

单路标题数据命中17,920个前缀token，约96.1%；速度包含思考，三轮都在思考阶段达到输出上限。五路中四路输出1,024 token，一路输出311 token后请求工具。完整工具往返另用官方 Claude Code 验收，Read成功，两轮对话正常结束。逐次计时、输出长度和测试条件都保留在[结果记录](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/benchmarks/results.json)里。

缓存也做了一次实际卸载重启：同一文本前缀从磁盘回载16,128 token，首个思考或文本增量约2.15秒。[这次复测的记录](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/measurements.md)和准备脚本、补丁摘要一起放在仓库，方便核对。

日常使用时，服务和 Claude Code 分开启动。多个终端连接同一个服务，启动器通过当前进程的环境变量接入，不写入 Claude Code 或 cc-switch 配置。中英文安装说明提供固定版本、已有环境复用方式，以及 hf-mirror 和清华源入口。

推理算法和内核来自 vLLM、HyperQwen、DFlash、LMCache，模型来自对应的权重作者。这份仓库整理了它们在这台机器上的组合、准备过程和实测记录。

如果你也有双3090，尤其是没有NVLink的配置，欢迎试跑并反馈显卡互联方式、实际上下文、缓存状态和逐路速度。我想先收集几台不同机器的复现，把安装和日常使用的路径补齐。有帮助的话，欢迎Star收藏，后续结果会继续更新在仓库。

## English

### Title

Getting Qwen3.8-27B into Claude Code on two RTX 3090s: ~150 tok/s at 18.6k warm context, recipe included

### Post

I use Claude Code for long tasks, sometimes with several terminals open at once. I wanted to use my 3090s for the same workflow: one local Qwen3.8-27B server that several sessions could connect to, with its lifetime managed separately from the clients.

Coming back to an existing conversation was where things got difficult. The model was loaded and occupying VRAM, but the next message could still take a long time as the history grew. Tool results exposed content-format errors, and each restart meant checking whether the cached prefix could be reused. Every configuration change sent me back to the same daily workflow to try again.

I ended up using one real Claude Code conversation to check tool round trips, warm decode, five simultaneous requests, and prefix recovery after an unload/restart. I archived a working dual-GPU profile and turned model preparation, runtime assembly, and startup into scripts. I've published the recipe for people with similar hardware, and to have a configuration I can return to after the next experiment.

Repo: [YYTbit/qwen3.8-27b-3090](https://github.com/YYTbit/qwen3.8-27b-3090)

**Hardware: two 24 GB RTX 3090s, no NVLink, and no CUDA peer access on this host.** The stack is vLLM 0.30 with native DFlash2, public HyperQwen patches, and LMCache. The target is an abliterated AWQ4 checkpoint with INT8 embeddings/output head and INT4 KV; the draft is DFlash2 W4A16. Model CPU offload is zero. Disk KV save/load uses host staging.

Results on an 18,649-token conversation:

| Workload | Result |
| --- | --- |
| One warm stream, three runs of 1,024 output tokens | **153 tok/s median**, range 148–159 |
| Independent archive restoration, same three-run workload | **151 tok/s median** |
| Checkpoint/runtime rebuilt with the published scripts and reused Python dependencies | **145 tok/s median**, three warm runs of 1,024 outputs |
| Five API requests submitted together | **56–69 tok/s per stream**; five running requests observed |

The headline runs reused 17,920 prefix tokens, about 96.1%. Rates include reasoning, and all three capped runs stopped during thinking. In the five-request run, four produced 1,024 tokens and one requested a tool after 311 tokens. Separately, the official Claude Code client completed a Read call and two conversation rounds. [Timing records](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/benchmarks/results.json) include the individual runs and conditions.

One actual unload/restart recovered 16,128 tokens of a text prefix from disk, with the first thinking/text delta at 2.15 seconds. [Measurement notes](https://github.com/YYTbit/qwen3.8-27b-3090/blob/main/docs/measurements.md), patch hashes, and preparation scripts are included.

The server and Claude Code start independently. Connection settings apply to the client process, and the launcher leaves Claude Code and cc-switch configuration files untouched. English/Chinese setup docs cover pinned sources, environment reuse, and Chinese download mirrors.

Credit for the inference algorithms and kernels goes to vLLM, HyperQwen, DFlash, LMCache, and the checkpoint authors. This repository packages the combination and measurements from this machine.

If you have two 3090s, I'd like to compare reproductions, particularly on hosts without NVLink. GPU topology, actual context length, cache state, and each stream's speed would be useful. Feedback on installation would help make the recipe easier to reproduce. Star it if you'd like to follow the updates.

## Distribution plan

1. Start with an appropriate technical sharing category in club-3090 Discussions and a Chinese post in V2EX 分享创造. Identify your relationship to the recipe and credit upstream.
2. Check each destination's current account eligibility, self-promotion, and AI-content rules. Disclose the assistance involved and use a permitted format. The current draft has not been approved by any community.
3. Retain actual input length, warm-cache conditions, output lengths, reasoning-token accounting, and per-stream qualifiers when adapting the text. The README and measurement records provide the complete validation scope.
4. Reply to reproduction questions and add third-party results with their hardware and workload conditions. Keep publication status separate from draft preparation.
