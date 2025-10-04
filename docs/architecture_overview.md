# Architecture: Single Source of Truth Analysis

## Current Architecture

The project follows a **layered architecture** with the quiz suggestion engine as the single source of truth:

```
┌─────────────────────────────────────────────────────────────┐
│                  Quiz Suggestion Engine                      │
│              (student/quiz_suggestion/)                      │
│                                                              │
│  Core Functions (Single Source of Truth):                   │
│  - suggest_next_quiz()                                       │
│  - update_scores()                                           │
│  - get_learning_progress()                                   │
│  - load_quizzes_from_neo4j()                                 │
│  - KnowledgeGraph.from_neo4j()                               │
│  - UserProfile (Pydantic models)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   API Services   │                  │   CLI Command    │
│  (API Layer)     │                  │ (Interactive)    │
├──────────────────┤                  ├──────────────────┤
│ SuggestQuiz      │                  │ quiz_suggestion  │
│ SubmitAnswers    │                  │ QuizSession      │
│ GetStudentGraph  │                  │ cli_helpers      │
└──────────────────┘                  └──────────────────┘
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   REST API       │                  │   Terminal       │
│ (HTTP/JSON)      │                  │ (Interactive)    │
└──────────────────┘                  └──────────────────┘
```

## Single Source of Truth: Quiz Suggestion Engine

### Core Functions

Both the API services and CLI command use the **same underlying functions** from the quiz suggestion engine:

#### 1. `suggest_next_quiz(profile, kg, quizzes) -> Quiz`
- **Used by**: SuggestQuizService, QuizSession
- **Purpose**: Adaptive quiz selection algorithm
- **Single source**: `student/quiz_suggestion/__init__.py`

#### 2. `update_scores(profile, quiz, is_correct, kg) -> UserProfile`
- **Used by**: SubmitAnswersService, QuizSession
- **Purpose**: Score updates and spaced repetition
- **Single source**: `student/quiz_suggestion/__init__.py`

#### 3. `load_quizzes_from_neo4j() -> List[Quiz]`
- **Used by**: SuggestQuizService, quiz_suggestion command
- **Purpose**: Load quiz bank from database
- **Single source**: `student/quiz_suggestion/__init__.py`

#### 4. `KnowledgeGraph.from_neo4j() -> KnowledgeGraph`
- **Used by**: All services, CLI command
- **Purpose**: Load knowledge graph structure
- **Single source**: `student/quiz_suggestion/models/knowledge_graph.py`

#### 5. `UserProfile` (Pydantic model)
- **Used by**: All services, CLI command
- **Purpose**: Track student learning state
- **Single source**: `student/quiz_suggestion/models/user_profile.py`

## Code Comparison

### API Service (SuggestQuizService)

```python
# student/services/suggest_quiz_service.py
from student.quiz_suggestion import suggest_next_quiz, KnowledgeGraph, UserProfile

class SuggestQuizService(BaseService):
    def run(self):
        # Load profile
        profile = self._load_user_profile(username)
        
        # Load knowledge graph
        kg = KnowledgeGraph.from_neo4j()
        
        # Load quizzes
        quizzes = load_quizzes_from_neo4j()
        
        # Get suggestions using engine
        quiz = suggest_next_quiz(profile, kg, quizzes)
        
        # Convert to API format
        return self._convert_to_api_format(quiz)
```

### CLI Command (quiz_suggestion)

```python
# student/management/commands/quiz_suggestion.py
from student.quiz_suggestion import suggest_next_quiz, KnowledgeGraph, UserProfile

class Command(BaseCommand):
    def run_test_session(self, options):
        # Load profile
        profile = self.load_profile(user_id, profile_path)
        
        # Load knowledge graph
        kg = KnowledgeGraph.from_neo4j()
        
        # Load quizzes
        quizzes = load_quizzes_from_neo4j()
        
        # Get suggestions using engine
        quiz = suggest_next_quiz(profile, kg, quizzes)
        
        # Display in terminal
        display_quiz(quiz, self.stdout, self.style)
```

### QuizSession Helper

```python
# student/quiz_suggestion/cli_helpers.py
from student.quiz_suggestion import suggest_next_quiz, update_scores

class QuizSession:
    def get_next_quiz(self):
        return suggest_next_quiz(self.profile, self.kg, self.quizzes)
    
    def submit_answer(self, quiz, is_correct):
        self.profile = update_scores(self.profile, quiz, is_correct, self.kg)
```

## Analysis: Is This Single Source of Truth?

### ✅ YES - The Engine is the Single Source

**Evidence:**
1. Both API and CLI use the **exact same functions** from the quiz suggestion engine
2. The core logic (scoring, suggestion algorithm, graph traversal) is in **one place**
3. Changes to the engine automatically affect both API and CLI
4. No duplication of business logic

**Benefits:**
- Clean separation of concerns
- Engine is framework-agnostic (no Django/DRF dependencies)
- Can be tested independently
- Can be reused in other contexts (e.g., batch processing, analytics)

### ❌ NO - If You Consider Services as the Source

**Argument:**
- Services add additional logic (validation, error handling, Neo4j student lookup)
- CLI doesn't use this service-level logic
- Could lead to inconsistencies if service logic changes

**Counter-argument:**
- Service logic is **API-specific** (HTTP status codes, serialization)
- CLI has **different concerns** (terminal display, user input)
- Forcing CLI to use services would add unnecessary overhead

## Recommendation

### Current Architecture is Correct ✅

The current architecture **already follows single source of truth**:

1. **Core Logic**: Quiz suggestion engine (framework-agnostic)
2. **API Layer**: Services (add HTTP/REST concerns)
3. **CLI Layer**: Commands (add interactive concerns)

