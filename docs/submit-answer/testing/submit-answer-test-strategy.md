---
feature: submit-answer
type: testing
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/submit_answers_service.py", "student/api_views.py", "student/tests/"]
related_docs: ["../requirements/submit-answer-requirements.md", "../design/submit-answer-design-2025-10-08.md"]
last_validated: "2025-10-08"
---

# Submit Answer - Test Strategy

## Summary

This document outlines the testing strategy for the Submit Answer feature, including unit tests, integration tests, and end-to-end API tests. The strategy ensures correctness of answer validation, score updates, and knowledge graph integration.

## Test Pyramid

```
        ┌─────────────────┐
        │   E2E API Tests │  (10%)
        │   - Full flow   │
        └─────────────────┘
       ┌───────────────────┐
       │ Integration Tests │  (30%)
       │ - Service + Neo4j │
       │ - Service + Files │
       └───────────────────┘
      ┌─────────────────────┐
      │    Unit Tests       │  (60%)
      │ - Service methods   │
      │ - Serializers       │
      │ - Helpers           │
      └─────────────────────┘
```

## Unit Tests

### Test File: `student/tests/test_submit_answers_service.py`

#### Test Class: `TestSubmitAnswersService`

##### Test: `test_get_student_existing`
**Purpose**: Verify student node retrieval from Neo4j

**Setup**:
- Create Student node in Neo4j with known db_id

**Execution**:
```python
service = SubmitAnswersService(inp={})
student = service._get_student("test-student-123")
```

**Assertions**:
- Student is not None
- Student.db_id matches expected value
- Student.username is correct

##### Test: `test_get_student_not_found`
**Purpose**: Verify graceful handling of missing student

**Setup**:
- No student created

**Execution**:
```python
student = service._get_student("nonexistent-id")
```

**Assertions**:
- Returns None
- No exception raised
- Warning logged

##### Test: `test_load_user_profile_existing`
**Purpose**: Verify loading existing profile from file

**Setup**:
- Create profile JSON file in `data/profiles/test-student.json`

**Execution**:
```python
profile = service._load_user_profile("test-student")
```

**Assertions**:
- Profile loaded successfully
- user_id matches
- Scores dict is populated
- Metadata is correct

##### Test: `test_load_user_profile_new`
**Purpose**: Verify creation of new profile when file missing

**Setup**:
- Ensure no profile file exists

**Execution**:
```python
profile = service._load_user_profile("new-student")
```

**Assertions**:
- New profile created
- user_id is "new-student"
- Scores dict is empty
- total_attempts is 0

##### Test: `test_save_user_profile`
**Purpose**: Verify profile persistence to file

**Setup**:
- Create UserProfile in memory

**Execution**:
```python
service._save_user_profile(profile, "test-student")
```

**Assertions**:
- File exists at expected path
- File contains valid JSON
- JSON deserializes to UserProfile
- All fields match original

##### Test: `test_check_answer_correctness_correct`
**Purpose**: Verify correct answer detection

**Setup**:
- Create Quiz with Choices in Neo4j
- Mark one choice as correct

**Execution**:
```python
is_correct = service._check_answer_correctness(quiz, correct_choice_id)
```

**Assertions**:
- Returns True
- No errors logged

##### Test: `test_check_answer_correctness_incorrect`
**Purpose**: Verify incorrect answer detection

**Setup**:
- Create Quiz with Choices
- Submit incorrect choice ID

**Execution**:
```python
is_correct = service._check_answer_correctness(quiz, wrong_choice_id)
```

**Assertions**:
- Returns False
- No errors logged

##### Test: `test_check_answer_correctness_missing_choice`
**Purpose**: Verify handling of invalid choice ID

**Setup**:
- Create Quiz with Choices
- Use non-existent choice ID

**Execution**:
```python
is_correct = service._check_answer_correctness(quiz, "invalid-id")
```

**Assertions**:
- Returns False
- Warning logged about missing choice

