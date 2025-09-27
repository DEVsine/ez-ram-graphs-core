# การเพิ่ม Provider ใหม่

## คำอธิบาย

Provider คืออะแดปเตอร์เล็ก ๆ ที่ทำหน้าที่เชื่อมต่อกับโมเดล AI โดยมีเมธอดหลักเพียงตัวเดียวคือ
`chat(messages, cfg) -> str` (async function)
Kernel จะสร้างข้อความสำหรับ task นั้น ๆ แล้วเรียก `provider` ที่เราลงทะเบียนไว้ จากนั้น provider จะคืนค่าผลลัพธ์เป็น **ข้อความดิบ** (แนะนำให้เป็น JSON string ที่ถูกต้องเสมอ)

> **หมายเหตุ**: ต้องใช้ `_RPSLimiter` เพื่อเคารพ rate limit ของ API และต้อง register provider ก่อนใช้งาน

---

## เป้าหมาย

1. สร้างคลาส provider พร้อมเมธอด `chat`
2. ลงทะเบียน provider ด้วย `register_provider`
3. ตั้งค่า config ให้เลือก provider ของเรา
4. ทดสอบด้วย `invoke` call ง่าย ๆ

---

## สิ่งที่ควรมีล่วงหน้า

- API access หรือ SDK ของโมเดลที่คุณจะใช้
- ความเข้าใจพื้นฐานเกี่ยวกับ `ai_module.schemas.Message` และ `ai_module.config.AIConfig`

---

## ขั้นตอนการทำงาน

### 1) สร้าง provider class

```python
# my_project/providers/my_provider.py
from ai_module.providers.base import _RPSLimiter
from ai_module.schemas import Message
from ai_module.config import AIConfig

class MyProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)
        # TODO: สร้าง client ของจริง เช่น self.client = SDK(api_key=...)

    async def chat(self, messages: list[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()
        # TODO: แปลง messages ให้อยู่ในรูปแบบที่ API รองรับ
        # TODO: เรียก API ของโมเดล (sync → run_in_executor, หรือใช้ async SDK ได้เลย)
        # ควรคืนค่าเป็น JSON string ที่ถูกต้องเสมอ
        return '{"ok": true}'
```

---

### 2) ลงทะเบียน provider

```python
# ทำใน AppConfig.ready() หรือในไฟล์ startup อื่น ๆ
from ai_module.registry import register_provider
from my_project.providers.my_provider import MyProvider

register_provider("myprov", lambda cfg: MyProvider(cfg))
```

---

### 3) ตั้งค่า provider ผ่าน settings หรือ env

```python
# settings.py
AI = {
    "provider": "myprov",   # key ที่เราใช้ใน register_provider
    "model": "my-model",
    "json_only": True,
    "rps": 2.0,
    "parallelism": 4,
}
# API key สามารถส่งผ่าน env เช่น OPENAI_API_KEY, GEMINI_API_KEY หรือ key ของคุณเอง
```

หรือใช้ environment variables โดยตรง:

```
AI_PROVIDER=myprov
AI_MODEL=my-model
```

---

### 4) ทดสอบด้วยการเรียก invok# Add a New Task

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

e

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

```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig(provider="myprov", model="my-model")
res = asyncio.run(invoke("summarize", {"text": "hello"}, cfg))
print(res)
```

---

## แนวทางที่แนะนำ (Best Practices)

- บังคับให้โมเดลตอบกลับเป็น JSON เท่านั้น โดยตั้ง `json_only=True`
- ใช้ `_RPSLimiter` และพิจารณาเพิ่มระบบ retry/backoff เมื่อเจอ error 429 หรือ 5xx
- พยายามทำให้ข้อความสั้นและตรงประเด็น (Kernel จะช่วยตัดข้อความที่ยาวเกิน)

---

## ปัญหาที่เจอบ่อย (Troubleshooting)

- **Unknown provider 'myprov'**: ตรวจสอบว่าได้เรียก `register_provider("myprov", ...)` ก่อน `invoke` หรือไม่
- **Provider ไม่คืนค่า JSON ที่ถูกต้อง**: ต้องมั่นใจว่า prompt ของ task บังคับให้โมเดลตอบเป็น JSON และ provider คืนค่า string JSON เท่านั้น (ไม่มี code fences)
- **Rate limit error**: ลดค่า `rps` หรือ `parallelism` หรือเพิ่ม backoff/retry

---

คุณอยากให้ผมเขียน **ตัวอย่างโค้ดที่เชื่อมกับ API จริง** (เช่น OpenAI SDK หรือ HTTP API สมมติ) ให้ดูด้วยไหมครับ?
