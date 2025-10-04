"""
Basic smoke tests for the quiz suggestion engine.

Run with: python -m pytest student/quiz_suggestion/test_basic.py -v
"""

import pytest
from student.quiz_suggestion.models.user_profile import UserProfile, AttemptRecord, ScheduleEntry
from student.quiz_suggestion.models.knowledge_graph import KnowledgeGraph
from student.quiz_suggestion.models.adapters import Quiz, QuizContent
from student.quiz_suggestion.engine.policies import MASTERY_THRESHOLD, SCORE_BOUNDS
from student.quiz_suggestion.exceptions import InvalidDifficultyError
from datetime import datetime, timezone


def test_user_profile_creation():
    """Test creating a user profile"""
    profile = UserProfile(user_id="test_user")
    
    assert profile.user_id == "test_user"
    assert len(profile.scores) == 0
    assert profile.total_attempts == 0
    assert profile.total_correct == 0


def test_user_profile_scores():
    """Test score management"""
    profile = UserProfile(user_id="test_user")
    
    # Set score
    profile.set_score("python_basics", 2.5)
    assert profile.get_score("python_basics") == 2.5
    
    # Get non-existent score (should default to 0)
    assert profile.get_score("unknown_node") == 0.0
    
    # Test bounds
    profile.set_score("test_node", 100.0)  # Should clamp to max
    assert profile.get_score("test_node") == SCORE_BOUNDS[1]
    
    profile.set_score("test_node", -100.0)  # Should clamp to min
    assert profile.get_score("test_node") == SCORE_BOUNDS[0]


def test_user_profile_attempts():
    """Test attempt tracking"""
    profile = UserProfile(user_id="test_user")
    
    # Add attempt
    record = AttemptRecord(
        quiz_id="q1",
        node_ids=["python_basics"],
        is_correct=True,
        difficulty_level=3
    )
    profile.add_attempt(record)
    
    assert profile.total_attempts == 1
    assert profile.total_correct == 1
    assert len(profile.attempt_history) == 1


def test_user_profile_serialization():
    """Test JSON serialization"""
    profile = UserProfile(user_id="test_user")
    profile.set_score("python_basics", 2.5)
    
    # To JSON and back
    json_str = profile.to_json()
    loaded = UserProfile.from_json(json_str)
    
    assert loaded.user_id == profile.user_id
    assert loaded.get_score("python_basics") == 2.5


def test_knowledge_graph_creation():
    """Test creating a knowledge graph"""
    kg = KnowledgeGraph()
    
    # Add nodes
    kg.add_node("python_basics", name="Python Basics")
    kg.add_node("python_functions", name="Python Functions")
    kg.add_node("python_classes", name="Python Classes")
    
    assert len(kg.nodes()) == 3
    assert kg.has_node("python_basics")


def test_knowledge_graph_prerequisites():
    """Test prerequisite relationships"""
    kg = KnowledgeGraph()
    
    kg.add_node("basics")
    kg.add_node("functions")
    kg.add_node("classes")
    
    # functions depends on basics
    kg.add_edge("functions", "basics")
    # classes depends on functions
    kg.add_edge("classes", "functions")
    
    # Check prerequisites
    assert "basics" in kg.get_prerequisites("functions")
    assert "functions" in kg.get_prerequisites("classes")
    
    # Check all prerequisites (transitive)
    all_prereqs = kg.get_all_prerequisites("classes")
    assert "functions" in all_prereqs
    assert "basics" in all_prereqs


def test_knowledge_graph_acyclic():
    """Test cycle detection"""
    kg = KnowledgeGraph()
    
    kg.add_node("a")
    kg.add_node("b")
    kg.add_node("c")
    
    # Create linear dependency: c -> b -> a
    kg.add_edge("c", "b")
    kg.add_edge("b", "a")
    
    assert kg.is_acyclic()
    
    # Add cycle: a -> c (creates cycle)
    kg.add_edge("a", "c")
    
    assert not kg.is_acyclic()
    cycles = kg.find_cycles()
    assert len(cycles) > 0


def test_quiz_model():
    """Test Quiz Pydantic model"""
    quiz = Quiz(
        id="q1",
        linked_nodes=["python_basics"],
        quiz_type="multiple_choice",
        content=QuizContent(
            stem="What is 2+2?",
            choices=["3", "4", "5"],
            answer="4"
        ),
        difficulty_level=1
    )
    
    assert quiz.id == "q1"
    assert quiz.difficulty_level == 1
    assert len(quiz.content.choices) == 3


def test_quiz_difficulty_validation():
    """Test quiz difficulty validation"""
    # Valid difficulty
    quiz = Quiz(
        id="q1",
        linked_nodes=[],
        quiz_type="multiple_choice",
        content=QuizContent(stem="Test"),
        difficulty_level=3
    )
    assert quiz.difficulty_level == 3
    
    # Invalid difficulty should raise error
    with pytest.raises(InvalidDifficultyError):
        Quiz(
            id="q2",
            linked_nodes=[],
            quiz_type="multiple_choice",
            content=QuizContent(stem="Test"),
            difficulty_level=10  # Invalid
        )


def test_quiz_type_validation():
    """Test quiz type validation"""
    # Valid type
    quiz = Quiz(
        id="q1",
        linked_nodes=[],
        quiz_type="fill_in_blank",
        content=QuizContent(stem="Test"),
        difficulty_level=3
    )
    assert quiz.quiz_type == "fill_in_blank"
    
    # Invalid type should raise error
    with pytest.raises(ValueError):
        Quiz(
            id="q2",
            linked_nodes=[],
            quiz_type="invalid_type",
            content=QuizContent(stem="Test"),
            difficulty_level=3
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

