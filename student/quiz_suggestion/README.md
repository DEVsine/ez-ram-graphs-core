# Quiz Suggestion Engine

An adaptive quiz selection system that personalizes learning based on individual progress, knowledge graph structure, and spaced repetition principles.

## Features

✅ **Weakness-First Selection** - Prioritizes concepts with low scores  
✅ **Prerequisite Validation** - Blocks advanced concepts until foundations are met  
✅ **Difficulty Adaptation** - Matches quiz difficulty to current skill level  
✅ **Spaced Repetition** - SM-2 inspired scheduling for optimal review timing  
✅ **Progress Tracking** - Detailed analytics on learning progress  
✅ **Neo4j Integration** - Uses existing Knowledge graph and Quiz models  

## Quick Start

### 1. Installation

Dependencies are already installed via `pyproject.toml`:
- `networkx>=3.0` - Graph algorithms
- `pydantic>=2.0` - Data validation

### 2. Basic Usage

```python
from student.quiz_suggestion import (
    suggest_next_quiz,
    update_scores,
    get_learning_progress,
    KnowledgeGraph,
    UserProfile,
    load_quizzes_from_neo4j,
)

# Load data
profile = UserProfile(user_id="student123")
kg = KnowledgeGraph.from_neo4j()
quizzes = load_quizzes_from_neo4j()

# Get suggestion
quiz = suggest_next_quiz(profile, kg, quizzes)
print(f"Next quiz: {quiz.content.stem}")

# After user answers
is_correct = True  # User got it right
profile = update_scores(profile, quiz, is_correct, kg)

# Check progress
progress = get_learning_progress(profile, kg)
print(f"Mastered: {len(progress['mastered_nodes'])} nodes")
print(f"Accuracy: {progress['accuracy']:.1%}")
```

### 3. Django Management Command

Test the engine interactively:

```bash
# Run interactive quiz session
python manage.py quiz_suggestion test --user=student123 --quizzes=10

# Check progress
python manage.py quiz_suggestion progress --user=student123

# Show graph statistics
python manage.py quiz_suggestion stats

# Run demo with simulated answers
python manage.py quiz_suggestion demo

# Reset progress
python manage.py quiz_suggestion reset --user=student123
```

## Architecture

```
student/quiz_suggestion/
├── __init__.py              # Public API
├── exceptions.py            # Custom exceptions
├── cli_helpers.py           # CLI utilities
│
├── models/
│   ├── user_profile.py      # Pydantic UserProfile (runtime state)
│   ├── knowledge_graph.py   # NetworkX wrapper for Neo4j
│   └── adapters.py          # Neo4j ↔ Pydantic converters
│
├── engine/
│   ├── policies.py          # Configuration constants
│   ├── scoring_system.py    # Score updates & scheduling
│   └── suggestion_engine.py # Core recommendation logic
│
└── utils/
    ├── graph_traversal.py   # Cached Neo4j queries
    └── schedule.py          # Spaced repetition intervals
```

## Core Concepts

### 1. User Profile

Tracks learning progress for a user:
- **Scores**: Float values in range [-5, 10] for each knowledge node
- **Schedule**: Spaced repetition schedule for each node
- **Attempt History**: Record of all quiz attempts

```python
profile = UserProfile(user_id="student123")
profile.set_score("python_basics", 2.5)
print(profile.get_accuracy())  # Overall accuracy
```

### 2. Knowledge Graph

NetworkX-based representation of the knowledge graph:
- **Nodes**: Knowledge concepts
- **Edges**: DEPENDS_ON relationships (prerequisites)

```python
kg = KnowledgeGraph.from_neo4j()
prereqs = kg.get_prerequisites("python_functions")
print(f"Must learn: {prereqs}")
```

### 3. Scoring Rules

- **Correct answer**: +1.0 to linked nodes, +0.1 to prerequisites
- **Incorrect answer**: -1.0 to linked nodes, no penalty to prerequisites
- **Bounds**: Scores clamped to [-5, 10]
- **Mastery**: Score >= 3.0

### 4. Spaced Repetition

SM-2 inspired intervals (in days):
```
[1, 3, 7, 14, 30, 60, 120]
```

- Correct answer → advance to next interval
- Incorrect answer → reset to first interval
- Low accuracy → move back one interval

### 5. Difficulty Adaptation

Difficulty levels (1-5) mapped to score ranges:

