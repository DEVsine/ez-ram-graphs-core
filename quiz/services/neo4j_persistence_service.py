import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from knowledge.neo_models import Knowledge
from quiz.neo_models import Quiz, Choice
from quiz.models.question_data import QuestionData
from quiz.models.validation_data import ValidationResult, BatchValidationResult
from quiz.services.bulk_generation_service import BulkGenerationResult

logger = logging.getLogger(__name__)


class Neo4jPersistenceService:
    """Service for saving approved questions to Neo4j database with proper relationships"""
    
    def __init__(self):
        """Initialize persistence service"""
        self.logger = logger
    
    def save_approved_questions(
        self,
        questions: List[QuestionData],
        knowledge_node: Knowledge,
        validation_results: List[ValidationResult],
        generation_result: BulkGenerationResult,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Quiz]:
        """
        Save approved questions to Neo4j with complete relationships
        
        Args:
            questions: List of generated questions to save
            knowledge_node: The knowledge node these questions relate to
            validation_results: Validation results for each question
            generation_result: Generation metadata and statistics
            session_metadata: Additional session information
            
        Returns:
            List of saved Quiz nodes
        """
        logger.info(f"Starting Neo4j persistence for {len(questions)} questions")
        
        saved_quizzes = []
        session_id = str(uuid.uuid4())
        
        try:
            for i, question in enumerate(questions):
                # Get corresponding validation result
                validation = validation_results[i] if i < len(validation_results) else None
                
                # Create Quiz node with metadata
                quiz_node = self._create_quiz_node(
                    question, 
                    validation, 
                    generation_result,
                    session_id
                )
                
                # Link Quiz to Knowledge
                self._link_quiz_to_knowledge(quiz_node, knowledge_node)
                
                # Create and link Choice nodes
                choice_nodes = self._create_and_link_choices(
                    quiz_node, 
                    question, 
                    knowledge_node
                )
                
                saved_quizzes.append(quiz_node)
                logger.info(f"Saved question {i+1}/{len(questions)}: {quiz_node.element_id}")
            
            # Log success
            logger.info(f"Successfully saved {len(saved_quizzes)} questions to Neo4j")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Knowledge Node: {knowledge_node.name}")
            
            return saved_quizzes
            
        except Exception as e:
            logger.error(f"Failed to save questions to Neo4j: {e}")
            # Clean up any partially created nodes if needed
            self._cleanup_failed_session(session_id)
            raise
    
    def _create_quiz_node(
        self,
        question: QuestionData,
        validation: Optional[ValidationResult],
        generation_result: BulkGenerationResult,
        session_id: str
    ) -> Quiz:
        """Create Quiz node with all metadata"""
        
        # Prepare quiz data
        quiz_data = {
            'quiz_text': question.question,
            'question_style': question.style.value,
            'generation_session_id': session_id,
            'created_at': datetime.now().isoformat(),
        }
        
        # Add validation data if available
        if validation:
            quiz_data.update({
                'validation_score': validation.overall_score,
                'is_validated': validation.is_valid,
                'spelling_grammar_score': validation.validation_details.spelling_grammar_score,
                'explanation_quality_score': validation.validation_details.explanation_quality_score,
                'knowledge_relevance_score': validation.validation_details.knowledge_relevance_score,
                'clarity_score': validation.validation_details.clarity_score,
                'single_correct_answer': validation.validation_details.single_correct_answer,
            })
        
        # Add generation metadata
        quiz_data.update({
            'generation_time': generation_result.generation_time,
            'ai_model_used': 'openai',  # Could be dynamic based on config
            'generation_success_rate': generation_result.success_rate,
        })
        
        # Create and save Quiz node
        quiz_node = Quiz(**quiz_data).save()
        logger.debug(f"Created Quiz node: {quiz_node.element_id}")
        
        return quiz_node
    
    def _link_quiz_to_knowledge(self, quiz_node: Quiz, knowledge_node: Knowledge) -> None:
        """Create relationship between Quiz and Knowledge nodes"""
        try:
            quiz_node.related_to.connect(knowledge_node)
            logger.debug(f"Linked Quiz {quiz_node.element_id} to Knowledge {knowledge_node.name}")
        except Exception as e:
            logger.error(f"Failed to link Quiz to Knowledge: {e}")
            raise
    
    def _create_and_link_choices(
        self,
        quiz_node: Quiz,
        question: QuestionData,
        knowledge_node: Knowledge
    ) -> List[Choice]:
        """Create Choice nodes and establish relationships"""
        
        choice_nodes = []
        
        for choice_data in question.choices:
            try:
                # Create Choice node
                choice_node = Choice(
                    choice_letter=choice_data.letter,
                    choice_text=choice_data.text,
                    is_correct=choice_data.is_correct,
                    answer_explanation=choice_data.explanation,
                    question_id=quiz_node.element_id  # Reference to quiz
                ).save()
                
                # Link Choice to Quiz
                quiz_node.has_choice.connect(choice_node)
                
                # Link Choice to Knowledge
                choice_node.related_to.connect(knowledge_node)
                
                choice_nodes.append(choice_node)
                logger.debug(f"Created and linked Choice {choice_data.letter}: {choice_node.element_id}")
                
            except Exception as e:
                logger.error(f"Failed to create/link Choice {choice_data.letter}: {e}")
                raise
        
        return choice_nodes
    
    def _cleanup_failed_session(self, session_id: str) -> None:
        """Clean up any nodes created during a failed session"""
        try:
            # Find and delete any Quiz nodes from this session
            failed_quizzes = Quiz.nodes.filter(generation_session_id=session_id)
            for quiz in failed_quizzes:
                # Delete related choices first
                for choice in quiz.has_choice.all():
                    choice.delete()
                # Delete quiz
                quiz.delete()
            
            logger.info(f"Cleaned up failed session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    def get_questions_by_knowledge(self, knowledge_name: str) -> List[Quiz]:
        """Retrieve all questions for a specific knowledge node"""
        try:
            knowledge_node = Knowledge.nodes.get(name=knowledge_name)
            questions = knowledge_node.related_quizzes.all()
            return list(questions)
        except Exception as e:
            logger.error(f"Failed to retrieve questions for {knowledge_name}: {e}")
            return []
    
    def get_questions_by_style(self, question_style: str) -> List[Quiz]:
        """Retrieve all questions of a specific style"""
        try:
            questions = Quiz.nodes.filter(question_style=question_style)
            return list(questions)
        except Exception as e:
            logger.error(f"Failed to retrieve questions for style {question_style}: {e}")
            return []
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific generation session"""
        try:
            session_quizzes = Quiz.nodes.filter(generation_session_id=session_id)
            session_list = list(session_quizzes)
            
            if not session_list:
                return {}
            
            # Calculate statistics
            total_questions = len(session_list)
            avg_validation_score = sum(q.validation_score or 0 for q in session_list) / total_questions
            high_quality = sum(1 for q in session_list if (q.validation_score or 0) >= 0.9)
            medium_quality = sum(1 for q in session_list if 0.7 <= (q.validation_score or 0) < 0.9)
            low_quality = sum(1 for q in session_list if (q.validation_score or 0) < 0.7)
            
            return {
                'session_id': session_id,
                'total_questions': total_questions,
                'average_validation_score': avg_validation_score,
                'high_quality_count': high_quality,
                'medium_quality_count': medium_quality,
                'low_quality_count': low_quality,
                'knowledge_node': session_list[0].related_to.single().name if session_list[0].related_to.single() else 'Unknown',
                'question_style': session_list[0].question_style,
                'created_at': session_list[0].created_at
            }
            
        except Exception as e:
            logger.error(f"Failed to get session statistics for {session_id}: {e}")
            return {}
    
    def display_persistence_summary(self, saved_quizzes: List[Quiz], session_id: str) -> None:
        """Display summary of saved questions"""
        print("\n" + "=" * 60)
        print("=== Neo4j Persistence Summary ===")
        print("=" * 60)
        print(f"Session ID: {session_id}")
        print(f"Questions Saved: {len(saved_quizzes)}")
        
        if saved_quizzes:
            knowledge_name = saved_quizzes[0].related_to.single().name
            question_style = saved_quizzes[0].question_style
            print(f"Knowledge Node: {knowledge_name}")
            print(f"Question Style: {question_style}")
            
            # Show validation scores if available
            scores = [q.validation_score for q in saved_quizzes if q.validation_score is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"Average Validation Score: {avg_score:.2f}")
        
        print(f"Database Status: ✅ Successfully persisted to Neo4j")
        print("=" * 60)
