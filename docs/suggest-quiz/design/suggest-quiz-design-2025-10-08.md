---
feature: suggest-quiz
type: design
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/suggest_quiz_service.py", "student/api_views.py"]
related_docs: ["../requirements/suggest-quiz-requirements.md", "../adr/0001-weakness-based-quiz-suggestion.md"]
last_validated: "2025-10-08"
---

# Suggest Quiz Design - Weakness-Based Approach

## Summary

This document describes the design of the refactored Suggest Quiz feature, which uses Neo4j Student-Knowledge relationships to provide personalized quiz recommendations based on student weakness areas.

## Architecture

### High-Level Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /student/v1/<ram_id>/suggest-quiz/
       ▼
┌─────────────────────┐
│  SuggestQuizAPI     │  (View Layer)
│  - Validate input   │
│  - Call service     │
│  - Return response  │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│           SuggestQuizService                              │
│  1. Get/create student node                              │
│  2. Load user profile (quiz history)                     │
│  3. Check if student has knowledge relationships         │
│  4. Branch: Existing user OR New user                    │
│  5. Collect quizzes (weakness-based or random)           │
│  6. Convert to API response format                       │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│   Neo4j Database    │
│  - Student nodes    │
│  - Knowledge nodes  │
│  - Quiz nodes       │
│  - Relationships    │
└─────────────────────┘
```

### Component Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     API Layer                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SuggestQuizAPI (BaseAPIView)                        │  │
│  │  - post(request, ram_id)                             │  │
│  │  - Validates request data                            │  │
│  │  - Calls SuggestQuizService                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SuggestQuizService (BaseService)                    │  │
│  │  - run()                                             │  │
│  │  - _get_or_create_student()                          │  │
│  │  - _has_knowledge_relationships()                    │  │
│  │  - _get_weakness_knowledge_nodes()                   │  │
│  │  - _get_quizzes_for_knowledge()                      │  │
│  │  - _get_recent_quiz_ids()                            │  │
│  │  - _get_random_quizzes()                             │  │
│  │  - _load_user_profile()                              │  │
│  │  - _convert_quizzes_to_response()                    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Neo4j Models    │  │  UserProfile     │               │
│  │  - Student       │  │  (Pydantic)      │               │
│  │  - Knowledge     │  │  - attempt_      │               │
│  │  - Quiz          │  │    history       │               │
│  │  - Choice        │  │  - scores        │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────────────────────────────────────────┘
```

## Detailed Design

### 1. Service Entry Point: `run()`

**Purpose**: Main orchestration method

**Steps**:
1. Parse and validate input
2. Get/create student node
3. Load user profile for quiz history
4. Get recent quiz IDs (last 5)
5. Check if student has knowledge relationships
6. Branch to appropriate suggestion strategy
7. Convert results to API format
8. Return response

**Pseudocode**:
```python
def run():
    # Parse input
    student_inp = data.get("student")
    quiz_limit = data.get("quiz_limit", 10)
    scope_topic = data.get("scope_topic")
    
    # Validate
    if not username:
        raise APIError("username required")
    
    # Get student
    student_node = _get_or_create_student(username, db_id)
    
    # Load profile
    profile = _load_user_profile(username)
    recent_quiz_ids = _get_recent_quiz_ids(profile, n=5)
    
    # Check knowledge relationships
    if _has_knowledge_relationships(student_node):
        # Existing user: weakness-based
        suggested_quizzes = _suggest_for_existing_user(...)
    else:
        # New user: random
        suggested_quizzes = _get_random_quizzes(...)
    
    # Convert and return
    quizzes_out = _convert_quizzes_to_response(suggested_quizzes)
    return {"student": {...}, "quiz": quizzes_out}
```

---

### 2. Weakness-Based Suggestion (Existing Users)

**Method**: `_get_weakness_knowledge_nodes()`

**Purpose**: Query knowledge nodes ordered by last_score (weakest first)

**Cypher Query**:
```cypher
MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
WHERE elementId(s) = $student_id
[AND toLower(k.name) CONTAINS toLower($topic)]
RETURN k, r.last_score as score
ORDER BY r.last_score ASC
```

**Parameters**:
- `student_id`: Student element_id
- `topic`: Optional scope_topic filter

**Returns**: List of Knowledge nodes (weakest first)

