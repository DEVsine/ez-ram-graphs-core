---
feature: submit-answer
type: requirement
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/submit_answers_service.py", "student/api_views.py", "student/serializers.py"]
related_docs: ["design/submit-answer-design-2025-10-08.md", "testing/submit-answer-test-strategy.md"]
last_validated: "2025-10-08"
---

# Submit Answer - Requirements

## Summary

The Submit Answer feature allows students to submit quiz answers and automatically updates their learning progress based on correctness. The system tracks knowledge mastery through a sophisticated scoring algorithm that adjusts student profiles and maintains a knowledge graph of their learning journey.

## Functional Requirements

### FR-1: Answer Submission

**Priority**: MUST HAVE

Students must be able to submit one or more quiz answers in a single request.

**Acceptance Criteria**:

- Accept multiple answer submissions in a single API call
- Each answer must include:
  - `quiz_gid`: The graph ID of the quiz question
  - `answer_gid`: The graph ID of the selected answer choice
  - `time_to_answer` (optional): Time taken to answer in seconds
  - `use_helper` (optional): List of helpers used (e.g., "cut-choice", "two-answer")
  - `time_read_answer` (optional): Time spent reading the answer
  - `choice_cutting` (optional): List of eliminated choice IDs
- Student must be identified by `student_id` (db_id)

### FR-2: Answer Validation

**Priority**: MUST HAVE

The system must validate each submitted answer against the correct answer stored in the knowledge graph.

**Acceptance Criteria**:

- Retrieve quiz from Neo4j using `quiz_gid`
- Compare submitted `answer_gid` with correct choice in quiz
- Return boolean correctness for each answer
- Handle missing quizzes gracefully (log warning, continue processing other answers)
- Handle missing choices gracefully (log warning, mark as incorrect)

### FR-3: Score Updates

**Priority**: MUST HAVE

Student learning scores must be updated based on answer correctness using the quiz suggestion engine.

**Acceptance Criteria**:

- Load or create student UserProfile from JSON file storage
- Load knowledge graph from Neo4j
- For each answer:
  - Calculate score adjustments for linked knowledge nodes
  - Apply correct/incorrect scoring algorithm
  - Update spaced repetition schedule
  - Track attempt history
- Accumulate all score adjustments across multiple answers
- Save updated profile to persistent storage

### FR-4: Knowledge Graph Integration

**Priority**: MUST HAVE

The system must integrate with the knowledge graph to track which knowledge nodes are affected by each answer.

**Acceptance Criteria**:

- Load knowledge graph structure from Neo4j
- Identify knowledge nodes linked to each quiz
- Calculate score deltas for each affected knowledge node
- Return graph updates showing:
  - Knowledge node ID
  - Knowledge node name
  - Score adjustment amount (positive or negative)
- Sort updates by absolute adjustment magnitude (largest first)

### FR-5: Student-Knowledge Relationship Tracking

**Priority**: SHOULD HAVE

The system should create and maintain RELATED_TO relationships between Student nodes and Knowledge nodes in Neo4j to track which topics a student has engaged with.

**Acceptance Criteria**:

- Create or retrieve Student node in Neo4j
- For each knowledge node with score adjustments:
  - Create or update RELATED_TO relationship from Student to Knowledge node
  - Store relationship properties:
    - `last_score`: Most recent score for this knowledge topic
    - `last_updated`: Timestamp of last update
    - `total_attempts`: Total number of quiz attempts for this topic
    - `total_correct`: Total number of correct answers for this topic
  - Avoid duplicate relationships (check before creating)
- Handle Neo4j connection failures gracefully
- Log relationship creation/updates for audit trail

**Current Status**: ✅ IMPLEMENTED (2025-10-08) - Automatically updates on quiz submission

### FR-6: Error Handling

**Priority**: MUST HAVE

The system must handle errors gracefully and provide meaningful feedback.

**Acceptance Criteria**:

- Validate required fields (student_id, answers)
- Return 400 error for missing required fields
- Return 500 error for knowledge graph loading failures
- Continue processing remaining answers if one fails
- Log all errors with context
- Never expose internal errors to API consumers

### FR-7: Response Format

**Priority**: MUST HAVE

The API must return a consistent response format with student info and graph updates.

**Acceptance Criteria**:

- Return student information:
  - `name`: Student username
  - `db_id`: Student database ID
- Return graph updates array:
  - `graph_id`: Knowledge node element ID
  - `knowledge`: Knowledge node name
  - `adjustment`: Score change (rounded to 2 decimals)
- Sort graph updates by absolute adjustment (descending)

### FR-8: Manual Knowledge Adjustment

**Priority**: SHOULD HAVE

The system should allow authorized users (teachers, admins) to manually adjust student knowledge scores through a dedicated API endpoint.

**Acceptance Criteria**:

- Accept manual adjustment requests with:
  - `student_id`: Student identifier
  - `adjustments`: List of knowledge adjustments
  - `source`: Source of adjustment (e.g., "teacher_override", "placement_test")
  - `adjusted_by`: User/system making the adjustment
  - `reason`: Optional reason for adjustment
- Support multiple adjustment formats:
  - Absolute score: Set exact score value
  - Score delta: Adjust by relative amount
  - Metadata updates: Update attempts/correct counts
- Support knowledge lookup by element_id or name
- Validate permissions (teacher/admin only)
- Create or update Student-Knowledge relationships in Neo4j
- Update UserProfile JSON with new scores
- Log all adjustments with full audit trail
- Return detailed results showing what was updated/created
- Prevent students from adjusting their own knowledge

**Current Status**: Planned (see ADR 0001)

## Non-Functional Requirements

### NFR-1: Performance

