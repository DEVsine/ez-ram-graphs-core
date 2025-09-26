from __future__ import annotations

import asyncio
from typing import Protocol, List

from ..config import AIConfig
from ..schemas import Message


class AIProvider(Protocol):
    async def chat(self, messages: List[Message], cfg: AIConfig) -> str: ...


class _RPSLimiter:
    def __init__(self, rps: float):
        self._rps = max(0.0, rps)
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def pace(self):
        if self._rps <= 0:
            return
        async with self._lock:
            now = asyncio.get_event_loop().time()
            interval = 1.0 / self._rps
            wait = max(0.0, self._last + interval - now)
            if wait:
                await asyncio.sleep(wait)
            self._last = asyncio.get_event_loop().time()


__all__ = ["AIProvider", "_RPSLimiter"]

