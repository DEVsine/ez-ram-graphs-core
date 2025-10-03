import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from knowledge.neo_models import Knowledge
from quiz.models.question_data import QuestionData
from quiz.models.validation_data import ValidationResult, BatchValidationResult
from quiz.models.export_data import ExportConfig, ExportResult, ExportFormat
from quiz.services.bulk_generation_service import BulkGenerationResult

logger = logging.getLogger(__name__)


class JSONExportService:
    """Service for exporting questions to JSON files in various formats"""
    
    def __init__(self, config: Optional[ExportConfig] = None):
        """Initialize export service with configuration"""
        self.config = config or ExportConfig()
        logger.info(f"Initialized JSONExportService with format: {self.config.format.value}")
    
    def export_questions_complete(
        self,
        questions: List[QuestionData],
        knowledge_node: Knowledge,
        generation_result: BulkGenerationResult,
        validation_result: BatchValidationResult,
        output_path: Optional[str] = None
    ) -> ExportResult:
        """Export questions in complete format with all metadata"""
        logger.info(f"Exporting {len(questions)} questions in complete format")
        
        try:
            # Prepare export data
            export_data = {
                "export_metadata": self._prepare_export_metadata(
                    knowledge_node,
                    generation_result,
                    validation_result,
                    len(questions)
                ),
                "questions": [
                    self._convert_to_complete_format(q, knowledge_node, i)
                    for i, q in enumerate(questions)
                ]
            }
            
            # Generate filename if not provided
            if not output_path:
                output_path = self._generate_filename(
                    ExportFormat.COMPLETE,
                    knowledge_node.name,
                    generation_result.generation_time
                )
            
            # Write to file
            file_path = self._write_json_file(export_data, output_path)
            file_size = self._calculate_file_size(file_path)
            
            logger.info(f"Successfully exported to {file_path}")
            
            return ExportResult(
                success=True,
                file_path=file_path,
                questions_exported=len(questions),
                export_format=ExportFormat.COMPLETE,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Failed to export questions in complete format: {e}")
            return ExportResult(
                success=False,
                file_path="",
                questions_exported=0,
                export_format=ExportFormat.COMPLETE,
                error_message=str(e)
            )
    
    def export_questions_legacy(
        self,
        questions: List[QuestionData],
        knowledge_node: Knowledge,
        output_path: Optional[str] = None
    ) -> ExportResult:
        """Export questions in legacy format (backward compatible)"""
        logger.info(f"Exporting {len(questions)} questions in legacy format")
        
        try:
            # Convert to legacy format
            export_data = [
                self._convert_to_legacy_format(q)
                for q in questions
            ]
            
            # Generate filename if not provided
            if not output_path:
                output_path = self._generate_filename(
                    ExportFormat.LEGACY,
                    knowledge_node.name
                )
            
            # Write to file
            file_path = self._write_json_file(export_data, output_path)
            file_size = self._calculate_file_size(file_path)
            
            logger.info(f"Successfully exported to {file_path}")
            
            return ExportResult(
                success=True,
                file_path=file_path,
                questions_exported=len(questions),
                export_format=ExportFormat.LEGACY,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Failed to export questions in legacy format: {e}")
            return ExportResult(
                success=False,
                file_path="",
                questions_exported=0,
                export_format=ExportFormat.LEGACY,
                error_message=str(e)
            )
    
    def export_questions_mapping(
        self,
        questions: List[QuestionData],
        knowledge_node: Knowledge,
        knowledge_id_map: Optional[Dict[str, List[int]]] = None,
        output_path: Optional[str] = None
    ) -> ExportResult:
        """Export questions with knowledge ID mappings"""
        logger.info(f"Exporting {len(questions)} questions in mapping format")
        
        try:
            # Convert to mapping format
            export_data = [
                self._convert_to_mapping_format(q, knowledge_id_map or {})
                for q in questions
            ]
            
            # Generate filename if not provided
            if not output_path:
                output_path = self._generate_filename(
                    ExportFormat.MAPPING,
                    knowledge_node.name
                )
            
            # Write to file
            file_path = self._write_json_file(export_data, output_path)
            file_size = self._calculate_file_size(file_path)
            
            logger.info(f"Successfully exported to {file_path}")
            
            return ExportResult(
                success=True,
                file_path=file_path,
                questions_exported=len(questions),
                export_format=ExportFormat.MAPPING,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Failed to export questions in mapping format: {e}")
            return ExportResult(
                success=False,
                file_path="",
                questions_exported=0,
                export_format=ExportFormat.MAPPING,
                error_message=str(e)
            )
    
    def export_all_formats(
        self,
        questions: List[QuestionData],
        knowledge_node: Knowledge,
        generation_result: BulkGenerationResult,
        validation_result: BatchValidationResult,
        knowledge_id_map: Optional[Dict[str, List[int]]] = None
    ) -> Dict[ExportFormat, ExportResult]:
        """Export questions in all supported formats"""
        logger.info(f"Exporting {len(questions)} questions in all formats")
        
        results = {}
        
        # Export complete format
        results[ExportFormat.COMPLETE] = self.export_questions_complete(
            questions, knowledge_node, generation_result, validation_result
        )
        
        # Export legacy format
        results[ExportFormat.LEGACY] = self.export_questions_legacy(
            questions, knowledge_node
        )
        
        # Export mapping format
        results[ExportFormat.MAPPING] = self.export_questions_mapping(
            questions, knowledge_node, knowledge_id_map
        )
        
        return results
    
    def _prepare_export_metadata(
        self,
        knowledge_node: Knowledge,
        generation_result: BulkGenerationResult,
        validation_result: BatchValidationResult,
        total_questions: int
    ) -> Dict[str, Any]:
        """Prepare export metadata"""
        return {
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0",
            "knowledge_name": knowledge_node.name,
            "knowledge_description": knowledge_node.description or "",
            "knowledge_example": knowledge_node.example or "",
            "generation_session_id": generation_result.generation_time,  # Use as session identifier
            "total_questions": total_questions,
            "average_validation_score": validation_result.average_score,
            "high_quality_count": validation_result.high_quality_count,
            "medium_quality_count": validation_result.medium_quality_count,
            "low_quality_count": validation_result.low_quality_count,
            "generation_time": generation_result.generation_time,
            "success_rate": generation_result.success_rate
        }
    
    def _convert_to_complete_format(
        self,
        question: QuestionData,
        knowledge_node: Knowledge,
        index: int
    ) -> Dict[str, Any]:
        """Convert QuestionData to complete JSON format"""
        return {
            "id": f"quiz_{index + 1:03d}",
            "quiz_text": question.question,
            "question_style": question.style.value,
            "generation_metadata": {
                "created_at": datetime.now().isoformat(),
                "ai_model_used": "openai",
                "question_index": index + 1
            },
            "choices": [
                {
                    "choice_letter": choice.letter,
                    "choice_text": choice.text,
                    "is_correct": choice.is_correct,
                    "answer_explanation": choice.explanation
                }
                for choice in question.choices
            ],
            "knowledge_reference": {
                "name": knowledge_node.name,
                "description": knowledge_node.description or ""
            }
        }
    
    def _convert_to_legacy_format(self, question: QuestionData) -> Dict[str, Any]:
        """Convert QuestionData to legacy format"""
        correct_choice = question.get_correct_choice()
        
        return {
            "question": question.question,
            "choices": [choice.text for choice in question.choices],
            "answer": correct_choice.text,
            "answer_description": correct_choice.explanation
        }
    
    def _convert_to_mapping_format(
        self,
        question: QuestionData,
        knowledge_id_map: Dict[str, List[int]]
    ) -> Dict[str, Any]:
        """Convert QuestionData to mapping format with knowledge IDs"""
        correct_choice = question.get_correct_choice()
        
        return {
            "question": question.question,
            "answer_description": correct_choice.explanation,
            "question_knowledge_ids": knowledge_id_map.get(question.question, []),
            "choices": [
                {
                    "index": i + 1,
                    "text": choice.text,
                    "knowledge_ids": knowledge_id_map.get(choice.text, []),
                    "is_correct": choice.is_correct
                }
                for i, choice in enumerate(question.choices)
            ]
        }
    
    def _generate_filename(
        self,
        format_type: ExportFormat,
        knowledge_name: str,
        session_id: Optional[float] = None
    ) -> str:
        """Generate filename with timestamp"""
        # Sanitize knowledge name
        safe_name = self._sanitize_filename(knowledge_name)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build filename
        if session_id:
            filename = f"quiz_{format_type.value}_{safe_name}_session{int(session_id)}_{timestamp}.json"
        else:
            filename = f"quiz_{format_type.value}_{safe_name}_{timestamp}.json"
        
        # Build full path
        if self.config.create_subdirectories:
            subdir = Path(self.config.output_directory) / format_type.value
            subdir.mkdir(parents=True, exist_ok=True)
            return str(subdir / filename)
        else:
            Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
            return str(Path(self.config.output_directory) / filename)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        # Limit length
        max_length = 50
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized
    
    def _write_json_file(self, data: Any, file_path: str) -> str:
        """Write data to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    data,
                    f,
                    indent=self.config.indent if self.config.pretty_print else None,
                    ensure_ascii=self.config.ensure_ascii
                )
            logger.debug(f"Wrote JSON to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write JSON file {file_path}: {e}")
            raise
    
    def _calculate_file_size(self, file_path: str) -> int:
        """Calculate file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.warning(f"Failed to get file size for {file_path}: {e}")
            return 0

