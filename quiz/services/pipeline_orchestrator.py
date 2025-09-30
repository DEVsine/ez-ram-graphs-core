import time
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from knowledge.neo_models import Knowledge
from knowledge.services.query_service import KnowledgeQueryService
from quiz.models.question_data import QuestionData, QuestionStyle
from quiz.models.validation_data import BatchValidationResult
from quiz.services.bulk_generation_service import BulkGenerationService, BulkGenerationResult
from quiz.services.validation_service import ValidationService
from quiz.services.terminal_interface import TerminalInterface
from quiz.services.neo4j_persistence_service import Neo4jPersistenceService
from ai_module.config import AIConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineProgress:
    """Track overall pipeline progress"""
    current_step: int
    total_steps: int
    step_name: str
    step_progress: float = 0.0
    
    @property
    def overall_progress(self) -> float:
        """Calculate overall pipeline progress"""
        if self.total_steps == 0:
            return 0.0
        
        completed_steps = self.current_step - 1
        current_step_progress = self.step_progress
        
        return (completed_steps + current_step_progress) / self.total_steps


@dataclass
class PipelineResult:
    """Complete pipeline execution result"""
    knowledge_node: Knowledge
    question_style: QuestionStyle
    questions_requested: int
    generation_result: BulkGenerationResult
    validation_result: BatchValidationResult
    pipeline_time: float
    success: bool
    error_message: Optional[str] = None
    saved_to_neo4j: bool = False
    neo4j_session_id: Optional[str] = None
    saved_quiz_count: int = 0
    
    @property
    def questions_generated(self) -> int:
        return len(self.generation_result.questions)
    
    @property
    def questions_validated(self) -> int:
        return len(self.validation_result.results)
    
    @property
    def average_validation_score(self) -> float:
        return self.validation_result.average_score
    
    @property
    def high_quality_questions(self) -> int:
        return self.validation_result.high_quality_count


