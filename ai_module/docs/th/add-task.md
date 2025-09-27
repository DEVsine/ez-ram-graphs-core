# การเพิ่ม Task ใหม่

## คำอธิบาย

**Task** กำหนดวิธีแปลง `input dict` ให้เป็นข้อความสำหรับ provider และวิธี parse JSON ที่ได้กลับมาเป็น `dict` ที่มีโครงสร้างชัดเจน

**สัญญา (Contract):**

- `name`: ชื่อสตริงที่ไม่ซ้ำ
- `build_messages(inp) -> list[Message]`
- `parse_output(raw_json: dict) -> dict`

ลงทะเบียน (register) หนึ่งครั้ง จากนั้นเรียกใช้งานที่ไหนก็ได้ผ่าน kernel

---

## เป้าหมาย

- เขียน `build_messages` พร้อม **system prompt ที่บังคับ JSON-only**
- เขียน `parse_output` พร้อมการตรวจสอบความถูกต้อง (strict validation)
- ลงทะเบียนด้วย `register_task`
- เรียกใช้งานและยืนยันผล

---

## ความรู้ที่ควรมีก่อน (Prerequisites)

- คุ้นเคยกับ `ai_module.schemas.Message` และรูปแบบ I/O ที่คาดหวัง

---

## ขั้นตอนทีละก้าว

### 1) สร้างคลาส task

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
        # ตัวอย่างการบังคับความเรียบร้อย (optional):
        ans = ans.strip()
        return {"answer": ans}
```

### 2) ลงทะเบียน task

```python
from ai_module.registry import register_task
from my_project.tasks.my_task import MyTask

register_task(MyTask)
```

### 3) เรียกใช้งาน (Invoke)

```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig()  # จะอ่านจาก settings.AI / env โดยอัตโนมัติ
out = asyncio.run(invoke("mytask", {"question": "What is EZRam?"}, cfg))
print(out["answer"])
```

---

## เคล็ดลับการตรวจสอบ (Validation tips)

- แต่ง **system message** ให้กำชับว่า **ต้องส่งออกเป็น JSON ล้วน ๆ** เท่านั้น
- ใน `parse_output` ให้ตรวจชนิดข้อมูลของทุกฟิลด์ที่คาดหวัง และโยน error ที่ชัดเจนเมื่อไม่ตรงสเปค
- ถ้าผลลัพธ์มีขนาดใหญ่ ให้คงโครงสร้างตื้น ๆ (shallow) เพื่อประหยัดโทเคน

---

## ตัวอย่างที่มากับระบบ (ศึกษาแนวทาง)

- `ai_module/tasks/builtin/summarize.py`
- `ai_module/tasks/builtin/classify.py`
- `ai_module/tasks/builtin/extract.py`
- `ai_module/tasks/builtin/nl2cypher.py`

---

## การแก้ปัญหา (Troubleshooting)

- **Unknown task**: ตรวจสอบว่าได้เรียก `register_task(MyTask)` ก่อนการ `invoke` ครั้งแรก
- **JSON validation error**: ให้แน่ใจว่า _provider_ คืนค่าเป็น **strict JSON (ไม่มี code fences)** และกุญแจ/ชนิดข้อมูลตรงกับที่ `parse_output` ต้องการ
- **Prompt drift**: เน้นย้ำ “JSON-only” ใน system prompt และจำกัด keys ให้น้อย/ชัดเจน

---

> ถ้าต้องการ ผมสามารถช่วยเสริมตัวอย่าง `parse_output` แบบเข้มขึ้น (เช่น ตรวจ key ที่ไม่รู้จัก, ขีดจำกัดความยาว, หรือ schema เบื้องต้น) ให้ได้ทันทีครับ
