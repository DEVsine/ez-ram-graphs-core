# ai_module Developer Guideline

This guide shows how to extend and use ai_module:
- Add a new provider
- Add a new task
- Run the orchestrator for parallel/batch AI

The module is provider‑agnostic and JSON‑first. You switch providers via config only, and tasks enforce strict JSON outputs.

## Imports you’ll use

```python
from ai_module.config import AIConfig
from ai_module.kernel import invoke
from ai_module.registry import register_provider, register_task
from ai_module.schemas import Message
from ai_module.orchestrator import run_batch
```

---

## 1) Add a new provider

Providers implement a simple async interface that returns the raw model text (usually JSON). Use the built‑in RPS limiter to respect API rate limits.

### Interface
```python
# ai_module/providers/base.py
class AIProvider(Protocol):
    async def chat(self, messages: list[Message], cfg: AIConfig) -> str: ...
```

### Minimal example provider
```python
# my_project/providers/my_provider.py
from ai_module.providers.base import _RPSLimiter
from ai_module.schemas import Message
from ai_module.config import AIConfig

class MyProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)
        # Initialize your real client here (e.g., SDK)

    async def chat(self, messages: list[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()
        # Convert messages to the format your API expects
        # Call the API and return a string (preferably strict JSON)
        return '{"ok": true}'
```

### Register the provider
```python
# Register at import time (e.g., in app ready, or module import)
from ai_module.registry import register_provider
from my_project.providers.my_provider import MyProvider

register_provider("myprov", lambda cfg: MyProvider(cfg))
```

### Configure the provider
Use Django settings.AI or environment variables (prefix AI_).

```python
# settings.py
AI = {
    "provider": "myprov",  # <- use your provider key here
    "model": "my-model",
    "json_only": True,
    "rps": 2.0,
    "parallelism": 4,
}
# Add any provider-specific keys in settings or env as you like
```

Environment variables (optional): AI_PROVIDER, AI_MODEL, AI_RPS, AI_PARALLELISM, AI_JSON_ONLY, etc.

### Test the provider
```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig(provider="myprov", model="my-model")
result = asyncio.run(invoke("summarize", {"text": "hello"}, cfg))
print(result)
```

---

## 2) Add a new task

Tasks are small adapters that:
- build_messages(inp) → list[Message]
- parse_output(json) → dict

They should enforce JSON output via the system prompt.

### Minimal task example
```python
# my_project/tasks/my_task.py
from typing import Any, Dict, List
from ai_module.schemas import Message

SYSTEM = (
    "You are a helpful assistant.\n"
    'Output STRICT JSON only: {"answer": string}. No other text.'
)

class MyTask:
    name = "mytask"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        question = inp.get("question") or ""
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=f"Question: {question}"),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        # Validate/shape the JSON returned by the provider
        ans = raw_json.get("answer")
        if not isinstance(ans, str):
            raise ValueError("Output must contain 'answer' string")
        return {"answer": ans}
```

### Register the task
```python
from ai_module.registry import register_task
from my_project.tasks.my_task import MyTask

register_task(MyTask)
```

### Invoke the task
```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig()  # respects settings.AI and env vars
out = asyncio.run(invoke("mytask", {"question": "What is EZRam?"}, cfg))
print(out["answer"])
```

Notes:
- The kernel enforces JSON if cfg.json_only is True (default). It will raise if the provider returns non‑JSON.
- Reuse patterns from built‑ins (summarize, classify, extract, nl2cypher) for prompts and output validation.

---

## 3) Run the orchestrator (batch/parallel)

Use run_batch to execute many inputs concurrently for a given task. Concurrency is controlled by AIConfig.parallelism. Rate is paced by your provider using _RPSLimiter.

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

# For built-in NL→Cypher task
results = asyncio.run(run_batch("nl2cypher", inputs, cfg))

# Handle successes and exceptions (run_batch returns exceptions as items)
for i, r in enumerate(results):
    if isinstance(r, Exception):
        print(f"[{i}] ERROR:", r)
    else:
        print(f"[{i}] CYPHER:", r.get("cypher"))
        print(f"[{i}] PARAMS:", r.get("params"))
```

Tips:
- Increase parallelism for throughput; increase rps gradually to avoid provider throttling.
- For very large batches, chunk your inputs and call run_batch per chunk.

---

## Configuration reference

You can set via Django settings.AI or environment variables (AI_*). Precedence: settings.AI → env → defaults.

- provider (AI_PROVIDER): e.g., "openai", "gemini", or your custom key
- model (AI_MODEL)
- temperature (AI_TEMPERATURE)
- max_tokens (AI_MAX_TOKENS)
- rps (AI_RPS) — requests per second pacing for providers
- parallelism (AI_PARALLELISM) — max concurrent tasks in orchestrator
- json_only (AI_JSON_ONLY) — enforce strict JSON outputs

Provider keys (example):
- OPENAI_API_KEY, GEMINI_API_KEY in Django settings (or use your own names for custom providers)

---

## Troubleshooting

- ValueError: Unknown provider 'X' — did you register_provider("X", ...)? Is settings.AI["provider"] set to "X"?
- Provider did not return valid JSON — ensure your system prompt forces strict JSON, cfg.json_only=True, and your provider returns pure JSON text (no code fences).
- Rate limit errors — lower cfg.rps or parallelism, or add exponential backoff in your provider implementation.
- Batch errors — run_batch returns exceptions inline; log and retry failed items selectively.

