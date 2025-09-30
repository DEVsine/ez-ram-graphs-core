import asyncio
import logging
from typing import List, Optional
from knowledge.neo_models import Knowledge
from quiz.models.question_data import QuestionData, QuestionStyle, GenerationRequest, ChoiceData
from ai_module.kernel import invoke
from ai_module.config import AIConfig

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    """Service for AI-powered question generation"""
    
    def __init__(self, ai_config: Optional[AIConfig] = None):
        """Initialize with AI configuration"""
        self.ai_config = ai_config or AIConfig()
        logger.info(f"Initialized QuestionGenerationService with provider: {self.ai_config.provider}")
    
    async def generate_single_question(self, knowledge: Knowledge, style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE) -> QuestionData:
        """Generate a single question for a knowledge node"""
        logger.info(f"Generating question for knowledge: {knowledge.name}")
        
        try:
            # Prepare generation request
            request = GenerationRequest(
                knowledge_name=knowledge.name,
                knowledge_description=knowledge.description or "",
                knowledge_example=knowledge.example or "",
                question_style=style
            )
            
            # Call AI service
            ai_input = request.to_ai_input()
            logger.debug(f"AI input: {ai_input}")
            
            result = await invoke("generate_question", ai_input, self.ai_config)
            logger.debug(f"AI result: {result}")
            
            # Convert to QuestionData
            question_data = QuestionData.from_ai_response(result, style)
            
            logger.info(f"Successfully generated question: {question_data.question[:50]}...")
            return question_data
            
        except Exception as e:
            logger.error(f"Failed to generate question for {knowledge.name}: {e}")
            raise
    
    def generate_single_question_sync(self, knowledge: Knowledge, style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE) -> QuestionData:
        """Synchronous wrapper for generate_single_question"""
        return asyncio.run(self.generate_single_question(knowledge, style))
    
    async def generate_multiple_questions(self, knowledge: Knowledge, count: int, style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE) -> List[QuestionData]:
        """Generate multiple questions for a knowledge node"""
        logger.info(f"Generating {count} questions for knowledge: {knowledge.name}")
        
        questions = []
        for i in range(count):
            try:
                question = await self.generate_single_question(knowledge, style)
                questions.append(question)
                logger.info(f"Generated question {i+1}/{count}")
            except Exception as e:
                logger.error(f"Failed to generate question {i+1}/{count}: {e}")
                # Continue with other questions
                continue
        
        logger.info(f"Successfully generated {len(questions)}/{count} questions")
        return questions
    
    def generate_multiple_questions_sync(self, knowledge: Knowledge, count: int, style: QuestionStyle = QuestionStyle.MULTIPLE_CHOICE) -> List[QuestionData]:
        """Synchronous wrapper for generate_multiple_questions"""
        return asyncio.run(self.generate_multiple_questions(knowledge, count, style))
    
    def validate_ai_config(self) -> bool:
        """Validate AI configuration"""
        try:
            if not self.ai_config.api_key:
                logger.error("No API key configured")
                return False
            
            if self.ai_config.provider not in ["openai", "gemini"]:
                logger.error(f"Unsupported provider: {self.ai_config.provider}")
                return False
            
            logger.info("AI configuration is valid")
            return True
            
        except Exception as e:
            logger.error(f"AI configuration validation failed: {e}")
            return False
    
    def display_question_terminal(self, question: QuestionData) -> None:
        """Display a question in formatted terminal output"""
        print("\n" + "=" * 60)
        print("=== Generated Question ===")
        print("=" * 60)
        print(question.to_display_format())
        print("=" * 60)
    
    def display_questions_summary(self, questions: List[QuestionData]) -> None:
        """Display summary of multiple questions"""
        print(f"\n📊 Generated {len(questions)} questions:")
        print("=" * 50)
        
        for i, question in enumerate(questions, 1):
            correct_choice = question.get_correct_choice()
            print(f"[{i}] {question.question[:60]}...")
            print(f"    Correct Answer: {correct_choice.letter}) {correct_choice.text[:40]}...")
            print()
        
        print("=" * 50)
