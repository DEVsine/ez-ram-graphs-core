from __future__ import annotations

import asyncio
from typing import List

from .base import AIProvider, _RPSLimiter
from ..config import AIConfig
from ..schemas import Message


class OpenAIProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)

    async def chat(self, messages: List[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()
        # Import inside to avoid hard dependency at import time
        try:
            import openai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ImportError(
                "openai package is required for OpenAIProvider. Install 'openai' or switch provider."
            ) from e

        client = openai.OpenAI(api_key=cfg.api_key or cfg.openai_api_key)
        # Prefer Chat Completions with JSON mode
        payload_msgs = [{"role": m.role, "content": m.content} for m in messages]
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=cfg.model,
                    messages=payload_msgs,
                    response_format={"type": "json_object"} if cfg.json_only else None,
                ),
            )
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"OpenAI API error: {e}") from e

        content = resp.choices[0].message.content if resp and resp.choices else ""
        if not isinstance(content, str):
            content = str(content)
        return content