| Difficulty | Score Range | Description |
|------------|-------------|-------------|
| 1 | -5.0 to -2.0 | Very weak: easiest quizzes |
| 2 | -2.0 to 0.0 | Weak: easy quizzes |
| 3 | 0.0 to 2.0 | Learning: medium quizzes |
| 4 | 2.0 to 4.0 | Strong: hard quizzes |
| 5 | 4.0 to 10.0 | Mastered: hardest quizzes |

## Configuration

Edit `student/quiz_suggestion/engine/policies.py` to tune the algorithm:

```python
# Mastery threshold
MASTERY_THRESHOLD = 3.0

# Score bounds
SCORE_BOUNDS = (-5.0, 10.0)

# Prerequisite bonus
PREREQ_BONUS = 0.1

# Review intervals (days)
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60, 120]

# Fallback strategy when no quiz meets criteria
FALLBACK_STRATEGY = "easiest"  # or "random", "raise_error"
```

## API Reference

### Main Functions

#### `suggest_next_quiz(profile, knowledge_graph, quizzes) -> Quiz`

Suggest the next quiz for a user.

**Raises**: `NoQuizAvailableError` if no suitable quiz found

#### `update_scores(profile, quiz, is_correct, knowledge_graph) -> UserProfile`

Update user profile after a quiz attempt.

**Returns**: Updated user profile

#### `get_learning_progress(profile, knowledge_graph) -> dict`

Get learning progress statistics.

**Returns**:
- `mastered_nodes`: List of mastered node IDs
- `in_progress_nodes`: List of nodes being learned
- `weak_nodes`: List of weak nodes
- `coverage_pct`: Percentage of nodes attempted
- `total_attempts`: Total quiz attempts
- `accuracy`: Overall accuracy
- `next_due_reviews`: Number of nodes due for review

#### `reset_user_progress(user_id) -> UserProfile`

Reset all progress for a user.

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest student/quiz_suggestion/test_basic.py -v

# Run specific test
python -m pytest student/quiz_suggestion/test_basic.py::test_user_profile_creation -v
```

## Performance

- **Target**: <50ms per suggestion with 1000+ nodes
- **Caching**: LRU cache for graph traversal queries
- **Optimization**: NetworkX for efficient graph algorithms

## Troubleshooting

### No quizzes available

**Problem**: `NoQuizAvailableError` raised

**Solutions**:
1. Check if quizzes exist in Neo4j: `Quiz.nodes.count()`
2. Check if quizzes have `difficulty_level` and `quiz_type` fields
3. Check if quizzes are linked to knowledge nodes via `related_to`
4. Adjust `FALLBACK_STRATEGY` in policies.py

### Circular dependencies

**Problem**: `CycleDetectedError` raised

**Solutions**:
1. Check knowledge graph for cycles: `python manage.py quiz_suggestion stats`
2. Fix cycles in Neo4j by removing circular DEPENDS_ON relationships
3. Use `kg.find_cycles()` to identify problematic nodes

### Low accuracy

**Problem**: User keeps getting quizzes wrong

**Solutions**:
1. Check if difficulty is too high
2. Verify prerequisites are properly set
3. Review weak nodes: `python manage.py quiz_suggestion progress --user=<id>`

## Examples

### Example 1: Simple Quiz Session

```python
from student.quiz_suggestion import *

# Setup
profile = UserProfile(user_id="alice")
kg = KnowledgeGraph.from_neo4j()
quizzes = load_quizzes_from_neo4j()

# Quiz loop
for i in range(10):
    quiz = suggest_next_quiz(profile, kg, quizzes)
    print(f"\nQuiz {i+1}: {quiz.content.stem}")
    
    # Simulate answer (replace with actual user input)
    is_correct = input("Correct? (y/n): ").lower() == 'y'
    
    profile = update_scores(profile, quiz, is_correct, kg)
    print(f"Score updated. Accuracy: {profile.get_accuracy():.1%}")

# Save profile
profile.save_to_file(Path("data/profiles/alice.json"))
```

### Example 2: Progress Dashboard

```python
from student.quiz_suggestion import *

profile = UserProfile.load_from_file(Path("data/profiles/alice.json"))
kg = KnowledgeGraph.from_neo4j()

progress = get_learning_progress(profile, kg)

print(f"📊 Learning Progress for {profile.user_id}")
print(f"Mastered: {len(progress['mastered_nodes'])} nodes")
print(f"In Progress: {len(progress['in_progress_nodes'])} nodes")
print(f"Weak: {len(progress['weak_nodes'])} nodes")
print(f"Coverage: {progress['coverage_pct']:.1f}%")
print(f"Accuracy: {progress['accuracy']:.1%}")
print(f"Due Reviews: {progress['next_due_reviews']}")
```

## License

Part of the EZ RAM project.

