"""
AI Task for mapping quiz questions and choices to knowledge nodes.

This task takes a question, its choices, and a list of knowledge nodes,
then returns a structured mapping indicating which knowledge nodes are
relevant to the question and each choice.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM = (
    "You are a knowledge mapping assistant for educational quizzes.\n"
    "Given a quiz question, its answer choices, and a list of knowledge nodes, "
    "identify which knowledge nodes are relevant to:\n"
    "1. The question itself (question_knowledge_ids)\n"
    "2. Each individual choice (choices[].knowledge_ids)\n\n"
    "Return STRICT JSON only with this structure:\n"
    "{\n"
    '  "question_knowledge_ids": [list of integer IDs],\n'
    '  "choices": [\n'
    '    {"index": 1, "knowledge_ids": [list of integer IDs]},\n'
    '    {"index": 2, "knowledge_ids": [list of integer IDs]},\n'
    "    ...\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Use only IDs from the provided knowledge nodes list\n"
    "- question_knowledge_ids should contain knowledge relevant to understanding the question\n"
    "- Each choice's knowledge_ids should contain knowledge that explains why that choice is correct or incorrect\n"
    "- Return empty arrays if no relevant knowledge is found\n"
    "- Do not include explanations or rationale in the output"
)


class MapQuestionKnowledgeTask:
    """Task for mapping quiz questions to knowledge nodes using AI."""
    
    name = "map_question_knowledge"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        """
        Build messages for the AI provider.
        
        Expected input:
        {
            "question": "Question text",
            "choices": ["choice1", "choice2", ...],
            "knowledge_nodes": [{"id": 123, "name": "..."}, ...]
        }
        """
        question = inp.get("question", "")
        choices = inp.get("choices", [])
        knowledge_nodes = inp.get("knowledge_nodes", [])
        
        # Format knowledge nodes for the prompt
        knowledge_list = []
        for node in knowledge_nodes:
            node_id = node.get("id") or node.get("element_id")
            node_name = node.get("name", "")
            if node_id and node_name:
                # Extract numeric ID if it's a Neo4j element_id format
                if isinstance(node_id, str) and ":" in node_id:
                    # Format: "4:uuid:numeric_id"
                    parts = node_id.split(":")
                    if len(parts) >= 3:
                        try:
                            node_id = int(parts[-1])
                        except (ValueError, IndexError):
                            continue
                knowledge_list.append(f"ID {node_id}: {node_name}")
        
        knowledge_text = "\n".join(knowledge_list) if knowledge_list else "No knowledge nodes provided"
        
        # Format choices
        choices_text = "\n".join([f"{i+1}. {choice}" for i, choice in enumerate(choices)])
        
        user_content = (
            f"Question: {question}\n\n"
            f"Choices:\n{choices_text}\n\n"
            f"Available Knowledge Nodes:\n{knowledge_text}"
        )
        
        return [
            Message(role="system", content=SYSTEM),
            Message(role="user", content=user_content),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate the AI output.
        
        Expected output:
        {
            "question_knowledge_ids": [int, ...],
            "choices": [
                {"index": int, "knowledge_ids": [int, ...]},
                ...
            ]
        }
        """
        # Validate structure
        if "question_knowledge_ids" not in raw_json:
            raise ValueError("Output must contain 'question_knowledge_ids'")
        
        if "choices" not in raw_json:
            raise ValueError("Output must contain 'choices'")
        
        question_ids = raw_json.get("question_knowledge_ids", [])
        if not isinstance(question_ids, list):
            raise ValueError("'question_knowledge_ids' must be a list")
        
        choices = raw_json.get("choices", [])
        if not isinstance(choices, list):
            raise ValueError("'choices' must be a list")
        
        # Validate and normalize each choice
        normalized_choices = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            
            index = choice.get("index")
            knowledge_ids = choice.get("knowledge_ids", [])
            
            if not isinstance(index, int):
                continue
            
            if not isinstance(knowledge_ids, list):
                knowledge_ids = []
            
            normalized_choices.append({
                "index": index,
                "knowledge_ids": [int(kid) for kid in knowledge_ids if isinstance(kid, (int, str))]
            })
        
        return {
            "question_knowledge_ids": [int(qid) for qid in question_ids if isinstance(qid, (int, str))],
            "choices": normalized_choices,
        }

