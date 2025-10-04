"""
Helper functions for the quiz suggestion CLI.

This module provides utilities for interactive quiz sessions, progress display,
and user input handling.
"""

from typing import List
from student.quiz_suggestion import (
    suggest_next_quiz,
    update_scores,
    get_learning_progress,
)
from student.quiz_suggestion.models.user_profile import UserProfile
from student.quiz_suggestion.models.knowledge_graph import KnowledgeGraph
from student.quiz_suggestion.models.adapters import Quiz


class QuizSession:
    """
    Manages an interactive quiz session.

    This class handles:
    - Quiz suggestion
    - Answer submission
    - Score updates
    - Progress tracking

    Example:
        session = QuizSession(profile, kg, quizzes)
        quiz = session.get_next_quiz()
        session.submit_answer(quiz, is_correct=True)
    """

    def __init__(self, profile: UserProfile, kg: KnowledgeGraph, quizzes: List[Quiz]):
        """
        Initialize a quiz session.

        Args:
            profile: User profile
            kg: Knowledge graph
            quizzes: Available quiz bank
        """
        self.profile = profile
        self.kg = kg
        self.quizzes = quizzes

    def get_next_quiz(self) -> Quiz:
        """Get the next quiz suggestion"""
        return suggest_next_quiz(self.profile, self.kg, self.quizzes)

    def submit_answer(self, quiz: Quiz, is_correct: bool):
        """Submit an answer and update profile"""
        self.profile = update_scores(self.profile, quiz, is_correct, self.kg)

    def get_progress(self) -> dict:
        """Get current learning progress"""
        return get_learning_progress(self.profile, self.kg)


def display_quiz(quiz: Quiz, stdout, style):
    """
    Display a quiz question.

    Args:
        quiz: Quiz to display
        stdout: Output stream
        style: Django style helper
    """
    stdout.write(f"\n{quiz.content.stem}\n")

    if quiz.content.choices:
        for i, choice in enumerate(quiz.content.choices, 1):
            stdout.write(f"  {i}. {choice}")

    stdout.write(f"\nDifficulty: {quiz.difficulty_level}/5")
    stdout.write(f"Type: {quiz.quiz_type}")
    stdout.write(
        f"Covers: {', '.join(quiz.linked_nodes[:3])}{'...' if len(quiz.linked_nodes) > 3 else ''}\n"
    )


def get_user_answer(quiz: Quiz, stdout, style) -> bool:
    """
    Get user answer and check if correct.

    Args:
        quiz: Quiz being answered
        stdin: Input stream
        stdout: Output stream
        style: Django style helper

    Returns:
        True if correct, False otherwise
    """
    if quiz.content.choices:
        # Multiple choice
        while True:
            try:
                answer = input(f"\nYour answer (1-{len(quiz.content.choices)}): ")
                idx = int(answer) - 1
                if 0 <= idx < len(quiz.content.choices):
                    user_choice = quiz.content.choices[idx]
                    return user_choice == quiz.content.answer
                else:
                    stdout.write(style.ERROR("Invalid choice. Try again."))
            except (ValueError, KeyboardInterrupt):
                stdout.write(style.ERROR("\nInvalid input. Try again."))
    else:
        # Fill in the blank
        answer = input("\nYour answer: ")
        return answer.strip().lower() == quiz.content.answer.strip().lower()


def display_progress(profile: UserProfile, kg: KnowledgeGraph, stdout, style):
    """
    Display learning progress.

    Args:
        profile: User profile
        kg: Knowledge graph
        stdout: Output stream
        style: Django style helper
    """
    progress = get_learning_progress(profile, kg)

    stdout.write(style.SUCCESS("\n📊 Learning Progress\n"))
    stdout.write("─" * 60)

    stdout.write(f"\nMastered nodes: {len(progress['mastered_nodes'])}")
    stdout.write(f"In progress: {len(progress['in_progress_nodes'])}")
    stdout.write(f"Weak nodes: {len(progress['weak_nodes'])}")
    stdout.write(f"Coverage: {progress['coverage_pct']:.1f}%")

    stdout.write(f"\nTotal attempts: {progress['total_attempts']}")
    stdout.write(f"Correct: {progress['total_correct']}")
    stdout.write(f"Accuracy: {progress['accuracy']:.1%}")

    stdout.write(f"\nDue for review: {progress['next_due_reviews']} nodes")

    # Show top weak nodes
    if progress["weak_nodes"]:
        stdout.write(f"\n\nWeakest nodes (top 5):")
        for i, node_id in enumerate(progress["weak_nodes"][:5], 1):
            score = profile.get_score(node_id)
            stdout.write(f"  {i}. {node_id}: {score:.2f}")

    # Show recently mastered
    if progress["mastered_nodes"]:
        stdout.write(
            f"\n\nMastered nodes (showing {min(5, len(progress['mastered_nodes']))}):"
        )
        for i, node_id in enumerate(progress["mastered_nodes"][:5], 1):
            score = profile.get_score(node_id)
            stdout.write(f"  {i}. {node_id}: {score:.2f}")

    stdout.write("\n" + "─" * 60 + "\n")


def display_graph_stats(kg: KnowledgeGraph, quizzes: List[Quiz], stdout, style):
    """
    Display knowledge graph statistics.

    Args:
        kg: Knowledge graph
        quizzes: Quiz bank
        stdout: Output stream
        style: Django style helper
    """
    stdout.write(style.SUCCESS("\n📈 Knowledge Graph Statistics\n"))
    stdout.write("─" * 60)

    stdout.write(f"\nTotal knowledge nodes: {len(kg.nodes())}")
    stdout.write(f"Total prerequisite edges: {len(kg.edges())}")
    stdout.write(f"Total quizzes: {len(quizzes)}")

    # Check for cycles
    if kg.is_acyclic():
        stdout.write(style.SUCCESS("\n✓ Graph is acyclic (no circular dependencies)"))
    else:
        cycles = kg.find_cycles()
        stdout.write(style.ERROR(f"\n✗ Graph has {len(cycles)} cycle(s)!"))
        for i, cycle in enumerate(cycles[:3], 1):
            stdout.write(f"  Cycle {i}: {' → '.join(cycle)}")

    # Topological order sample
    try:
        topo = kg.topological_order()
        stdout.write(f"\n\nTopological order (first 10):")
        for i, node_id in enumerate(topo[:10], 1):
            stdout.write(f"  {i}. {node_id}")
    except Exception as e:
        stdout.write(style.ERROR(f"\nFailed to compute topological order: {e}"))

    # Quiz difficulty distribution
    difficulty_counts = {}
    for quiz in quizzes:
        difficulty_counts[quiz.difficulty_level] = (
            difficulty_counts.get(quiz.difficulty_level, 0) + 1
        )

    stdout.write(f"\n\nQuiz difficulty distribution:")
    for difficulty in sorted(difficulty_counts.keys()):
        count = difficulty_counts[difficulty]
        pct = count / len(quizzes) * 100
        stdout.write(f"  Level {difficulty}: {count} ({pct:.1f}%)")

    stdout.write("\n" + "─" * 60 + "\n")
