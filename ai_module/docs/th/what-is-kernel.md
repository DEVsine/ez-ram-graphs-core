## What “kernel” means in ai_module

- The kernel is the small, provider‑agnostic core that runs an AI “task”
- It takes: task_name + input dict + AIConfig
- It builds provider messages via the task, calls the configured provider, validates JSON, and returns a typed dict
- It has no knowledge of Django/Neo4j; it stays pure and reusable

## Responsibilities

- Resolve the task by name (via the registry)
- Build messages for the provider using the task’s build_messages
- Call the active provider (selected by AIConfig.provider)
- Enforce JSON (if cfg.json_only) and validate output
- Delegate final shaping to the task’s parse_output
- Keep a minimal, stable API: invoke and invoke_task

## How it fits with the rest

- Tasks: define how to prompt and how to parse results
- Providers: implement chat(messages, cfg) for an AI backend
- Registry: maps provider names and task names to implementations
- Safety: ensures strict JSON and trims overly long strings
- Orchestrator: runs many kernel calls in parallel; it uses invoke_task internally

## Public API (core excerpt)

```python path=ai_module/kernel.py mode=EXCERPT
async def invoke_task(task, inp, cfg):
    messages = task.build_messages(inp)
    raw = await resolve_provider(cfg).chat(messages, cfg)
    obj = ensure_json_obj(raw) if cfg.json_only else {"text": raw}
    return task.parse_output(obj) if cfg.json_only else obj

async def invoke(task_name, inp, cfg):
    task = get_task(task_name)
    return await invoke_task(task, inp, cfg)
```

## Typical usage

- One‑off call from any Python/Django code path:

```python mode=EXCERPT
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig(provider="openai", model="gpt-4o-mini")
out = asyncio.run(invoke("nl2cypher", {"prompt": "list all users"}, cfg))
print(out["cypher"], out["params"])
```

- For many inputs, prefer the orchestrator (it calls the kernel under the hood) to get concurrency and rate limiting.

## Guarantees and behavior

- Provider‑agnostic: switching providers needs no code changes, only config
- JSON‑first: raises if provider output isn’t valid JSON when cfg.json_only=True
- Small surface area: just invoke/invoke_task; everything else is pluggable
- Errors you may see:
  - Unknown task: task not registered
  - Provider error: bubbled from provider.chat
  - JSON validation error: non‑JSON or wrong schema for the task

If you’d like, I can add a “Kernel” section to the guideline docs you’re editing to summarize this.
