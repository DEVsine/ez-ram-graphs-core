"""
ai_kernel_core: Pure, pluggable AI kernel with general tasks and provider switching.

- No Django or database dependencies
- General tasks (e.g., nl2cypher, summarize, classify, extract)
- Providers: OpenAI, Gemini (config-only switching)

Usage (programmatic):
    from ai_kernel_core.kernel import invoke
    from ai_kernel_core.config import AIConfig

    cfg = AIConfig()
    result = asyncio.run(invoke("summarize", {"text": "..."}, cfg))

You can also run as a module:
    python -m ai_kernel_core.cli run nl2cypher --input '{"prompt":"..."}'
"""

from .config import AIConfig
from .kernel import invoke, invoke_task
from .orchestrator import run_batch
from .registry import register_provider, resolve_provider, register_task, get_task

# Ensure default providers and builtin tasks are registered on import
from .providers import openai as _register_openai  # noqa: F401
from .providers import gemini as _register_gemini  # noqa: F401
from .tasks.builtin import nl2cypher as _nl2cypher  # noqa: F401
from .tasks.builtin import summarize as _summarize  # noqa: F401
from .tasks.builtin import classify as _classify  # noqa: F401
from .tasks.builtin import extract as _extract  # noqa: F401

