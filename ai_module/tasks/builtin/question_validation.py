from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


VALIDATION_SYSTEM_PROMPT = """You are an expert English language teacher and quiz validator. Your task is to thoroughly review quiz questions for quality and correctness.

You must validate these aspects:
1. SPELLING & GRAMMAR: Check for any spelling or grammatical errors
2. SINGLE CORRECT ANSWER: Verify exactly one choice is correct
3. EXPLANATION QUALITY: Ensure explanations are accurate and helpful
4. KNOWLEDGE RELEVANCE: Confirm question relates to the knowledge node
5. CLARITY: Check if question and choices are clear and unambiguous

Scoring: Use 0.0 to 1.0 scale (1.0 = perfect, 0.0 = completely wrong)

Output STRICT JSON only in this format:
{
  "overall_score": 0.95,
  "is_valid": true,
  "validation_details": {
    "spelling_grammar_score": 0.9,
    "single_correct_answer": true,
    "explanation_quality_score": 0.95,
    "knowledge_relevance_score": 1.0,
    "clarity_score": 0.9
  },
  "issues": [
    {
      "type": "spelling|grammar|logic|clarity",
      "severity": "low|medium|high",
      "description": "Specific issue description",
      "suggestion": "How to fix it"
    }
  ],
  "recommendations": [
    "Specific recommendation for improvement"
  ]
}

No other text outside the JSON."""


class QuestionValidationTask:
    name = "validate_question"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        question_data = inp.get("question_data", {})
        knowledge_name = inp.get("knowledge_name", "")
        knowledge_description = inp.get("knowledge_description", "")
        
        # Format the question for validation
        question_text = question_data.get("question", "")
        choices = question_data.get("choices", [])
        
        choices_text = ""
        for choice in choices:
            status = "CORRECT" if choice.get("is_correct", False) else "INCORRECT"
            choices_text += f"{choice.get('letter', '')}) {choice.get('text', '')} [{status}]\n"
            choices_text += f"   Explanation: {choice.get('explanation', '')}\n\n"
        
        user_prompt = f"""Please validate this quiz question thoroughly.

Original Knowledge Node:
- Name: {knowledge_name}
- Description: {knowledge_description}

Question to Validate:
Q: {question_text}

{choices_text}

Please check all validation criteria and provide detailed feedback."""

        return [
            Message(role="system", content=VALIDATION_SYSTEM_PROMPT),
            Message(role="user", content=user_prompt),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        # Validate required fields
        required_fields = ["overall_score", "is_valid", "validation_details"]
        for field in required_fields:
            if field not in raw_json:
                raise ValueError(f"Output must contain '{field}' field")
        
        # Validate overall_score range
        overall_score = raw_json["overall_score"]
        if not isinstance(overall_score, (int, float)) or not (0.0 <= overall_score <= 1.0):
            raise ValueError("overall_score must be a number between 0.0 and 1.0")
        
        # Validate validation_details structure
        details = raw_json["validation_details"]
        required_detail_fields = [
            "spelling_grammar_score", "single_correct_answer", 
            "explanation_quality_score", "knowledge_relevance_score", "clarity_score"
        ]
        
        for field in required_detail_fields:
            if field not in details:
                raise ValueError(f"validation_details must contain '{field}' field")
        
        # Validate score ranges
        score_fields = ["spelling_grammar_score", "explanation_quality_score", 
                       "knowledge_relevance_score", "clarity_score"]
        for field in score_fields:
            score = details[field]
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError(f"{field} must be a number between 0.0 and 1.0")
        
        # Validate single_correct_answer is boolean
        if not isinstance(details["single_correct_answer"], bool):
            raise ValueError("single_correct_answer must be a boolean")
        
        return {
            "overall_score": overall_score,
            "is_valid": raw_json["is_valid"],
            "validation_details": details,
            "issues": raw_json.get("issues", []),
            "recommendations": raw_json.get("recommendations", [])
        }
