import asyncio
import time
import logging
from typing import List, Optional, Callable
from knowledge.neo_models import Knowledge
from quiz.models.question_data import QuestionData
from quiz.models.validation_data import ValidationResult, BatchValidationResult
from ai_module.config import AIConfig
from ai_module.providers.base import AIProvider
from ai_module.providers.openai import OpenAIProvider
from ai_module.providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating questions using Expert English AI"""
    
    def __init__(self, ai_config: Optional[AIConfig] = None):
        """Initialize validation service"""
        self.ai_config = ai_config or AIConfig()
        self.provider = self._get_provider()
        
    def _get_provider(self) -> AIProvider:
        """Get AI provider based on configuration"""
        if self.ai_config.provider == "openai":
            return OpenAIProvider(self.ai_config)
        elif self.ai_config.provider == "gemini":
            return GeminiProvider(self.ai_config)
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_config.provider}")
    
    def validate_single_question_sync(
        self, 
        question: QuestionData, 
        knowledge: Knowledge
    ) -> ValidationResult:
        """Validate a single question synchronously"""
        try:
            # Prepare input for AI task
            task_input = {
                "question_data": {
                    "question": question.question,
                    "choices": [
                        {
                            "letter": choice.letter,
                            "text": choice.text,
                            "is_correct": choice.is_correct,
                            "explanation": choice.explanation
                        }
                        for choice in question.choices
                    ]
                },
                "knowledge_name": knowledge.name,
                "knowledge_description": knowledge.description
            }
            
            # Call AI validation task
            result = self.provider.run_task_sync("validate_question", task_input)
            
            # Create validation result
            validation_result = ValidationResult.from_ai_response(result, question.question)
            
            logger.info(f"Validated question with score: {validation_result.overall_score:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Question validation failed: {e}")
            # Return a failed validation result
            from quiz.models.validation_data import ValidationDetails, ValidationIssue, ValidationIssueType, ValidationSeverity
            
            failed_details = ValidationDetails(
                spelling_grammar_score=0.0,
                single_correct_answer=False,
                explanation_quality_score=0.0,
                knowledge_relevance_score=0.0,
                clarity_score=0.0
            )
            
            error_issue = ValidationIssue(
                type=ValidationIssueType.LOGIC,
                severity=ValidationSeverity.HIGH,
                description=f"Validation failed: {str(e)}",
                suggestion="Please check the question format and try again"
            )
            
            return ValidationResult(
                overall_score=0.0,
                is_valid=False,
                validation_details=failed_details,
                issues=[error_issue],
                recommendations=["Question needs manual review due to validation error"],
                question_text=question.question
            )
    
    async def validate_single_question_async(
        self, 
        question: QuestionData, 
        knowledge: Knowledge
    ) -> ValidationResult:
        """Validate a single question asynchronously"""
        try:
            # Prepare input for AI task
            task_input = {
                "question_data": {
                    "question": question.question,
                    "choices": [
                        {
                            "letter": choice.letter,
                            "text": choice.text,
                            "is_correct": choice.is_correct,
                            "explanation": choice.explanation
                        }
                        for choice in question.choices
                    ]
                },
                "knowledge_name": knowledge.name,
                "knowledge_description": knowledge.description
            }
            
            # Call AI validation task
            result = await self.provider.run_task("validate_question", task_input)
            
            # Create validation result
            validation_result = ValidationResult.from_ai_response(result, question.question)
            
            logger.info(f"Validated question with score: {validation_result.overall_score:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Question validation failed: {e}")
            # Return a failed validation result (same as sync version)
            from quiz.models.validation_data import ValidationDetails, ValidationIssue, ValidationIssueType, ValidationSeverity
            
            failed_details = ValidationDetails(
                spelling_grammar_score=0.0,
                single_correct_answer=False,
                explanation_quality_score=0.0,
                knowledge_relevance_score=0.0,
                clarity_score=0.0
            )
            
            error_issue = ValidationIssue(
                type=ValidationIssueType.LOGIC,
                severity=ValidationSeverity.HIGH,
                description=f"Validation failed: {str(e)}",
                suggestion="Please check the question format and try again"
            )
            
            return ValidationResult(
                overall_score=0.0,
                is_valid=False,
                validation_details=failed_details,
                issues=[error_issue],
                recommendations=["Question needs manual review due to validation error"],
                question_text=question.question
            )
    
    def validate_multiple_questions_sync(
        self, 
        questions: List[QuestionData], 
        knowledge: Knowledge,
        progress_callback: Optional[Callable] = None
    ) -> BatchValidationResult:
        """Validate multiple questions synchronously with progress tracking"""
        logger.info(f"Starting validation of {len(questions)} questions")
        
        results = []
        start_time = time.time()
        
        for i, question in enumerate(questions):
            # Update progress
            if progress_callback:
                progress_callback(i + 1, len(questions), question.question[:50] + "...")
            
            # Validate question
            result = self.validate_single_question_sync(question, knowledge)
            results.append(result)
            
            logger.info(f"Validated question {i + 1}/{len(questions)}: {result.overall_score:.2f}")
        
        # Final progress update
        if progress_callback:
            progress_callback(len(questions), len(questions), "Validation complete")
        
        # Create batch result
        batch_result = BatchValidationResult.from_results(results)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Batch validation completed in {elapsed_time:.1f}s. Average score: {batch_result.average_score:.2f}")
        
        return batch_result
    
    async def validate_multiple_questions_async(
        self, 
        questions: List[QuestionData], 
        knowledge: Knowledge,
        progress_callback: Optional[Callable] = None,
        max_concurrent: int = 3
    ) -> BatchValidationResult:
        """Validate multiple questions asynchronously with concurrency control"""
        logger.info(f"Starting async validation of {len(questions)} questions")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        completed = 0
        
        async def validate_with_semaphore(question: QuestionData) -> ValidationResult:
            nonlocal completed
            async with semaphore:
                result = await self.validate_single_question_async(question, knowledge)
                completed += 1
                
                # Update progress
                if progress_callback:
                    progress_callback(completed, len(questions), question.question[:50] + "...")
                
                return result
        
        # Create tasks for all questions
        tasks = [validate_with_semaphore(question) for question in questions]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to ValidationResult
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Question {i + 1} validation failed: {result}")
                # Create a failed validation result
                from quiz.models.validation_data import ValidationDetails, ValidationIssue, ValidationIssueType, ValidationSeverity
                
                failed_details = ValidationDetails(
                    spelling_grammar_score=0.0,
                    single_correct_answer=False,
                    explanation_quality_score=0.0,
                    knowledge_relevance_score=0.0,
                    clarity_score=0.0
                )
                
                error_issue = ValidationIssue(
                    type=ValidationIssueType.LOGIC,
                    severity=ValidationSeverity.HIGH,
                    description=f"Async validation failed: {str(result)}",
                    suggestion="Please check the question format and try again"
                )
                
                failed_result = ValidationResult(
                    overall_score=0.0,
                    is_valid=False,
                    validation_details=failed_details,
                    issues=[error_issue],
                    recommendations=["Question needs manual review due to validation error"],
                    question_text=questions[i].question if i < len(questions) else "Unknown question"
                )
                valid_results.append(failed_result)
            else:
                valid_results.append(result)
        
        # Final progress update
        if progress_callback:
            progress_callback(len(questions), len(questions), "Validation complete")
        
        # Create batch result
        batch_result = BatchValidationResult.from_results(valid_results)
        
        logger.info(f"Async batch validation completed. Average score: {batch_result.average_score:.2f}")
        
        return batch_result
    
    def display_validation_progress(self, current: int, total: int, current_question: str = "") -> None:
        """Display validation progress bar"""
        if total == 0:
            return
        
        percentage = current / total
        bar_length = 40
        filled_length = int(bar_length * percentage)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r🔍 Validating: [{bar}] {current}/{total} ({percentage:.1%}) - {current_question[:30]}...", 
              end='', flush=True)
    
    def display_batch_summary(self, batch_result: BatchValidationResult) -> None:
        """Display batch validation summary"""
        print("\n\n" + "=" * 60)
        print("=== Validation Summary ===")
        print("=" * 60)
        print(f"Total Questions: {batch_result.total_questions}")
        print(f"Average Score: {batch_result.average_score:.2f}/1.0")
        print(f"High Quality (≥0.9): {batch_result.high_quality_count} questions")
        print(f"Medium Quality (0.7-0.9): {batch_result.medium_quality_count} questions")
        print(f"Low Quality (<0.7): {batch_result.low_quality_count} questions")
        print(f"Total Issues Found: {batch_result.total_issues}")
        print(f"Total Recommendations: {batch_result.total_recommendations}")
        print("=" * 60)
