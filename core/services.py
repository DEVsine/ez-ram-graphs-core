from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, TypeVar

from core.api import APIError

Input = TypeVar("Input")
Output = TypeVar("Output")


@dataclass
class ServiceContext:
    """Optional ambient context that services can use (e.g., user, ram_id)."""
    user: Any | None = None
    ram_id: str | None = None


class BaseService(Generic[Input, Output]):
    """
    Base class for class-based services.

    Pattern:
      - Define __init__(self, inp: Input, ctx: ServiceContext | None = None)
      - Implement run(self) -> Output
      - Prefer small, pure methods; raise APIError for domain failures
    """

    def __init__(self, inp: Input, ctx: Optional[ServiceContext] = None) -> None:
        self.inp = inp
        self.ctx = ctx or ServiceContext()

    def run(self) -> Output:  # pragma: no cover - abstract pattern
        raise NotImplementedError

    @classmethod
    def execute(cls, inp: Input, ctx: Optional[ServiceContext] = None) -> Output:
        return cls(inp, ctx=ctx).run()

