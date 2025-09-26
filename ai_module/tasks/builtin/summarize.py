from __future__ import annotations

from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You are a helpful assistant that produces concise summaries.\n"
    'Output STRICT JSON only: {"summary": string}. No other text.'
)


class SummarizeTask:
    name = "summarize"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        text = inp.get("text") or ""
        max_words = inp.get("max_words")
        style = inp.get("style")
        hints = []
        if max_words:
            hints.append(f"MaxWords: {max_words}")
        if style:
            hints.append(f"Style: {style}")
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=f"Text: {text}\n" + "\n".join(hints)),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        summary = raw_json.get("summary")
        if not isinstance(summary, str):
            raise ValueError("Output must contain 'summary' string")
        return {"summary": summary}
