# 双 RTX 3090 部署 Qwen3.8-27B

**[English](README.md) | [简体中文](README.zh-CN.md)**

用于本地 Claude Code 的推理配方，采用 vLLM 原生 DFlash2 和 HyperQwen 公开补丁。在没有 NVLink、CUDA peer access 不可用的两张 RTX 3090 上，真实 18.6k-token 会话的**热缓存单路 decode 中位数为 153 token/s**。独立归档恢复后重测，中位数为 **151 token/s**。

仓库包含实测启动配置、按顺序固定的上游补丁、模型准备脚本、磁盘缓存配置及测速记录。目标模型使用去拒绝版本的 AWQ4 权重，embedding 和输出头为 INT8；草稿模型采用 DFlash2 W4A16。

**[双卡完整探索故事](docs/exploration.zh-CN.md)**覆盖llama.cpp、SGLang、TP/PP、动态分块、MTP/DFlash、KV精度与缓存回载。[数据档案](benchmarks/history/README.md)包含247份留存证据文件的脱敏摘录、41行关键结果，并附[成绩与配置归属映射](benchmarks/history/lineage.json)。

## 实测结果

| 场景 | 结果 | 测量范围 |
| --- | --- | --- |
| 18,649 输入 token，热缓存单路 | 三轮中位数 **153 token/s** | 每轮输出 1,024 token，包含思考 |
| 独立归档恢复后，同配置重测 | 三轮中位数 **151 token/s** | 三轮范围 143–161 token/s |
| 使用公开脚本新建权重和运行库 | 热缓存三轮中位数 **145 token/s** | 每卡10.5 GiB KV；18,649输入token；复用Python依赖 |
| 五路同时请求 | **每路 56–69 token/s** | 引擎观测到五路运行，四路输出 1,024 token，一路输出 311 token 后调用工具 |
| 热缓存首个思考或文本增量 | **0.80–0.91 秒** | 首个流式思考或文本 |
| 一次卸载重启后的磁盘缓存回载 | 首个思考或文本增量 **2.15 秒** | 回载 16,128 token，验证了一个文本前缀 |
| 真实 Claude Code 完整两轮对话 | **104 / 138 token/s** | Read 工具成功，两轮均正常结束 |

[完整记录](benchmarks/results.json)保留逐次计时与恢复复测。标题回放的输出上限为1,024 token，速度包含思考；完整Claude Code回答与工具往返另行验收。使用的工作负载来自本机真实私有会话。

[公开脚本组装验收](benchmarks/assembly-validation-20261017.json)使用独立的约1.23M-token共享KV池。热缓存命中16,128 token，首个思考或文本增量为2.07–2.08秒。真实Claude Code第一轮完成Read工具调用及回答，速度136 token/s，正文在37.68秒开始。完整运行条件见链接记录。

**标题成绩对应18,649个实际输入token和热前缀缓存。** 归档启动器配置1,048,576-token单请求上限与五个请求槽位，共享约1.32M-token GPU KV池。更长上下文和多客户端的测量列入后续复现计划。

## 为什么保留这组配置

长历史实测逐步明确了需要检查什么。早期vLLM W4A8 PP2的初期prefill窗口达到3437 token/s，但真实520k输入末段的批次速度中位数降到363。后续轮次原生前缀命中约99.8%，decode仍为18至19 token/s。这些成绩属于早期配置。

[完整决策过程](docs/exploration.zh-CN.md)保留了SGLang并行方式观测、原生动态分块校准失败、投机与精度尝试，以及历史内核分支的同请求对照。最终回到原生DFlash2与九个原样公开补丁，用其自身的重复测量和归档恢复记录验证。早期自改内核的成绩另行标明；不同框架的测试条件存在差异，不据此宣称框架整体加速倍数。

![最终双卡配置的完整探索决策路线](docs/figures/decision-trail.png)

## 技术栈

- vLLM **0.30.0+cu129** 完整官方 wheel，加 **9 个原样应用的 HyperQwen 公开补丁**。
- 原生 DFlash2，7 个投机 token，standard 拒绝采样；关闭 lookup drafting。
- 目标主体 AWQ4，embedding 和 `lm_head` INT8，草稿 W4A16，目标 KV INT4，草稿 KV BF16。
- 双卡张量并行、分块 prefill、GPU 前缀缓存、上游 LMCache 磁盘存储。
- 原生 Anthropic 接口，附带兼容文本、图片和工具内容的 Claude 聊天模板。
- 模型推理在 GPU，`--cpu-offload-gb 0`。磁盘 KV 保存和回载经过主机内存暂存。

