from __future__ import annotations

from .base import AIProvider
from ..registry import register_provider
from ..config import AIConfig

# Register default providers lazily via factories

def _openai_factory(cfg: AIConfig) -> AIProvider:
    from .openai import OpenAIProvider
    return OpenAIProvider(cfg)


def _gemini_factory(cfg: AIConfig) -> AIProvider:
    from .gemini import GeminiProvider
    return GeminiProvider(cfg)


# Side-effect registration on import
register_provider("openai", _openai_factory)
register_provider("gemini", _gemini_factory)

