import asyncio
import time
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from knowledge.neo_models import Knowledge
from quiz.models.question_data import QuestionData, QuestionStyle
from quiz.services.generation_service import QuestionGenerationService
from ai_module.config import AIConfig

logger = logging.getLogger(__name__)


@dataclass
class GenerationProgress:
    """Track progress of bulk generation"""
    total: int
    completed: int
    failed: int
    current_question: Optional[str] = None
    start_time: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        if self.completed + self.failed == 0:
            return 0.0
        return self.completed / (self.completed + self.failed)
    
    @property
    def elapsed_time(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    @property
    def avg_time_per_question(self) -> float:
        if self.completed == 0:
            return 0.0
        return self.elapsed_time / self.completed
    
    @property
    def estimated_remaining_time(self) -> float:
        if self.completed == 0:
            return 0.0
        remaining = self.total - self.completed
        return remaining * self.avg_time_per_question


@dataclass
class BulkGenerationResult:
    """Result of bulk generation process"""
    questions: List[QuestionData]
    total_requested: int
    total_generated: int
    total_failed: int
    generation_time: float
    knowledge_node: str
    question_style: str
    errors: List[str]
    
    @property
    def success_rate(self) -> float:
        if self.total_requested == 0:
            return 0.0
        return self.total_generated / self.total_requested
    
    @property
    def avg_time_per_question(self) -> float:
        if self.total_generated == 0:
            return 0.0
        return self.generation_time / self.total_generated


class BulkGenerationService:
    """Service for generating multiple questions with progress tracking"""
    
    def __init__(self, ai_config: Optional[AIConfig] = None, max_retries: int = 3):
        """Initialize bulk generation service"""
        self.generation_service = QuestionGenerationService(ai_config)
        self.max_retries = max_retries
        self.progress = GenerationProgress(0, 0, 0)
        
    def generate_bulk_questions(
        self, 
        knowledge: Knowledge, 
        count: int, 
        style: QuestionStyle,
        progress_callback: Optional[callable] = None
    ) -> BulkGenerationResult:
        """Generate multiple questions with progress tracking"""
        logger.info(f"Starting bulk generation: {count} questions for {knowledge.name}")
        
        # Initialize progress tracking
        self.progress = GenerationProgress(
            total=count,
            completed=0,
            failed=0,
            start_time=time.time()
        )
        
        questions = []
        errors = []
        
        for i in range(count):
            question_num = i + 1
            self.progress.current_question = f"Question {question_num}/{count}"
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(self.progress)
            
            # Generate single question with retries
            question, error = self._generate_with_retries(knowledge, style, question_num)
            
            if question:
                questions.append(question)
                self.progress.completed += 1
                logger.info(f"Generated question {question_num}/{count}")
            else:
                self.progress.failed += 1
                errors.append(f"Question {question_num}: {error}")
                logger.error(f"Failed to generate question {question_num}: {error}")
        
        # Final progress update
        if progress_callback:
            progress_callback(self.progress)
        
        # Create result
        result = BulkGenerationResult(
            questions=questions,
            total_requested=count,
            total_generated=len(questions),
            total_failed=self.progress.failed,
            generation_time=self.progress.elapsed_time,
            knowledge_node=knowledge.name,
            question_style=style.value,
            errors=errors
        )
        
        logger.info(f"Bulk generation completed: {result.total_generated}/{result.total_requested} questions")
        return result
    
    def _generate_with_retries(
        self, 
        knowledge: Knowledge, 
        style: QuestionStyle, 
        question_num: int
    ) -> Tuple[Optional[QuestionData], Optional[str]]:
        """Generate a single question with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                question = self.generation_service.generate_single_question_sync(knowledge, style)
                return question, None
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Question {question_num} attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        return None, last_error
    
    def display_progress_bar(self, progress: GenerationProgress) -> None:
        """Display a progress bar in terminal"""
        if progress.total == 0:
            return
        
        percentage = (progress.completed + progress.failed) / progress.total
        bar_length = 40
        filled_length = int(bar_length * percentage)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r🤖 {progress.current_question or 'Generating'}: [{bar}] "
              f"{progress.completed + progress.failed}/{progress.total} "
              f"({percentage:.1%}) - "
              f"✅ {progress.completed} ❌ {progress.failed}", end='', flush=True)
    
    def display_generation_summary(self, result: BulkGenerationResult) -> None:
        """Display detailed generation summary"""
        print("\n\n" + "=" * 60)
        print("=== Bulk Generation Summary ===")
        print("=" * 60)
        print(f"Knowledge Node: {result.knowledge_node}")
        print(f"Question Style: {result.question_style.replace('_', ' ').title()}")
        print(f"Requested: {result.total_requested} questions")
        print(f"Generated: {result.total_generated} questions")
        print(f"Failed: {result.total_failed} questions")
        print(f"Success Rate: {result.success_rate:.1%}")
        print(f"Total Time: {result.generation_time:.1f} seconds")
        print(f"Avg Time/Question: {result.avg_time_per_question:.1f} seconds")
        
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
            if len(result.errors) > 5:
                print(f"  • ... and {len(result.errors) - 5} more errors")
        
        print("=" * 60)
    
    def display_questions_preview(self, questions: List[QuestionData], max_display: int = 3) -> None:
        """Display a preview of generated questions"""
        if not questions:
            print("\n❌ No questions to display")
            return
        
        print(f"\n📋 Generated Questions Preview (showing {min(len(questions), max_display)}/{len(questions)}):")
        print("=" * 60)
        
        for i, question in enumerate(questions[:max_display], 1):
            correct_choice = question.get_correct_choice()
            print(f"\n[{i}] {question.question}")
            print(f"    Style: {question.style.value}")
            print(f"    Correct: {correct_choice.letter}) {correct_choice.text}")
            
            if i < min(len(questions), max_display):
                print("-" * 40)
        
        if len(questions) > max_display:
            print(f"\n... and {len(questions) - max_display} more questions")
        
        print("=" * 60)
