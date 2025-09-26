import asyncio
import json
import unittest

from ai_module.config import AIConfig
from ai_module.registry import register_provider
from ai_module.orchestrator import run_batch
from ai_module.schemas import Message


class FakeProvider:
    async def chat(self, messages, cfg):
        return json.dumps({"summary": "ok"})


class OrchestratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_provider("fake", lambda cfg: FakeProvider())

    def test_run_batch(self):
        cfg = AIConfig(provider="fake", parallelism=3)
        inputs = [{"text": f"hello {i}"} for i in range(5)]
        out = asyncio.run(run_batch("summarize", inputs, cfg))
        self.assertEqual(len(out), 5)
        self.assertTrue(all(isinstance(x, dict) for x in out))
        self.assertTrue(all(x.get("summary") == "ok" for x in out))


if __name__ == "__main__":
    unittest.main()
