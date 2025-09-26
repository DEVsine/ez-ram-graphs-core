from __future__ import annotations
import os
from dataclasses import dataclass
from django.conf import settings as dj_settings  # type: ignore


def _getenv_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _get_from_django_ai(key: str):
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
    model: str = _get("model", "gpt-5")
    temperature: float = float(_get("temperature", 0.0))
    max_tokens: int = int(_get("max_tokens", 1024))
    rps: float = float(_get("rps", 2.0))
    parallelism: int = int(_get("parallelism", 4))
    json_only: bool = _get_bool("json_only", True)

    # Provider-specific keys (for convenience; not required by callers)
    openai_api_key: str | None = dj_settings.OPENAI_API_KEY
    gemini_api_key: str | None = dj_settings.GEMINI_API_KEY
