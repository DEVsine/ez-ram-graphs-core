"""
Quiz Suggestion Engine - Public API

This module provides adaptive quiz selection based on:
- Individual learner progress (scores)
- Knowledge graph structure (prerequisites)
- Spaced repetition scheduling
- Difficulty adaptation

Usage:
    from student.quiz_suggestion import (
        suggest_next_quiz,
        update_scores,
        get_learning_progress,
        reset_user_progress,
        KnowledgeGraph,
        UserProfile,
    )

    # Load data
    profile = UserProfile(user_id="student123")
    kg = KnowledgeGraph.from_neo4j()
    quizzes = load_quizzes_from_neo4j()

    # Get suggestion
    quiz = suggest_next_quiz(profile, kg, quizzes)

    # Update after attempt
    profile = update_scores(profile, quiz, is_correct=True)

    # Check progress
    progress = get_learning_progress(profile, kg)
"""

from typing import List, Dict, Any
from student.quiz_suggestion.models.user_profile import UserProfile
from student.quiz_suggestion.models.knowledge_graph import KnowledgeGraph
from student.quiz_suggestion.models.adapters import Quiz, load_quizzes_from_neo4j
from student.quiz_suggestion.engine.suggestion_engine import SuggestionEngine
from student.quiz_suggestion.engine.scoring_system import ScoringSystem
from student.quiz_suggestion.utils.schedule import is_due_for_review


def suggest_next_quiz(
    profile: UserProfile, knowledge_graph: KnowledgeGraph, quizzes: List[Quiz]
) -> Quiz:
    """
    Suggest the next quiz for a user.

    This is the main entry point for quiz recommendation.

    Args:
        profile: User profile with scores and history
        knowledge_graph: Knowledge graph for prerequisite validation
        quizzes: Available quiz bank

    Returns:
        Suggested quiz

    Raises:
        NoQuizAvailableError: If no suitable quiz can be found

    Example:
        profile = UserProfile(user_id="student123")
        kg = KnowledgeGraph.from_neo4j()
        quizzes = load_quizzes_from_neo4j()

        quiz = suggest_next_quiz(profile, kg, quizzes)
        print(f"Next quiz: {quiz.content.stem}")
    """
    engine = SuggestionEngine(knowledge_graph)
    return engine.suggest(profile, quizzes)


def update_scores(
    profile: UserProfile, quiz: Quiz, is_correct: bool, knowledge_graph: KnowledgeGraph
) -> UserProfile:
    """
    Update user profile after a quiz attempt.

    This updates:
    - Scores for linked knowledge nodes
    - Spaced repetition schedule
    - Attempt history
    - Prerequisite bonuses (if correct)

    Args:
        profile: User profile to update
        quiz: Quiz that was attempted
        is_correct: Whether the answer was correct
        knowledge_graph: Knowledge graph for prerequisite lookups

    Returns:
        Updated user profile

    Example:
        profile = update_scores(profile, quiz, is_correct=True, kg=kg)
        print(f"New score: {profile.get_score('python_basics')}")
    """
    scorer = ScoringSystem(knowledge_graph)

    if is_correct:
        return scorer.apply_correct(
            profile, quiz.linked_nodes, quiz.id, quiz.difficulty_level
        )
    else:
        return scorer.apply_incorrect(
            profile, quiz.linked_nodes, quiz.id, quiz.difficulty_level
        )


def get_learning_progress(
    profile: UserProfile, knowledge_graph: KnowledgeGraph
) -> Dict[str, Any]:
    """
    Get learning progress statistics for a user.

    Returns:
        Dictionary with progress metrics:
        - mastered_nodes: List of mastered node IDs
        - in_progress_nodes: List of nodes being learned
        - weak_nodes: List of weak nodes (negative scores)
        - coverage_pct: Percentage of nodes with attempts
        - total_attempts: Total quiz attempts
        - accuracy: Overall accuracy
        - next_due_reviews: Number of nodes due for review

    Example:
        progress = get_learning_progress(profile, kg)
        print(f"Mastered: {len(progress['mastered_nodes'])} nodes")
        print(f"Accuracy: {progress['accuracy']:.1%}")
    """
    scorer = ScoringSystem(knowledge_graph)

    # Categorize nodes
    mastered = scorer.get_mastered_nodes(profile)
    weak = scorer.get_weak_nodes(profile)

    in_progress = [
        node_id
        for node_id, score in profile.scores.items()
        if 0 <= score < 3.0  # Between 0 and mastery threshold
    ]

    # Calculate coverage
    total_nodes = len(knowledge_graph.nodes())
    attempted_nodes = len(profile.scores)
    coverage_pct = (attempted_nodes / total_nodes * 100) if total_nodes > 0 else 0

    # Count due reviews
    due_reviews = sum(
        1
        for node_id, entry in profile.schedule.items()
        if is_due_for_review(entry.next_review)
    )

    return {
        "mastered_nodes": mastered,
        "in_progress_nodes": in_progress,
        "weak_nodes": weak,
        "coverage_pct": coverage_pct,
        "total_attempts": profile.total_attempts,
        "total_correct": profile.total_correct,
        "accuracy": profile.get_accuracy(),
        "next_due_reviews": due_reviews,
    }


def reset_user_progress(user_id: str) -> UserProfile:
    """
    Reset all progress for a user.

    Creates a fresh user profile with no scores or history.

    Args:
        user_id: User identifier

    Returns:
        New empty user profile

    Example:
        profile = reset_user_progress("student123")
    """
    return UserProfile(user_id=user_id)


# Public API exports
__all__ = [
    # Main functions
    "suggest_next_quiz",
    "update_scores",
    "get_learning_progress",
    "reset_user_progress",
    # Models
    "UserProfile",
    "KnowledgeGraph",
    "Quiz",
    # Utilities
    "load_quizzes_from_neo4j",
]