推理算法与内核来自 [vLLM](https://github.com/vllm-project/vllm)、[HyperQwen](https://github.com/syv-ai/HyperQwen)、[DFlash](https://github.com/z-lab/dflash) 和 [LMCache](https://github.com/LMCache/LMCache)。[上游署名](THIRD_PARTY.md)记录具体来源。

## 快速开始

实测环境为 Linux、两张 24 GB RTX 3090、兼容的 CUDA 12.9 用户态环境，每卡约占 23.3 GiB。**先阅读[环境安装说明](docs/setup.zh-CN.md)**。原环境复用了已有依赖，尚未完成干净机器的从零安装验收。

```bash
git clone https://github.com/YYTbit/qwen3.8-27b-3090.git
cd qwen3.8-27b-3090
```

### 1. 下载固定版本的模型

可以复用兼容的已有 Python 环境。Hugging Face 下载优先使用中国镜像。

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download twolven/Qwen3.8-27B-abliterated-AWQ-MTP \
  --revision c2f5341e7c9a1c55e6d61cfc8e6d0ca897bd7443 --local-dir weights/base
hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
  --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 --local-dir weights/draft
```

### 2. 单独准备权重和运行库

以下命令使用兼容环境中的 Python。模型脚本先复制源模型，再调用上游 CPU 量化脚本；需要预留新权重及量化备份的磁盘空间。

```bash
python scripts/prepare_model.py --source weights/base --output weights/target-head8
python scripts/prepare_runtime.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

[wheel 来源](configs/wheel-source.json)固定官方地址和 SHA256。运行库脚本校验 wheel、补丁摘要，在新目录中按顺序应用，`fuzz=0`。

[模型准备核对](benchmarks/preparation-audit.json)确认所有非 MTP 张量与实测模型一致。省略的三个辅助 MTP 草稿输出头张量不参与 DFlash2，已验收范围以审计记录为准。

### 3. 启动模型

```bash
python scripts/serve.py --runtime runtime/tp2 \
  --target weights/target-head8 --draft weights/draft \
  --work-dir .local --gpus 0,1 --port 8000
```

保持此进程运行。首次启动编译内核和计算图可能需要几分钟，看到 `Application startup complete` 后再连接。API 监听 `127.0.0.1:8000`，随机密钥保存在 `.local/api-key`，磁盘 KV 放在 `.local/kv-cache`。`Ctrl+C` 停止推理服务及其缓存进程，磁盘上的权重与缓存保留。

便携启动器固定使用**每卡10.5 GiB KV预算**，为工作区保留余量。归档测速配置采用0.94显存比例自动分配，原参数仍保留在启动模板中。两者均保留1M长度和五槽位，共享池容量有所不同，可用`--kv-cache-gib`调节便携预算。

多路 CPU 主机先查看 `nvidia-smi topo -m`，可通过 `--numa-node N` 绑定合适的 NUMA 节点。实测配置关闭 P2P 和 custom all-reduce。[完整启动配置](configs/launch-template.json)可直接核对。

### 4. 连接 Claude Code

在另一个终端运行：

```bash
env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL=http://127.0.0.1:8000 \
  ANTHROPIC_AUTH_TOKEN="$(cat .local/api-key)" \
  claude --model qwen3.8-27b-uncensor
```

这些变量仅作用于该进程，启动器不写入 Claude Code 或 cc-switch 配置。服务与 Claude 会话独立，多个客户端可以连接同一服务。在其他工作目录使用时，将密钥改为绝对路径。Claude Code 的权限由使用者自行控制。

## 测试自己的工作负载

将自己的 Anthropic Messages 请求保存为本地 JSON。测速脚本接受本机回环地址，仅保存用量和时间元数据，不保存提示词或回答正文。

```bash
python scripts/benchmark.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

[测量说明](docs/measurements.md)解释冷、热缓存、逐路速度及正确性检查。原私有工作负载发布了请求摘要，不公开会话正文。

## 缓存与上下文配置

引擎运行期间，GPU前缀缓存可复用已处理前缀。LMCache将兼容的KV和状态对象保存到磁盘，卸载后可以回载。本配方向上游配置256 GiB LRU存储，未设置TTL。[缓存说明](docs/cache.md)记录命名空间、容量统计和重启行为。

命中取决于前缀、模型、运行库布局一致，以及对应缓存块仍存在。后续复现计划包含长上下文质量和INT4 KV评估。

模型可以接收图片。本次记录的重启复用覆盖文本前缀，图片磁盘缓存与多日保留列入下一阶段验证。[缓存及排障说明](docs/cache.md)记录更多细节。

## 后续计划

- [x] 归档、恢复双卡配置，保留原始测量结果。
- [x] 发布中英双语说明、补丁摘要、模型准备及本地测速工具。
- [x] 发布双卡探索档案、结果归属和完整决策故事。
- [ ] 在其他机器验证干净环境安装。
- [ ] 验证长上下文、多模态持久化和多日缓存复用。


## 参与复现

欢迎提交其他机器的复现。请附实际上下文、输出长度、缓存状态、互联方式和各路速度。[提交说明](CONTRIBUTING.md) · [Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues)

## 许可

[Apache-2.0](LICENSE)。权重单独下载，遵循各自许可。[第三方署名](THIRD_PARTY.md)。
