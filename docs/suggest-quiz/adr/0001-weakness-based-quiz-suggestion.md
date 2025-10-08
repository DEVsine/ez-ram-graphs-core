---
feature: suggest-quiz
type: adr
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/suggest_quiz_service.py"]
related_docs: ["requirements/suggest-quiz-requirements.md", "design/suggest-quiz-design.md"]
last_validated: "2025-10-08"
updated: "2025-10-08"
---

# ADR 0001: Weakness-Based Quiz Suggestion with Neo4j Student-Knowledge Relationships

## Status

**APPROVED** - Implemented on 2025-10-08

## Context

The original quiz suggestion service used a file-based UserProfile system with a complex suggestion engine that considered:

- Knowledge graph structure (prerequisites)
- Spaced repetition scheduling
- Difficulty adaptation
- User scores stored in JSON files

However, we needed a simpler, more direct approach that:

1. Uses Neo4j Student-Knowledge relationships (`StudentKnowledgeRel.last_score`) to identify weakness areas
2. Suggests quizzes based on the student's weakest knowledge topics
3. Avoids duplicating quizzes from recent history (last 5 attempts)
4. Supports topic scoping for focused learning
5. Handles new users (no knowledge relationships) with random quiz selection

### Problems with Previous Approach

1. **Complexity**: The suggestion engine had many configurable policies and complex scoring logic
2. **Dual Storage**: Scores were stored both in Neo4j relationships AND JSON files
3. **Inconsistency**: The suggestion engine didn't directly use Neo4j relationship data
4. **Maintenance**: Complex codebase with many interdependent components

### Requirements

- Query student's weakness knowledge from Neo4j `StudentKnowledgeRel.last_score`
- Suggest quizzes related to weakness knowledge (lowest scores first)
- Avoid duplicating quizzes from last 5 quiz history
- Support `scope_topic` filtering
- Handle new users with random quiz selection
- Track quiz history (last 15 quizzes) for deduplication

## Decision

**We refactored `SuggestQuizService` to use a weakness-based approach with direct Neo4j queries.**

### New Algorithm

#### For Existing Users (with knowledge relationships):

1. **Get Student Node**: Retrieve or create student from Neo4j
2. **Load User Profile**: Load UserProfile for quiz history tracking
3. **Get Recent Quiz IDs**: Extract last 5 quiz IDs from `UserProfile.attempt_history`
4. **Query Weakness Knowledge**: Use Cypher query to get knowledge nodes ordered by `last_score` ASC (lowest first)
   ```cypher
   MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
   WHERE elementId(s) = $student_id
   [AND toLower(k.name) CONTAINS toLower($topic)]  // if scope_topic provided
   RETURN k, r.last_score as score
   ORDER BY r.last_score ASC
   ```
5. **Collect Quizzes**: For each weakness knowledge node (in order):
   - Get related quizzes via `Knowledge.related_quizzes`
   - Filter out quizzes from last 5 history
   - Add to suggestion list
   - Stop when `quiz_limit` is reached

#### For New Users (no knowledge relationships):

1. **Get Random Quizzes**: Query all quizzes (optionally filtered by `scope_topic`)
2. **Exclude Recent**: Filter out quizzes from last 5 history
3. **Random Selection**: Randomly select up to `quiz_limit` quizzes

### Implementation Changes

#### 1. Updated Imports

```python
import random
from neomodel import db
from knowledge.neo_models import Knowledge as NeoKnowledge
```

Removed:

- `KnowledgeGraph`
- `suggest_next_quiz`
- `load_quizzes_from_neo4j`
- `NoQuizAvailableError`

#### 2. New Helper Methods

- `_has_knowledge_relationships(student_node)`: Check if student has any RELATED_TO relationships
- `_get_weakness_knowledge_nodes(student_node, scope_topic)`: Query weakness knowledge via Cypher
- `_get_quizzes_for_knowledge(knowledge_node)`: Get quizzes related to a knowledge node
- `_get_recent_quiz_ids(profile, n=5)`: Extract recent quiz IDs from attempt history
- `_get_random_quizzes(scope_topic, limit, exclude_quiz_ids)`: Get random quizzes for new users

#### 3. Removed Methods

- `_filter_by_topic()`: Topic filtering now done in Cypher queries
- `_get_neo_quiz_by_id()`: No longer needed (working with Neo4j nodes directly)

#### 4. Updated `_convert_quizzes_to_response()`

Changed signature from:

```python
def _convert_quizzes_to_response(self, pydantic_quizzes: list) -> List[Dict[str, Any]]
```

To:

```python
def _convert_quizzes_to_response(self, neo_quizzes: List[NeoQuiz]) -> List[Dict[str, Any]]
```

Now works directly with Neo4j Quiz nodes instead of Pydantic models.

#### 5. Updated Quiz History Limit

Changed `ATTEMPT_HISTORY_LEN` from 200 to 15 in `student/quiz_suggestion/engine/policies.py`:

```python
# Updated to 15 to match quiz history requirement for suggest-quiz deduplication
ATTEMPT_HISTORY_LEN = 15
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SuggestQuizService                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Get Student Node │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Load UserProfile │
                    │ (quiz history)   │
                    └──────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Has Knowledge Relationships?│
                └─────────────────────────────┘
                       │              │
                  YES  │              │  NO
                       ▼              ▼
        ┌──────────────────────┐  ┌──────────────────┐
        │ Query Weakness       │  │ Get Random       │
        │ Knowledge (Cypher)   │  │ Quizzes          │
        │ ORDER BY last_score  │  │ (filtered by     │
        │                      │  │  scope_topic)    │
        └──────────────────────┘  └──────────────────┘
                       │              │
                       ▼              ▼
        ┌──────────────────────┐  ┌──────────────────┐
        │ For each knowledge:  │  │ Random sample    │
        │ - Get related quizzes│  │ up to quiz_limit │
        │ - Filter recent (5)  │  │                  │
        │ - Add to list        │  │                  │
        └──────────────────────┘  └──────────────────┘
                       │              │
                       └──────┬───────┘
                              ▼
                    ┌──────────────────┐
                    │ Convert to API   │
                    │ Response Format  │
                    └──────────────────┘
```

