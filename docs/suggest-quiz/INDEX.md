---
feature: suggest-quiz
type: index
status: approved
owners: ["@ceofourfactplus"]
last_validated: "2025-10-08"
---

# Suggest Quiz Feature Documentation

## 📋 Overview

The **Suggest Quiz** feature provides personalized quiz recommendations to students based on their learning progress and weakness areas. The system uses Neo4j Student-Knowledge relationships to identify areas where students need improvement and suggests relevant quizzes.

### Key Features

- ✅ **Weakness-Based Suggestions**: Prioritizes quizzes for student's weakest knowledge areas
- ✅ **New User Support**: Random quiz selection for initial assessment
- ✅ **Quiz History Deduplication**: Avoids suggesting recently attempted quizzes (last 5)
- ✅ **Topic Scoping**: Filter suggestions by knowledge topic
- ✅ **Configurable Limit**: Control number of quizzes returned

### Quick Links

- **API Endpoint**: `POST /student/v1/<ram_id>/suggest-quiz/`
- **Service**: `student/services/suggest_quiz_service.py`
- **View**: `student/api_views.py` → `SuggestQuizAPI`

---

## 📚 Documentation Structure

### Requirements
- **[Suggest Quiz Requirements](requirements/suggest-quiz-requirements.md)**: Functional and non-functional requirements

### Design
- **[Suggest Quiz Design (2025-10-08)](design/suggest-quiz-design-2025-10-08.md)**: Architecture and detailed design

### ADRs (Architecture Decision Records)
- **[ADR 0001: Weakness-Based Quiz Suggestion](adr/0001-weakness-based-quiz-suggestion.md)**: Decision to refactor from suggestion engine to weakness-based approach

### Testing
- ⏳ Test plans and acceptance criteria (to be added)

---

## 🚀 Quick Start

### API Request

```bash
curl -X POST http://localhost:8000/student/v1/RAM1111/suggest-quiz/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student": {
      "username": "ceo",
      "id": "123-ceo"
    },
    "quiz_limit": 5,
    "scope_topic": "Simple Tense"
  }'
```

### Response

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
        }
      ]
    }
  ]
}
```

---

## 🏗️ Architecture

### High-Level Flow

```
Client Request
     │
     ▼
SuggestQuizAPI (View)
     │
     ▼
SuggestQuizService (Service)
     │
     ├─► Get Student Node (Neo4j)
     ├─► Load User Profile (JSON)
     ├─► Check Knowledge Relationships
     │
     ├─► Existing User?
     │   ├─► YES: Query Weakness Knowledge
     │   │        ├─► Get Related Quizzes
     │   │        └─► Filter Recent History
     │   │
     │   └─► NO: Get Random Quizzes
     │            └─► Filter by Topic (optional)
     │
     └─► Convert to API Response
```

### Key Components

1. **SuggestQuizAPI** (View Layer)
   - Validates request
   - Calls service
   - Returns response

2. **SuggestQuizService** (Service Layer)
   - Orchestrates quiz suggestion logic
   - Queries Neo4j for student/knowledge/quiz data
   - Manages quiz history deduplication

3. **Neo4j Database** (Data Layer)
   - Student nodes
   - Knowledge nodes
   - Quiz nodes
   - Student-Knowledge relationships (with last_score)

4. **UserProfile** (File Storage)
   - Quiz attempt history (last 15)
   - User scores
   - Spaced repetition schedule

---

## 🔄 Algorithm

### For Existing Users (with knowledge relationships)

1. Query Student-Knowledge relationships ordered by `last_score` ASC (weakest first)
2. For each weakness knowledge node:
   - Get related quizzes
   - Filter out quizzes from last 5 history
   - Add to suggestion list
   - Stop when `quiz_limit` reached

### For New Users (no knowledge relationships)

1. Get all quizzes (or filtered by `scope_topic`)
2. Exclude quizzes from last 5 history
3. Randomly select up to `quiz_limit` quizzes

---

## 📊 Data Models

### Neo4j Graph Schema

```
Student -[RELATED_TO]-> Knowledge <-[RELATED_TO]- Quiz
                                                    │
                                                    └─[HAS_CHOICE]-> Choice
