import json
import os
import tempfile
import shutil
from pathlib import Path
from django.test import TestCase
from quiz.services.json_export_service import JSONExportService
from quiz.models.export_data import ExportConfig, ExportFormat
from quiz.models.question_data import QuestionData, ChoiceData, QuestionStyle
from quiz.models.validation_data import ValidationResult, ValidationDetails, BatchValidationResult
from quiz.services.bulk_generation_service import BulkGenerationResult
from knowledge.neo_models import Knowledge


class JSONExportServiceTest(TestCase):
    """Test cases for JSON export service"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for exports
        self.test_dir = tempfile.mkdtemp()
        
        # Create export config
        self.config = ExportConfig(
            output_directory=self.test_dir,
            create_subdirectories=True
        )
        
        # Create export service
        self.service = JSONExportService(self.config)
        
        # Create sample question data
        self.questions = [
            QuestionData(
                question="She is ___ for class.",
                choices=[
                    ChoiceData("A", "often late", True, "Correct! Adverb after be verb."),
                    ChoiceData("B", "late often", False, "Wrong! Wrong word order."),
                    ChoiceData("C", "is often", False, "Wrong! Duplicate 'is'."),
                    ChoiceData("D", "often is late", False, "Wrong! Adverb before be verb.")
                ],
                style=QuestionStyle.FILL_IN_BLANK
            )
        ]
        
        # Create mock knowledge node
        self.knowledge = type('Knowledge', (), {
            'name': 'Test Knowledge',
            'description': 'Test description',
            'example': 'Test example'
        })()
        
        # Create mock generation result
        self.generation_result = BulkGenerationResult(
            questions=self.questions,
            total_requested=1,
            total_generated=1,
            total_failed=0,
            generation_time=1.5,
            knowledge_node="Test Knowledge",
            question_style="fill_in_blank",
            errors=[]
        )
        
        # Create mock validation result
        validation_details = ValidationDetails(
            spelling_grammar_score=1.0,
            single_correct_answer=True,
            explanation_quality_score=0.9,
            knowledge_relevance_score=0.95,
            clarity_score=0.9
        )
        
        validation = ValidationResult(
            question_text="She is ___ for class.",
            overall_score=0.93,
            is_valid=True,
            validation_details=validation_details,
            issues=[],
            recommendations=[]
        )
        
        self.validation_result = BatchValidationResult(
            results=[validation],
            total_validated=1,
            validation_time=0.5
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_export_complete_format(self):
        """Test exporting questions in complete format"""
        result = self.service.export_questions_complete(
            self.questions,
            self.knowledge,
            self.generation_result,
            self.validation_result
        )
        
        # Verify export succeeded
        self.assertTrue(result.success)
        self.assertEqual(result.questions_exported, 1)
        self.assertEqual(result.export_format, ExportFormat.COMPLETE)
        
        # Verify file exists
        self.assertTrue(os.path.exists(result.file_path))
        
        # Verify file content
        with open(result.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('export_metadata', data)
        self.assertIn('questions', data)
        self.assertEqual(len(data['questions']), 1)
        
        question = data['questions'][0]
        self.assertEqual(question['quiz_text'], "She is ___ for class.")
        self.assertEqual(question['question_style'], "fill_in_blank")
        self.assertEqual(len(question['choices']), 4)
        
        # Verify choice structure
        choice = question['choices'][0]
        self.assertIn('choice_letter', choice)
        self.assertIn('choice_text', choice)
        self.assertIn('is_correct', choice)
        self.assertIn('answer_explanation', choice)
    
    def test_export_legacy_format(self):
        """Test exporting questions in legacy format"""
        result = self.service.export_questions_legacy(
            self.questions,
            self.knowledge
        )
        
        # Verify export succeeded
        self.assertTrue(result.success)
        self.assertEqual(result.questions_exported, 1)
        self.assertEqual(result.export_format, ExportFormat.LEGACY)
        
        # Verify file exists
        self.assertTrue(os.path.exists(result.file_path))
        
        # Verify file content
        with open(result.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(len(data), 1)
        
        question = data[0]
        self.assertEqual(question['question'], "She is ___ for class.")
        self.assertIn('choices', question)
        self.assertIn('answer', question)
        self.assertIn('answer_description', question)
        
        # Verify choices are strings
        self.assertIsInstance(question['choices'][0], str)
    
    def test_export_mapping_format(self):
        """Test exporting questions in mapping format"""
        result = self.service.export_questions_mapping(
            self.questions,
            self.knowledge
        )
        
        # Verify export succeeded
        self.assertTrue(result.success)
        self.assertEqual(result.questions_exported, 1)
        self.assertEqual(result.export_format, ExportFormat.MAPPING)
        
        # Verify file exists
        self.assertTrue(os.path.exists(result.file_path))
        
        # Verify file content
        with open(result.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(len(data), 1)
        
        question = data[0]
        self.assertIn('question_knowledge_ids', question)
        self.assertIn('choices', question)
        
        # Verify choice structure
        choice = question['choices'][0]
        self.assertIn('index', choice)
        self.assertIn('text', choice)
        self.assertIn('knowledge_ids', choice)
        self.assertIn('is_correct', choice)
    
    def test_export_all_formats(self):
        """Test exporting questions in all formats"""
        results = self.service.export_all_formats(
            self.questions,
            self.knowledge,
            self.generation_result,
            self.validation_result
        )
        
        # Verify all formats exported
        self.assertEqual(len(results), 3)
        self.assertIn(ExportFormat.COMPLETE, results)
        self.assertIn(ExportFormat.LEGACY, results)
        self.assertIn(ExportFormat.MAPPING, results)
        
        # Verify all succeeded
        for fmt, result in results.items():
            self.assertTrue(result.success, f"{fmt.value} export failed")
            self.assertTrue(os.path.exists(result.file_path))
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        # Test with special characters
        unsafe_name = "Test/Knowledge:With*Special?Chars"
        safe_name = self.service._sanitize_filename(unsafe_name)
        
        # Verify no invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            self.assertNotIn(char, safe_name)
        
        # Verify spaces replaced with underscores
        self.assertNotIn(' ', safe_name)
    
    def test_subdirectory_creation(self):
        """Test subdirectory creation for different formats"""
        result = self.service.export_questions_complete(
            self.questions,
            self.knowledge,
            self.generation_result,
            self.validation_result
        )
        
        # Verify file is in subdirectory
        self.assertIn('complete', result.file_path)
        
        # Verify subdirectory exists
        complete_dir = Path(self.test_dir) / 'complete'
        self.assertTrue(complete_dir.exists())
        self.assertTrue(complete_dir.is_dir())

