"""
Service for Neo4j quiz operations.

This service handles creating and managing quiz graphs in Neo4j.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Neo4jQuizService:
    """
    Service for Neo4j quiz operations.

    This is a utility service that provides methods for creating
    and managing quiz graphs in Neo4j.
    """

    @staticmethod
    def create_question_graph(
        question_text: str,
        choices: List[Dict[str, Any]],
        question_knowledge_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Create or merge a complete question graph in Neo4j.

        If a Quiz with the same quiz_text already exists, it will be merged
        (updated with new relationships and choices).

        Args:
            question_text: The quiz question text
            choices: List of choice dicts with structure:
                {
                    "index": int,
                    "text": str,
                    "knowledge_ids": [int, ...],
                    "is_correct": bool,
                    "answer_explanation": str
                }
            question_knowledge_ids: List of knowledge IDs related to the question
            answer_description: Optional explanation for the answer

        Returns:
            Dict with created/merged node information
        """
        # Import here to avoid circular import
        from knowledge.neo_models import Knowledge
        from quiz.neo_models import Quiz, Choice

        # Check if Quiz with same quiz_text already exists
        try:
            existing_quiz = Quiz.nodes.filter(quiz_text=question_text).first()
        except Quiz.DoesNotExist:
            existing_quiz = None

        if existing_quiz:
            # Merge: use existing quiz
            quiz = existing_quiz
            is_new = False
        else:
            # Create new Quiz node
            quiz = Quiz(quiz_text=question_text).save()
            is_new = True

        # Link quiz to knowledge nodes (avoid duplicates)
        if question_knowledge_ids:
            # Get existing knowledge relationships
            existing_knowledge_ids = set()
            for k in quiz.related_to.all():
                kid = Neo4jQuizService._extract_numeric_id(k.element_id)
                if kid:
                    existing_knowledge_ids.add(kid)

            # Add new knowledge relationships
            for kid in question_knowledge_ids:
                if kid in existing_knowledge_ids:
                    continue  # Skip if already connected

                try:
                    # Find knowledge node by element_id
                    knowledge_nodes = Knowledge.nodes.all()
                    for k in knowledge_nodes:
                        if Neo4jQuizService._extract_numeric_id(k.element_id) == kid:
                            quiz.related_to.connect(k)
                            break
                except Exception:
                    # Skip if knowledge node not found
                    pass

        # Get existing choices for this quiz
        existing_choices_map = {}  # choice_text -> Choice node
        for existing_choice in quiz.has_choice.all():
            existing_choices_map[existing_choice.choice_text] = existing_choice

        # Create or update Choice nodes and link them
        created_choices = []
        for choice_data in choices:
            choice_text = choice_data.get("text", "")
            is_correct = choice_data.get("is_correct", False)
            knowledge_ids = choice_data.get("knowledge_ids", [])
            choice_answer_description = choice_data.get("answer_description", "")

            if not choice_text:
                continue

            # Check if choice already exists
            if choice_text in existing_choices_map:
                # Merge: update existing choice
                choice = existing_choices_map[choice_text]
                choice.is_correct = is_correct
                choice.answer_explanation = choice_answer_description
                choice.save()
            else:
                # Create new Choice node
                choice = Choice(
                    choice_text=choice_text,
                    is_correct=is_correct,
                    answer_explanation=choice_answer_description,
                ).save()

                # Link choice to quiz
                quiz.has_choice.connect(choice)

            # Get existing knowledge relationships for this choice
            existing_choice_knowledge_ids = set()
            for k in choice.related_to.all():
                kid = Neo4jQuizService._extract_numeric_id(k.element_id)
                if kid:
                    existing_choice_knowledge_ids.add(kid)

            # Link choice to knowledge nodes (avoid duplicates)
            for kid in knowledge_ids:
                if kid in existing_choice_knowledge_ids:
                    continue  # Skip if already connected

                try:
                    knowledge_nodes = Knowledge.nodes.all()
                    for k in knowledge_nodes:
                        if Neo4jQuizService._extract_numeric_id(k.element_id) == kid:
                            choice.related_to.connect(k)
                            break
                except Exception:
                    # Skip if knowledge node not found
                    pass

            created_choices.append(
                {
                    "element_id": choice.element_id,
                    "text": choice_text,
                    "is_correct": is_correct,
                    "answer_explanation": choice_answer_description,
                }
            )

        return {
            "quiz_element_id": quiz.element_id,
            "quiz_text": question_text,
            "choices_count": len(created_choices),
            "choices": created_choices,
            "is_new": is_new,  # True if created, False if merged
        }

    @staticmethod
    def _extract_numeric_id(element_id: str) -> Optional[int]:
        """
        Extract numeric ID from Neo4j element_id format.

        Format: "4:uuid:numeric_id"
        """
        if not isinstance(element_id, str):
            return None

        parts = element_id.split(":")
        if len(parts) >= 3:
            try:
                return int(parts[-1])
            except (ValueError, IndexError):
                pass

        return None
