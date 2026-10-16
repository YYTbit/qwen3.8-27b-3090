# 双 RTX 3090 部署 Qwen3.8-27B

**[English](README.md) | [简体中文](README.zh-CN.md)**

用于本地 Claude Code 的推理配方，采用 vLLM 原生 DFlash2 和 HyperQwen 公开补丁。在没有 NVLink、CUDA peer access 不可用的两张 RTX 3090 上，真实 18.6k-token 会话的**热缓存单路 decode 中位数为 153 token/s**。独立归档恢复后重测，中位数为 **151 token/s**。

仓库包含实测启动配置、按顺序固定的上游补丁、模型准备脚本、磁盘缓存配置及测速记录。目标模型使用去拒绝版本的 AWQ4 权重，embedding 和输出头为 INT8；草稿模型采用 DFlash2 W4A16。

## 实测结果

| 场景 | 结果 | 测量范围 |
| --- | --- | --- |
| 18,649 输入 token，热缓存单路 | 三轮中位数 **153 token/s** | 每轮输出 1,024 token，包含思考 |
| 独立归档恢复后，同配置重测 | 三轮中位数 **151 token/s** | 三轮范围 143–161 token/s |
| 五路同时请求 | **每路 56–69 token/s** | 引擎观测到五路运行，四路输出 1,024 token，一路输出 311 token 后调用工具 |
| 热缓存首个思考或文本增量 | **0.80–0.91 秒** | 不等于正文开始时间 |
| 一次卸载重启后的磁盘缓存回载 | 首个思考或文本增量 **2.15 秒** | 回载 16,128 token，验证了一个文本前缀 |
| 真实 Claude Code 完整两轮对话 | **104 / 138 token/s** | Read 工具成功，两轮均正常结束 |
| 120k-token 含图片冷输入 | 100 秒内没有首 token | 达到截止时间后取消 |

[完整记录](benchmarks/results.json)保留后续恢复复测和未达成目标。速度包含思考 token；标题数据对应的三轮均在正文出现前达到 `max_tokens`。这些数据来自本机私有工作负载，不是公开排行榜或模型质量评测。

**1M 是配置的上下文长度上限。实际 1M 性能、五路各超过 100 token/s、多日 99% 缓存命中均尚未验证。** GPU KV 池合计约 1.32M token，由请求共享，五个槽位不代表五份独立的 1M 上下文可以同时驻留。

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
python scripts/zhunbei_moxing.py --source weights/base --output weights/target-head8
python scripts/zhunbei_yunxing.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

[wheel 来源](configs/wheel-source.json)固定官方地址和 SHA256。运行库脚本校验 wheel、补丁摘要，在新目录中按顺序应用，`fuzz=0`。

[模型准备核对](benchmarks/preparation-audit.json)确认所有非 MTP 张量与实测模型一致。省略的三个辅助 MTP 草稿输出头张量不参与 DFlash2，准备副本尚未单独启动进行 GPU 集成验收。

### 3. 启动模型

```bash
python scripts/qidong.py --runtime runtime/tp2 \
  --target weights/target-head8 --draft weights/draft \
  --work-dir .local --gpus 0,1 --port 8000
```

保持此进程运行。API 监听 `127.0.0.1:8000`，随机密钥保存在 `.local/api-key`，磁盘 KV 放在 `.local/kv-cache`。`Ctrl+C` 停止推理服务及其缓存进程，磁盘上的权重与缓存保留。

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
python scripts/cesu.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

[测量说明](docs/measurements.md)解释冷、热缓存、逐路速度及正确性检查。原私有工作负载发布了请求摘要，不公开会话正文。

## 缓存与长上下文边界

引擎运行期间，GPU 前缀缓存可复用已处理前缀。LMCache 将兼容的 KV 和状态对象保存到磁盘，卸载后可以回载。本配方未设置 TTL，并向上游配置 256 GiB LRU 存储。上游跨重启容量统计存在缺口，这不是跨重启严格容量保证。

命中取决于前缀、模型、运行库布局一致，以及对应缓存块仍存在。去拒绝处理不代表安全性或智力得到保证，长上下文质量和 INT4 KV 的影响仍需单独评估。

多模态模型可以接收图片，但本次已验收的重启复用为文本。图片磁盘缓存、多日保留、多份独立 1M 会话和 1M 冷 prefill 延迟尚未通过端到端验证。[缓存及排障说明](docs/cache.md)记录更多细节。

## 后续计划

- [x] 归档、恢复双卡配置，保留原始测量结果。
- [x] 发布中英双语说明、补丁摘要、模型准备及本地测速工具。
- [ ] 在其他机器验证干净环境安装。
- [ ] 在**每卡 17 GiB**内改善四卡五并发性能。
- [ ] 验证长上下文、多模态持久化和多日缓存复用。

## 参与复现

欢迎提交其他机器的复现。请附实际上下文、输出长度、缓存状态、互联方式和各路速度。[提交说明](CONTRIBUTING.md) · [Issues](https://github.com/YYTbit/qwen3.8-27b-3090/issues)

## 许可

[Apache-2.0](LICENSE)。权重单独下载，遵循各自许可。[第三方署名](THIRD_PARTY.md)。
