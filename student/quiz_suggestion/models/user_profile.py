"""
User Profile model for tracking learning progress.

This is a Pydantic model (not stored in Neo4j) that tracks runtime state
for a learner, including scores, scheduling, and attempt history.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import json
from pathlib import Path


class AttemptRecord(BaseModel):
    """Record of a single quiz attempt"""

    quiz_id: str
    node_ids: List[str]  # Knowledge nodes linked to this quiz
    is_correct: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    difficulty_level: int

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ScheduleEntry(BaseModel):
    """Spaced repetition schedule for a knowledge node"""

    interval_index: int = 0  # Index into REVIEW_INTERVALS
    next_review: Optional[datetime] = None
    last_reviewed: Optional[datetime] = None
    streak: int = 0  # Consecutive correct reviews

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserProfile(BaseModel):
    """
    User learning profile with scores and scheduling.

    This model tracks:
    - Scores for each knowledge node (float in range [-5, 10])
    - Spaced repetition schedule for each node
    - Attempt history
    - Metadata (last updated, total attempts, etc.)

    Example:
        profile = UserProfile(user_id="student123")
        profile.scores["python_basics"] = 2.5
        profile.schedule["python_basics"] = ScheduleEntry(
            interval_index=2,
            next_review=datetime.now() + timedelta(days=7)
        implement this api)
    """

    user_id: str
    scores: Dict[str, float] = Field(default_factory=dict)
    schedule: Dict[str, ScheduleEntry] = Field(default_factory=dict)
    attempt_history: List[AttemptRecord] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_attempts: int = 0
    total_correct: int = 0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v):
        """Ensure all scores are within bounds [-5, 10]"""
        from student.quiz_suggestion.engine.policies import SCORE_BOUNDS

        for node_id, score in v.items():
            if not (SCORE_BOUNDS[0] <= score <= SCORE_BOUNDS[1]):
                raise ValueError(
                    f"Score {score} for node {node_id} is outside bounds {SCORE_BOUNDS}"
                )
        return v

    def get_score(self, node_id: str) -> float:
        """Get score for a node (default 0.0 if not seen)"""
        return self.scores.get(node_id, 0.0)

    def set_score(self, node_id: str, score: float):
        """Set score for a node (clamped to bounds)"""
        from student.quiz_suggestion.engine.policies import SCORE_BOUNDS

        self.scores[node_id] = max(SCORE_BOUNDS[0], min(SCORE_BOUNDS[1], score))
        self.last_updated = datetime.now(timezone.utc)

    def add_attempt(self, record: AttemptRecord):
        """Add an attempt record to history"""
        from student.quiz_suggestion.engine.policies import ATTEMPT_HISTORY_LEN

        self.attempt_history.append(record)
        self.total_attempts += 1
        if record.is_correct:
            self.total_correct += 1

        # Trim history if too long
        if len(self.attempt_history) > ATTEMPT_HISTORY_LEN:
            self.attempt_history = self.attempt_history[-ATTEMPT_HISTORY_LEN:]

        self.last_updated = datetime.now(timezone.utc)

    def get_recent_attempts(self, node_id: str, n: int = 10) -> List[AttemptRecord]:
        """Get the N most recent attempts for a specific node"""
        attempts = [a for a in self.attempt_history if node_id in a.node_ids]
        return attempts[-n:]

    def get_accuracy(self, node_id: Optional[str] = None, n: int = 10) -> float:
        """
        Calculate accuracy for recent attempts.

        Args:
            node_id: If provided, calculate accuracy for this node only
            n: Number of recent attempts to consider

        Returns:
            Accuracy as a float in [0, 1], or 0.0 if no attempts
        """
        if node_id:
            attempts = self.get_recent_attempts(node_id, n)
        else:
            attempts = self.attempt_history[-n:]

        if not attempts:
            return 0.0

        correct = sum(1 for a in attempts if a.is_correct)
        return correct / len(attempts)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create from dictionary"""
        # Convert schedule entries
        if "schedule" in data:
            data["schedule"] = {
                k: ScheduleEntry(**v) if isinstance(v, dict) else v
                for k, v in data["schedule"].items()
            }

        # Convert attempt records
        if "attempt_history" in data:
            data["attempt_history"] = [
                AttemptRecord(**a) if isinstance(a, dict) else a
                for a in data["attempt_history"]
            ]

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "UserProfile":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, path: Path):
        """Save profile to JSON file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, path: Path) -> "UserProfile":
        """Load profile from JSON file"""
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def __repr__(self) -> str:
        return (
            f"UserProfile(user_id={self.user_id!r}, "
            f"nodes={len(self.scores)}, "
            f"attempts={self.total_attempts}, "
            f"accuracy={self.get_accuracy():.2%})"
        )
