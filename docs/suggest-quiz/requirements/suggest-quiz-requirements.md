---
feature: suggest-quiz
type: requirement
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/suggest_quiz_service.py", "student/api_views.py"]
related_docs: ["../adr/0001-weakness-based-quiz-suggestion.md", "../design/suggest-quiz-design.md"]
last_validated: "2025-10-08"
---

# Suggest Quiz Requirements

## Overview

The Suggest Quiz feature provides personalized quiz recommendations to students based on their learning progress and weakness areas. The system uses Neo4j Student-Knowledge relationships to identify areas where students need improvement and suggests relevant quizzes.

## Functional Requirements

### FR-1: Student Identification

**Priority**: MUST HAVE

The system must identify the student requesting quiz suggestions.

**Acceptance Criteria**:
- Accept student username (required)
- Accept student db_id (optional, for existing students)
- Create new student node in Neo4j if not exists
- Return error if username is missing

**Input**:
```json
{
  "student": {
    "username": "ceo",
    "id": "123-ceo"
  }
}
```

**Validation**:
- `student.username` is required
- `student.id` or `student.db_id` is optional

---

### FR-2: Weakness-Based Quiz Suggestion (Existing Users)

**Priority**: MUST HAVE

For students with existing knowledge relationships, suggest quizzes based on their weakness areas.

**Acceptance Criteria**:
- Query Student-Knowledge relationships from Neo4j
- Order knowledge nodes by `last_score` ascending (lowest first)
- For each weakness knowledge node:
  - Get related quizzes
  - Filter out quizzes from last 5 quiz history
  - Add to suggestion list until `quiz_limit` is reached
- Support `scope_topic` filtering (knowledge name contains topic)

**Algorithm**:
1. Check if student has any `RELATED_TO` relationships
2. If YES:
   - Query knowledge nodes ordered by `last_score` ASC
   - Filter by `scope_topic` if provided
   - For each knowledge node (weakest first):
     - Get related quizzes
     - Exclude quizzes from last 5 history
     - Add to list until `quiz_limit` reached

**Cypher Query**:
```cypher
MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
WHERE elementId(s) = $student_id
[AND toLower(k.name) CONTAINS toLower($topic)]
RETURN k, r.last_score as score
ORDER BY r.last_score ASC
```

---

### FR-3: Random Quiz Suggestion (New Users)

**Priority**: MUST HAVE

For new students with no knowledge relationships, suggest random quizzes for initial assessment.

**Acceptance Criteria**:
- Detect students with no `RELATED_TO` relationships
- Get all available quizzes
- Filter by `scope_topic` if provided
- Exclude quizzes from last 5 history (if any)
- Randomly select up to `quiz_limit` quizzes

**Algorithm**:
1. Check if student has any `RELATED_TO` relationships
2. If NO:
   - Get all quizzes (or filtered by `scope_topic`)
   - Exclude quizzes from last 5 history
   - Random sample up to `quiz_limit`

---

### FR-4: Quiz History Deduplication

**Priority**: MUST HAVE

Avoid suggesting quizzes that the student has recently attempted.

**Acceptance Criteria**:
- Load student's UserProfile from JSON file
- Extract last 5 quiz IDs from `attempt_history`
- Filter out these quizzes from suggestions
- Maintain quiz history limit of 15 quizzes (in UserProfile)

**Implementation**:
- Use `UserProfile.attempt_history` (last 15 quizzes)
- Get last 5 quiz IDs for deduplication
- Filter suggestions to exclude these IDs

---

### FR-5: Topic Scoping

**Priority**: SHOULD HAVE

Allow filtering quiz suggestions by topic/knowledge area.

**Acceptance Criteria**:
- Accept optional `scope_topic` parameter
- Filter knowledge nodes by name (case-insensitive contains)
- For random quizzes, filter by related knowledge nodes
- Return quizzes only related to matching knowledge nodes

**Input**:
```json
{
  "scope_topic": "Simple Tense"
}
```

**Behavior**:
- If `scope_topic` provided:
  - For existing users: Filter weakness knowledge by name
  - For new users: Filter quizzes by related knowledge name
- If not provided: No filtering

---

### FR-6: Quiz Limit

**Priority**: MUST HAVE

Control the number of quizzes returned.

**Acceptance Criteria**:
- Accept `quiz_limit` parameter (default: 10)
- Validate `quiz_limit >= 1`
- Return at most `quiz_limit` quizzes
- Return fewer if not enough quizzes available

**Input**:
```json
{
  "quiz_limit": 5
}
```

**Validation**:
- `quiz_limit` must be >= 1
- Default to 10 if not provided

---

### FR-7: Quiz Response Format

**Priority**: MUST HAVE

Return quizzes in standardized API format.

**Acceptance Criteria**:
- Include quiz metadata (graph_id, quiz_text)
- Include all choices with metadata
- Include related knowledge for quiz and choices
- Include student information

