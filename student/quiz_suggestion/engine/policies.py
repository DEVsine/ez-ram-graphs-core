"""
Configuration constants and policies for the quiz suggestion engine.

These values control the behavior of the adaptive learning system.
Adjust these to tune the recommendation algorithm.
"""

# ============================================================================
# Scoring System
# ============================================================================

# Mastery threshold: score >= this value means the concept is mastered
MASTERY_THRESHOLD = 3.0

# Score bounds [min, max]
# Scores are clamped to this range
SCORE_BOUNDS = (-5.0, 10.0)

# Score delta for correct answer
CORRECT_DELTA = 1.0

# Score delta for incorrect answer
INCORRECT_DELTA = -1.0

# Bonus added to immediate prerequisites on correct answer
# This helps reinforce foundational concepts
PREREQ_BONUS = 0.1

# ============================================================================
# Spaced Repetition
# ============================================================================

# Review intervals in days (SM-2 inspired)
# After each successful review, move to the next interval
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60, 120]

# Maximum interval index (stays at this level after reaching it)
MAX_INTERVAL_INDEX = len(REVIEW_INTERVALS) - 1

# Lapse threshold: if accuracy drops below this, reset interval
LAPSE_THRESHOLD = 0.5

# ============================================================================
# Difficulty Adaptation
# ============================================================================

# Difficulty levels: 1 (easiest) to 5 (hardest)
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5

# Score ranges for difficulty mapping
# These determine which difficulty level to suggest based on current score
DIFFICULTY_SCORE_RANGES = {
    1: (-5.0, -2.0),   # Very weak: easiest quizzes
    2: (-2.0, 0.0),    # Weak: easy quizzes
    3: (0.0, 2.0),     # Learning: medium quizzes
    4: (2.0, 4.0),     # Strong: hard quizzes
    5: (4.0, 10.0),    # Mastered: hardest quizzes
}

# Accuracy ranges for difficulty adjustment
# If recent accuracy is in these ranges, adjust difficulty
DIFFICULTY_ACCURACY_RANGES = {
    "too_easy": 0.9,      # If accuracy > 90%, increase difficulty
    "too_hard": 0.4,      # If accuracy < 40%, decrease difficulty
}

# ============================================================================
# Suggestion Engine
# ============================================================================

# Number of recent attempts to consider for accuracy calculation
RECENT_ATTEMPTS_WINDOW = 10

# Minimum number of attempts before adjusting difficulty
MIN_ATTEMPTS_FOR_ADJUSTMENT = 5

# Weight for weakness-first selection (higher = prioritize weaker nodes more)
WEAKNESS_WEIGHT = 2.0

# Weight for due reviews (higher = prioritize overdue reviews more)
DUE_REVIEW_WEIGHT = 1.5

# Maximum number of quizzes to consider in each selection round
# This limits the search space for performance
MAX_QUIZ_CANDIDATES = 100

# ============================================================================
# Prerequisite Validation
# ============================================================================

# Minimum score required for a prerequisite to be considered "met"
# Nodes with score < this are considered blockers
PREREQUISITE_THRESHOLD = 0.0

# Whether to allow "soft" prerequisites (can attempt even if not fully met)
ALLOW_SOFT_PREREQUISITES = False

# ============================================================================
# Attempt History
# ============================================================================

# Maximum number of attempts to store per user
# Older attempts are discarded to save memory
ATTEMPT_HISTORY_LEN = 200

# Whether to track detailed attempt metadata (timestamps, quiz IDs, etc.)
TRACK_DETAILED_HISTORY = True

# ============================================================================
# Fallback Behavior
# ============================================================================

# What to do when no quiz meets all criteria
# Options: "random", "easiest", "most_recent", "raise_error"
FALLBACK_STRATEGY = "easiest"

# Whether to allow fallback to already-mastered content
ALLOW_MASTERED_FALLBACK = False

# ============================================================================
# Performance Tuning
# ============================================================================

# Enable caching for graph traversal queries
ENABLE_GRAPH_CACHE = True

# Cache TTL in seconds (0 = no expiration)
GRAPH_CACHE_TTL = 300  # 5 minutes

# Maximum cache size (number of entries)
GRAPH_CACHE_SIZE = 1000

# ============================================================================
# Logging
# ============================================================================

# Log level for suggestion decisions
# Options: "DEBUG", "INFO", "WARNING", "ERROR"
LOG_LEVEL = "INFO"

# Whether to log detailed scoring information
LOG_SCORE_DETAILS = False

# Whether to log prerequisite validation details
LOG_PREREQUISITE_DETAILS = False

