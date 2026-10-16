# 四卡实验

[English](four-gpu.md)

这些候选采用四张RTX 3090、TP4、原生DFlash2、1,048,576上下文长度配置、五个请求槽位、目标INT4 KV，CPU模型offload为0。每张物理GPU总占用限制为17 GiB。本机没有NVLink，CUDA peer access不可用，NCCL使用主机共享内存。

工作负载为相同的真实18,649-token Claude Code历史，每路输出上限1,024 token，速度包含思考，热缓存首token门槛为10秒。1M长度配置不是实际1M输入测速。

| 候选 | 热缓存单路中位数 | 五路中完成数 | 完成流的观测速率 | 实际最大运行请求数 |
| --- | --- | --- | --- | --- |
| W4A8，standard采样 | 85.84 token/s | 4 | 33.79–45.29 token/s | 5 |
| W4A8 + 原生分片采样 | 82.28 token/s | 4 | 37.80–43.27 token/s | 5 |
| W4A8 + 原生逐worker NUMA绑定 | 68.08 token/s | 2 | 40.93–45.52 token/s | 4 |

未完成请求在首token门槛处取消，因此完成流的部分生成阶段实际并发更少。**这些速率不代表五路持续并发已经通过验收。** 表内所有完成流均输出1,024 token。[结构化记录](../benchmarks/four-gpu-20261017.json)保留各路结果。

三种候选均未设为默认。各卡总显存峰值低于15.25 GiB，未观测到严重Xid事件。单独看显存或功耗，无法确定推理引擎是否存在问题，也无法推出速度会提升多少。

## 已核查的原生功能

vLLM[分片采样](https://docs.vllm.ai/en/stable/cli/serve/)默认关闭，Qwen实现提供`compute_logits_local`，四个worker均确认开启。它通过all-to-all减少重复词表采样，但本次没有改善性能。

原生NUMA绑定正确识别GPU节点`[0,0,1,1]`，已确认各worker绑定。首次启动失败来自解包后上游`numa_wrapper.sh`缺少执行权限；按官方wheel恢复为`0755`后可以启动，文件内容未修改。公开运行库构建脚本已保留wheel文件权限。

[整块验证](https://github.com/vllm-project/vllm/pull/46781)也已存在于Model Runner V2，通过`rejection_sample_method=block`选择，可用于后续受控对照。本页没有声称已取得它的本机结果。

## 两组双卡副本

原生DP2×TP2可以避免四rank张量并行，但需要两份模型和两份KV池。目前TP2的模型及草稿加载约为9.2 GiB/卡，1M目标INT4 KV至少再需要8 GiB/卡，还未计入scale、循环状态与工作区。现有配置无法直接复制为两组，同时满足每卡17 GiB和1M容量。

降低实验长度可以诊断拓扑收益，但属于另一套配置，不能当作1M目标已经完成。CPU模型offload也不在当前推理方案范围内。

已验收双卡配置继续作为参照。替换它需要同时检查输出可读、真实Claude Code完整对话、逐路并发速率，以及实际内存和上下文范围。