class QuestionPipelineOrchestrator:
    """Orchestrates the complete question management pipeline"""
    
    def __init__(self, ai_config: Optional[AIConfig] = None):
        """Initialize pipeline orchestrator"""
        self.ai_config = ai_config or AIConfig()
        
        # Initialize services
        self.knowledge_service = KnowledgeQueryService()
        self.bulk_service = BulkGenerationService(ai_config)
        self.validation_service = ValidationService(ai_config)
        self.terminal_interface = TerminalInterface()
        self.persistence_service = Neo4jPersistenceService()
        
        # Pipeline configuration
        self.total_steps = 5
        self.current_progress = PipelineProgress(0, self.total_steps, "Initializing")
    
    def run_complete_pipeline(
        self,
        knowledge_id: Optional[str] = None,
        style: Optional[QuestionStyle] = None,
        count: int = 10,
        auto_mode: bool = False,
        progress_callback: Optional[callable] = None
    ) -> PipelineResult:
        """Run the complete question management pipeline"""
        logger.info("Starting complete question management pipeline")
        start_time = time.time()
        
        try:
            # Step 1: Knowledge Node Selection
            self._update_progress(1, "Knowledge Node Selection", 0.0, progress_callback)
            selected_knowledge = self._step_1_select_knowledge(knowledge_id, auto_mode)
            self._update_progress(1, "Knowledge Node Selection", 1.0, progress_callback)
            
            # Step 2: Question Style Selection
            self._update_progress(2, "Question Style Selection", 0.0, progress_callback)
            selected_style = self._step_2_select_style(style, auto_mode)
            self._update_progress(2, "Question Style Selection", 1.0, progress_callback)
            
            # Step 3: Question Generation
            self._update_progress(3, "Question Generation", 0.0, progress_callback)
            generation_result = self._step_3_generate_questions(
                selected_knowledge, selected_style, count, progress_callback
            )
            self._update_progress(3, "Question Generation", 1.0, progress_callback)
            
            # Step 4: Question Validation
            self._update_progress(4, "Question Validation", 0.0, progress_callback)
            validation_result = self._step_4_validate_questions(
                generation_result.questions, selected_knowledge, progress_callback
            )
            self._update_progress(4, "Question Validation", 1.0, progress_callback)
            
            # Step 5: Results Review and Neo4j Persistence
            self._update_progress(5, "Results Review", 0.0, progress_callback)
            neo4j_result = self._step_5_review_results(
                selected_knowledge, generation_result, validation_result, auto_mode
            )
            self._update_progress(5, "Results Review", 1.0, progress_callback)
            
            # Create final result
            pipeline_time = time.time() - start_time
            result = PipelineResult(
                knowledge_node=selected_knowledge,
                question_style=selected_style,
                questions_requested=count,
                generation_result=generation_result,
                validation_result=validation_result,
                pipeline_time=pipeline_time,
                success=True,
                saved_to_neo4j=neo4j_result.get('saved', False),
                neo4j_session_id=neo4j_result.get('session_id'),
                saved_quiz_count=neo4j_result.get('saved_count', 0)
            )
            
            logger.info(f"Pipeline completed successfully in {pipeline_time:.1f}s")
            return result
            
        except Exception as e:
            pipeline_time = time.time() - start_time
            logger.error(f"Pipeline failed: {e}")
            
            # Create error result
            from quiz.models.validation_data import BatchValidationResult
            empty_generation = BulkGenerationResult([], 0, 0, 0, 0.0, "", "", [])
            empty_validation = BatchValidationResult([], 0, 0.0, 0, 0, 0, 0, 0)
            
            return PipelineResult(
                knowledge_node=None,
                question_style=QuestionStyle.MULTIPLE_CHOICE,
                questions_requested=count,
                generation_result=empty_generation,
                validation_result=empty_validation,
                pipeline_time=pipeline_time,
                success=False,
                error_message=str(e),
                saved_to_neo4j=False,
                neo4j_session_id=None,
                saved_quiz_count=0
            )
    
    def _update_progress(
        self, 
        step: int, 
        step_name: str, 
        step_progress: float, 
        callback: Optional[callable]
    ) -> None:
        """Update pipeline progress"""
        self.current_progress = PipelineProgress(step, self.total_steps, step_name, step_progress)
        
        if callback:
            callback(self.current_progress)
    
    def _step_1_select_knowledge(
        self, 
        knowledge_id: Optional[str], 
        auto_mode: bool
    ) -> Knowledge:
        """Step 1: Select knowledge node"""
        logger.info("Step 1: Knowledge node selection")
        
        # Get all knowledge nodes
        nodes = self.knowledge_service.list_all_knowledge_nodes()
        if not nodes:
            raise ValueError("No knowledge nodes found in database")
        
        # Select knowledge node
        if knowledge_id:
            # Pre-selected by ID
            for node in nodes:
                if node.name.lower() == knowledge_id.lower():
                    logger.info(f"Pre-selected knowledge: {node.name}")
                    return node
            raise ValueError(f"Knowledge node '{knowledge_id}' not found")
        
        elif auto_mode:
            # Auto-select first node
            selected = nodes[0]
            logger.info(f"Auto-selected knowledge: {selected.name}")
            return selected
        
        else:
            # Interactive selection
            self.knowledge_service.display_knowledge_terminal(nodes)
            selected = self.knowledge_service.get_user_selection(nodes)
            if not selected:
                raise ValueError("No knowledge node selected")
            return selected
    
    def _step_2_select_style(
        self, 
        style: Optional[QuestionStyle], 
        auto_mode: bool
    ) -> QuestionStyle:
        """Step 2: Select question style"""
        logger.info("Step 2: Question style selection")
        
        if style:
            # Pre-selected style
            logger.info(f"Pre-selected style: {style.value}")
            return style
        
        elif auto_mode:
            # Auto-select multiple choice
            selected = QuestionStyle.MULTIPLE_CHOICE
            logger.info(f"Auto-selected style: {selected.value}")
            return selected
        
        else:
            # Interactive selection
            selected = self.terminal_interface.get_question_style_selection()
            if not selected:
                raise ValueError("No question style selected")
            return selected
    
    def _step_3_generate_questions(
        self, 
        knowledge: Knowledge, 
        style: QuestionStyle, 
        count: int,
        progress_callback: Optional[callable]
    ) -> BulkGenerationResult:
        """Step 3: Generate questions"""
        logger.info(f"Step 3: Generating {count} questions")
        
        def generation_progress(progress):
            # Convert generation progress to pipeline progress
            step_progress = (progress.completed + progress.failed) / progress.total
            if progress_callback:
                self._update_progress(3, "Question Generation", step_progress, progress_callback)
        
        result = self.bulk_service.generate_bulk_questions(
            knowledge, count, style, generation_progress
        )
        
        if result.total_generated == 0:
            raise ValueError("Failed to generate any questions")
        
        return result
    
    def _step_4_validate_questions(
        self, 
        questions: List[QuestionData], 
        knowledge: Knowledge,
        progress_callback: Optional[callable]
    ) -> BatchValidationResult:
        """Step 4: Validate questions"""
        logger.info(f"Step 4: Validating {len(questions)} questions")
        
        def validation_progress(current, total, current_question):
            # Convert validation progress to pipeline progress
            step_progress = current / total if total > 0 else 0.0
            if progress_callback:
                self._update_progress(4, "Question Validation", step_progress, progress_callback)
        
        result = self.validation_service.validate_multiple_questions_sync(
            questions, knowledge, validation_progress
        )
        
        return result
    
    def _step_5_review_results(
        self,
        knowledge_node: Knowledge,
        generation_result: BulkGenerationResult,
        validation_result: BatchValidationResult,
        auto_mode: bool
    ) -> dict:
        """Step 5: Review results and save to Neo4j if approved"""
        logger.info("Step 5: Results review and Neo4j persistence")

        neo4j_result = {'saved': False, 'session_id': None, 'saved_count': 0}

        if not auto_mode:
            # Interactive review
            self.display_pipeline_summary(generation_result, validation_result)

            # Ask for approval
            approval = input("\n✅ Approve these questions for Quiz Team submission? (y/n): ").lower().strip()
            if approval == 'y':
                print("💾 Saving approved questions to Neo4j database...")

                # Save to Neo4j
                saved_quizzes = self.persistence_service.save_approved_questions(
                    generation_result.questions,
                    knowledge_node,
                    validation_result.results,
                    generation_result
                )

                # Get session ID from first saved quiz
                session_id = saved_quizzes[0].generation_session_id if saved_quizzes else None

                # Display persistence summary
                self.persistence_service.display_persistence_summary(saved_quizzes, session_id)

                print("✅ Questions approved and saved to Neo4j database!")

                neo4j_result = {
                    'saved': True,
                    'session_id': session_id,
                    'saved_count': len(saved_quizzes)
                }

            else:
                print("❌ Questions not approved. Pipeline completed for review.")
        else:
            # Auto mode - save automatically if validation score is good
            avg_score = validation_result.average_score
            auto_approval_threshold = 0.8  # Configurable threshold

            if avg_score >= auto_approval_threshold:
                print(f"🤖 Auto-approving questions (avg score: {avg_score:.2f} ≥ {auto_approval_threshold})")
                print("💾 Saving to Neo4j database...")

                saved_quizzes = self.persistence_service.save_approved_questions(
                    generation_result.questions,
                    knowledge_node,
                    validation_result.results,
                    generation_result
                )

                session_id = saved_quizzes[0].generation_session_id if saved_quizzes else None

                print(f"✅ Auto-approved and saved {len(saved_quizzes)} questions to Neo4j!")

                neo4j_result = {
                    'saved': True,
                    'session_id': session_id,
                    'saved_count': len(saved_quizzes)
                }

                logger.info(f"Auto-approved and saved {len(saved_quizzes)} questions to Neo4j")

            else:
                print(f"🤖 Questions not auto-approved (avg score: {avg_score:.2f} < {auto_approval_threshold})")
                logger.info(f"Auto mode: Generated {generation_result.total_generated} questions, "
                           f"average validation score: {avg_score:.2f} - not saved")

        return neo4j_result
    
    def display_pipeline_progress(self, progress: PipelineProgress) -> None:
        """Display pipeline progress bar"""
        overall_percentage = progress.overall_progress
        bar_length = 50
        filled_length = int(bar_length * overall_percentage)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r🚀 Pipeline Progress: [{bar}] {overall_percentage:.1%} - "
              f"Step {progress.current_step}/{progress.total_steps}: {progress.step_name}", 
              end='', flush=True)
    
    def display_pipeline_summary(
        self, 
        generation_result: BulkGenerationResult, 
        validation_result: BatchValidationResult
    ) -> None:
        """Display complete pipeline summary"""
        print("\n\n" + "=" * 70)
        print("=== Question Management Pipeline Results ===")
        print("=" * 70)
        
        # Generation summary
        print(f"📊 Generation Results:")
        print(f"   Requested: {generation_result.total_requested} questions")
        print(f"   Generated: {generation_result.total_generated} questions")
        print(f"   Success Rate: {generation_result.success_rate:.1%}")
        print(f"   Generation Time: {generation_result.generation_time:.1f}s")
        
        # Validation summary
        print(f"\n🔍 Validation Results:")
        print(f"   Average Score: {validation_result.average_score:.2f}/1.0")
        print(f"   High Quality (≥0.9): {validation_result.high_quality_count} questions")
        print(f"   Medium Quality (0.7-0.9): {validation_result.medium_quality_count} questions")
        print(f"   Low Quality (<0.7): {validation_result.low_quality_count} questions")
        print(f"   Issues Found: {validation_result.total_issues}")
        print(f"   Recommendations: {validation_result.total_recommendations}")
        
        print("=" * 70)
