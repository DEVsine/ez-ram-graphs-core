from __future__ import annotations

import json
from typing import Any, Dict, List

from ...schemas import Message
from ..base import AITask


SYSTEM_PROMPT = """You are an expert English language quiz creator. Your task is to create high-quality questions based on knowledge nodes.

Requirements:
1. Create a clear, grammatically correct question
2. Provide exactly 4 answer choices (A, B, C, D)
3. Only ONE choice should be correct
4. Provide detailed explanations for each choice explaining why it's correct or incorrect in Thai language
5. Ensure the question directly relates to the knowledge node
6. Use appropriate difficulty level for English learners
7. Adapt the question format based on the specified style

Question Styles:
- MULTIPLE_CHOICE: Standard comprehension questions with 4 options
- FILL_IN_BLANK: Questions where students complete a sentence (format: "She _____ to school.")
- MISSING_WORD: Questions where students identify missing words (format: "She goes school. What's missing?")

Output STRICT JSON only in this format:
{
  "question": "Your question text here",
  "choices": [
    {
      "letter": "A",
      "text": "Choice A text",
      "is_correct": false,
      "explanation": "Why this choice is incorrect"
    },
    {
      "letter": "B",
      "text": "Choice B text",
      "is_correct": true,
      "explanation": "Why this choice is correct"
    },
    {
      "letter": "C",
      "text": "Choice C text",
      "is_correct": false,
      "explanation": "Why this choice is incorrect"
    },
    {
      "letter": "D",
      "text": "Choice D text",
      "is_correct": false,
      "explanation": "Why this choice is incorrect"
    }
  ]
}

No other text outside the JSON."""


class QuestionGenerationTask:
    name = "generate_question"

    @staticmethod
    def build_messages(inp: Dict[str, Any]) -> List[Message]:
        knowledge_name = inp.get("knowledge_name", "")
        knowledge_description = inp.get("knowledge_description", "")
        knowledge_example = inp.get("knowledge_example", "")
        question_style = inp.get("question_style", "multiple_choice")
        
        # Style-specific instructions
        style_instructions = {
            "multiple_choice": "Create a standard comprehension question with 4 clear options.",
            "fill_in_blank": "Create a sentence with a blank (___) that students must complete. The question should be: 'Complete the sentence: [sentence with blank]'",
            "missing_word": "Create a sentence with a missing word, then ask what word is missing. Format: '[incomplete sentence]. What word is missing?'"
        }

        style_instruction = style_instructions.get(question_style, style_instructions["multiple_choice"])

        user_prompt = f"""Based on the following knowledge node, create ONE high-quality question.

Knowledge Node:
- Name: {knowledge_name}
- Description: {knowledge_description}
- Example: {knowledge_example}

Question Style: {question_style}
Style Instructions: {style_instruction}

Create a question that tests understanding of this knowledge area using the specified style."""

        return [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=user_prompt),
        ]

    @staticmethod
    def parse_output(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        # Validate the structure
        if "question" not in raw_json:
            raise ValueError("Output must contain 'question' field")
        
        if "choices" not in raw_json:
            raise ValueError("Output must contain 'choices' field")
        
        choices = raw_json["choices"]
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError("Must have exactly 4 choices")
        
        # Validate that exactly one choice is correct
        correct_count = sum(1 for choice in choices if choice.get("is_correct", False))
        if correct_count != 1:
            raise ValueError(f"Must have exactly 1 correct answer, found {correct_count}")
        
        # Validate choice structure
        for i, choice in enumerate(choices):
            required_fields = ["letter", "text", "is_correct", "explanation"]
            for field in required_fields:
                if field not in choice:
                    raise ValueError(f"Choice {i+1} missing required field: {field}")
        
        return {
            "question": raw_json["question"],
            "choices": choices,
            "metadata": {
                "question_style": raw_json.get("question_style", "multiple_choice"),
                "validation_passed": True
            }
        }
