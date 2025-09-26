import asyncio
import json
import unittest

import ai_kernel_core as core
from ai_module.config import AIConfig
from ai_module.schemas import Message
from ai_module.registry import register_provider


class FakeProvider:
    async def chat(self, messages, cfg):
        # Return JSON depending on user content hints
        user = next((m for m in messages if m.role == "user"), None)
        text = user.content if user else ""
        if "Prompt:" in text:  # nl2cypher
            return json.dumps({"cypher": "MATCH (n) RETURN n LIMIT 1", "params": {}})
        if "Labels:" in text or "Label:" in text:  # classify
            return json.dumps({"label": "A", "confidence": 0.9})
        if "Schema:" in text:  # extract
            return json.dumps({"data": {"x": 1}})
        # summarize fallback
        return json.dumps({"summary": "ok"})


class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_provider("fake", lambda cfg: FakeProvider())

    def test_invoke_summarize(self):
        cfg = AIConfig(provider="fake")
        out = asyncio.run(core.invoke("summarize", {"text": "hello"}, cfg))
        self.assertEqual(out["summary"], "ok")

    def test_invoke_nl2cypher(self):
        cfg = AIConfig(provider="fake")
        out = asyncio.run(core.invoke("nl2cypher", {"prompt": "list"}, cfg))
        self.assertIn("MATCH", out["cypher"])
        self.assertIsInstance(out["params"], dict)

    def test_invoke_classify(self):
        cfg = AIConfig(provider="fake")
        out = asyncio.run(
            core.invoke("classify", {"text": "t", "labels": ["A", "B"]}, cfg)
        )
        self.assertEqual(out["label"], "A")

    def test_invoke_extract(self):
        cfg = AIConfig(provider="fake")
        out = asyncio.run(
            core.invoke("extract", {"text": "t", "schema": {"x": "int"}}, cfg)
        )
        self.assertIn("data", out)


if __name__ == "__main__":
    unittest.main()
