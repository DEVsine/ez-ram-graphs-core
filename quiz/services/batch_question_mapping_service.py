"""
Batch service for mapping multiple quiz questions to knowledge nodes using AI.

This service sends ALL questions in ONE prompt to the AI and receives
ALL mappings in a single response, reducing API calls from N to 1.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from ai_module.config import AIConfig
from ai_module.kernel import invoke
from core.services import BaseService


class BatchQuestionMappingService(BaseService[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Class-based service for batch mapping of quiz questions to knowledge nodes.

    This service sends ALL questions in ONE AI prompt and receives ALL mappings
    in a single response. This is TRUE batching - reducing API calls from N to 1.

    Input structure:
    {
        "questions": [
            {
                "question": str,
                "choices": [{
                    "index": 1,
                    "text": "Do",
                    "is_correct": true,
                    "answer_description": "ถูกต้อง เพราะประธาน **they** เป็นพหูพจน์ ต้องใช้โครงสร้าง __Do + subject + base verb__. กริยาหลักคงรูป: `Do they live near here?` ใช้ถามข้อเท็จจริงทั่วไปหรือความเป็นจริงในปัจจุบัน."
                }],
            },
            ...
        ],
        "knowledge_nodes": [{"id": ..., "name": ...}, ...],
        "ai_provider": str,  # optional
        "ai_model": str,  # optional
    }

    Output structure:
    [
        {
            "question": str,
            "answer_description": str,
            "question_knowledge_ids": [int, ...],
            "choices": [
                {
                    "index": int,
                    "text": str,
                    "knowledge_ids": [int, ...],
                    "is_correct": bool
                },
                ...
            ]
        },
        ...
    ]
    """

    def run(self) -> List[Dict[str, Any]]:
        """Execute batch question-knowledge mapping with TRUE batching (1 AI call for all questions)."""
        data = self.inp or {}

        # Extract inputs
        questions = data.get("questions", [])
        knowledge_nodes = data.get("knowledge_nodes", [])
        ai_provider = data.get("ai_provider")
        ai_model = data.get("ai_model")

        # Validate inputs
        if not questions:
            raise ValueError("At least one question is required")

        if not isinstance(questions, list):
            raise ValueError("'questions' must be a list")

        # Prepare AI config
        cfg = AIConfig()
        if ai_provider:
            cfg.provider = ai_provider
        if ai_model:
            cfg.model = ai_model

        # Prepare questions data (filter out invalid ones)
        valid_questions = []
        question_metadata = []  # Store metadata separately

        for q_data in questions:
            question = q_data.get("question", "")
            choices = q_data.get("choices", [])

            if not question or not isinstance(choices, list) or len(choices) < 2:
                # Skip invalid questions
                continue

            valid_questions.append(
                {
                    "question": question,
                    "choices": [f"{c.get('text', '')}" for c in choices],
                }
            )

            question_metadata.append(q_data)

        if not valid_questions:
            return []

        # Prepare input for TRUE batch AI task (all questions in one prompt)
        batch_input = {
            "questions": valid_questions,
            "knowledge_nodes": knowledge_nodes,
        }

        # Make ONE AI call for ALL questions
        import logging

        logging.getLogger(__name__).info(
            f"Sending {len(valid_questions)} questions in ONE batch AI request"
        )

        result = asyncio.run(invoke("batch_map_questions_knowledge", batch_input, cfg))

        with open("ai_response.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Extract mappings from the single response
        mappings = result.get("mappings", [])

        logging.getLogger(__name__).info(
            f"Received {len(mappings)} mappings from AI in single response"
        )

        # Normalize results
        normalized_results = []
        for mapping in mappings:
            question_index = mapping.get("question_index", 0)

            # question_index is 1-based, convert to 0-based for array access
            array_index = question_index - 1

            metadata = question_metadata[array_index]

            normalized = self._normalize_mapping(
                mapping=mapping,
                question=metadata,
            )
            normalized_results.append(normalized)

        return normalized_results

    def _normalize_mapping(
        self,
        mapping: Dict[str, Any],
        question: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize the AI mapping output with additional metadata.

        Ensures all choices are present with correct structure and metadata.
        """

        output: Dict[str, Any] = {
            "question": question.get("question", ""),
            "question_knowledge_ids": (mapping.get("question_knowledge_ids") or []),
            "choices": [],
        }

        # Process each choice
        for choice, found in zip(
            question.get("choices", []), mapping.get("choices", [])
        ):
            output["choices"].append(
                {
                    "index": choice.get("index", 0),
                    "text": choice.get("text", ""),
                    "knowledge_ids": found.get("knowledge_ids", []) if found else [],
                    "is_correct": choice.get("is_correct", False),
                    "answer_description": choice.get("answer_description", ""),
                }
            )

        return output
