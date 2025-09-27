# Add a New Provider

Explanation

- A provider is a small adapter that implements a single async method `chat(messages, cfg) -> str`.
- The kernel builds task-specific messages and calls the provider; provider returns raw text (preferably strict JSON string) from the model.
- Use the built-in `_RPSLimiter` to respect rate limits. Register the provider and select it via config.

Objectives

- Implement a provider class with `chat`
- Register it with `register_provider`
- Configure `AI.provider` to your provider key
- Verify with a simple `invoke` call

Prerequisites

- API access and SDK for your model, if applicable
- Basic familiarity with `ai_module.schemas.Message` and `ai_module.config.AIConfig`

Step-by-step

1. Create a provider class

```python
# my_project/providers/my_provider.py
from ai_module.providers.base import _RPSLimiter
from ai_module.schemas import Message
from ai_module.config import AIConfig

class MyProvider:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self._limiter = _RPSLimiter(cfg.rps)
        # Initialize your real client here, e.g. self.client = SDK(api_key=...)

    async def chat(self, messages: list[Message], cfg: AIConfig) -> str:
        await self._limiter.pace()
        # Convert messages into your API's input format
        # Call your API (sync via run_in_executor or async SDK) and return string
        # IMPORTANT: Prefer returning strict JSON text (no code fences)
        return '{"ok": true}'
```

2. Register the provider

```python
# E.g., in AppConfig.ready() or a module import path that runs on startup
from ai_module.registry import register_provider
from my_project.providers.my_provider import MyProvider

register_provider("myprov", lambda cfg: MyProvider(cfg))
```

3. Configure selection via settings or env

```python
# settings.py
AI = {
    "provider": "myprov",  # Select your provider key
    "model": "my-model",
    "json_only": True,
    "rps": 2.0,
    "parallelism": 4,
}
# Provide API keys as needed (OPENAI_API_KEY, GEMINI_API_KEY, or your own)
```

Or set environment variables: `AI_PROVIDER=myprov`, `AI_MODEL=my-model`, etc.

4. Verify with a simple call

```python
import asyncio
from ai_module.config import AIConfig
from ai_module.kernel import invoke

cfg = AIConfig(provider="myprov", model="my-model")
res = asyncio.run(invoke("summarize", {"text": "hello"}, cfg))
print(res)
```

Best practices

- Force JSON output in your prompts (tasks do this via system messages) and set `json_only=True` to validate.
- Use `_RPSLimiter` and consider adding retry/backoff for 429/5xx.
- Keep messages small; the kernel also caps overly long strings.

Troubleshooting

- Unknown provider 'myprov': Ensure `register_provider("myprov", ...)` ran before first `invoke`.
- Provider did not return valid JSON: Ensure your task prompts enforce strict JSON; return pure JSON text.
- Rate limit errors: Lower `rps` or `parallelism`, or add backoff.
