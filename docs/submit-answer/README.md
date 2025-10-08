---
feature: submit-answer
type: overview
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/submit_answers_service.py", "student/api_views.py"]
last_validated: "2025-10-08"
---

# Submit Answer Feature Documentation

## Overview

The **Submit Answer** feature is a core component of the EZ RAM learning platform that processes student quiz submissions and automatically updates their learning progress. It integrates with the quiz suggestion engine and knowledge graph to provide adaptive learning through intelligent score adjustments.

## Quick Links

### Documentation

- **[Requirements](requirements/submit-answer-requirements.md)** - What the feature must do
- **[Design](design/submit-answer-design-2025-10-08.md)** - How it works (architecture, data flows)
- **[Testing](testing/submit-answer-test-strategy.md)** - Test plans and acceptance criteria
- **[ADR 0001](adr/0001-student-knowledge-relationship-tracking.md)** - Student-Knowledge relationship tracking decision

### Code

- **API View**: `student/api_views.py` → `SubmitAnswersAPI`
- **Service**: `student/services/submit_answers_service.py` → `SubmitAnswersService`
- **Serializers**: `student/serializers.py` → `SubmitAnswersRequestSerializer`, `AnswerSubmissionSerializer`
- **Models**: `student/neo_models.py`, `quiz/neo_models.py`, `knowledge/neo_models.py`
- **Tests**: `student/tests/test_submit_answers_*.py`

## Feature Summary

### What It Does

1. **Accepts quiz answer submissions** from students (single or batch)
2. **Validates answers** against correct choices stored in Neo4j
3. **Updates learning scores** using adaptive scoring algorithm
4. **Tracks knowledge graph adjustments** showing which topics were affected
5. **Persists student profiles** to JSON files for future sessions
6. **Returns detailed feedback** on score changes per knowledge node

### Key Capabilities

