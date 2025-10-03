"""
Test for TRUE batch question mapping (1 AI call for all questions).
"""

import os
import django

# Setup Django settings before importing anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from ai_module.config import AIConfig
from ai_module.kernel import invoke
from quiz.services.batch_question_mapping_service import BatchQuestionMappingService


class TestTrueBatchQuestionMapping(unittest.TestCase):
    """Test the TRUE batch mapping service (all questions in one AI call)."""

    def test_batch_mapping_single_ai_call(self):
        """Test that all questions are sent in ONE AI call and get ONE response."""

        # Mock AI response for multiple questions
        mock_ai_response = {
            "mappings": [
                {
                    "question_index": 1,
                    "question_knowledge_ids": [1, 2],
                    "choices": [
                        {"index": 1, "knowledge_ids": [1]},
                        {"index": 2, "knowledge_ids": [2]},
                    ],
                },
                {
                    "question_index": 2,
                    "question_knowledge_ids": [3, 4],
                    "choices": [
                        {"index": 1, "knowledge_ids": [3]},
                        {"index": 2, "knowledge_ids": [4]},
                    ],
                },
            ]
        }

        # Patch the invoke function to return our mock response
        with patch(
            "quiz.services.batch_question_mapping_service.invoke",
            new=AsyncMock(return_value=mock_ai_response),
        ) as mock_invoke:
            # Prepare input with 2 questions
            service_input = {
                "questions": [
                    {
                        "question": "What is 2+2?",
                        "choices": ["3", "4"],
                        "correct_answers": ["4"],
                    },
                    {
                        "question": "What is 3+3?",
                        "choices": ["5", "6"],
                        "correct_answers": ["6"],
                    },
                ],
                "knowledge_nodes": [
                    {"id": 1, "name": "Addition"},
                    {"id": 2, "name": "Numbers"},
                    {"id": 3, "name": "Math"},
                    {"id": 4, "name": "Arithmetic"},
                ],
            }

            # Execute service
            result = BatchQuestionMappingService.execute(service_input)

            # Verify invoke was called ONLY ONCE (true batching!)
            self.assertEqual(mock_invoke.call_count, 1)

            # Verify we got results for both questions
            self.assertEqual(len(result), 2)

            # Verify first question mapping
            self.assertEqual(result[0]["question"], "What is 2+2?")
            self.assertEqual(result[0]["question_knowledge_ids"], [1, 2])
            self.assertEqual(len(result[0]["choices"]), 2)

            # Verify second question mapping
            self.assertEqual(result[1]["question"], "What is 3+3?")
            self.assertEqual(result[1]["question_knowledge_ids"], [3, 4])
            self.assertEqual(len(result[1]["choices"]), 2)

    def test_batch_mapping_empty_questions(self):
        """Test handling of empty questions list."""
        service_input = {
            "questions": [],
            "knowledge_nodes": [{"id": 1, "name": "Test"}],
        }

        with self.assertRaises(ValueError) as context:
            BatchQuestionMappingService.execute(service_input)

        self.assertIn("At least one question is required", str(context.exception))

    def test_batch_mapping_filters_invalid_questions(self):
        """Test that invalid questions are filtered out before sending to AI."""

        mock_ai_response = {
            "mappings": [
                {
                    "question_index": 1,
                    "question_knowledge_ids": [1],
                    "choices": [
                        {"index": 1, "knowledge_ids": [1]},
                        {"index": 2, "knowledge_ids": [1]},
                    ],
                },
            ]
        }

        with patch(
            "quiz.services.batch_question_mapping_service.invoke",
            new=AsyncMock(return_value=mock_ai_response),
        ) as mock_invoke:
            service_input = {
                "questions": [
                    {
                        "question": "Valid question?",
                        "choices": ["A", "B"],
                    },
                    {
                        "question": "",  # Invalid: empty question
                        "choices": ["A", "B"],
                    },
                    {
                        "question": "Another question?",
                        "choices": ["A"],  # Invalid: only 1 choice
                    },
                ],
                "knowledge_nodes": [{"id": 1, "name": "Test"}],
            }

            result = BatchQuestionMappingService.execute(service_input)

            # Should only get 1 result (the valid question)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["question"], "Valid question?")


if __name__ == "__main__":
    unittest.main()
