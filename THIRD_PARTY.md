# Upstream projects

This is a deployment recipe built on upstream implementations. It introduces no inference algorithm or handwritten attention kernel.

| Project | Role | Source |
| --- | --- | --- |
| vLLM | Inference engine, native DFlash scheduling, Anthropic API | [vllm-project/vllm](https://github.com/vllm-project/vllm), release 0.30.0+cu129 |
| HyperQwen | Nine public patches and CPU head quantization scripts | [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen), Apache-2.0 |
| DFlash | Block diffusion speculative decoding | [z-lab/dflash](https://github.com/z-lab/dflash) |
| LMCache | Persistent KV storage and native vLLM MP connector | [LMCache/LMCache](https://github.com/LMCache/LMCache), Apache-2.0 |
| Qwen | Base model architecture and tokenizer | [QwenLM](https://github.com/QwenLM) |
| twolven | Abliterated AWQ target checkpoint | [model source](https://huggingface.co/twolven/Qwen3.8-27B-abliterated-AWQ-MTP) |
| syvai | Quantized DFlash2 draft checkpoint | [draft source](https://huggingface.co/syvai/Qwen3.8-27B-DFlash2-W4A16) |

The patch files are byte-for-byte copies of public HyperQwen patches, applied in the order recorded in [patches.json](configs/patches.json). SHA256 hashes identify the exact patch contents. The local source audit records no handwritten kernel changes.

The three vendored preparation scripts are unmodified copies pinned to HyperQwen commit `d1ba27f495a0213f8582bdb298ebbe96e2c97234`. Their license and source hashes are in [third_party/hyperqwen](third_party/hyperqwen).

The release includes an unchanged LMCache upstream source snapshot with SHA256 `b026def84282947124f4997a7f640b9f7682411182dc5ea83485e663a7e37d9f`. Its original archive contains the upstream license. The original URL used a moving `dev` branch; the archived bytes and digest identify the source used here. This is not an official LMCache release.

Apache-2.0 covers the recipe's own files and the included Apache-licensed material. Model licenses and other dependencies retain their original terms. No weights are redistributed.
