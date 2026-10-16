# 环境安装

[English](setup.md)

## 实测环境

| 组件 | 版本或状态 |
| --- | --- |
| GPU | 2 × RTX 3090 24 GB，SM86 |
| 互联 | 无 NVLink，CUDA peer access 为 false，NCCL 使用 SHM |
| 驱动 | 550.78，`nvidia-smi` 显示 CUDA 12.4 |
| 用户态 CUDA | 12.9，runtime 12.9.79 |
| 系统 | Linux x86_64，glibc 2.35 |
| Python | 3.13.12 |
| Torch / Triton | 2.13.0+cu129 / 3.7.1 |
| 实际 vLLM | 完整 0.30.0+cu129 wheel 加 9 个公开补丁 |
| FlashInfer / compressed-tensors | 0.6.18 / 0.18.0 |
| Transformers / xgrammar | 5.12.1 / 0.2.1 |
| 编译器 | gcc-10、g++-10 |

驱动显示的 CUDA 版本与 Python 环境安装的 CUDA 用户态库不同。这套组合已在记录主机运行，期间没有升级驱动；其他主机仍需核实兼容性。启动器可传入 `--cuda-home /path/to/cuda-12.9`，不会安装或修改驱动。

原环境保留了 vLLM **0.28 的发行元数据**，通过 `PYTHONPATH` 加载独立解包的 **0.30 完整运行库及其原生扩展**。本仓库重建完整运行库。[environment.json](../benchmarks/environment.json)保留了这一区别，不能简单将 `pip freeze` 的 0.28 当成实测引擎版本。

## 优先复用已有环境

先用已有环境的 Python 查看依赖版本，后续命令保持使用同一个解释器。记录的依赖版本用于说明实测条件，尚不是经过干净安装验收的 lock 文件。

官方 0.30 wheel 声明依赖 `compressed-tensors==0.17.0`、`flashinfer-python==0.6.18.post1`，本机复用环境实际为 0.18.0 和 0.6.18。这里明确保留差异，避免把工作环境清单误写成依赖解析一定成功的安装配方。

## 下载官方 wheel

已有相同文件可以直接复用。官方地址为：

```bash
mkdir -p downloads
curl -fL --retry 3 \
  'https://github.com/vllm-project/vllm/releases/download/v0.30.0/vllm-0.30.0%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl' \
  -o downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
sha256sum downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

预期 SHA256：

```text
e98cb69659bfcfc849cf11ce0781a7161d40b02b51a6c3636924a5909f2aabcc
```

国内可尝试在原地址前添加 `https://ghfast.top/`，但下载后仍要核对上述摘要。Python 包优先使用清华源 `https://pypi.tuna.tsinghua.edu.cn/simple`，模型优先使用 `https://hf-mirror.com`。

## 新环境安装起点

以下路径**尚未完成干净机器从零验收**。建议单独建环境，保留现有工作环境。

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/python -m pip install \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
  --extra-index-url https://download.pytorch.org/whl/cu129 \
  downloads/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

随后安装下述 LMCache。原生扩展还需要兼容的 CUDA toolkit 和编译器。如果无法获得兼容依赖，可提交脱敏的环境信息，不要用实验覆盖正在工作的生产环境。

## 固定 LMCache 源码

实测使用未修改的上游源码快照。到 [v0.1.0 Release](https://github.com/YYTbit/qwen3.8-27b-3090/releases/tag/v0.1.0) 下载 `LMCache-dev-b026def84282.tar.gz`，摘要为：

```text
b026def84282947124f4997a7f640b9f7682411182dc5ea83485e663a7e37d9f
```

解压到被忽略的临时目录，用与推理服务相同的 Python 安装：

```bash
mkdir -p scratch/lmcache
tar -xzf downloads/LMCache-dev-b026def84282.tar.gz -C scratch/lmcache
python -m pip install --no-build-isolation scratch/lmcache/LMCache-dev \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

本机构建显示版本为 `0.0.0+qwen.local20261015`，这是本机构建标识，不是可以到 PyPI 下载的上游发行号。MP connector 和 `lmcache.cli.main server` 按上游实现使用。

## 模型准备

固定来源包含非对称 AWQ4 主体及 BF16 输出头。准备脚本先复制到新目录，再调用上游 `quant_heads_stream.py`，不修改源模型。输出头与 embedding 使用 group128 对称 INT8，线性层 scale 为 FP16，embedding scale 为 BF16。MTP 线性层为 INT8，但本配方的 DFlash 不使用 MTP。

随后复制归档配置，保持量化分组及 YaRN factor4、原长度 262,144，与实测目标一致。1,048,576 长度配置不代表已经通过该长度的精度与速度验收。量化脚本保留的备份也会占用磁盘。

运行库脚本校验 wheel、补丁的 SHA256，以 `fuzz=0` 应用到新目录。本机用此脚本重建后，2,683 个 Python 源文件与归档版本一致。

[模型准备核对](../benchmarks/preparation-audit.json)显示，所有非 MTP 张量与实测模型的形状、类型、原始字节 SHA256 一致。省略的三个辅助 MTP 草稿输出头张量不参与原生 DFlash2；尚未单独启动此副本进行 GPU 集成验收。

## 启动与连接

按照主 README 操作。双卡实测约用 23.3 GiB/卡，需要先确认所选卡没有其他负载；这不是四卡 17 GiB 候选配置。

启动器创建本地密钥、编译缓存及磁盘缓存目录，然后前台运行服务，只设置进程环境并监听本机，不写 Claude 配置。多个独立服务使用不同工作目录和端口；同一权重、运行库、工作目录重启时保留缓存命名空间。