**Algorithm**:
```python
def _get_weakness_knowledge_nodes(student_node, scope_topic):
    query = """
    MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
    WHERE elementId(s) = $student_id
    """
    params = {"student_id": student_node.element_id}
    
    if scope_topic:
        query += " AND toLower(k.name) CONTAINS toLower($topic)"
        params["topic"] = scope_topic
    
    query += """
    RETURN k, r.last_score as score
    ORDER BY r.last_score ASC
    """
    
    results = db.cypher_query(query, params)
    return [NeoKnowledge.inflate(row[0]) for row in results]
```

---

### 3. Quiz Collection Loop

**Purpose**: Collect quizzes from weakness knowledge until quiz_limit reached

**Algorithm**:
```python
suggested_quiz_nodes = []

for knowledge_node in weakness_knowledge_nodes:
    if len(suggested_quiz_nodes) >= quiz_limit:
        break
    
    # Get quizzes for this knowledge
    related_quizzes = _get_quizzes_for_knowledge(knowledge_node)
    
    for quiz_node in related_quizzes:
        if len(suggested_quiz_nodes) >= quiz_limit:
            break
        
        quiz_id = quiz_node.element_id
        
        # Skip if in recent history
        if quiz_id in recent_quiz_ids:
            continue
        
        # Skip if already in current suggestions
        if quiz_id in [q.element_id for q in suggested_quiz_nodes]:
            continue
        
        suggested_quiz_nodes.append(quiz_node)
```

**Key Points**:
- Iterate through weakness knowledge in order (weakest first)
- For each knowledge, get related quizzes
- Filter out recent history (last 5)
- Avoid duplicates in current suggestion
- Stop when quiz_limit reached

---

### 4. Random Quiz Suggestion (New Users)

**Method**: `_get_random_quizzes()`

**Purpose**: Get random quizzes for initial assessment

**Algorithm**:
```python
def _get_random_quizzes(scope_topic, limit, exclude_quiz_ids):
    if scope_topic:
        # Get quizzes related to topic
        query = """
        MATCH (q:Quiz)-[:RELATED_TO]->(k:Knowledge)
        WHERE toLower(k.name) CONTAINS toLower($topic)
        RETURN DISTINCT q
        """
        results = db.cypher_query(query, {"topic": scope_topic})
        all_quizzes = [NeoQuiz.inflate(row[0]) for row in results]
    else:
        # Get all quizzes
        all_quizzes = list(NeoQuiz.nodes.all())
    
    # Filter out recent history
    filtered = [q for q in all_quizzes 
                if q.element_id not in exclude_quiz_ids]
    
    # Random sample
    if len(filtered) <= limit:
        return filtered
    else:
        return random.sample(filtered, limit)
```

---

### 5. Quiz History Deduplication

**Method**: `_get_recent_quiz_ids()`

**Purpose**: Extract last N quiz IDs from attempt history

**Algorithm**:
```python
def _get_recent_quiz_ids(profile, n=5):
    recent_attempts = profile.attempt_history[-n:]
    return {attempt.quiz_id for attempt in recent_attempts}
```

**Data Source**: `UserProfile.attempt_history`
- Stored in JSON file: `data/profiles/{username}.json`
- Limited to last 15 quizzes (ATTEMPT_HISTORY_LEN = 15)
- Used for deduplication (last 5)

---

### 6. Response Conversion

**Method**: `_convert_quizzes_to_response()`

**Purpose**: Convert Neo4j Quiz nodes to API response format

**Algorithm**:
```python
def _convert_quizzes_to_response(neo_quizzes):
    quizzes_out = []
    
    for neo_quiz in neo_quizzes:
        # Get choices
        choices_data = []
        for choice in neo_quiz.has_choice.all():
            choices_data.append({
                "graph_id": choice.element_id,
                "choice_text": choice.choice_text,
                "is_correct": choice.is_correct,
                "answer_explanation": choice.answer_explanation,
                "related_to": [
                    {"graph_id": k.element_id, "knowledge": k.name}
                    for k in choice.related_to.all()
                ]
            })
        
        # Get quiz-level knowledge
        rel_k_q = [
            {"graph_id": k.element_id, "knowledge": k.name}
            for k in neo_quiz.related_to.all()
        ]
        
        quizzes_out.append({
            "graph_id": neo_quiz.element_id,
            "quiz_text": neo_quiz.quiz_text,
            "choices": choices_data,
            "related_to": rel_k_q
        })
    
    return quizzes_out
```

