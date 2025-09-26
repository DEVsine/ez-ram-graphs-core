from __future__ import annotations

from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You are a text classifier.\n"
    'Output STRICT JSON only: {"label": string, "confidence": number?}. No other text.'
)


class ClassifyTask:
    name = "classify"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        text = inp.get("text") or ""
        labels = inp.get("labels") or []
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=f"Text: {text}\nLabels: {labels}"),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        label = raw_json.get("label")
        if not isinstance(label, str):
            raise ValueError("Output must contain 'label' string")
        out = {"label": label}
        conf = raw_json.get("confidence")
        if isinstance(conf, (int, float)):
            out["confidence"] = float(conf)
        return out
