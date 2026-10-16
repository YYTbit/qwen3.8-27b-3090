# Changelog

## v0.2.0 (2026-10-17)

- Preserve official wheel file modes, including the executable NUMA wrapper.
- Initialize the local API key with exclusive creation and mode 0600.
- Pin a 10.5 GiB per-GPU KV pool in the portable launcher for workspace headroom.
- Set physical GPU ordering and isolate inherited proxy and activation-quantization options.
- Publish the three rejected four-GPU candidates with per-stream results.
- Validate GPU inference on a separately prepared public-script checkpoint/runtime using existing Python dependencies; publish cold/warm timings, a complete Claude Code tool round, and the later thermal interruption.
- Keep the original 153 token/s profile separate from the portable launcher's 145 token/s assembly check.

## v0.1.2 (2026-10-17)

- Preserve request object order during replay, including tool schema fields that affect rendered prefix tokens.

## v0.1.1 (2026-10-17)

- Send Bearer authentication in the timing tool for vLLM's native endpoint.

## v0.1.0 (2026-10-17)

- Publish the dual-RTX-3090 launch profile and bilingual README.
- Include nine upstream patch files with SHA256 and ordered application.
- Add separate runtime/checkpoint preparation and a process-local launcher.
- Preserve original and restoration measurements, concurrency scope, and unmet targets.
- Archive the exact unchanged LMCache source used by the recorded build.
