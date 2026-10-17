# Cache Configuration

## Storage Layout

`--work-dir` contains the API key, compilation caches, generated LMCache configuration, logs, and `kv-cache/<namespace>/objects`. The directory is excluded from Git.

| Storage | Lifecycle |
| --- | --- |
| GPU prefix cache | Live engine state; released when the engine exits |
| LMCache disk objects | Persist across service restarts for compatible configurations |
| Model weights | Remain on disk after the service stops |
| Host staging buffers | Used during disk-cache save/load |

Model inference and active attention KV remain on GPU, with CPU model offload set to zero.

## Retention Policy

The configuration requests **256 GiB of LRU disk storage with no TTL**. Retention depends on available storage and eviction. Upstream capacity accounting after restart can omit older files, so filesystem usage requires separate monitoring.

Cache namespaces include the runtime manifest, launch profile, chat template, model JSON, and weight-file identity. Changes to these inputs create a separate namespace, preserving compatibility between stored objects and the active configuration.

## Persistence Validation

One text prefix was saved and recovered after a full unload/restart: **16,128 externally cached tokens**, zero GPU prefix hits, and **2.15 s** to the first thinking/text delta. Validation includes readable output and draft acceptance. Multi-day retention, multimodal persistence, and concurrent cache behavior remain evaluation tasks.

## Capacity

The archived TP2 profile allocated approximately **23.3 GiB per GPU**, with a shared GPU KV pool of approximately **1.32M tokens**. The portable launcher instead reserves **10.5 GiB of KV per GPU** for a pool of approximately **1.23M tokens**, leaving workspace headroom.

Five request slots share the active KV pool. Identical prefixes can share storage; admission of unrelated contexts depends on their combined active KV requirements. Disk persistence provides reuse across restarts, while active requests use the available GPU capacity.

## Troubleshooting

| Symptom | Configuration check |
| --- | --- |
| `auto tool choice requires...` | Include both `--enable-auto-tool-choice` and `--tool-call-parser qwen3_xml`. |
| `Unexpected item type in content` | Use the supplied chat template for Claude text, image, and tool-reference content. |
| Image input unsupported | Use the complete multimodal checkpoint and processor files. The selected runtime uses the native model. |
| vLLM version or extension mismatch | Use the complete prepared runtime, including native libraries, and inspect the effective module path. |
| Model absent from Claude `/model` | Point the client to the local endpoint and specify the served-model name explicitly. |
| Disk-cache port occupied | Select available `--cache-port` and `--cache-http-port` values; the HTTP service also uses the next port. |
| High cold-start response latency | Inspect actual input length, cache state, and compilation status. |
| Repetition or unreadable output | Cancel the request, retain diagnostics, and isolate the cache namespace for investigation. |
