"""
Adapters to convert between Neo4j models and Pydantic models.

These adapters provide a clean separation between the database layer (Neo4j)
and the engine layer (Pydantic), allowing the engine to work with simple,
validated data structures.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from student.quiz_suggestion.exceptions import InvalidDifficultyError


class QuizContent(BaseModel):
    """Content of a quiz question"""

    stem: str  # The question text
    choices: List[str] = Field(default_factory=list)  # Answer choices (for MC)
    answer: str = ""  # Correct answer
    explanation: str = ""  # Explanation for the answer


class Quiz(BaseModel):
    """
    Pydantic Quiz model for the suggestion engine.

    This is a lightweight representation of a quiz that the engine uses
    for recommendation logic. It's converted from Neo4j Quiz nodes.
    """

    id: str  # Neo4j node ID or unique identifier
    linked_nodes: List[str]  # Knowledge node IDs this quiz covers
    quiz_type: str  # "multiple_choice" or "fill_in_blank"
    content: QuizContent
    difficulty_level: int  # 1-5 scale

    @field_validator("difficulty_level")
    @classmethod
    def validate_difficulty(cls, v):
        """Ensure difficulty is in valid range [1, 5]"""
        from student.quiz_suggestion.engine.policies import (
            MIN_DIFFICULTY,
            MAX_DIFFICULTY,
        )

        if not (MIN_DIFFICULTY <= v <= MAX_DIFFICULTY):
            raise InvalidDifficultyError(
                f"Difficulty {v} must be in range [{MIN_DIFFICULTY}, {MAX_DIFFICULTY}]"
            )
        return v

    @field_validator("quiz_type")
    @classmethod
    def validate_quiz_type(cls, v):
        """Ensure quiz type is valid"""
        valid_types = ["multiple_choice", "fill_in_blank"]
        if v not in valid_types:
            raise ValueError(f"Quiz type must be one of {valid_types}, got {v!r}")
        return v

    @classmethod
    def from_neo4j(cls, neo_quiz) -> "Quiz":
        """
        Convert a Neo4j Quiz node to a Pydantic Quiz.

        Args:
            neo_quiz: A quiz.neo_models.Quiz instance

        Returns:
            Quiz: Pydantic Quiz model

        Example:
            from quiz.neo_models import Quiz as NeoQuiz
            neo_quiz = NeoQuiz.nodes.get(id="...")
            pydantic_quiz = Quiz.from_neo4j(neo_quiz)
        """
        # Get linked knowledge nodes
        linked_nodes = []
        try:
            for knowledge in neo_quiz.related_to.all():
                # Use element_id (Neo4j v5+) or fallback to name
                node_id = getattr(knowledge, "element_id", None) or getattr(
                    knowledge, "name", str(knowledge)
                )
                linked_nodes.append(str(node_id))
        except Exception:
            # If relationship doesn't exist or fails, continue with empty list
            pass

        # Get choices and find correct answer
        choices = []
        answer = ""
        explanation = ""

        try:
            for choice in neo_quiz.has_choice.all():
                choice_text = choice.choice_text
                choices.append(choice_text)

                if choice.is_correct:
                    answer = choice_text
                    if (
                        hasattr(choice, "answer_explanation")
                        and choice.answer_explanation
                    ):
                        explanation = choice.answer_explanation
        except Exception:
            # If relationship doesn't exist or fails, continue with empty choices
            pass

        # Get quiz properties with defaults
        difficulty = getattr(neo_quiz, "difficulty_level", 3) or 3
        quiz_type = (
            getattr(neo_quiz, "quiz_type", "multiple_choice") or "multiple_choice"
        )

        # Get unique ID (use element_id for Neo4j v5+)
        quiz_id = getattr(neo_quiz, "element_id", str(neo_quiz))

        return cls(
            id=str(quiz_id),
            linked_nodes=linked_nodes,
            quiz_type=quiz_type,
            content=QuizContent(
                stem=neo_quiz.quiz_text,
                choices=choices,
                answer=answer,
                explanation=explanation,
            ),
            difficulty_level=difficulty,
        )


class KnowledgeNode(BaseModel):
    """
    Pydantic representation of a Knowledge node.

    This is used by the KnowledgeGraph to represent nodes in the graph.
    """

    id: str
    name: str
    description: Optional[str] = None
    example: Optional[str] = None

    @classmethod
    def from_neo4j(cls, neo_knowledge) -> "KnowledgeNode":
        """
        Convert a Neo4j Knowledge node to a Pydantic KnowledgeNode.

        Args:
            neo_knowledge: A knowledge.neo_models.Knowledge instance

        Returns:
            KnowledgeNode: Pydantic KnowledgeNode model
        """
        # Get unique ID (use element_id for Neo4j v5+, fallback to name)
        node_id = getattr(neo_knowledge, "element_id", None) or getattr(
            neo_knowledge, "name", str(neo_knowledge)
        )

        return cls(
            id=str(node_id),
            name=neo_knowledge.name,
            description=getattr(neo_knowledge, "description", None),
            example=getattr(neo_knowledge, "example", None),
        )


def load_quizzes_from_neo4j() -> List[Quiz]:
    """
    Load all quizzes from Neo4j and convert to Pydantic models.

    Returns:
        List[Quiz]: List of Pydantic Quiz models

    Example:
        quizzes = load_quizzes_from_neo4j()
        print(f"Loaded {len(quizzes)} quizzes")
    """
    from quiz.neo_models import Quiz as NeoQuiz

    quizzes = []
    for neo_quiz in NeoQuiz.nodes.all():
        try:
            quiz = Quiz.from_neo4j(neo_quiz)
            quizzes.append(quiz)
        except Exception as e:
            # Log warning but continue
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load quiz {neo_quiz}: {e}")
            continue

    return quizzes


def load_knowledge_nodes_from_neo4j() -> List[KnowledgeNode]:
    """
    Load all knowledge nodes from Neo4j and convert to Pydantic models.

    Returns:
        List[KnowledgeNode]: List of Pydantic KnowledgeNode models
    """
    from knowledge.neo_models import Knowledge as NeoKnowledge

    nodes = []
    for neo_knowledge in NeoKnowledge.nodes.all():
        try:
            node = KnowledgeNode.from_neo4j(neo_knowledge)
            nodes.append(node)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load knowledge node {neo_knowledge}: {e}")
            continue

    return nodes
