from __future__ import annotations

from typing import Callable, Dict, Any

from .config import AIConfig


# Providers
_PROVIDERS: Dict[str, Callable[[AIConfig], Any]] = {}


def register_provider(name: str, factory: Callable[[AIConfig], Any]) -> None:
    _PROVIDERS[name] = factory


def resolve_provider(cfg: AIConfig):
    if cfg.provider not in _PROVIDERS:
        raise ValueError(f"Unknown provider '{cfg.provider}'. Registered: {list(_PROVIDERS)}")
    return _PROVIDERS[cfg.provider](cfg)


# Tasks
_TASKS: Dict[str, Any] = {}


def register_task(task: Any) -> None:
    name = getattr(task, "name", None)
    if not name:
        raise ValueError("Task must define a class/static attribute 'name'")
    _TASKS[name] = task


def get_task(name: str):
    if name not in _TASKS:
        raise ValueError(f"Unknown task '{name}'. Registered: {list(_TASKS)}")
    return _TASKS[name]

