from __future__ import annotations

import os
from dataclasses import dataclass

try:  # Prefer Django settings when available
    from django.conf import settings as dj_settings  # type: ignore

    _HAS_DJANGO = True
except Exception:  # pragma: no cover
    dj_settings = None  # type: ignore
    _HAS_DJANGO = False


def _getenv_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _get_from_django_ai(key: str):
    if not _HAS_DJANGO:
        return None
    try:
        # Only access settings if configured
        if not getattr(dj_settings, "configured", False):
            return None
        ai = getattr(dj_settings, "AI", None)
    except Exception:
        return None
    if isinstance(ai, dict):
        if key in ai:
            return ai[key]
        if key.upper() in ai:
            return ai[key.upper()]
    return None


def _get(key: str, default):
    # Priority: Django settings.AI[key/KEY] -> env AI_KEY -> default
    val = _get_from_django_ai(key)
    if val is None:
        val = os.getenv(f"AI_{key.upper()}")
    return default if val is None else val


def _get_bool(key: str, default: bool) -> bool:
    val = _get_from_django_ai(key)
    if isinstance(val, bool):
        return val
    if val is not None:
        return str(val).lower() in ("1", "true", "yes", "on")
    return _getenv_bool(f"AI_{key.upper()}", default)


@dataclass
class AIConfig:
    # Core configuration
    provider: str = _get("provider", "openai")
    model: str = _get("model", "gpt-4o-mini")
    temperature: float = float(_get("temperature", 0.0))
    max_tokens: int = int(_get("max_tokens", 1024))
    rps: float = float(_get("rps", 2.0))
    parallelism: int = int(_get("parallelism", 4))
    json_only: bool = _get_bool("json_only", True)

    # Credentials (generic preferred; provider-specific env fallbacks)
    api_key: str | None = (
        _get_from_django_ai("api_key")
        or os.getenv("AI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    # Provider-specific keys (for convenience; not required by callers)
    # openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    # gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    openai_api_key: str | None = (
        "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"
    )
    gemini_api_key: str | None = "AIzaSyDLwvFl4XW38LFCWEci2QCQNvoFetTSgz4"
