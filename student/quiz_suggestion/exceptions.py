"""
Custom exceptions for the quiz suggestion engine.

These exceptions provide clear error handling for various failure modes
in the adaptive learning system.
"""


class QuizSuggestionError(Exception):
    """Base exception for all quiz suggestion errors"""
    pass


class NoQuizAvailableError(QuizSuggestionError):
    """
    Raised when no suitable quiz can be found for the user.
    
    This can happen when:
    - All quizzes have been mastered
    - No quizzes match the current difficulty level
    - All available quizzes are blocked by prerequisites
    - The quiz bank is empty
    """
    pass


class CycleDetectedError(QuizSuggestionError):
    """
    Raised when a circular dependency is detected in the knowledge graph.
    
    Example: A depends on B, B depends on C, C depends on A
    
    This violates the prerequisite structure and must be fixed in the
    knowledge graph before the suggestion engine can work properly.
    """
    pass


class MissingNodeError(QuizSuggestionError):
    """
    Raised when a referenced knowledge node doesn't exist in the graph.
    
    This can happen when:
    - A quiz references a knowledge node that was deleted
    - The knowledge graph is incomplete
    - There's a mismatch between quiz data and graph data
    """
    pass


class InvalidDifficultyError(QuizSuggestionError):
    """
    Raised when a quiz has an invalid difficulty level.
    
    Difficulty must be in range [1, 5].
    """
    pass


class InvalidScoreError(QuizSuggestionError):
    """
    Raised when a score is outside the valid bounds.
    
    Scores must be in range [-5.0, 10.0] as defined in policies.
    """
    pass

