# Announcement drafts

These drafts are prepared for an appropriate self-promotion or benchmark thread. They have not been posted to external communities.

## English

**Qwen3.8-27B on 2×RTX 3090: ~153 tok/s warm decode with native DFlash2**

I published a local Claude Code serving recipe for two RTX 3090s without NVLink or CUDA peer access. It uses vLLM 0.30 + native DFlash2, nine public HyperQwen patches, an abliterated AWQ4 target with INT8 heads, and LMCache disk storage.

On one real 18.6k-token conversation, three 1,024-token warm runs had a 153 tok/s median; an archive restoration rerun reached 151. Five simultaneous streams achieved 56–69 tok/s each. Rates include reasoning. 1M is configured, but actual 1M speed and five streams each above 100 tok/s have not been achieved.

The repo includes bilingual docs, exact patch hashes, preparation scripts, timing records, and the limitations. The original conversation is private. Reproductions on public workloads and other 3090 topologies would be useful.

https://github.com/YYTbit/qwen3.8-27b-3090

Credit goes to vLLM, HyperQwen, DFlash, LMCache, and the checkpoint authors.

## 中文

**双3090运行Qwen3.8-27B：原生DFlash2，热decode约153 token/s**

整理了一份本地 Claude Code 推理配方。两张3090，没有NVLink，CUDA peer access也不可用。使用vLLM0.30原生DFlash2、9个HyperQwen公开补丁、AWQ4去拒绝模型及INT8输出头，磁盘缓存采用LMCache。

真实18.6k输入会话，三轮各1024输出，热decode中位153 token/s，独立归档恢复后复测151；五并发每路56至69。速度包含思考。1M是配置上限，实际1M性能及五路各100仍未达到。

仓库提供中英文说明、精确补丁摘要、准备脚本、测量记录及已知边界。原会话涉及隐私，不公开正文。欢迎用公开工作负载和其他3090互联拓扑复现。

https://github.com/YYTbit/qwen3.8-27b-3090

算法和内核归功于vLLM、HyperQwen、DFlash、LMCache及模型作者。

## Distribution plan

1. Keep the first screen focused on hardware, actual context length, measured speed, and reproduction links.
2. Publish a tagged release, searchable topics, and English/Chinese documentation.
3. Invite public reproductions and retain their hardware/context/cache conditions in a separate results section.
4. Consider a single relevant club-3090 benchmark discussion and a LocalLLaMA self-promotion thread after checking their current posting rules. Tailor the post to the audience and credit upstream work.
5. Treat third-party reproduction and a clean-install path as higher priorities than promotional claims. Never buy stars or label a configured 1M limit as a verified benchmark.
