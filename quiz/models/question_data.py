from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class QuestionStyle(Enum):
    """Enumeration of supported question styles"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    MISSING_WORD = "missing_word"


@dataclass
class ChoiceData:
    """Data class for a single choice in a question"""
    letter: str
    text: str
    is_correct: bool
    explanation: str
    
    def __post_init__(self):
        """Validate choice data after initialization"""
        if not self.letter or self.letter not in ['A', 'B', 'C', 'D']:
            raise ValueError(f"Invalid choice letter: {self.letter}")
        
        if not self.text or not self.text.strip():
            raise ValueError("Choice text cannot be empty")
        
        if not self.explanation or not self.explanation.strip():
            raise ValueError("Choice explanation cannot be empty")


@dataclass
class QuestionData:
    """Data class for a complete question with choices"""
    question: str
    choices: List[ChoiceData]
    style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """Validate question data after initialization"""
        if not self.question or not self.question.strip():
            raise ValueError("Question text cannot be empty")
        
        if len(self.choices) != 4:
            raise ValueError(f"Must have exactly 4 choices, got {len(self.choices)}")
        
        # Validate exactly one correct answer
        correct_count = sum(1 for choice in self.choices if choice.is_correct)
        if correct_count != 1:
            raise ValueError(f"Must have exactly 1 correct answer, found {correct_count}")
        
        # Validate choice letters are A, B, C, D
        expected_letters = ['A', 'B', 'C', 'D']
        actual_letters = [choice.letter for choice in self.choices]
        if sorted(actual_letters) != sorted(expected_letters):
            raise ValueError(f"Choices must have letters A, B, C, D. Got: {actual_letters}")
    
    @classmethod
    def from_ai_response(cls, ai_response: dict, style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE) -> 'QuestionData':
        """Create QuestionData from AI response"""
        choices = []
        for choice_data in ai_response.get("choices", []):
            choice = ChoiceData(
                letter=choice_data["letter"],
                text=choice_data["text"],
                is_correct=choice_data["is_correct"],
                explanation=choice_data["explanation"]
            )
            choices.append(choice)
        
        return cls(
            question=ai_response["question"],
            choices=choices,
            style=style,
            metadata=ai_response.get("metadata", {})
        )
    
    def get_correct_choice(self) -> ChoiceData:
        """Get the correct choice"""
        for choice in self.choices:
            if choice.is_correct:
                return choice
        raise ValueError("No correct choice found")
    
    def get_incorrect_choices(self) -> List[ChoiceData]:
        """Get all incorrect choices"""
        return [choice for choice in self.choices if not choice.is_correct]
    
    def to_display_format(self) -> str:
        """Format question for terminal display"""
        lines = [f"Q: {self.question}", ""]
        
        for choice in self.choices:
            status = "✅" if choice.is_correct else "❌"
            lines.append(f"{choice.letter}) {choice.text} [{status}]")
            lines.append(f"   Explanation: {choice.explanation}")
            lines.append("")
        
        return "\n".join(lines)


@dataclass
class GenerationRequest:
    """Data class for question generation requests"""
    knowledge_name: str
    knowledge_description: str
    knowledge_example: str
    question_style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE
    count: int = 1
    
    def to_ai_input(self) -> dict:
        """Convert to AI task input format"""
        return {
            "knowledge_name": self.knowledge_name,
            "knowledge_description": self.knowledge_description,
            "knowledge_example": self.knowledge_example,
            "question_style": self.question_style.value
        }