##### Test: `test_process_answer_correct`
**Purpose**: Verify score adjustments for correct answer

**Setup**:
- Create Quiz linked to Knowledge nodes
- Create UserProfile with initial scores
- Load KnowledgeGraph

**Execution**:
```python
adjustments = service._process_answer(
    {"quiz_gid": quiz_id, "answer_gid": correct_choice_id},
    profile,
    kg,
    "student-123"
)
```

**Assertions**:
- Adjustments dict is not empty
- All adjustments are positive (for correct answer)
- Linked knowledge nodes have adjustments
- Profile scores increased

##### Test: `test_process_answer_incorrect`
**Purpose**: Verify score adjustments for incorrect answer

**Setup**:
- Create Quiz linked to Knowledge nodes
- Create UserProfile with initial scores

**Execution**:
```python
adjustments = service._process_answer(
    {"quiz_gid": quiz_id, "answer_gid": wrong_choice_id},
    profile,
    kg,
    "student-123"
)
```

**Assertions**:
- Adjustments dict is not empty
- All adjustments are negative (for incorrect answer)
- Profile scores decreased

##### Test: `test_process_answer_quiz_not_found`
**Purpose**: Verify handling of missing quiz

**Setup**:
- Use non-existent quiz ID

**Execution**:
```python
adjustments = service._process_answer(
    {"quiz_gid": "invalid-quiz", "answer_gid": "any-id"},
    profile,
    kg,
    "student-123"
)
```

**Assertions**:
- Returns empty dict
- Warning logged
- No exception raised

##### Test: `test_build_graph_updates`
**Purpose**: Verify response formatting

**Setup**:
- Create adjustments dict
- Load KnowledgeGraph with known nodes

**Execution**:
```python
graph_updates = service._build_graph_updates(
    {"node-1": 2.5, "node-2": -1.0, "node-3": 0.5},
    kg
)
```

**Assertions**:
- Returns list of dicts
- Each dict has graph_id, knowledge, adjustment
- Sorted by absolute adjustment (descending)
- Adjustments rounded to 2 decimals

##### Test: `test_run_single_answer`
**Purpose**: Verify full service execution with one answer

**Setup**:
- Create Student, Quiz, Choices, Knowledge in Neo4j
- Prepare valid input data

**Execution**:
```python
result = service.run()
```

**Assertions**:
- Result has "student" and "graph_update" keys
- Student info is correct
- Graph updates are present
- Profile file saved

##### Test: `test_run_multiple_answers`
**Purpose**: Verify batch answer processing

**Setup**:
- Create multiple Quizzes
- Prepare input with multiple answers

**Execution**:
```python
result = service.run()
```

**Assertions**:
- All answers processed
- Adjustments accumulated correctly
- Profile updated once (not per answer)

##### Test: `test_run_partial_failure`
**Purpose**: Verify resilience to individual answer failures

**Setup**:
- Create valid quiz for answer 1
- Use invalid quiz ID for answer 2
- Create valid quiz for answer 3

**Execution**:
```python
result = service.run()
```

**Assertions**:
- Answers 1 and 3 processed successfully
- Answer 2 skipped (logged error)
- Result includes adjustments from answers 1 and 3
- No exception raised

### Test File: `student/tests/test_serializers.py`

#### Test Class: `TestAnswerSubmissionSerializer`

##### Test: `test_valid_answer_submission`
**Purpose**: Verify valid answer data passes validation

**Input**:
```python
data = {
    "quiz_gid": "4:abc:123",
    "answer_gid": "4:def:456",
    "time_to_answer": 30,
    "use_helper": ["cut-choice"],
    "time_read_answer": 10,
    "choice_cutting": ["4:ghi:789"]
}
```

**Assertions**:
- is_valid() returns True
- validated_data matches input

##### Test: `test_missing_required_fields`
**Purpose**: Verify validation fails for missing fields

**Input**:
```python
data = {"quiz_gid": "4:abc:123"}  # Missing answer_gid
```

