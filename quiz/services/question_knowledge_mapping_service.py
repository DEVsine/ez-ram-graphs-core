"""
Service for mapping quiz questions to knowledge nodes using AI.

This service handles the business logic for:
1. Fetching knowledge nodes from Neo4j
2. Using AI to map questions and choices to knowledge nodes
3. Normalizing and validating the mapping results
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ai_module.config import AIConfig
from ai_module.kernel import invoke
from core.services import BaseService, ServiceContext


class QuestionKnowledgeMappingService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """
    Class-based service for mapping quiz questions to knowledge nodes.

    This service is framework-agnostic and uses the ai_module for AI operations.
    It accepts plain dictionaries and returns plain dictionaries.

    Input structure:
    {
        "question": str,
        "choices": [str, ...],
        "correct_answers": [str, ...],  # optional
        "answer_description": str,  # optional
        "knowledge_nodes": [{"id": ..., "name": ...}, ...],  # optional, will fetch if not provided
        "knowledge_labels": [str, ...],  # optional, defaults to ["Knowledge"]
        "knowledge_limit": int,  # optional, defaults to 400
        "ai_provider": str,  # optional, defaults to config
        "ai_model": str,  # optional, defaults to config
    }

    Output structure:
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
    }
    """

    def run(self) -> Dict[str, Any]:
        """Execute the question-knowledge mapping."""
        data = self.inp or {}

        # Extract inputs
        question = data.get("question", "")
        choices = data.get("choices", [])
        correct_answers = data.get("correct_answers") or []
        answer_description = data.get("answer_description")
        knowledge_nodes = data.get("knowledge_nodes")
        knowledge_labels = data.get("knowledge_labels") or ["Knowledge"]
        knowledge_limit = data.get("knowledge_limit", 400)
        ai_provider = data.get("ai_provider")
        ai_model = data.get("ai_model")

        # Validate inputs
        if not question:
            raise ValueError("Question text is required")

        if not isinstance(choices, list) or len(choices) < 2:
            raise ValueError("At least 2 choices are required")

        # Fetch knowledge nodes if not provided
        if knowledge_nodes is None:
            knowledge_nodes = self._fetch_knowledge_nodes(
                labels=knowledge_labels, limit=knowledge_limit
            )

        # Use AI to generate mapping
        mapping = self._generate_mapping(
            question=question,
            choices=choices,
            knowledge_nodes=knowledge_nodes,
            ai_provider=ai_provider,
            ai_model=ai_model,
        )

        # Normalize the mapping with additional metadata
        normalized = self._normalize_mapping(
            mapping=mapping,
            question=question,
            choices=choices,
            correct_answers=correct_answers,
            answer_description=answer_description,
        )

        return normalized

    def _fetch_knowledge_nodes(
        self, labels: List[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch knowledge nodes from Neo4j.

        Returns a list of dicts with 'id' and 'name' keys.
        """
        nodes = []

        try:
            # Import here to avoid circular import
            from knowledge.neo_models import Knowledge

            # Query all Knowledge nodes
            for knowledge in Knowledge.nodes.all()[:limit]:
                node_id = knowledge.element_id
                node_name = getattr(knowledge, "name", "")

                if node_id and node_name:
                    # Extract numeric ID from Neo4j element_id format
                    numeric_id = self._extract_numeric_id(node_id)
                    if numeric_id is not None:
                        nodes.append(
                            {"id": numeric_id, "element_id": node_id, "name": node_name}
                        )
        except Exception as e:
            # Log but don't fail - return empty list
            import logging

            logging.getLogger(__name__).warning(f"Failed to fetch knowledge nodes: {e}")

        return nodes

    def _extract_numeric_id(self, element_id: str) -> Optional[int]:
        """
        Extract numeric ID from Neo4j element_id format.

        Format: "4:uuid:numeric_id"
        """
        if not isinstance(element_id, str):
            return None

        parts = element_id.split(":")
        if len(parts) >= 3:
            try:
                return int(parts[-1])
            except (ValueError, IndexError):
                pass

        return None

    def _generate_mapping(
        self,
        question: str,
        choices: List[str],
        knowledge_nodes: List[Dict[str, Any]],
        ai_provider: Optional[str] = None,
        ai_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use AI to generate question-knowledge mapping.

        Returns the raw mapping from the AI task.
        """
        # Prepare AI config
        cfg = AIConfig()
        if ai_provider:
            cfg.provider = ai_provider
        if ai_model:
            cfg.model = ai_model

        # Prepare input for AI task
        task_input = {
            "question": question,
            "choices": choices,
            "knowledge_nodes": knowledge_nodes,
        }

        # Invoke AI task
        try:
            result = asyncio.run(invoke("map_question_knowledge", task_input, cfg))
            return result
        except Exception as e:
            # Log and return empty mapping
            import logging

            logging.getLogger(__name__).error(f"AI mapping failed: {e}")
            return {"question_knowledge_ids": [], "choices": []}

    def _normalize_mapping(
        self,
        mapping: Dict[str, Any],
        question: str,
        choices: List[str],
        correct_answers: List[str],
        answer_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalize the AI mapping output with additional metadata.

        Ensures all choices are present with correct structure and metadata.
        """
        correct_set = set(correct_answers or [])

        output: Dict[str, Any] = {
            "question": question,
            "answer_description": answer_description,
            "question_knowledge_ids": [
                int(x) for x in (mapping.get("question_knowledge_ids") or [])
            ],
            "choices": [],
        }

        # Process each choice
        for i, choice_text in enumerate(choices, start=1):
            # Find matching choice from AI mapping
            found = next(
                (c for c in mapping.get("choices", []) if c.get("index") == i), None
            )

            output["choices"].append(
                {
                    "index": i,
                    "text": choice_text,
                    "knowledge_ids": [
                        int(x)
                        for x in (found.get("knowledge_ids", []) if found else [])
                    ],
                    "is_correct": choice_text in correct_set,
                }
            )

        return output
