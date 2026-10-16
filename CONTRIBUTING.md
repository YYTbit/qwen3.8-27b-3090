# Contributing

Reports from other RTX 3090 systems are welcome. Include the recipe commit, GPU count, interconnect and CUDA peer-access status, driver/runtime versions, model revisions, actual input/output token counts, sampling settings, cache state, first-token latency, and per-stream decode rates.

For concurrent runs, report every client and distinguish submitted clients from requests actually running on the engine. Keep failed and timed-out runs in the results.

Use your own shareable workload. Remove API keys, private conversation content, usernames, and machine-specific paths before attaching logs. A minimal public request is preferable to a full private session.

For inference changes, link the upstream implementation or pull request. Candidate profiles belong in a separate directory with their own cache namespace; promote them after correctness and real conversation checks.
