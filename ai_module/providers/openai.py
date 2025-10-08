from __future__ import annotations

import asyncio
from typing import List

from openai import AsyncOpenAI
from .base import _RPSLimiter
from ..config import AIConfig
from ..schemas import Message


class OpenAIProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)

    async def chat(self, messages: List[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()
        client = AsyncOpenAI(api_key=cfg.openai_api_key)
        # Prefer Chat Completions with JSON mode
        payload_msgs = [{"role": m.role, "content": m.content} for m in messages]
        try:
            resp = await client.responses.create(
                model=cfg.model,
                input=payload_msgs,
                # response_format={"type": "json_object"} if cfg.json_only else None,
                reasoning={
                    "effort": "minimal"
                },
                text={"format": {"type": "json_object"}} if cfg.json_only else None,
            )
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"OpenAI API error: {e}") from e

        content = resp.output[-1].content[0].text
        if not isinstance(content, str):
            content = str(content)
        return content
