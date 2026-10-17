# Qwen3.8-27B 双 RTX 3090 部署

**[English](README.md) | [简体中文](README.zh-CN.md)**

面向 Claude Code 的本地 Qwen3.8-27B 部署方案，采用 **vLLM、原生 DFlash2 和 HyperQwen 公开补丁**。在无 NVLink 的双 RTX 3090 上，18.6k 输入、热缓存单路 decode 的中位数达到 **153 token/s**；从独立归档恢复后复测达到 **151 token/s**。

[环境配置](docs/setup.zh-CN.md) · [性能评测](docs/exploration.zh-CN.md) · [测量方法](docs/measurements.md) · [缓存配置](docs/cache.md) · [版本发布](https://github.com/YYTbit/qwen3.8-27b-3090/releases)

## 功能特性

- **Claude Code 接入**：通过原生 Anthropic 接口处理文本、图片和工具内容。
- **原生投机解码**：使用 DFlash2、7 个投机 token 和标准拒绝采样。
- **前缀缓存与磁盘持久化**：集成 GPU 前缀缓存和上游 LMCache。
- **独立服务管理**：多个客户端共用服务，连接设置限定于当前进程。
- **完整部署资料**：提供固定配置、权重准备脚本、上游补丁及评测档案。

## 性能表现

| 工作负载 | 结果 | 测量条件 |
| --- | --- | --- |
| 热缓存单路 | 中位数 **153 token/s** | 18,649 输入，三次各输出 1,024 token |
| 独立归档恢复 | 中位数 **151 token/s** | 相同请求与选定配置，三次测量 |
| 公开脚本重建 | 中位数 **145 token/s** | 相同输入，独立的每卡 10.5 GiB KV 配置 |
| 五路同时请求 | **每路 56–69 token/s** | 观测到五路运行；四路输出 1,024 token，一路 311 token 后调用工具 |
| 热缓存首个思考或文本增量 | **0.80–0.91 秒** | 选定配置，单路请求 |
| 重启后磁盘缓存回载 | 首个思考或文本增量 **2.15 秒** | 验证一个文本前缀，回载 16,128 token |
| Claude Code 完整对话 | **104 / 138 token/s** | 两个完整轮次，Read 工具调用成功 |

单路测量命中 17,920 个前缀 token，速度包含思考，输出上限为 1,024 token。完整回答和工具往返另行测量。[逐次结果](benchmarks/results.json)与[重建记录](benchmarks/assembly-validation-20261017.json)保留完整条件。

归档配置提供 **1,048,576-token 单请求上限**和**五个请求槽位**，共用约 **1.32M-token GPU KV 池**。表中性能对应实际测量的工作负载，长上下文评测列入后续计划。

## 部署配置

| 组件 | 选定配置 |
| --- | --- |
| 硬件 | 2 × RTX 3090 24 GB，无 NVLink，CUDA peer access 不可用 |
| 运行库 | 官方 vLLM 0.30.0+cu129 wheel，原样应用九个 HyperQwen 公开补丁 |
| 目标模型 | 去拒绝版本，AWQ4 主体，INT8 embedding 与输出头 |
| 草稿模型 | DFlash2 W4A16，7 个投机 token，关闭 lookup |
| 缓存与状态精度 | 目标 KV 为 INT4，草稿 KV 为 BF16，循环状态为 FP16 |
| 执行方式 | TP2、分块 prefill、GPU 前缀缓存，CPU 模型卸载为 0 |
| 持久化缓存 | 上游 LMCache 磁盘存储，保存与回载使用主机内存暂存 |

[性能评测报告](docs/exploration.zh-CN.md)整理了 llama.cpp、SGLang 和 vLLM 的配置选择过程，涵盖 TP/PP、动态分块、MTP/DFlash、量化精度与缓存持久化。[数据档案](benchmarks/history/README.md)包含 247 份源文件摘录、41 行关键结果及[配置归属](benchmarks/history/lineage.json)。

![双卡评测概览](docs/figures/decision-trail.png)

## 快速开始

实测部署使用 Linux、两张 24 GB RTX 3090 和 CUDA 12.9 用户态环境，每卡约占 23.3 GiB。[环境配置](docs/setup.zh-CN.md)介绍驱动兼容性、已有 Python 环境复用和中国镜像。当前部署已通过复用依赖的验收，干净主机安装列入复现计划。

```bash
git clone https://github.com/YYTbit/qwen3.8-27b-3090.git
cd qwen3.8-27b-3090
```

### 模型下载

下载固定版本的目标模型与草稿模型，使用 `HF_ENDPOINT` 指定中国镜像。

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download twolven/Qwen3.8-27B-abliterated-AWQ-MTP \
  --revision c2f5341e7c9a1c55e6d61cfc8e6d0ca897bd7443 --local-dir weights/base
hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
  --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 --local-dir weights/draft
```

### 权重与运行库准备

使用兼容环境中的 Python 执行以下命令。模型准备脚本复制源权重，再调用上游 CPU 量化脚本；需要为新权重与量化备份预留磁盘空间。

```bash
python scripts/prepare_model.py --source weights/base --output weights/target-head8
python scripts/prepare_runtime.py \
  --wheel downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl \
  --output runtime/tp2
```

构建脚本校验固定的 [wheel](configs/wheel-source.json) 与补丁摘要，在独立目录中按顺序应用补丁，`fuzz=0`。[权重审计](benchmarks/preparation-audit.json)记录所有非 MTP 张量的形状、精度和原始字节摘要一致性。DFlash2 权重省略三个辅助 MTP 草稿输出头张量。

### 服务启动

```bash
python scripts/serve.py --runtime runtime/tp2 \
  --target weights/target-head8 --draft weights/draft \
  --work-dir .local --gpus 0,1 --port 8000
```

服务在前台运行，监听 `127.0.0.1:8000`。首次内核与计算图编译可能需要数分钟，出现 `Application startup complete` 后即可连接。本地密钥保存在 `.local/api-key`，持久化 KV 位于 `.local/kv-cache`。`Ctrl+C` 释放服务占用的显存，磁盘权重和缓存继续保留。

便携启动器采用**每卡 10.5 GiB KV 预算**，共享池约 1.23M token。153 token/s 的归档配置按 0.94 显存比例自动分配，共享池较大。两者均保留 1M 上下文上限与五个槽位，可通过 `--kv-cache-gib` 调节 KV 预算。

多路 CPU 主机可查看 `nvidia-smi topo -m`，并按需使用 `--numa-node N`。实测配置关闭 P2P 和 custom all-reduce，详见[启动配置](configs/launch-template.json)。

### Claude Code 连接

在另一个终端运行：

```bash
env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL=http://127.0.0.1:8000 \
  ANTHROPIC_AUTH_TOKEN="$(cat .local/api-key)" \
  claude --model qwen3.8-27b-uncensor
```

连接设置限定于当前进程，保留已有 Claude Code 和 cc-switch 配置。多个客户端可以共用独立管理的推理服务。在其他目录启动时使用密钥文件的绝对路径，客户端权限仍由 Claude Code 控制。

## 性能测量

将 Anthropic Messages 请求保存为本地 JSON 文件，然后执行：

```bash
python scripts/benchmark.py --request /path/to/your-request.json \
  --key-file .local/api-key --concurrency 5 \
  --ttft-limit 10 --total-limit 120 --output .local/results-five.json
```

工具接受回环地址，保存用量、计时与请求摘要，会话内容保留在本地。[测量方法](docs/measurements.md)定义冷请求、GPU 热缓存、磁盘回载、逐路吞吐和完整客户端验收的口径。

## 缓存持久化

引擎运行期间，GPU 前缀缓存复用已处理内容。LMCache 将兼容的 KV 和状态对象持久化，在重启后回载。配置采用 **256 GiB LRU 磁盘存储，不设置 TTL**。缓存身份包含模型、运行库、启动配置和模板。

已验证一次文本前缀的卸载与重启复用。多日保留、多模态持久化及长上下文质量列入后续计划。[缓存配置与排障](docs/cache.md)说明容量统计和命名空间细节。

## 后续计划

- [x] 归档选定配置，并通过独立恢复复测。
- [x] 发布双语部署说明、权重准备、固定补丁和测量工具。
- [x] 发布框架评测、配置归属及可编辑图表。
- [ ] 在干净主机验证安装。
- [ ] 扩展长上下文与多客户端评测。
- [ ] 验证多模态缓存持久化、多日复用及 INT4 KV 质量。

## 参与贡献

复现报告请提供实际上下文、输出长度、缓存状态、互联方式和逐路吞吐。详见[提交说明](CONTRIBUTING.md)和[问题反馈](https://github.com/YYTbit/qwen3.8-27b-3090/issues)。

## 许可与致谢

[Apache-2.0](LICENSE)。模型权重单独分发，遵循各自许可。

推理算法与内核来自 [vLLM](https://github.com/vllm-project/vllm)、[HyperQwen](https://github.com/syv-ai/HyperQwen)、[DFlash](https://github.com/z-lab/dflash) 和 [LMCache](https://github.com/LMCache/LMCache)，详见[第三方署名](THIRD_PARTY.md)。
