# ai_module Developer Guideline

This folder contains focused, step-by-step guides to extend and operate the AI module.

Guides:

- Add a new provider: add-provider.md
- Add a new task: add-task.md
- Run the orchestrator for batch/parallel AI: run-orchestrator.md

Prerequisites:

- Python 3.11+
- Access to your chosen AI provider (API key, SDK installed if needed)
- Django settings configured (optional but recommended) or environment variables with `AI_` prefix

Quick imports you will commonly use:

```python
from ai_module.config import AIConfig
from ai_module.kernel import invoke
from ai_module.registry import register_provider, register_task
from ai_module.schemas import Message
from ai_module.orchestrator import run_batch
```

Tip: The module is provider-agnostic and JSON-first. Switch providers via config only; tasks should enforce strict JSON output.

## Conclusion: Module Overview

- Purpose: A small, provider-agnostic AI kernel with pluggable tasks that enforces JSON-first outputs and clean separation from frameworks.
- Core pieces:
  - Kernel: single API to run tasks (`invoke`/`invoke_task`)
  - Tasks: define prompts and parse validated JSON
  - Providers: OpenAI/Gemini (or custom) via a simple `chat` interface
  - Registry: registers tasks/providers by name
  - Safety: ensures strict JSON and caps overly long outputs
  - Orchestrator: `run_batch` for concurrent, rate-limited processing
- Built-in tasks: `nl2cypher`, `summarize`, `classify`, `extract`
- Typical usage:
  - One-off: `asyncio.run(invoke("nl2cypher", {"prompt": "..."}, AIConfig()))`
  - CLI: `python manage.py ai_cypher` to generate/review/execute Cypher
  - Batch: `asyncio.run(run_batch("nl2cypher", inputs, AIConfig()))`
- Configuration: via `settings.AI` or `AI_*` environment variables; switch providers without code changes.
- Extensibility: add new providers (`register_provider`) and tasks (`register_task`) with minimal boilerplate.
- Next steps: see add-provider.md, add-task.md, and run-orchestrator.md for step-by-step guides.
