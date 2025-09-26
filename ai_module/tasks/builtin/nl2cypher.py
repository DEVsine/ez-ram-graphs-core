from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You are a Cypher generator.\n"
    "Return STRICT JSON only with keys: cypher (string), params (object), rationale (optional string).\n"
    "Rules: one Cypher statement only; no semicolons; parameterize all values; prefer RETURN with LIMIT for reads;\n"
    "Do not use LOAD CSV or CALL apoc.* unless explicitly asked."
)


class NL2CypherTask:
    name = "nl2cypher"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        prompt = inp.get("prompt") or ""
        action = inp.get("action")
        label = inp.get("label")
        where = inp.get("where")
        props = inp.get("props")
        limit = inp.get("limit")
        hints = []
        if action:
            hints.append(f"Action: {action}")
        if label:
            hints.append(f"Label: {label}")
        if where:
            hints.append("Where: " + json.dumps(where))
        if props:
            hints.append("Props: " + json.dumps(props))
        if limit:
            hints.append(f"Limit: {limit}")
        hint_text = "\n".join(hints)
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=f"Prompt: {prompt}\n{hint_text}"),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        # Basic shape validation
        if "cypher" not in raw_json or not isinstance(raw_json["cypher"], str):
            raise ValueError("Output must contain 'cypher' string")
        params = raw_json.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ValueError("'params' must be an object")
        out = {
            "cypher": raw_json["cypher"],
            "params": params,
        }
        if isinstance(raw_json.get("rationale"), str):
            out["rationale"] = raw_json["rationale"]
        return out
