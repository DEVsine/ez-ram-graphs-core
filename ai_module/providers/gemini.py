from __future__ import annotations

import asyncio
from typing import List

from google import genai  # type: ignore
from .base import AIProvider, _RPSLimiter
from ..config import AIConfig
from ..schemas import Message


class GeminiProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)

    async def chat(self, messages: List[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()

        api_key = cfg.api_key or cfg.gemini_api_key
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        client = genai.Client(api_key=api_key)
        # generation_config = {
        #     "temperature": cfg.temperature,
        #     "response_mime_type": "application/json" if cfg.json_only else "text/plain",
        #     "max_output_tokens": cfg.max_tokens,
        # }
        # Convert to list of dicts per Gemini API style
        parts = []
        for m in messages:
            # Flatten to one text stream: prepend role markers for safety
            parts.append(f"[{m.role}]\n{m.content}\n")
        text_input = "\n".join(parts)
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=cfg.model, contents=text_input
                ),
            )
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Gemini API error: {e}") from e

        # Gemini SDK: resp.text contains the plain text content
        content = getattr(resp, "text", "")
        if not isinstance(content, str):
            content = str(content)
        return content
