"""
Spaced repetition scheduling utilities.

This module implements SM-2 inspired scheduling for optimal review timing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
from student.quiz_suggestion.engine.policies import (
    REVIEW_INTERVALS,
    MAX_INTERVAL_INDEX,
    LAPSE_THRESHOLD,
)

logger = logging.getLogger(__name__)


def calculate_next_review(
    interval_index: int,
    is_correct: bool,
    accuracy: float,
    last_reviewed: Optional[datetime] = None
) -> tuple[int, datetime]:
    """
    Calculate the next review date based on performance.
    
    This implements an SM-2 inspired algorithm:
    - Correct answer: advance to next interval
    - Incorrect answer: reset to first interval
    - Low accuracy: reset to earlier interval
    
    Args:
        interval_index: Current index in REVIEW_INTERVALS
        is_correct: Whether the last attempt was correct
        accuracy: Recent accuracy (0.0 to 1.0)
        last_reviewed: When the node was last reviewed (default: now)
        
    Returns:
        Tuple of (new_interval_index, next_review_datetime)
    """
    if last_reviewed is None:
        last_reviewed = datetime.now(timezone.utc)
    
    # Determine new interval index
    if not is_correct:
        # Incorrect: reset to first interval
        new_index = 0
        logger.debug(f"Incorrect answer, resetting to interval 0")
    elif accuracy < LAPSE_THRESHOLD:
        # Low accuracy: move back one interval (but not below 0)
        new_index = max(0, interval_index - 1)
        logger.debug(f"Low accuracy ({accuracy:.2%}), moving back to interval {new_index}")
    else:
        # Correct and good accuracy: advance to next interval
        new_index = min(interval_index + 1, MAX_INTERVAL_INDEX)
        logger.debug(f"Correct answer, advancing to interval {new_index}")
    
    # Calculate next review date
    days = REVIEW_INTERVALS[new_index]
    next_review = last_reviewed + timedelta(days=days)
    
    logger.debug(f"Next review in {days} days: {next_review.isoformat()}")
    
    return new_index, next_review


def is_due_for_review(next_review: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """
    Check if a node is due for review.
    
    Args:
        next_review: Scheduled review datetime
        now: Current datetime (default: now)
        
    Returns:
        True if due for review, False otherwise
    """
    if next_review is None:
        # Never reviewed: always due
        return True
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure both are timezone-aware
    if next_review.tzinfo is None:
        next_review = next_review.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    return now >= next_review


def days_until_review(next_review: Optional[datetime], now: Optional[datetime] = None) -> int:
    """
    Calculate days until next review.
    
    Args:
        next_review: Scheduled review datetime
        now: Current datetime (default: now)
        
    Returns:
        Number of days (negative if overdue, 0 if due today)
    """
    if next_review is None:
        return 0  # Due now
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure both are timezone-aware
    if next_review.tzinfo is None:
        next_review = next_review.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    delta = next_review - now
    return delta.days


def update_streak(current_streak: int, is_correct: bool) -> int:
    """
    Update the streak counter.
    
    Args:
        current_streak: Current streak count
        is_correct: Whether the last attempt was correct
        
    Returns:
        New streak count
    """
    if is_correct:
        return current_streak + 1
    else:
        return 0


def get_interval_days(interval_index: int) -> int:
    """
    Get the number of days for a given interval index.
    
    Args:
        interval_index: Index in REVIEW_INTERVALS
        
    Returns:
        Number of days
    """
    if interval_index < 0:
        return REVIEW_INTERVALS[0]
    elif interval_index >= len(REVIEW_INTERVALS):
        return REVIEW_INTERVALS[-1]
    else:
        return REVIEW_INTERVALS[interval_index]


def estimate_mastery_time(current_interval_index: int, target_interval_index: Optional[int] = None) -> int:
    """
    Estimate days until mastery (reaching target interval).
    
    Args:
        current_interval_index: Current interval index
        target_interval_index: Target interval (default: max interval)
        
    Returns:
        Estimated days until mastery
    """
    if target_interval_index is None:
        target_interval_index = MAX_INTERVAL_INDEX
    
    if current_interval_index >= target_interval_index:
        return 0
    
    # Sum all intervals from current to target
    total_days = sum(
        REVIEW_INTERVALS[i]
        for i in range(current_interval_index, target_interval_index + 1)
    )
    
    return total_days