## Consequences

### Positive

1. **Simplicity**: Much simpler logic, easier to understand and maintain
2. **Direct Neo4j Usage**: Uses Neo4j relationships as single source of truth
3. **Performance**: Direct Cypher queries are efficient
4. **Flexibility**: Easy to adjust weakness criteria or add filters
5. **Consistency**: No dual storage of scores (Neo4j only)

### Negative

1. **Lost Features**: No longer uses:
   - Spaced repetition scheduling
   - Prerequisite validation
   - Difficulty adaptation
   - Complex scoring policies
2. **Simpler Algorithm**: May not be as sophisticated for adaptive learning
3. **New User Experience**: Random quizzes may not be optimal for initial assessment

### Neutral

1. **Quiz History**: Still uses UserProfile for attempt history (could be moved to Neo4j in future)
2. **Topic Filtering**: Now done in Cypher queries instead of Python

## Alternatives Considered

### Alternative 1: Keep Suggestion Engine, Add Neo4j Integration

**Pros**: Retain sophisticated features
**Cons**: Increased complexity, dual storage issues persist

**Decision**: Rejected - Complexity outweighed benefits

### Alternative 2: Move Quiz History to Neo4j

**Pros**: Single source of truth, better graph queries
**Cons**: More refactoring, potential performance impact

**Decision**: Deferred - Can be done in future iteration

### Alternative 3: Hybrid Approach

**Pros**: Use Neo4j for weakness detection, suggestion engine for selection
**Cons**: Still complex, unclear benefits

**Decision**: Rejected - Doesn't solve core issues

## Implementation Notes

### Testing Considerations

1. **Unit Tests**: Test each helper method independently
2. **Integration Tests**: Test full flow with Neo4j
3. **Edge Cases**:
   - New user (no relationships)
   - User with no quizzes for weakness knowledge
   - Empty quiz history
   - Topic filtering with no matches

### Migration Path

1. ✅ Update `ATTEMPT_HISTORY_LEN` to 15
2. ✅ Refactor `SuggestQuizService.run()`
3. ✅ Add new helper methods
4. ✅ Update `_convert_quizzes_to_response()`
5. ✅ Remove unused methods
6. ⏳ Update documentation
7. ⏳ Add/update tests
8. ⏳ Deploy and monitor

### Future Enhancements

1. **Adaptive Difficulty**: Reintroduce difficulty matching based on student level
2. **Spaced Repetition**: Add review scheduling for mastered topics
3. **Neo4j Quiz History**: Move attempt history to Neo4j relationships
4. **Smart New User Flow**: Better initial assessment for new users
5. **Learning Path**: Suggest knowledge topics to focus on

## References

- **Original Service**: `student/services/suggest_quiz_service.py` (before refactoring)
- **Student-Knowledge Relationships**: `docs/submit-answer/adr/0001-student-knowledge-relationship-tracking.md`
- **Quiz Suggestion Engine**: `student/quiz_suggestion/README.md`
- **Neo4j Schema**: `docs/neo4j_schema.md`

## Validation

- [x] Code compiles without errors
- [x] Service follows API style guide
- [x] Documentation updated
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

---

## Update: Neo4j Quiz History (2025-10-08)

### Change

Removed file-based `UserProfile` for quiz history tracking and migrated to Neo4j Student-[ATTEMPTED]->Quiz relationships.

### Rationale

1. **Single Source of Truth**: All student data now in Neo4j (no dual storage)
2. **Consistency**: Quiz history tracked in same database as knowledge relationships
3. **Simplicity**: Removed dependency on file-based UserProfile system
4. **Scalability**: Graph database better suited for relationship queries

### Implementation

1. **Added `StudentQuizRel` relationship model** in `student/neo_models.py`:

   ```python
   class StudentQuizRel(StructuredRel):
       attempted_at = DateTimeProperty()
       is_correct = BooleanProperty()
   ```

2. **Added `attempted` relationship** to Student model:

   ```python
   attempted = RelationshipTo("quiz.neo_models.Quiz", "ATTEMPTED", model=StudentQuizRel)
   ```

3. **Updated `_get_recent_quiz_ids()`** to query from Neo4j:

   ```cypher
   MATCH (s:Student)-[r:ATTEMPTED]->(q:Quiz)
   WHERE elementId(s) = $student_id
   RETURN q, r.attempted_at as attempted_at
   ORDER BY r.attempted_at DESC
   LIMIT $limit
   ```

4. **Removed `_load_user_profile()` method** and all UserProfile references

### Impact

- **Breaking Change**: Requires `submit_answers_service` to create Student-[ATTEMPTED]->Quiz relationships
- **Migration**: Existing quiz history in JSON files will not be migrated (fresh start)
- **Backward Compatibility**: API endpoint unchanged, response format unchanged

### Next Steps

1. Update `submit_answers_service` to create Student-[ATTEMPTED]->Quiz relationships
2. Add timestamp and correctness tracking to quiz attempts
3. Consider limiting quiz history to last 15 attempts (cleanup old relationships)
