# Cache behavior and troubleshooting

## Storage layout

`--work-dir` contains the API key, compilation caches, generated LMCache configuration, logs, and `kv-cache/<namespace>/objects`. It is ignored by Git. Keep this directory on a volume with adequate space.

- GPU prefix cache is live engine state and disappears when the engine exits.
- LMCache disk objects survive an engine stop and can be loaded by a compatible later run.
- Model weights stay on disk. Stopping the service releases its GPU allocation; it does not delete weight files.
- The configuration requests no TTL and 256 GiB LRU storage. Eviction and storage availability still matter. The upstream implementation's accounting after restart does not cover all old files; monitor actual disk usage separately.
- Host RAM is used for cache I/O staging. Model inference and active attention KV remain on GPUs; CPU model offload is zero.

The generated namespace includes the runtime manifest, launch profile, template, model JSON and weight-file identity. Changing those inputs creates a separate namespace. Do not manually reuse a cache between TP2 and TP4, different checkpoints, or incompatible runtime layouts.

## Verified and pending

One text prefix was saved, the server unloaded, and 16,128 tokens recovered from disk on restart. Multimodal persistence, multi-day retention, and every cache boundary under concurrent requests remain pending. A previous TP4 experiment produced repeated garbage after cache reuse; it was rejected and is not included as a recommended profile. Repeated text with zero draft acceptance is a correctness failure, even if the API returns HTTP 200.

## Common errors

| Symptom | Check |
| --- | --- |
| `auto tool choice requires...` | Both `--enable-auto-tool-choice` and `--tool-call-parser qwen3_xml` are in the recorded profile. |
| `Unexpected item type in content` | Keep the provided chat template. It handles Claude text/image/tool-reference forms; old templates can reject newer blocks. |
| Image input unsupported | Use the complete multimodal checkpoint and processor files, not a text-only export. This profile uses the native model, not GGUF/mmproj. |
| vLLM version or extension mismatch | Use the full prepared runtime, including `.so` files. Inspect its module path as well as package metadata. |
| No model in Claude `/model` | The process must point to the local endpoint and use the explicit served-model name. This recipe does not rewrite global model menus. |
| Disk cache port occupied | Choose unused `--cache-port` and `--cache-http-port`; the latter also uses its next port. |
| Slow first response after a cold start | A configured 1M limit does not precompute 1M tokens. Inspect actual input length and cache hits. |
| Generated repetitions or unreadable output | Stop that request, preserve diagnostics, and isolate the cache namespace. Do not call it a successful speed result. |

## Memory budget

The published TP2 profile uses about 23.3 GiB per 24 GB card. A separate four-GPU research budget is 17 GiB per card. Two copies of this TP2 configuration do not automatically fit that budget or retain the same 1M KV capacity.

Five request slots share one pool of roughly 1.32M GPU KV tokens. Prefix sharing can reduce repeated storage, but five unrelated 1M contexts require substantially more memory. Cache on disk does not make GPU capacity unlimited.
