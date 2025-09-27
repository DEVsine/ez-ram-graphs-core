# Run the Orchestrator (Batch/Parallel)

Explanation
- The orchestrator provides `run_batch(task_name, inputs, cfg)` to execute many inputs concurrently for a task.
- Concurrency is controlled by `AIConfig.parallelism`. Provider calls are paced by `_RPSLimiter(cfg.rps)`.
- Returns a list where each item is either the task result or an Exception for that item.

Objectives
- Prepare a list of input dicts for your task
- Configure parallelism and rps in `AIConfig`
- Call `run_batch` and handle successes/errors

Prerequisites
- A registered task (built-in or custom)
- A working provider configuration and API key

Step-by-step

1) Basic usage
```python
import asyncio
from ai_module.config import AIConfig
from ai_module.orchestrator import run_batch

cfg = AIConfig(provider="openai", model="gpt-4o-mini", parallelism=8, rps=4.0)
inputs = [
    {"prompt": "list all projects"},
    {"prompt": "count users"},
    {"prompt": "create node Person name:Alice"},
]

results = asyncio.run(run_batch("nl2cypher", inputs, cfg))

for i, r in enumerate(results):
    if isinstance(r, Exception):
        print(f"[{i}] ERROR:", r)
    else:
        print(f"[{i}] CYPHER:", r.get("cypher"))
        print(f"[{i}] PARAMS:", r.get("params"))
```

2) Chunk large jobs
```python
BATCH = 1000
for start in range(0, len(inputs), BATCH):
    chunk = inputs[start:start+BATCH]
    results = asyncio.run(run_batch("nl2cypher", chunk, cfg))
    # persist or stream results here
```

3) Custom tasks
```python
cfg = AIConfig(parallelism=6, rps=3.0)
news = [{"text": t} for t in corpus]
results = asyncio.run(run_batch("summarize", news, cfg))
```

Error handling tips
- `run_batch` includes exceptions as items. Log them and selectively retry.
- Tune `parallelism` and `rps` to balance throughput vs. rate limits.
- Consider adding backoff/retry logic inside your provider implementation.

Reference
- Orchestrator signature:
```python
async def run_batch(task_name: str, inputs: list[dict], cfg: AIConfig) -> list:
    ...
```
- Kernel/task flow: `run_batch` -> `invoke_task` -> provider `.chat()` -> JSON validation -> `task.parse_output()`

Troubleshooting
- Task not found: Ensure the task is registered before calling `run_batch`.
- Event loop issues: Use `asyncio.run(...)` in top-level scripts; avoid nested `asyncio.run` calls in already-async contexts.
- Memory spikes: Process in chunks; stream results to disk instead of holding all in memory.

