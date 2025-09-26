from __future__ import annotations

from typing import Dict, Any, List

from .config import AIConfig
from .schemas import Message
from .registry import resolve_provider, get_task
from .safety import ensure_json_obj, cap_len


async def invoke_task(task, inp: Dict[str, Any], cfg: AIConfig) -> Dict[str, Any]:
    messages: List[Message] = task.build_messages(inp)
    raw = await resolve_provider(cfg).chat(messages, cfg)
    raw = cap_len(raw)
    obj = ensure_json_obj(raw) if cfg.json_only else {"text": raw}
    return task.parse_output(obj) if cfg.json_only else obj


async def invoke(task_name: str, inp: Dict[str, Any], cfg: AIConfig) -> Dict[str, Any]:
    task = get_task(task_name)
    return await invoke_task(task, inp, cfg)

