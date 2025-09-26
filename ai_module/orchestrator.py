from __future__ import annotations

import asyncio
from typing import Dict, Any, List

from .config import AIConfig
from .registry import get_task
from .kernel import invoke_task


async def run_batch(task_name: str, inputs: List[Dict[str, Any]], cfg: AIConfig) -> List[Any]:
    task = get_task(task_name)
    sem = asyncio.Semaphore(max(1, cfg.parallelism))
    results: List[Any] = []

    async def one(inp: Dict[str, Any]):
        async with sem:
            return await invoke_task(task, inp, cfg)

    coros = [one(i) for i in inputs]
    return await asyncio.gather(*coros, return_exceptions=True)