**Assertions**:
- is_valid() returns False
- errors contain "answer_gid"

##### Test: `test_optional_fields_default`
**Purpose**: Verify optional fields have defaults

**Input**:
```python
data = {
    "quiz_gid": "4:abc:123",
    "answer_gid": "4:def:456"
}
```

**Assertions**:
- is_valid() returns True
- use_helper defaults to []
- choice_cutting defaults to []

#### Test Class: `TestSubmitAnswersRequestSerializer`

##### Test: `test_valid_request`
**Purpose**: Verify valid request passes validation

**Input**:
```python
data = {
    "student_id": "123-ceo",
    "answers": [
        {"quiz_gid": "4:abc:123", "answer_gid": "4:def:456"}
    ]
}
```

**Assertions**:
- is_valid() returns True
- validated_data has student_id and answers

##### Test: `test_empty_answers_array`
**Purpose**: Verify validation fails for empty answers

**Input**:
```python
data = {"student_id": "123-ceo", "answers": []}
```

**Assertions**:
- is_valid() returns False
- errors contain "answers"

## Integration Tests

### Test File: `student/tests/test_submit_answers_integration.py`

#### Test Class: `TestSubmitAnswersIntegration`

##### Test: `test_full_flow_with_neo4j`
**Purpose**: Verify complete flow with real Neo4j

**Setup**:
- Create complete graph structure in Neo4j:
  - Student node
  - Knowledge nodes with dependencies
  - Quiz nodes linked to knowledge
  - Choice nodes with correct/incorrect flags

**Execution**:
```python
service = SubmitAnswersService(inp={
    "student_id": "test-student",
    "answers": [
        {"quiz_gid": quiz1_id, "answer_gid": correct_choice_id},
        {"quiz_gid": quiz2_id, "answer_gid": wrong_choice_id}
    ]
})
result = service.run()
```

**Assertions**:
- Knowledge graph loaded successfully
- Both answers processed
- Profile saved to file
- Graph updates reflect both correct and incorrect answers
- Prerequisite bonuses applied (if applicable)

##### Test: `test_knowledge_graph_loading`
**Purpose**: Verify KnowledgeGraph loads correctly from Neo4j

**Setup**:
- Create knowledge nodes with DEPENDS_ON relationships

**Execution**:
```python
kg = KnowledgeGraph.from_neo4j()
```

**Assertions**:
- All nodes loaded
- All edges loaded
- Topological order is valid (no cycles)
- Node attributes preserved

##### Test: `test_profile_persistence`
**Purpose**: Verify profile survives save/load cycle

**Setup**:
- Create profile with scores and history
- Save to file

**Execution**:
```python
service._save_user_profile(profile, "test-student")
loaded_profile = service._load_user_profile("test-student")
```

**Assertions**:
- Loaded profile equals original
- All scores preserved
- Attempt history preserved
- Metadata preserved

## End-to-End API Tests

### Test File: `student/tests/test_submit_answers_api.py`

#### Test Class: `TestSubmitAnswersAPI`

##### Test: `test_submit_answers_success`
**Purpose**: Verify complete API flow

**Setup**:
- Authenticate user
- Create test data in Neo4j

**Request**:
```python
POST /student/v1/test-ram/submit-answers/
Authorization: Token <token>
Content-Type: application/json

{
  "student_id": "test-student",
  "answers": [
    {
      "quiz_gid": "4:abc:123",
      "answer_gid": "4:def:456",
      "time_to_answer": 30
    }
  ]
}
```

**Assertions**:
- Status code 200
- Response has "student" and "graph_update"
- Student info is correct
- Graph updates are present

##### Test: `test_submit_answers_unauthenticated`
**Purpose**: Verify authentication required

**Request**:
```python
POST /student/v1/test-ram/submit-answers/
# No Authorization header
```

**Assertions**:
- Status code 401
- Error response returned

##### Test: `test_submit_answers_invalid_input`
**Purpose**: Verify input validation

