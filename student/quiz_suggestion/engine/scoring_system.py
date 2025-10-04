"""
Scoring system for tracking learning progress.

This module handles score updates, prerequisite bonuses, and spaced repetition
scheduling based on quiz performance.
"""

from datetime import datetime, timezone
from typing import List
import logging
from student.quiz_suggestion.models.user_profile import UserProfile, ScheduleEntry, AttemptRecord
from student.quiz_suggestion.models.knowledge_graph import KnowledgeGraph
from student.quiz_suggestion.engine.policies import (
    CORRECT_DELTA,
    INCORRECT_DELTA,
    PREREQ_BONUS,
    SCORE_BOUNDS,
    MASTERY_THRESHOLD,
)
from student.quiz_suggestion.utils.schedule import (
    calculate_next_review,
    update_streak,
)

logger = logging.getLogger(__name__)


class ScoringSystem:
    """
    Manages score updates and spaced repetition scheduling.
    
    This class handles:
    - Score updates based on quiz performance
    - Prerequisite bonuses
    - Spaced repetition scheduling
    - Streak tracking
    
    Example:
        scorer = ScoringSystem(knowledge_graph)
        profile = scorer.apply_correct(profile, ["python_basics"], quiz_id="q1", difficulty=3)
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        Initialize the scoring system.
        
        Args:
            knowledge_graph: The knowledge graph for prerequisite lookups
        """
        self.kg = knowledge_graph
    
    def apply_correct(
        self,
        profile: UserProfile,
        node_ids: List[str],
        quiz_id: str,
        difficulty: int
    ) -> UserProfile:
        """
        Apply score updates for a correct answer.
        
        This:
        1. Adds +1.0 to all linked nodes
        2. Adds +0.1 to immediate prerequisites
        3. Updates spaced repetition schedule
        4. Records the attempt
        
        Args:
            profile: User profile to update
            node_ids: Knowledge nodes linked to the quiz
            quiz_id: Quiz identifier
            difficulty: Quiz difficulty level
            
        Returns:
            Updated user profile
        """
        logger.info(f"Applying correct answer for quiz {quiz_id}, nodes: {node_ids}")
        
        # Update scores for linked nodes
        for node_id in node_ids:
            old_score = profile.get_score(node_id)
            new_score = min(old_score + CORRECT_DELTA, SCORE_BOUNDS[1])
            profile.set_score(node_id, new_score)
            
            logger.debug(f"  {node_id}: {old_score:.2f} -> {new_score:.2f}")
            
            # Update spaced repetition schedule
            self._update_schedule(profile, node_id, is_correct=True)
        
        # Apply prerequisite bonus
        self._bump_prerequisites(profile, node_ids, PREREQ_BONUS)
        
        # Record attempt
        profile.add_attempt(AttemptRecord(
            quiz_id=quiz_id,
            node_ids=node_ids,
            is_correct=True,
            difficulty_level=difficulty
        ))
        
        return profile
    
    def apply_incorrect(
        self,
        profile: UserProfile,
        node_ids: List[str],
        quiz_id: str,
        difficulty: int
    ) -> UserProfile:
        """
        Apply score updates for an incorrect answer.
        
        This:
        1. Adds -1.0 to all linked nodes
        2. Does NOT penalize prerequisites
        3. Resets spaced repetition schedule
        4. Records the attempt
        
        Args:
            profile: User profile to update
            node_ids: Knowledge nodes linked to the quiz
            quiz_id: Quiz identifier
            difficulty: Quiz difficulty level
            
        Returns:
            Updated user profile
        """
        logger.info(f"Applying incorrect answer for quiz {quiz_id}, nodes: {node_ids}")
        
        # Update scores for linked nodes
        for node_id in node_ids:
            old_score = profile.get_score(node_id)
            new_score = max(old_score + INCORRECT_DELTA, SCORE_BOUNDS[0])
            profile.set_score(node_id, new_score)
            
            logger.debug(f"  {node_id}: {old_score:.2f} -> {new_score:.2f}")
            
            # Update spaced repetition schedule (reset)
            self._update_schedule(profile, node_id, is_correct=False)
        
        # NO prerequisite penalty
        
        # Record attempt
        profile.add_attempt(AttemptRecord(
            quiz_id=quiz_id,
            node_ids=node_ids,
            is_correct=False,
            difficulty_level=difficulty
        ))
        
        return profile
    
    def _bump_prerequisites(self, profile: UserProfile, node_ids: List[str], delta: float):
        """
        Add a small bonus to immediate prerequisites.
        
        This reinforces foundational concepts when advanced concepts are mastered.
        
        Args:
            profile: User profile to update
            node_ids: Nodes whose prerequisites should be bumped
            delta: Amount to add to prerequisite scores
        """
        prereq_set = set()
        
        # Collect all immediate prerequisites
        for node_id in node_ids:
            try:
                prereqs = self.kg.get_prerequisites(node_id)
                prereq_set.update(prereqs)
            except Exception as e:
                logger.warning(f"Failed to get prerequisites for {node_id}: {e}")
                continue
        
        # Apply bonus to each prerequisite
        for prereq_id in prereq_set:
            old_score = profile.get_score(prereq_id)
            new_score = min(old_score + delta, SCORE_BOUNDS[1])
            profile.set_score(prereq_id, new_score)
            
            logger.debug(f"  Prereq bonus: {prereq_id}: {old_score:.2f} -> {new_score:.2f}")
    
    def _update_schedule(self, profile: UserProfile, node_id: str, is_correct: bool):
        """
        Update spaced repetition schedule for a node.
        
        Args:
            profile: User profile to update
            node_id: Node to update schedule for
            is_correct: Whether the attempt was correct
        """
        # Get current schedule entry or create new one
        if node_id in profile.schedule:
            entry = profile.schedule[node_id]
        else:
            entry = ScheduleEntry()
        
        # Get recent accuracy for this node
        accuracy = profile.get_accuracy(node_id, n=10)
        
        # Calculate next review
        new_index, next_review = calculate_next_review(
            interval_index=entry.interval_index,
            is_correct=is_correct,
            accuracy=accuracy,
            last_reviewed=datetime.now(timezone.utc)
        )
        
        # Update streak
        new_streak = update_streak(entry.streak, is_correct)
        
        # Update entry
        entry.interval_index = new_index
        entry.next_review = next_review
        entry.last_reviewed = datetime.now(timezone.utc)
        entry.streak = new_streak
        
        profile.schedule[node_id] = entry
        
        logger.debug(
            f"  Schedule updated for {node_id}: "
            f"interval={new_index}, next_review={next_review.isoformat()}, streak={new_streak}"
        )
    
    def is_mastered(self, profile: UserProfile, node_id: str) -> bool:
        """
        Check if a node is mastered.
        
        Args:
            profile: User profile
            node_id: Node to check
            
        Returns:
            True if mastered (score >= threshold)
        """
        score = profile.get_score(node_id)
        return score >= MASTERY_THRESHOLD
    
    def get_mastered_nodes(self, profile: UserProfile) -> List[str]:
        """
        Get all mastered nodes.
        
        Args:
            profile: User profile
            
        Returns:
            List of mastered node IDs
        """
        return [
            node_id for node_id, score in profile.scores.items()
            if score >= MASTERY_THRESHOLD
        ]
    
    def get_weak_nodes(self, profile: UserProfile) -> List[str]:
        """
        Get all weak nodes (negative scores).
        
        Args:
            profile: User profile
            
        Returns:
            List of weak node IDs, sorted by score (weakest first)
        """
        weak = [
            (node_id, score) for node_id, score in profile.scores.items()
            if score < 0
        ]
        # Sort by score (ascending)
        weak.sort(key=lambda x: x[1])
        return [node_id for node_id, _ in weak]

