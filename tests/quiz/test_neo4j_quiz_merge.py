"""
Test for Quiz merge functionality (merging questions with same quiz_text).
"""

import os
import django

# Setup Django settings before importing anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import unittest
from unittest.mock import MagicMock, patch

from quiz.services.neo4j_quiz_service import Neo4jQuizService


class TestQuizMerge(unittest.TestCase):
    """Test the quiz merge functionality."""

    def test_create_new_quiz(self):
        """Test creating a new quiz when none exists."""

        # Mock the Quiz model (patch where it's imported)
        with patch("quiz.neo_models.Quiz") as MockQuiz:
            # Setup: no existing quiz
            MockQuiz.nodes.filter.return_value.first.return_value = None

            # Create a mock quiz instance
            mock_quiz = MagicMock()
            mock_quiz.element_id = "4:abc:123"
            mock_quiz.has_choice.all.return_value = []
            mock_quiz.related_to.all.return_value = []
            MockQuiz.return_value.save.return_value = mock_quiz

            # Mock Choice
            with patch("quiz.neo_models.Choice") as MockChoice:
                mock_choice = MagicMock()
                mock_choice.element_id = "4:def:456"
                mock_choice.related_to.all.return_value = []
                MockChoice.return_value.save.return_value = mock_choice

                # Mock Knowledge
                with patch("knowledge.neo_models.Knowledge"):
                    result = Neo4jQuizService.create_question_graph(
                        question_text="What is 2+2?",
                        choices=[
                            {
                                "text": "3",
                                "is_correct": False,
                                "knowledge_ids": [],
                            },
                            {
                                "text": "4",
                                "is_correct": True,
                                "knowledge_ids": [],
                            },
                        ],
                    )

                    # Verify new quiz was created
                    self.assertTrue(result["is_new"])
                    self.assertEqual(result["quiz_text"], "What is 2+2?")
                    self.assertEqual(result["choices_count"], 2)

    def test_merge_existing_quiz(self):
        """Test merging when quiz with same quiz_text exists."""

        with patch("quiz.neo_models.Quiz") as MockQuiz:
            # Setup: existing quiz found
            existing_quiz = MagicMock()
            existing_quiz.element_id = "4:abc:123"
            existing_quiz.has_choice.all.return_value = []
            existing_quiz.related_to.all.return_value = []

            MockQuiz.nodes.filter.return_value.first.return_value = existing_quiz

            with patch("quiz.neo_models.Choice") as MockChoice:
                mock_choice = MagicMock()
                mock_choice.element_id = "4:def:456"
                mock_choice.related_to.all.return_value = []
                MockChoice.return_value.save.return_value = mock_choice

                with patch("knowledge.neo_models.Knowledge"):
                    result = Neo4jQuizService.create_question_graph(
                        question_text="What is 2+2?",
                        choices=[
                            {
                                "text": "4",
                                "is_correct": True,
                                "knowledge_ids": [],
                            },
                        ],
                    )

                    # Verify quiz was merged (not created)
                    self.assertFalse(result["is_new"])
                    self.assertEqual(result["quiz_element_id"], "4:abc:123")

                    # Verify Quiz() constructor was NOT called (existing quiz used)
                    MockQuiz.assert_not_called()

    def test_merge_existing_choice(self):
        """Test that existing choices are updated, not duplicated."""

        with patch("quiz.neo_models.Quiz") as MockQuiz:
            # Setup: existing quiz with existing choice
            existing_choice = MagicMock()
            existing_choice.choice_text = "4"
            existing_choice.is_correct = False  # Will be updated to True
            existing_choice.element_id = "4:choice:789"
            existing_choice.related_to.all.return_value = []

            existing_quiz = MagicMock()
            existing_quiz.element_id = "4:abc:123"
            existing_quiz.has_choice.all.return_value = [existing_choice]
            existing_quiz.related_to.all.return_value = []

            MockQuiz.nodes.filter.return_value.first.return_value = existing_quiz

            with patch("quiz.neo_models.Choice") as MockChoice:
                with patch("knowledge.neo_models.Knowledge"):
                    result = Neo4jQuizService.create_question_graph(
                        question_text="What is 2+2?",
                        choices=[
                            {
                                "text": "4",  # Same choice text
                                "is_correct": True,  # Updated value
                                "knowledge_ids": [],
                            },
                        ],
                    )

                    # Verify existing choice was updated
                    self.assertTrue(existing_choice.is_correct)
                    existing_choice.save.assert_called_once()

                    # Verify new Choice was NOT created
                    MockChoice.assert_not_called()

                    # Verify result includes the existing choice
                    self.assertEqual(result["choices_count"], 1)
                    self.assertEqual(result["choices"][0]["element_id"], "4:choice:789")

    def test_add_new_choice_to_existing_quiz(self):
        """Test adding a new choice to an existing quiz."""

        with patch("quiz.neo_models.Quiz") as MockQuiz:
            # Setup: existing quiz with one choice
            existing_choice = MagicMock()
            existing_choice.choice_text = "3"
            existing_choice.element_id = "4:choice:111"
            existing_choice.related_to.all.return_value = []

            existing_quiz = MagicMock()
            existing_quiz.element_id = "4:abc:123"
            existing_quiz.has_choice.all.return_value = [existing_choice]
            existing_quiz.related_to.all.return_value = []

            MockQuiz.nodes.filter.return_value.first.return_value = existing_quiz

            with patch("quiz.neo_models.Choice") as MockChoice:
                # New choice to be created
                new_choice = MagicMock()
                new_choice.element_id = "4:choice:222"
                new_choice.related_to.all.return_value = []
                MockChoice.return_value.save.return_value = new_choice

                with patch("knowledge.neo_models.Knowledge"):
                    result = Neo4jQuizService.create_question_graph(
                        question_text="What is 2+2?",
                        choices=[
                            {
                                "text": "3",  # Existing choice
                                "is_correct": False,
                                "knowledge_ids": [],
                            },
                            {
                                "text": "4",  # New choice
                                "is_correct": True,
                                "knowledge_ids": [],
                            },
                        ],
                    )

                    # Verify both choices are in result
                    self.assertEqual(result["choices_count"], 2)

                    # Verify new choice was created
                    MockChoice.assert_called_once()
                    existing_quiz.has_choice.connect.assert_called_once_with(new_choice)


if __name__ == "__main__":
    unittest.main()