**Response Format**:
```json
{
  "student": {
    "name": "ceo",
    "db_id": "123-ceo"
  },
  "quiz": [
    {
      "graph_id": "4:abc123:456",
      "quiz_text": "She ___ to school every day.",
      "choices": [
        {
          "graph_id": "4:def456:789",
          "choice_text": "go",
          "is_correct": false,
          "answer_explanation": "Incorrect: Subject-verb agreement",
          "related_to": [
            {
              "graph_id": "4:ghi789:012",
              "knowledge": "Subject-Verb Agreement"
            }
          ]
        },
        {
          "graph_id": "4:jkl012:345",
          "choice_text": "goes",
          "is_correct": true,
          "answer_explanation": "Correct: Third person singular",
          "related_to": [
            {
              "graph_id": "4:ghi789:012",
              "knowledge": "Subject-Verb Agreement"
            }
          ]
        }
      ],
      "related_to": [
        {
          "graph_id": "4:ghi789:012",
          "knowledge": "Subject-Verb Agreement"
        },
        {
          "graph_id": "4:mno345:678",
          "knowledge": "Simple Present Tense"
        }
      ]
    }
  ]
}
```

---

## Non-Functional Requirements

### NFR-1: Performance

**Priority**: SHOULD HAVE

- Quiz suggestions should be returned within 2 seconds
- Cypher queries should be optimized with proper indexes
- Limit quiz bank queries to necessary data only

### NFR-2: Scalability

**Priority**: SHOULD HAVE

- Support up to 10,000 students
- Support up to 1,000 quizzes per knowledge node
- Handle concurrent requests efficiently

### NFR-3: Reliability

**Priority**: MUST HAVE

- Gracefully handle missing data (no quizzes, no knowledge)
- Return partial results if some queries fail
- Log errors for debugging

### NFR-4: Maintainability

**Priority**: MUST HAVE

- Follow API style guide (class-based service)
- Clear separation of concerns (view → service)
- Comprehensive logging
- Well-documented code

---

## API Endpoint

### POST `/student/v1/<ram_id>/suggest-quiz/`

**Authentication**: Required (Token)

**Request Body**:
```json
{
  "student": {
    "username": "ceo",
    "id": "123-ceo"
  },
  "quiz_limit": 10,
  "scope_topic": "Simple Tense"
}
```

**Response** (200 OK):
```json
{
  "student": {
    "name": "ceo",
    "db_id": "123-ceo"
  },
  "quiz": [...]
}
```

**Error Responses**:
- 400 Bad Request: Invalid input (missing username, invalid quiz_limit)
- 404 Not Found: No quizzes available
- 500 Internal Server Error: Database errors

---

## Dependencies

### Internal Dependencies

- `core.api.BaseAPIView`: Base class for API views
- `core.api.APIError`: Standard error handling
- `core.services.BaseService`: Base class for services
- `student.neo_models.Student`: Student node model
- `student.neo_models.StudentKnowledgeRel`: Student-Knowledge relationship
- `quiz.neo_models.Quiz`: Quiz node model
- `knowledge.neo_models.Knowledge`: Knowledge node model
- `student.quiz_suggestion.UserProfile`: User profile for quiz history

### External Dependencies

- Neo4j database (via neomodel)
- Django REST Framework
- Python 3.10+

---

## Data Models

### Student Node
```python
class Student(StructuredNode):
    username = StringProperty(required=True)
    db_id = StringProperty(required=True)
    related_to = RelationshipTo("Knowledge", "RELATED_TO", model=StudentKnowledgeRel)
```

### StudentKnowledgeRel
```python
class StudentKnowledgeRel(StructuredRel):
    last_score = FloatProperty()
    last_updated = DateTimeProperty()
    total_attempts = IntegerProperty(default=0)
    total_correct = IntegerProperty(default=0)
```

### UserProfile (JSON)
```python
class UserProfile(BaseModel):
    user_id: str
    attempt_history: List[AttemptRecord]  # Last 15 quizzes
    # ... other fields
```

---

## Testing Requirements

### Unit Tests

- Test `_has_knowledge_relationships()` with/without relationships
- Test `_get_weakness_knowledge_nodes()` ordering and filtering
- Test `_get_quizzes_for_knowledge()` with various knowledge nodes
- Test `_get_recent_quiz_ids()` with different history sizes
- Test `_get_random_quizzes()` with/without topic filter

### Integration Tests

- Test full flow for existing user with weakness knowledge
- Test full flow for new user (random quizzes)
- Test topic filtering for both user types
- Test quiz history deduplication
- Test quiz_limit enforcement

### Edge Cases

- Student with no quizzes for weakness knowledge
- Empty quiz history
- Topic filter with no matches
- quiz_limit larger than available quizzes
- Concurrent requests for same student

---

## Future Enhancements

1. **Adaptive Difficulty**: Match quiz difficulty to student level
2. **Spaced Repetition**: Prioritize overdue reviews
3. **Learning Path**: Suggest knowledge topics to focus on
4. **Neo4j Quiz History**: Move attempt history to Neo4j
5. **Smart New User Flow**: Better initial assessment strategy

