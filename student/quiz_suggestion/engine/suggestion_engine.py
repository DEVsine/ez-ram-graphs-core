"""
Core quiz suggestion engine.

This module implements the adaptive quiz selection algorithm based on:
- Weakness-first prioritization
- Prerequisite validation
- Difficulty adaptation
- Spaced repetition scheduling
"""

from typing import List, Set, Optional
import logging
import random
from student.quiz_suggestion.models.user_profile import UserProfile
from student.quiz_suggestion.models.knowledge_graph import KnowledgeGraph
from student.quiz_suggestion.models.adapters import Quiz
from student.quiz_suggestion.exceptions import NoQuizAvailableError
from student.quiz_suggestion.engine.policies import (
    PREREQUISITE_THRESHOLD,
    MASTERY_THRESHOLD,
    RECENT_ATTEMPTS_WINDOW,
    DIFFICULTY_SCORE_RANGES,
    DIFFICULTY_ACCURACY_RANGES,
    MIN_ATTEMPTS_FOR_ADJUSTMENT,
    FALLBACK_STRATEGY,
    ALLOW_MASTERED_FALLBACK,
)
from student.quiz_suggestion.utils.schedule import is_due_for_review

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Adaptive quiz suggestion engine.
    
    This engine selects quizzes based on:
    1. Weakness-first: Prioritize nodes with low scores
    2. Prerequisites: Block nodes until prerequisites are met
    3. Difficulty: Match quiz difficulty to current skill level
    4. Spaced repetition: Prioritize overdue reviews
    5. Variety: Avoid repeating the same quiz too soon
    
    Example:
        engine = SuggestionEngine(knowledge_graph)
        quiz = engine.suggest(profile, quizzes)
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        Initialize the suggestion engine.
        
        Args:
            knowledge_graph: The knowledge graph for prerequisite validation
        """
        self.kg = knowledge_graph
    
    def suggest(self, profile: UserProfile, quizzes: List[Quiz]) -> Quiz:
        """
        Suggest the next quiz for a user.
        
        This is the main entry point for quiz selection.
        
        Args:
            profile: User profile with scores and history
            quizzes: Available quiz bank
            
        Returns:
            Suggested quiz
            
        Raises:
            NoQuizAvailableError: If no suitable quiz can be found
        """
        logger.info(f"Suggesting quiz for user {profile.user_id}")
        
        if not quizzes:
            raise NoQuizAvailableError("Quiz bank is empty")
        
        # Step 1: Filter quizzes by prerequisite validation
        valid_quizzes = self._filter_by_prerequisites(profile, quizzes)
        logger.debug(f"After prerequisite filter: {len(valid_quizzes)}/{len(quizzes)} quizzes")
        
        if not valid_quizzes:
            logger.warning("No quizzes pass prerequisite validation")
            return self._fallback_selection(profile, quizzes)
        
        # Step 2: Filter out recently attempted quizzes
        fresh_quizzes = self._filter_recent_attempts(profile, valid_quizzes)
        logger.debug(f"After recency filter: {len(fresh_quizzes)}/{len(valid_quizzes)} quizzes")
        
        if not fresh_quizzes:
            logger.warning("All valid quizzes were recently attempted")
            fresh_quizzes = valid_quizzes  # Use all valid quizzes
        
        # Step 3: Prioritize by weakness and due reviews
        prioritized = self._prioritize_quizzes(profile, fresh_quizzes)
        
        # Step 4: Adapt difficulty
        difficulty_matched = self._filter_by_difficulty(profile, prioritized)
        logger.debug(f"After difficulty filter: {len(difficulty_matched)}/{len(prioritized)} quizzes")
        
        if not difficulty_matched:
            logger.warning("No quizzes match current difficulty level")
            difficulty_matched = prioritized  # Use all prioritized quizzes
        
        # Step 5: Select from top candidates
        if difficulty_matched:
            selected = difficulty_matched[0]
            logger.info(f"Selected quiz {selected.id} (difficulty={selected.difficulty_level})")
            return selected
        
        # Fallback
        return self._fallback_selection(profile, quizzes)
    
    def _filter_by_prerequisites(self, profile: UserProfile, quizzes: List[Quiz]) -> List[Quiz]:
        """
        Filter quizzes to only those whose prerequisites are met.
        
        A prerequisite is "met" if its score >= PREREQUISITE_THRESHOLD (default 0).
        
        Args:
            profile: User profile
            quizzes: Candidate quizzes
            
        Returns:
            Filtered list of quizzes
        """
        valid = []
        
        for quiz in quizzes:
            # Check if all linked nodes have prerequisites met
            all_met = True
            
            for node_id in quiz.linked_nodes:
                blockers = self._compute_prerequisite_blockers(profile, node_id)
                if blockers:
                    all_met = False
                    logger.debug(
                        f"Quiz {quiz.id} blocked by prerequisites for {node_id}: {blockers}"
                    )
                    break
            
            if all_met:
                valid.append(quiz)
        
        return valid
    
    def _compute_prerequisite_blockers(self, profile: UserProfile, node_id: str) -> Set[str]:
        """
        Compute which prerequisites are blocking a node.
        
        Args:
            profile: User profile
            node_id: Node to check
            
        Returns:
            Set of prerequisite node IDs that are not yet met
        """
        try:
            prereqs = self.kg.get_prerequisites(node_id)
        except Exception as e:
            logger.warning(f"Failed to get prerequisites for {node_id}: {e}")
            return set()
        
        blockers = set()
        for prereq_id in prereqs:
            score = profile.get_score(prereq_id)
            if score < PREREQUISITE_THRESHOLD:
                blockers.add(prereq_id)
        
        return blockers
    
    def _filter_recent_attempts(self, profile: UserProfile, quizzes: List[Quiz], window: int = 5) -> List[Quiz]:
        """
        Filter out quizzes that were recently attempted.
        
        Args:
            profile: User profile
            quizzes: Candidate quizzes
            window: Number of recent attempts to check
            
        Returns:
            Filtered list of quizzes
        """
        recent_quiz_ids = set()
        for attempt in profile.attempt_history[-window:]:
            recent_quiz_ids.add(attempt.quiz_id)
        
        return [q for q in quizzes if q.id not in recent_quiz_ids]
    
    def _prioritize_quizzes(self, profile: UserProfile, quizzes: List[Quiz]) -> List[Quiz]:
        """
        Prioritize quizzes by weakness and due reviews.
        
        Priority order:
        1. Quizzes covering weak nodes (negative scores)
        2. Quizzes covering nodes due for review
        3. Quizzes covering unmastered nodes
        4. Random selection from remaining
        
        Args:
            profile: User profile
            quizzes: Candidate quizzes
            
        Returns:
            Sorted list of quizzes (highest priority first)
        """
        scored_quizzes = []
        
        for quiz in quizzes:
            priority_score = self._calculate_priority_score(profile, quiz)
            scored_quizzes.append((quiz, priority_score))
        
        # Sort by priority score (descending)
        scored_quizzes.sort(key=lambda x: x[1], reverse=True)
        
        return [quiz for quiz, _ in scored_quizzes]
    
    def _calculate_priority_score(self, profile: UserProfile, quiz: Quiz) -> float:
        """
        Calculate priority score for a quiz.
        
        Higher score = higher priority.
        
        Args:
            profile: User profile
            quiz: Quiz to score
            
        Returns:
            Priority score
        """
        score = 0.0
        
        for node_id in quiz.linked_nodes:
            node_score = profile.get_score(node_id)
            
            # Weakness bonus (negative scores get high priority)
            if node_score < 0:
                score += abs(node_score) * 10  # High weight for weak nodes
            
            # Due review bonus
            if node_id in profile.schedule:
                entry = profile.schedule[node_id]
                if is_due_for_review(entry.next_review):
                    score += 5  # Moderate weight for due reviews
            
            # Unmastered bonus
            if node_score < MASTERY_THRESHOLD:
                score += (MASTERY_THRESHOLD - node_score)
        
        return score
    
    def _filter_by_difficulty(self, profile: UserProfile, quizzes: List[Quiz]) -> List[Quiz]:
        """
        Filter quizzes to match current skill level.
        
        Difficulty is determined by average score of linked nodes.
        
        Args:
            profile: User profile
            quizzes: Candidate quizzes
            
        Returns:
            Filtered list of quizzes
        """
        matched = []
        
        for quiz in quizzes:
            # Calculate average score for linked nodes
            if quiz.linked_nodes:
                avg_score = sum(profile.get_score(n) for n in quiz.linked_nodes) / len(quiz.linked_nodes)
            else:
                avg_score = 0.0
            
            # Determine target difficulty
            target_difficulty = self._score_to_difficulty(avg_score)
            
            # Allow ±1 difficulty level
            if abs(quiz.difficulty_level - target_difficulty) <= 1:
                matched.append(quiz)
        
        return matched
    
    def _score_to_difficulty(self, score: float) -> int:
        """
        Map a score to a difficulty level.
        
        Args:
            score: Node score
            
        Returns:
            Difficulty level (1-5)
        """
        for difficulty, (min_score, max_score) in DIFFICULTY_SCORE_RANGES.items():
            if min_score <= score < max_score:
                return difficulty
        
        # Default to medium
        return 3
    
    def _fallback_selection(self, profile: UserProfile, quizzes: List[Quiz]) -> Quiz:
        """
        Fallback quiz selection when no quiz meets all criteria.
        
        Args:
            profile: User profile
            quizzes: All available quizzes
            
        Returns:
            Selected quiz
            
        Raises:
            NoQuizAvailableError: If fallback also fails
        """
        logger.warning(f"Using fallback strategy: {FALLBACK_STRATEGY}")
        
        if FALLBACK_STRATEGY == "easiest":
            # Select easiest quiz
            easiest = min(quizzes, key=lambda q: q.difficulty_level)
            return easiest
        
        elif FALLBACK_STRATEGY == "random":
            # Random selection
            return random.choice(quizzes)
        
        elif FALLBACK_STRATEGY == "raise_error":
            raise NoQuizAvailableError("No suitable quiz found and fallback is disabled")
        
        else:
            # Default: random
            return random.choice(quizzes)

