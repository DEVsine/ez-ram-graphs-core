from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You extract structured fields from text according to a requested schema.\n"
    'Output STRICT JSON only: {"data": object}. No other text.'
)


class ExtractTask:
    name = "extract"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        text = inp.get("text") or ""
        schema = inp.get("schema") or {}
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=f"Text: {text}\nSchema: {json.dumps(schema)}"),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        data = raw_json.get("data")
        if not isinstance(data, dict):
            raise ValueError("Output must contain 'data' object")
        return {"data": data}