### Why This is Better Than CLI Using Services

| Aspect | Current (CLI uses engine) | Alternative (CLI uses services) |
|--------|---------------------------|----------------------------------|
| **Separation of concerns** | ✅ Clean | ❌ Mixed (CLI has API concerns) |
| **Performance** | ✅ Direct | ❌ Extra layer |
| **Flexibility** | ✅ Each optimized for use case | ❌ CLI constrained by API design |
| **Dependencies** | ✅ Minimal | ❌ CLI depends on API services |
| **Testing** | ✅ Can test engine independently | ❌ Must test through services |
| **Error handling** | ✅ Appropriate for each context | ❌ HTTP errors in CLI? |

### What IS Shared (Single Source of Truth)

✅ **Scoring algorithm** - `update_scores()`  
✅ **Suggestion algorithm** - `suggest_next_quiz()`  
✅ **Knowledge graph** - `KnowledgeGraph`  
✅ **User profiles** - `UserProfile`  
✅ **Quiz loading** - `load_quizzes_from_neo4j()`  

### What is NOT Shared (Appropriately Different)

✅ **Input validation** - Services use DRF serializers, CLI uses argparse  
✅ **Output format** - Services return JSON, CLI prints to terminal  
✅ **Error handling** - Services raise APIError with HTTP codes, CLI prints errors  
✅ **Student lookup** - Services find by graph_id, CLI uses username  

## Potential Issues and Solutions

### Issue 1: Service Logic Not in CLI

**Example**: If we add caching to SuggestQuizService, CLI won't benefit.

**Solution**: Add caching to the **engine** level, not service level.

```python
# Good: Cache in engine
@lru_cache
def load_quizzes_from_neo4j():
    # Both API and CLI benefit
    pass

# Bad: Cache in service
class SuggestQuizService:
    def run(self):
        # Only API benefits
        cached_quizzes = self._get_cached_quizzes()
```

### Issue 2: Validation Differences

**Example**: API validates quiz_limit (1-100), CLI doesn't.

**Solution**: Add validation to the **engine** if it's business logic.

```python
# Good: Validate in engine
def suggest_next_quiz(profile, kg, quizzes, limit=10):
    if limit < 1 or limit > 100:
        raise ValueError("limit must be 1-100")
    # Both API and CLI get validation
```

### Issue 3: Profile Loading Duplication

**Current**: Both services and CLI have profile loading logic.

**Solution**: Already solved - both use `UserProfile.load_from_file()`.

```python
# Engine provides the method
class UserProfile:
    @classmethod
    def load_from_file(cls, path: Path):
        # Single implementation
        pass

# Both use it
profile = UserProfile.load_from_file(path)  # Service
profile = UserProfile.load_from_file(path)  # CLI
```

## Best Practices Going Forward

### ✅ DO: Put Business Logic in Engine

```python
# student/quiz_suggestion/__init__.py
def suggest_next_quiz(profile, kg, quizzes, **options):
    # Core algorithm here
    # Both API and CLI use this
    pass
```

### ✅ DO: Put API Concerns in Services

```python
# student/services/suggest_quiz_service.py
class SuggestQuizService(BaseService):
    def run(self):
        # HTTP validation
        # Neo4j student lookup
        # JSON serialization
        # Call engine
        pass
```

### ✅ DO: Put CLI Concerns in Commands

```python
# student/management/commands/quiz_suggestion.py
class Command(BaseCommand):
    def handle(self):
        # Argument parsing
        # Terminal display
        # User input
        # Call engine
        pass
```

### ❌ DON'T: Duplicate Business Logic

```python
# Bad: Scoring logic in service
class SubmitAnswersService:
    def _calculate_score(self, is_correct):
        return 1.0 if is_correct else -1.0  # Duplicates engine logic!

# Good: Use engine
class SubmitAnswersService:
    def run(self):
        profile = update_scores(profile, quiz, is_correct, kg)  # Uses engine
```

### ❌ DON'T: Put API Logic in Engine

```python
# Bad: HTTP concerns in engine
def suggest_next_quiz(profile, kg, quizzes):
    if not quizzes:
        raise APIError("No quizzes", status_code=404)  # API-specific!

# Good: Keep engine framework-agnostic
def suggest_next_quiz(profile, kg, quizzes):
    if not quizzes:
        raise NoQuizAvailableError("No quizzes")  # Generic exception
```

## Conclusion

### ✅ Current Architecture is Correct

The project **already follows single source of truth** principles:

1. **Quiz suggestion engine** = Single source of truth for business logic
2. **Services** = API-specific layer (HTTP, validation, serialization)
3. **CLI** = Interactive layer (terminal, user input, display)

### No Refactoring Needed

The CLI command does **NOT** need to use the services because:
- Both already use the same underlying engine
- Services have API-specific concerns that don't apply to CLI
- Current architecture is cleaner and more maintainable

### If You Still Want CLI to Use Services

If you insist on having the CLI use services, here's what would be needed:

1. **Adapt service inputs** - Services expect serialized data, CLI has Pydantic models
2. **Ignore HTTP concerns** - CLI doesn't care about status codes
3. **Extract responses** - Services return API format, CLI needs different format
4. **Add overhead** - Extra layer for no benefit

**Recommendation**: Keep the current architecture. It's correct.

## Summary

| Component | Role | Uses |
|-----------|------|------|
| **Quiz Suggestion Engine** | Single source of truth | Core algorithms, models |
| **API Services** | HTTP/REST interface | Engine + API concerns |
| **CLI Commands** | Interactive interface | Engine + CLI concerns |

**Both API and CLI use the same engine = Single source of truth ✅**

