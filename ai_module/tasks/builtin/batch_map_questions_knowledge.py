"""
AI Task for batch mapping multiple quiz questions to knowledge nodes in a single prompt.

This task takes multiple questions with their choices and a list of knowledge nodes,
then returns structured mappings for ALL questions in one AI response.

This is a TRUE batch operation - one prompt, one response, multiple question mappings.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You are a knowledge mapping assistant for educational quizzes.\n"
    "Given MULTIPLE quiz questions, their answer choices, and a list of knowledge nodes, "
    "identify which knowledge nodes are relevant to:\n"
    "1. Each question itself (question_knowledge_ids)\n"
    "2. Each individual choice within each question (choices[].knowledge_ids)\n\n"
    "Return STRICT JSON only with this structure:\n"
    "{\n"
    '  "mappings": [\n'
    "    {\n"
    '      "question_index": 1,\n'
    '      "question_knowledge_ids": [list of IDs],\n'
    '      "choices": [\n'
    '        {"index": 1, "knowledge_ids": [list of IDs]},\n'
    '        {"index": 2, "knowledge_ids": [list of IDs]},\n'
    "        ...\n"
    "      ]\n"
    "    },\n"
    "    {\n"
    '      "question_index": 2,\n'
    '      "question_knowledge_ids": [...],\n'
    '      "choices": [...]\n'
    "    },\n"
    "    ...\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Use only IDs from the provided knowledge nodes list\n"
    "- question_knowledge_ids should contain knowledge relevant to understanding the question\n"
    "- Each choice's knowledge_ids should contain knowledge that explains why that choice is correct or incorrect\n"
    "- Return empty arrays if no relevant knowledge is found\n"
    "- Do not include explanations or rationale in the output\n"
    "- Process ALL questions provided and return mappings in the same order"
)


class BatchMapQuestionsKnowledgeTask:
    """Task for batch mapping multiple quiz questions to knowledge nodes using AI."""

    name = "batch_map_questions_knowledge"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        """
        Build messages for the AI provider.

        Expected input:
        {
            "questions": [
                {
                    "question": "Question text",
                    "choices": ["choice1", "choice2", ...]
                },
                ...
            ],
            "knowledge_nodes": [{"id": uuid, "name": "..."}, ...]
        }
        """
        questions = inp.get("questions", [])
        knowledge_nodes = inp.get("knowledge_nodes", [])

        # Format knowledge nodes for the prompt
        knowledge_list = []
        for node in knowledge_nodes:
            node_id = node.get("id") or node.get("element_id")
            node_name = node.get("name", "")
            knowledge_list.append(f"ID {node_id}: {node_name}")

        knowledge_text = (
            "\n".join(knowledge_list)
            if knowledge_list
            else "No knowledge nodes provided"
        )

        # Format all questions
        questions_text_parts = []
        for q_idx, q_data in enumerate(questions, start=1):
            question = q_data.get("question", "")
            choices = q_data.get("choices", [])

            choices_text = "\n".join(
                [f"  {i + 1}. {choice}" for i, choice in enumerate(choices)]
            )

            question_block = (
                f"Question {q_idx}:\n  Text: {question}\n  Choices:\n{choices_text}"
            )
            questions_text_parts.append(question_block)

        all_questions_text = "\n\n".join(questions_text_parts)

        user_content = (
            f"Questions to Map ({len(questions)} total):\n\n"
            f"{all_questions_text}\n\n"
            f"Available Knowledge Nodes:\n{knowledge_text}"
        )

        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=user_content),
        ]

    @staticmethod
    def parse_output(obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate the AI output.

        Expected output from AI:
        {
            "mappings": [
                {
                    "question_index": 1,
                    "question_knowledge_ids": [1, 2, 3],
                    "choices": [
                        {"index": 1, "knowledge_ids": [1, 2]},
                        {"index": 2, "knowledge_ids": [3, 4]}
                    ]
                },
                ...
            ]
        }
        """
        if not isinstance(obj, dict):
            raise ValueError("AI output must be a JSON object")

        mappings = obj.get("mappings", [])
        if not isinstance(mappings, list):
            raise ValueError("'mappings' must be a list")

        return obj