**Request**:
```python
POST /student/v1/test-ram/submit-answers/
{
  "student_id": "",  # Invalid: empty
  "answers": []      # Invalid: empty
}
```

**Assertions**:
- Status code 400
- Error response with validation details

##### Test: `test_submit_answers_knowledge_graph_error`
**Purpose**: Verify error handling for graph loading failure

**Setup**:
- Mock KnowledgeGraph.from_neo4j() to raise exception

**Assertions**:
- Status code 500
- Error code "knowledge_graph_error"

## Test Data Setup

### Fixtures

#### `neo4j_test_data`
Creates complete test graph:
- 5 Knowledge nodes (with dependencies)
- 3 Quiz nodes (linked to knowledge)
- 12 Choice nodes (4 per quiz, 1 correct each)
- 1 Student node

#### `sample_user_profile`
Creates UserProfile with:
- 3 knowledge nodes with scores
- 5 attempt records
- Spaced repetition schedule

#### `authenticated_client`
Provides Django test client with valid auth token

## Acceptance Criteria Tests

### AC-1: Multiple Answer Submission
**Test**: `test_run_multiple_answers`
**Validates**: FR-1

### AC-2: Answer Validation
**Test**: `test_check_answer_correctness_*`
**Validates**: FR-2

### AC-3: Score Updates
**Test**: `test_process_answer_correct`, `test_process_answer_incorrect`
**Validates**: FR-3

### AC-4: Knowledge Graph Integration
**Test**: `test_full_flow_with_neo4j`
**Validates**: FR-4

### AC-5: Error Handling
**Test**: `test_run_partial_failure`, `test_submit_answers_invalid_input`
**Validates**: FR-6

### AC-6: Response Format
**Test**: `test_build_graph_updates`, `test_submit_answers_success`
**Validates**: FR-7

## Performance Tests

### Test: `test_performance_100_answers`
**Purpose**: Verify performance with large batch

**Setup**:
- Create 100 quizzes
- Submit 100 answers in single request

**Assertions**:
- Completes within 5 seconds
- Memory usage reasonable
- All answers processed

### Test: `test_performance_large_knowledge_graph`
**Purpose**: Verify scalability with large graph

**Setup**:
- Create 1000 knowledge nodes
- Create complex dependency structure

**Assertions**:
- Graph loads within 2 seconds
- Score updates complete within 5 seconds

## Test Coverage Goals

- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Service Layer**: 100% (all methods tested)
- **API Layer**: 100% (all endpoints tested)
- **Error Paths**: 100% (all error handlers tested)

## Running Tests

### Run All Tests
```bash
python manage.py test student.tests.test_submit_answers_service
python manage.py test student.tests.test_submit_answers_integration
python manage.py test student.tests.test_submit_answers_api
```

### Run with Coverage
```bash
coverage run --source='student' manage.py test student.tests
coverage report
coverage html
```

### Run Specific Test
```bash
python manage.py test student.tests.test_submit_answers_service.TestSubmitAnswersService.test_run_single_answer
```

## Continuous Integration

### Pre-commit Checks
- Run unit tests
- Check code coverage
- Lint code (flake8, black)

### CI Pipeline
1. Run all unit tests
2. Run integration tests (with Neo4j container)
3. Run API tests
4. Generate coverage report
5. Fail if coverage < 90%

## Manual Testing Checklist

- [ ] Submit single correct answer
- [ ] Submit single incorrect answer
- [ ] Submit multiple answers (mixed correct/incorrect)
- [ ] Submit with all optional fields
- [ ] Submit with minimal fields
- [ ] Submit with invalid student_id
- [ ] Submit with invalid quiz_gid
- [ ] Submit with invalid answer_gid
- [ ] Verify profile file created for new student
- [ ] Verify profile file updated for existing student
- [ ] Verify graph updates sorted correctly
- [ ] Verify error responses have correct format
- [ ] Test with Neo4j unavailable
- [ ] Test with file system read-only