- ✅ Batch answer submission (up to 100 answers per request)
- ✅ Adaptive scoring based on correctness
- ✅ Knowledge graph integration
- ✅ Spaced repetition scheduling
- ✅ Prerequisite-aware score adjustments
- ✅ Resilient error handling (partial failures don't stop processing)
- ✅ Student-Knowledge relationship tracking (automatically updates Neo4j graph)
- ✅ Manual knowledge adjustment API (for teacher overrides and bulk imports)

## API Endpoint

### Request

```http
POST /student/v1/<ram_id>/submit-answers/
Authorization: Token <auth-token>
Content-Type: application/json

{
  "student_id": "123-ceo",
  "answers": [
    {
      "quiz_gid": "4:abc:123",
      "answer_gid": "4:def:456",
      "time_to_answer": 30,
      "use_helper": ["cut-choice"],
      "time_read_answer": 10,
      "choice_cutting": ["4:ghi:789"]
    }
  ]
}
```

### Response

```json
{
  "student": {
    "name": "ceo",
    "db_id": "123-ceo"
  },
  "graph_update": [
    {
      "graph_id": "4:node:123",
      "knowledge": "Simple Tense",
      "adjustment": 1.5
    },
    {
      "graph_id": "4:node:124",
      "knowledge": "Perfect Tense",
      "adjustment": -0.5
    }
  ]
}
```

## Architecture

### Layers

```
┌─────────────────────────────────────┐
│  API Layer (SubmitAnswersAPI)       │  ← Authentication, Validation
├─────────────────────────────────────┤
│  Service Layer (SubmitAnswersService)│  ← Business Logic
├─────────────────────────────────────┤
│  Data Layer                          │
│  - Neo4j (Graph Database)            │  ← Quiz, Knowledge, Student nodes
│  - JSON Files (Profile Storage)      │  ← UserProfile persistence
│  - Quiz Suggestion Engine            │  ← Scoring algorithm
└─────────────────────────────────────┘
```

### Data Flow

```
1. Client submits answers
   ↓
2. API validates request (serializer)
   ↓
3. Service loads student profile (JSON)
   ↓
4. Service loads knowledge graph (Neo4j)
   ↓
5. For each answer:
   - Fetch quiz from Neo4j
   - Check correctness
   - Calculate score adjustments
   - Update profile
   ↓
6. Save updated profile (JSON)
   ↓
7. Return graph updates to client
```

## Key Components

### SubmitAnswersService

**Purpose**: Core business logic for answer processing

**Key Methods**:

- `run()` - Main entry point, orchestrates entire flow
- `_get_student()` - Retrieve student node from Neo4j
- `_load_user_profile()` - Load or create student learning profile
- `_process_answer()` - Process single answer and calculate adjustments
- `_check_answer_correctness()` - Validate answer against correct choice
- `_save_user_profile()` - Persist profile to JSON file
- `_build_graph_updates()` - Format response with knowledge adjustments

### UserProfile (Pydantic Model)

**Purpose**: Student learning state

**Key Fields**:

- `user_id` - Student identifier
- `scores` - Dict mapping knowledge node IDs to scores (range: -5 to 10)
- `schedule` - Spaced repetition schedule per knowledge node
- `attempt_history` - Recent quiz attempts
- `total_attempts` - Total quiz count
- `total_correct` - Correct answer count

### KnowledgeGraph (NetworkX)

**Purpose**: Knowledge dependency structure

**Key Methods**:

- `from_neo4j()` - Load graph from Neo4j
- `get_prerequisites()` - Get prerequisite nodes
- `is_prerequisite_met()` - Check if prerequisites are mastered
- `get_topological_order()` - Get learning order

## Scoring Algorithm

### Correct Answer

1. Increase score for linked knowledge nodes
2. Apply prerequisite bonuses (if prerequisites mastered)
3. Update spaced repetition schedule (increase interval)
4. Record successful attempt

### Incorrect Answer

1. Decrease score for linked knowledge nodes
2. Penalize related prerequisite nodes
3. Update spaced repetition schedule (reset interval)
4. Record failed attempt

### Score Bounds

- Minimum: -5 (needs significant review)
- Maximum: 10 (mastered)
- Mastery threshold: 7+

## Data Storage

### JSON Files (Student Profiles)

**Location**: `data/profiles/{student_id}.json`

**Purpose**: Fast access to student learning state

**Example**:

```json
{
  "user_id": "123-ceo",
  "scores": {
    "4:node:123": 5.5,
    "4:node:124": 2.0
  },
  "schedule": {
    "4:node:123": {
      "interval_index": 3,
      "next_review": "2025-10-15T10:00:00Z"
    }
  },
  "attempt_history": [...],
  "total_attempts": 42,
  "total_correct": 35,
  "last_updated": "2025-10-08T14:30:00Z"
}
```

### Neo4j Graph

**Nodes**:

- `Student` - Student account
- `Quiz` - Quiz questions
- `Choice` - Answer choices
- `Knowledge` - Knowledge concepts

**Relationships**:

- `Quiz -[HAS_CHOICE]-> Choice`
- `Quiz -[RELATED_TO]-> Knowledge`
- `Choice -[RELATED_TO]-> Knowledge`
- `Knowledge -[DEPENDS_ON]-> Knowledge`
- `Student -[RELATED_TO]-> Knowledge` (planned - see ADR 0001)

## Error Handling

### Input Validation (400)

- Missing `student_id`
- Empty `answers` array
- Invalid answer format

### Business Logic (Logged, Continue)

- Quiz not found → Skip answer, log warning
- Answer choice not found → Mark incorrect, log warning
- Profile load failure → Create new profile

### System Errors (500)

- Knowledge graph loading failure → Abort request
- Neo4j connection failure → Abort request
- File system errors → Abort request

## Performance

### Current Limits

- **Batch size**: Up to 100 answers per request
- **Processing time**: ~5 seconds for 10 answers
- **Knowledge graph**: Tested with 1000+ nodes
- **Concurrent users**: Limited by Neo4j connection pool

### Optimization Strategies

- Knowledge graph loaded once per request (not per answer)
- Answers processed independently (failures don't cascade)
- Profile saved once at end (not per answer)
- Future: Batch Neo4j queries, parallel processing

## Testing

### Test Coverage

- **Unit Tests**: Service methods, serializers, helpers
- **Integration Tests**: Service + Neo4j, Service + Files
- **API Tests**: Full request/response flow
- **Performance Tests**: Large batches, large graphs

### Running Tests

```bash
# All tests
python manage.py test student.tests.test_submit_answers_*

# Specific test
python manage.py test student.tests.test_submit_answers_service.TestSubmitAnswersService.test_run_single_answer

# With coverage
coverage run --source='student' manage.py test student.tests
coverage report
```

See [Testing Strategy](testing/submit-answer-test-strategy.md) for details.

## Future Enhancements

### 1. Student-Knowledge Relationships (ADR 0001)

**Status**: Proposed
**Goal**: Create graph relationships between students and knowledge nodes
**Benefits**: Learning path visualization, cohort analysis, graph queries

### 2. Advanced Analytics

- Time-based performance trends
- Helper usage pattern analysis
- Choice elimination strategy tracking
- Learning velocity metrics

### 3. Real-time Updates

- WebSocket support for live score updates
- Push notifications for achievements
- Real-time leaderboards

### 4. Performance Optimization

- Redis caching for profiles and graphs
- Batch Neo4j operations
- Async processing for large submissions
- Connection pooling optimization

## Troubleshooting

### Issue: Profile not saving

**Cause**: File system permissions or disk space
**Solution**: Check `data/profiles/` directory permissions, ensure disk space

### Issue: Knowledge graph loading fails

**Cause**: Neo4j connection issue or missing nodes
**Solution**: Verify Neo4j is running, check connection settings, ensure knowledge nodes exist

### Issue: Scores not updating

**Cause**: Quiz not linked to knowledge nodes
**Solution**: Verify quiz has `RELATED_TO` relationships to knowledge nodes

### Issue: Slow performance

**Cause**: Large knowledge graph or many answers
**Solution**: Reduce batch size, optimize Neo4j queries, consider caching

## Related Features

- **[Suggest Quiz](../suggest-quiz/)** - Uses student profile to suggest next quiz
- **[Get Student Graph](../get-student-graph/)** - Retrieves student's knowledge graph with scores
- **[Quiz Suggestion Engine](../../student/quiz_suggestion/)** - Adaptive learning algorithm

## Changelog

### 2025-10-08

- Initial documentation created
- Requirements, design, and testing docs added
- ADR 0001 for Student-Knowledge relationships proposed

## Contact

**Feature Owner**: @ceofourfactplus
**Code Location**: `student/services/submit_answers_service.py`
**Documentation**: `docs/submit-answer/`