```

### StudentKnowledgeRel Properties

- `last_score`: Float (used for weakness detection)
- `last_updated`: DateTime
- `total_attempts`: Integer
- `total_correct`: Integer

### UserProfile (JSON)

- `user_id`: String
- `attempt_history`: List[AttemptRecord] (last 15 quizzes)
- `scores`: Dict[str, float]
- `schedule`: Dict[str, ScheduleEntry]

---

## 🧪 Testing

### Unit Tests

- `test_has_knowledge_relationships()`
- `test_get_weakness_knowledge_nodes()`
- `test_get_quizzes_for_knowledge()`
- `test_get_recent_quiz_ids()`
- `test_get_random_quizzes()`

### Integration Tests

- `test_suggest_quiz_existing_user()`
- `test_suggest_quiz_new_user()`
- `test_suggest_quiz_with_topic_filter()`
- `test_suggest_quiz_history_deduplication()`

### Edge Cases

- Student with no quizzes for weakness knowledge
- Empty quiz history
- Topic filter with no matches
- quiz_limit larger than available quizzes

---

## 🔧 Configuration

### Quiz History Limit

```python
# student/quiz_suggestion/engine/policies.py
ATTEMPT_HISTORY_LEN = 15  # Last 15 quizzes stored
```

### Deduplication Window

```python
# In SuggestQuizService.run()
recent_quiz_ids = self._get_recent_quiz_ids(profile, n=5)  # Last 5 for deduplication
```

---

## 📈 Performance

### Optimization Strategies

1. **Cypher Query Optimization**
   - Index on `Student.db_id`
   - Index on `Knowledge.name`
   - Limit results to needed data

2. **Caching**
   - User profiles (file-based, fast)
   - Knowledge graph (session cache)
   - Quiz bank (frequently accessed)

3. **Connection Pooling**
   - Neo4j connection management
   - Configured in `core/settings.py`

---

## 🐛 Error Handling

### Common Errors

| Error | Status | Cause | Solution |
|-------|--------|-------|----------|
| Missing username | 400 | Required field not provided | Include `student.username` |
| Invalid quiz_limit | 400 | quiz_limit < 1 | Use quiz_limit >= 1 |
| No quizzes available | 404 | Empty quiz bank | Add quizzes to database |
| Database error | 500 | Neo4j connection issue | Check database connection |

---

## 🔗 Related Features

### Submit Answer
- **Purpose**: Process quiz answers and update student knowledge
- **Link**: `docs/submit-answer/INDEX.md`
- **Relationship**: Updates `StudentKnowledgeRel.last_score` used by Suggest Quiz

### Get Student Graph
- **Purpose**: Retrieve student's knowledge graph with scores
- **Service**: `student/services/get_student_graph_service.py`
- **Relationship**: Visualizes same data used for quiz suggestions

---

## 📝 Change History

### 2025-10-08: Weakness-Based Refactoring

**Changes**:
- Refactored from suggestion engine to weakness-based approach
- Direct Neo4j queries for student knowledge relationships
- Simplified algorithm (removed spaced repetition, prerequisites, difficulty adaptation)
- Updated quiz history limit from 200 to 15

**Rationale**:
- Simpler, more maintainable code
- Direct use of Neo4j as single source of truth
- Better alignment with business requirements

**Migration**:
- No data migration required
- Backward compatible API
- Existing user profiles continue to work

---

## 🚧 Future Enhancements

### Planned Features

1. **Adaptive Difficulty** (Q1 2026)
   - Match quiz difficulty to student level
   - Gradually increase difficulty as student improves

2. **Spaced Repetition** (Q2 2026)
   - Prioritize overdue reviews
   - Implement forgetting curve algorithm

3. **Learning Path** (Q2 2026)
   - Suggest knowledge topics to focus on
   - Visualize learning progress

4. **Neo4j Quiz History** (Q3 2026)
   - Move attempt history to Neo4j relationships
   - Enable graph-based analytics

5. **Smart New User Flow** (Q3 2026)
   - Better initial assessment strategy
   - Adaptive first quiz selection

---

## 📚 Additional Resources

### System Documentation
- **[Architecture Overview](../architecture_overview.md)**: System-wide architecture
- **[Neo4j Schema](../neo4j_schema.md)**: Graph database schema
- **[URL Structure](../url_structure.md)**: API routing conventions

### Code Documentation
- **Quiz Suggestion Engine**: `student/quiz_suggestion/README.md`
- **API Style Guide**: `.augment/rules/api_style.md`
- **File Organization**: `.augment/rules/file_organization.md`

### Related ADRs
- **[Student-Knowledge Relationship Tracking](../submit-answer/adr/0001-student-knowledge-relationship-tracking.md)**

---

## 👥 Contributors

- **@ceofourfactplus**: Original implementation and refactoring

---

## 📞 Support

For questions or issues:
1. Check this documentation
2. Review related ADRs
3. Check code comments in `student/services/suggest_quiz_service.py`
4. Contact feature owner

---

**Last Updated**: 2025-10-08
**Status**: ✅ Active
**Version**: 2.0 (Weakness-Based)