---

## Data Models

### Neo4j Graph Schema

```
┌──────────────┐
│   Student    │
│ - username   │
│ - db_id      │
└──────┬───────┘
       │
       │ RELATED_TO
       │ - last_score
       │ - last_updated
       │ - total_attempts
       │ - total_correct
       ▼
┌──────────────┐       ┌──────────────┐
│  Knowledge   │◄──────│     Quiz     │
│ - name       │       │ - quiz_text  │
│ - description│       │ - difficulty │
└──────────────┘       └──────┬───────┘
                              │
                              │ HAS_CHOICE
                              ▼
                       ┌──────────────┐
                       │    Choice    │
                       │ - choice_text│
                       │ - is_correct │
                       │ - answer_exp │
                       └──────────────┘
```

### UserProfile (JSON)

```json
{
  "user_id": "ceo",
  "attempt_history": [
    {
      "quiz_id": "4:abc123:456",
      "node_ids": ["4:def456:789"],
      "is_correct": true,
      "timestamp": "2025-10-08T10:30:00Z",
      "difficulty_level": 3
    }
  ],
  "scores": {...},
  "schedule": {...}
}
```

---

## Error Handling

### Input Validation Errors

- **Missing username**: 400 Bad Request
- **Invalid quiz_limit**: 400 Bad Request (< 1)

### Database Errors

- **Student creation failed**: 500 Internal Server Error
- **Cypher query failed**: Log error, return empty list
- **Quiz conversion failed**: Log error, skip quiz

### Edge Cases

- **No quizzes available**: Return empty list
- **No weakness knowledge**: Fall back to random
- **Topic filter no matches**: Return empty list or all quizzes

---

## Performance Considerations

### Cypher Query Optimization

1. **Index on Student.db_id**: Fast student lookup
2. **Index on Knowledge.name**: Fast topic filtering
3. **Limit results**: Only fetch needed quizzes

### Caching Opportunities

1. **Knowledge graph**: Cache for session
2. **Quiz bank**: Cache frequently accessed quizzes
3. **User profile**: Already file-based (fast)

### Scalability

- **Pagination**: Consider for large quiz banks
- **Batch processing**: For multiple students
- **Connection pooling**: Neo4j connection management

---

## Testing Strategy

### Unit Tests

```python
def test_has_knowledge_relationships_true():
    student = create_student_with_knowledge()
    assert service._has_knowledge_relationships(student) == True

def test_has_knowledge_relationships_false():
    student = create_new_student()
    assert service._has_knowledge_relationships(student) == False

def test_get_weakness_knowledge_nodes_ordered():
    student = create_student_with_scores([5.0, 2.0, 8.0])
    nodes = service._get_weakness_knowledge_nodes(student)
    assert nodes[0].last_score == 2.0  # Weakest first

def test_get_random_quizzes_with_topic():
    quizzes = service._get_random_quizzes("Simple Tense", 5, set())
    assert all("simple tense" in q.related_knowledge for q in quizzes)
```

### Integration Tests

```python
def test_suggest_quiz_existing_user():
    response = client.post("/student/v1/RAM1111/suggest-quiz/", {
        "student": {"username": "ceo", "id": "123"},
        "quiz_limit": 5
    })
    assert response.status_code == 200
    assert len(response.data["quiz"]) <= 5

def test_suggest_quiz_new_user():
    response = client.post("/student/v1/RAM1111/suggest-quiz/", {
        "student": {"username": "newuser", "id": "456"},
        "quiz_limit": 10
    })
    assert response.status_code == 200
    # Should return random quizzes
```

---

## Future Enhancements

1. **Adaptive Difficulty**: Match quiz difficulty to student level
2. **Spaced Repetition**: Prioritize overdue reviews
3. **Learning Path**: Suggest knowledge topics to focus on
4. **Neo4j Quiz History**: Move attempt history to graph
5. **Smart New User Flow**: Better initial assessment
6. **Batch Suggestions**: Suggest quizzes for multiple students
7. **Real-time Updates**: WebSocket for live suggestions

