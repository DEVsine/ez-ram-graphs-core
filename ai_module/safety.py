from __future__ import annotations

import json
import re
from typing import Any

CODE_FENCE_RE = re.compile(r"^```(?:json)?\n|\n```$", re.MULTILINE)


def strip_code_fences(s: str) -> str:
    return CODE_FENCE_RE.sub("", s).strip()


def ensure_json_obj(raw: str) -> dict[str, Any]:
    cleaned = strip_code_fences(raw)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Provider did not return valid JSON: {e}\nRaw: {raw[:500]}") from e
    if not isinstance(obj, dict):
        raise ValueError("Expected a JSON object (dict) from provider")
    return obj


def cap_len(txt: str, max_chars: int = 20000) -> str:
    if len(txt) > max_chars:
        return txt[:max_chars]
    return txt

