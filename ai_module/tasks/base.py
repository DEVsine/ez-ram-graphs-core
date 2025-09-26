from __future__ import annotations

from typing import Protocol, ClassVar, Any, Dict, List

from ..schemas import Message


class AITask(Protocol):
    name: ClassVar[str]

    def build_messages(self, inp: Dict[str, Any]) -> List[Message]: ...

    def parse_output(self, raw_json: Dict[str, Any]) -> Dict[str, Any]: ...