- Process up to 100 answer submissions in a single request
- Complete processing within 5 seconds for typical workloads (10 answers)
- Load knowledge graph efficiently (cache if possible)

### NFR-2: Data Persistence

- Student profiles must be persisted to JSON files in `data/profiles/`
- Profile files must be named `{student_id}.json`
- Ensure atomic writes to prevent data corruption
- Create directories if they don't exist

### NFR-3: Scalability

- Support concurrent answer submissions from multiple students
- Handle knowledge graphs with 1000+ nodes efficiently
- Process answers independently (failure of one doesn't affect others)

### NFR-4: Observability

- Log all answer submissions at INFO level
- Log processing results (correct/incorrect, adjustments)
- Log errors at WARNING/ERROR level with full context
- Never log sensitive student data

### NFR-5: Security

- Require authentication (TokenAuthentication)
- Require authorization (IsAuthenticated)
- Validate all input data using serializers
- Prevent injection attacks through proper Neo4j query handling

## Data Requirements

### DR-1: Student Profile Storage

- Format: JSON
- Location: `data/profiles/{student_id}.json`
- Schema: UserProfile Pydantic model
- Fields:
  - `user_id`: Student identifier
  - `scores`: Dict mapping knowledge node IDs to scores
  - `schedule`: Spaced repetition schedule per node
  - `attempt_history`: List of recent attempts
  - `total_attempts`: Total quiz attempts
  - `total_correct`: Total correct answers
  - `last_updated`: Timestamp of last update

### DR-2: Neo4j Graph Data

- Student nodes: `username`, `db_id`
- Quiz nodes: `quiz_text`, `difficulty_level`, `quiz_type`
- Choice nodes: `choice_text`, `is_correct`, `answer_explanation`
- Knowledge nodes: `name`, `description`, `example`
- Relationships:
  - Quiz -[HAS_CHOICE]-> Choice
  - Quiz -[RELATED_TO]-> Knowledge
  - Choice -[RELATED_TO]-> Knowledge
  - Knowledge -[DEPENDS_ON]-> Knowledge
  - Student -[RELATED_TO]-> Knowledge (planned)

## API Contract

### Endpoint

```
POST /student/v1/<ram_id>/submit-answers/
```

### Request Body

```json
{
  "student_id": "123-ceo",
  "answers": [
    {
      "quiz_gid": "4:abc:123",
      "answer_gid": "4:def:456",
      "time_to_answer": 123,
      "use_helper": ["cut-choice", "two-answer"],
      "time_read_answer": 123,
      "choice_cutting": ["4:ghi:789", "4:jkl:012"]
    }
  ]
}
```

### Response (Success)

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
      "adjustment": 1.0
    },
    {
      "graph_id": "4:node:124",
      "knowledge": "Perfect Tense",
      "adjustment": -0.5
    }
  ]
}
```

### Response (Error)

```json
{
  "error": {
    "code": "invalid_input",
    "message": "student_id is required",
    "details": {}
  }
}
```

### Manual Adjustment Endpoint

```
POST /student/v1/<ram_id>/adjust-knowledge/
```

### Request Body

```json
{
  "student_id": "123-ceo",
  "adjustments": [
    {
      "knowledge_id": "4:node:123",
      "score": 7.5,
      "total_attempts": 10,
      "total_correct": 8
    },
    {
      "knowledge_id": "Simple Tense",
      "score_delta": 2.0
    }
  ],
  "source": "teacher_override",
  "adjusted_by": "teacher@example.com",
  "reason": "Placement test results"
}
```

### Response (Success)

```json
{
  "student_id": "123-ceo",
  "updated_count": 1,
  "created_count": 1,
  "adjustments": [
    {
      "knowledge_id": "4:node:123",
      "knowledge_name": "Simple Tense",
      "old_score": 5.0,
      "new_score": 7.5,
      "action": "updated"
    },
    {
      "knowledge_id": "4:node:124",
      "knowledge_name": "Perfect Tense",
      "old_score": 3.0,
      "new_score": 5.0,
      "action": "created"
    }
  ],
  "source": "teacher_override",
  "adjusted_by": "teacher@example.com",
  "timestamp": "2025-10-08T14:30:00Z"
}
```

### Response (Error)

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Only teachers and admins can adjust student knowledge",
    "details": {}
  }
}
```

## Dependencies

### Internal Dependencies

- `core.api.BaseAPIView`: Base class for API views
- `core.api.APIError`: Standard error handling
- `core.services.BaseService`: Base class for services
- `student.quiz_suggestion`: Quiz suggestion engine
  - `update_scores()`: Score update algorithm
  - `KnowledgeGraph`: Graph structure and traversal
  - `UserProfile`: Student learning profile
- `student.neo_models.Student`: Student Neo4j model
- `quiz.neo_models.Quiz`: Quiz Neo4j model
- `quiz.neo_models.Choice`: Choice Neo4j model
- `knowledge.neo_models.Knowledge`: Knowledge Neo4j model

### External Dependencies

- Neo4j database (neomodel)
- Django REST Framework
- NetworkX (for graph operations)
- Pydantic (for data validation)

## Future Enhancements

### FE-1: Real-time Graph Updates

Enable the Student-Knowledge relationship tracking in Neo4j to provide:

- Visual learning path visualization
- Student knowledge graph queries
- Relationship-based analytics

### FE-2: Advanced Analytics

Track additional metadata:

- Time-based performance trends
- Helper usage patterns
- Choice elimination strategies
- Learning velocity metrics

### FE-3: Batch Optimization

Optimize for large batch submissions:

- Bulk Neo4j queries
- Parallel processing
- Caching strategies

### FE-4: Adaptive Difficulty

Use submission data to:

- Adjust quiz difficulty dynamically
- Personalize learning paths
- Predict knowledge gaps
