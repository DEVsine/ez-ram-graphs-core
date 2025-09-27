# Add a New Task

Explanation

- A task defines how to turn your input dict into provider messages and how to parse JSON back into a structured dict.
- Contract:
  - `name`: unique string
  - `build_messages(inp) -> list[Message]`
  - `parse_output(raw_json: dict) -> dict`
- Register the task once; invoke it anywhere with the kernel.

Objectives

- Implement `build_messages` with a clear, JSON-only system prompt
- Implement `parse_output` with strict validation
- Register via `register_task`
- Invoke and verify

Prerequisites

- Familiarity with `ai_module.schemas.Message` and the expected I/O

Step-by-step

1. Create a task class

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
        ans = raw_json.get("answer")
        if not isinstance(ans, str):
            raise ValueError("Output must contain 'answer' string")
        return {"answer": ans}
```

2. Register the task

```python
from ai_module.registry import register_task
from my_project.tasks.my_task import MyTask

register_task(MyTask)
```

3. Invoke the task

```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig()  # picks up settings.AI / env
out = asyncio.run(invoke("mytask", {"question": "What is EZRam?"}, cfg))
print(out["answer"])
```

Validation tips

- Always craft the system message to demand strict JSON.
- Validate every expected field type in `parse_output` and throw clear errors.
- For larger outputs, consider returning structured, shallow objects to minimize token usage.

Examples

- See built-ins for patterns:
  - `ai_module/tasks/builtin/summarize.py`
  - `ai_module/tasks/builtin/classify.py`
  - `ai_module/tasks/builtin/extract.py`
  - `ai_module/tasks/builtin/nl2cypher.py`

Troubleshooting

- Unknown task: Ensure `register_task(MyTask)` ran before first `invoke`.
- JSON validation error: Ensure provider returned strict JSON (no fences) and keys/types match your parser.
- Prompt drift: Reinforce JSON-only and include minimal, explicit fields.
