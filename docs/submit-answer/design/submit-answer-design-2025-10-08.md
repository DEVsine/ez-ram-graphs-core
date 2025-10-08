---
feature: submit-answer
type: design
status: approved
owners: ["@ceofourfactplus"]
code_refs: ["student/services/submit_answers_service.py", "student/api_views.py", "student/serializers.py"]
related_docs: ["../requirements/submit-answer-requirements.md", "../testing/submit-answer-test-strategy.md"]
last_validated: "2025-10-08"
---

# Submit Answer - Design Document

## Summary

This document describes the architecture and implementation of the Submit Answer feature, which processes student quiz submissions and updates their learning profiles using an adaptive scoring algorithm integrated with a knowledge graph.

## Architecture Overview

### High-Level Flow

```
Client Request
    ↓
SubmitAnswersAPI (View Layer)
    ↓ [Validation via Serializer]
SubmitAnswersService (Business Logic)
    ↓
┌─────────────────────────────────────┐
│ 1. Load Student Node (Neo4j)        │
│ 2. Load/Create UserProfile (JSON)   │
│ 3. Load KnowledgeGraph (Neo4j)      │
│ 4. Process Each Answer:             │
│    - Validate quiz exists           │
│    - Check correctness              │
│    - Calculate score adjustments    │
│    - Update profile                 │
│ 5. Save UserProfile (JSON)          │
│ 6. Build Response                   │
└─────────────────────────────────────┘
    ↓
JSON Response
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  SubmitAnswersAPI (student/api_views.py)                    │
│  - Authentication & Authorization                            │
│  - Request Validation (SubmitAnswersRequestSerializer)       │
│  - Response Formatting                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                              │
│  SubmitAnswersService (student/services/)                   │
│  - Business Logic                                            │
│  - Answer Processing                                         │
│  - Score Calculation                                         │
│  - Profile Management                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────┬──────────────────┬──────────────────────┐
│   Quiz Engine    │   Neo4j Layer    │   File Storage       │
│  (quiz_suggest)  │  (neo_models)    │   (JSON)             │
│  - update_scores │  - Student       │  - UserProfile       │
│  - KnowledgeGraph│  - Quiz          │  - data/profiles/    │
│  - UserProfile   │  - Choice        │                      │
│                  │  - Knowledge     │                      │
└──────────────────┴──────────────────┴──────────────────────┘
```

## Detailed Design

### 1. API Layer (View)

**File**: `student/api_views.py`

**Class**: `SubmitAnswersAPI(BaseAPIView)`

**Responsibilities**:
- Authenticate user (TokenAuthentication)
- Validate request data using `SubmitAnswersRequestSerializer`
- Delegate to service layer
- Format and return response

**Implementation**:
```python
def post(self, request, ram_id: str):
    # Validate request data
    serializer = SubmitAnswersRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Execute service with validated data
    ctx = ServiceContext(user=request.user, ram_id=ram_id)
    result = SubmitAnswersService.execute(serializer.validated_data, ctx=ctx)
    
    return self.ok(result)
```

### 2. Serialization Layer

**File**: `student/serializers.py`

**Classes**:
- `AnswerSubmissionSerializer`: Validates individual answer
- `SubmitAnswersRequestSerializer`: Validates full request

**Validation Rules**:
- `student_id`: Required, non-empty string
- `answers`: Required, non-empty list
- `quiz_gid`: Required for each answer
- `answer_gid`: Required for each answer
- `time_to_answer`: Optional, non-negative integer
- `use_helper`: Optional, list of strings
- `time_read_answer`: Optional, non-negative integer
- `choice_cutting`: Optional, list of strings

### 3. Service Layer

**File**: `student/services/submit_answers_service.py`

**Class**: `SubmitAnswersService(BaseService[Dict[str, Any], Dict[str, Any]])`

**Main Method**: `run() -> Dict[str, Any]`

**Processing Steps**:

#### Step 1: Load Student Node
```python
def _get_student(self, student_id: str) -> NeoStudent | None:
    """Find student node in Neo4j."""
    try:
        qs = NeoStudent.nodes.filter(db_id=student_id)
        student_node = qs.first()
        return student_node
    except Exception as e:
        logger.warning(f"Failed to get student node: {e}")
        return None
```

**Purpose**: Retrieve or identify student in Neo4j graph
**Error Handling**: Returns None if not found, logs warning

#### Step 2: Load User Profile
```python
def _load_user_profile(self, student_id: str) -> UserProfile:
    """Load or create a UserProfile for the student."""
    profile_path = Path("data/profiles") / f"{student_id}.json"
    
    if profile_path.exists():
        try:
            profile = UserProfile.load_from_file(profile_path)
            logger.info(f"Loaded existing profile for {student_id}")
            return profile
        except Exception as e:
            logger.warning(f"Failed to load profile: {e}. Creating new.")
    
    # Create new profile
    profile = UserProfile(user_id=student_id)
    logger.info(f"Created new profile for {student_id}")
    return profile
```

**Purpose**: Load existing learning profile or create new one
**Storage**: JSON file in `data/profiles/{student_id}.json`
**Fallback**: Creates new profile if file missing or corrupted

#### Step 3: Load Knowledge Graph
```python
kg = KnowledgeGraph.from_neo4j()
logger.info(f"Loaded knowledge graph with {len(kg.nodes())} nodes")
```

**Purpose**: Load complete knowledge graph structure
**Implementation**: NetworkX DiGraph loaded from Neo4j
**Error Handling**: Raises APIError if loading fails

#### Step 4: Process Each Answer
```python
def _process_answer(
    self,
    answer_data: Dict[str, Any],
    profile: UserProfile,
    kg: KnowledgeGraph,
    student_id: str,
) -> Dict[str, float]:
    """Process a single answer submission and return knowledge adjustments."""
    
    # 4.1: Get quiz from Neo4j
    neo_quiz = self._get_neo_quiz_by_id(quiz_gid)
    if neo_quiz is None:
        logger.warning(f"Quiz {quiz_gid} not found")
        return {}
    
    # 4.2: Check answer correctness
    is_correct = self._check_answer_correctness(neo_quiz, answer_gid)
    
    # 4.3: Convert to Pydantic model
    pydantic_quiz = PydanticQuiz.from_neo4j(neo_quiz)
    
    # 4.4: Store old scores
    old_scores = {
        node_id: profile.get_score(node_id)
        for node_id in pydantic_quiz.linked_nodes
    }
    
    # 4.5: Update scores using quiz suggestion engine
    profile = update_scores(profile, pydantic_quiz, is_correct, kg)
    
    # 4.6: Calculate adjustments
    adjustments = {}
    for node_id in pydantic_quiz.linked_nodes:
        new_score = profile.get_score(node_id)
        old_score = old_scores.get(node_id, 0.0)
        delta = new_score - old_score
        if delta != 0:
            adjustments[node_id] = delta
    
    return adjustments
```

**Sub-steps**:
1. **Quiz Retrieval**: Find quiz by element_id in Neo4j
2. **Correctness Check**: Compare answer_gid with correct choice
3. **Model Conversion**: Convert Neo4j model to Pydantic for engine
4. **Score Snapshot**: Capture current scores before update
5. **Score Update**: Apply scoring algorithm from quiz suggestion engine
6. **Delta Calculation**: Compute score changes for each knowledge node

**Error Handling**: Returns empty dict on failure, continues processing other answers

#### Step 5: Accumulate Adjustments
```python
all_adjustments: Dict[str, float] = {}

for idx, answer_data in enumerate(answers):
    try:
        adjustments = self._process_answer(answer_data, profile, kg, student_id)
        
        # Accumulate adjustments
        for node_id, delta in adjustments.items():
            all_adjustments[node_id] = all_adjustments.get(node_id, 0.0) + delta
    except Exception as e:
        logger.error(f"Failed to process answer {idx}: {e}")
        continue
```

**Purpose**: Sum all score changes across multiple answers
**Resilience**: Individual answer failures don't stop processing

#### Step 6: Save User Profile
```python
def _save_user_profile(self, profile: UserProfile, student_id: str):
    """Save user profile to file."""
    profile_path = Path("data/profiles")
    profile_path.mkdir(parents=True, exist_ok=True)
    
    file_path = profile_path / f"{student_id}.json"
    profile.save_to_file(file_path)
    logger.info(f"Saved profile for {student_id}")
```

**Purpose**: Persist updated profile to disk
**Safety**: Creates directory if missing

#### Step 7: Build Response
```python
def _build_graph_updates(
    self, adjustments: Dict[str, float], kg: KnowledgeGraph
) -> List[Dict[str, Any]]:
    """Build the graph_update response array."""
    graph_updates = []
    
    for node_id, adjustment in adjustments.items():
        # Get knowledge node name from the graph
        node_data = kg.graph.nodes.get(node_id, {})
        knowledge_name = node_data.get("name", "Unknown")
        
        graph_updates.append({
            "graph_id": node_id,
            "knowledge": knowledge_name,
            "adjustment": round(adjustment, 2),
        })
    
    # Sort by absolute adjustment (largest changes first)
    graph_updates.sort(key=lambda x: abs(x["adjustment"]), reverse=True)
    
    return graph_updates
```

**Purpose**: Format adjustments for API response
**Sorting**: Largest absolute changes first (most impactful)

### 4. Quiz Suggestion Engine Integration

**Module**: `student.quiz_suggestion`

**Key Function**: `update_scores(profile, quiz, is_correct, knowledge_graph)`

**Algorithm**:
1. Identify linked knowledge nodes from quiz
2. Apply scoring policy based on correctness:
   - **Correct**: Increase scores, apply prerequisite bonuses
   - **Incorrect**: Decrease scores, penalize related nodes
3. Update spaced repetition schedule
4. Record attempt in history
5. Return updated profile

**Scoring Bounds**: [-5, 10] (configurable in policies)

**Spaced Repetition**: Uses interval-based scheduling for review timing

### 5. Data Models

#### UserProfile (Pydantic)
```python
class UserProfile(BaseModel):
    user_id: str
    scores: Dict[str, float] = {}  # node_id -> score
    schedule: Dict[str, ScheduleEntry] = {}  # node_id -> schedule
    attempt_history: List[AttemptRecord] = []
    total_attempts: int = 0
    total_correct: int = 0
    last_updated: datetime
```

#### KnowledgeGraph (NetworkX)
```python
class KnowledgeGraph:
    graph: nx.DiGraph  # Directed graph of knowledge dependencies
    
    def get_prerequisites(node_id: str) -> List[str]
    def is_prerequisite_met(node_id: str, profile: UserProfile) -> bool
    def get_topological_order() -> List[str]
```

#### Neo4j Models
- **Student**: `username`, `db_id`, `related_to` -> Knowledge
- **Quiz**: `quiz_text`, `difficulty_level`, `quiz_type`
- **Choice**: `choice_text`, `is_correct`, `answer_explanation`
- **Knowledge**: `name`, `description`, `example`, `depends_on` -> Knowledge

## Update Student-Knowledge Relationships (Planned Feature)

### Current Status
**Implementation exists but is DISABLED** (commented out in lines 94-101)

### Design
```python
# Link student to knowledge nodes
for node_id in all_adjustments:
    try:
        knowledge_node = NeoKnowledge.nodes.get(name=node_id)
        student_node.related_to.connect(knowledge_node)
    except Exception as e:
        logger.error(f"Failed to link student to knowledge node {node_id}: {e}")
        continue
```

### Purpose
Create RELATED_TO relationships in Neo4j between Student and Knowledge nodes to track:
- Which topics a student has engaged with
- Learning path visualization
- Relationship-based queries

### Why Disabled
Likely disabled due to:
- Performance concerns (N queries per submission)
- Duplicate relationship handling needed
- Need for relationship properties (score, timestamp)

### Recommended Implementation
```python
def _update_student_knowledge_links(
    self, 
    student_node: NeoStudent, 
    adjustments: Dict[str, float]
):
    """Create/update Student-Knowledge relationships in Neo4j."""
    if not student_node:
        return
    
    for node_id, adjustment in adjustments.items():
        try:
            # Find knowledge node by element_id
            knowledge_nodes = NeoKnowledge.nodes.all()
            for k_node in knowledge_nodes:
                if getattr(k_node, "element_id", None) == node_id:
                    # Check if relationship exists
                    if not student_node.related_to.is_connected(k_node):
                        student_node.related_to.connect(k_node)
                        logger.info(f"Linked student to knowledge: {k_node.name}")
                    break
        except Exception as e:
            logger.error(f"Failed to link knowledge {node_id}: {e}")
            continue
```

**Improvements**:
- Check for existing relationships before creating
- Use element_id for matching (not name)
- Batch operations for performance
- Consider adding relationship properties (last_score, last_updated)

## Error Handling Strategy

### Input Validation Errors (400)
- Missing student_id
- Empty answers array
- Invalid answer format

### Business Logic Errors (Logged, Continue Processing)
- Quiz not found
- Answer choice not found
- Profile loading failure (creates new)
- Individual answer processing failure

### System Errors (500)
- Knowledge graph loading failure
- Neo4j connection failure
- File system errors

### Error Response Format
```json
{
  "error": {
    "code": "error_code_slug",
    "message": "Human-readable message",
    "details": {}
  }
}
```

## Performance Considerations

### Optimization Strategies
1. **Knowledge Graph Caching**: Load once per request
2. **Batch Neo4j Queries**: Minimize round trips
3. **Parallel Processing**: Process independent answers concurrently (future)
4. **Profile Caching**: In-memory cache for frequent users (future)

### Current Bottlenecks
1. Loading knowledge graph from Neo4j (O(N) nodes + O(E) edges)
2. Quiz lookup by element_id (iterates all quizzes)
3. File I/O for profile save

### Scalability Limits
- **Current**: ~100 answers per request
- **Knowledge Graph**: Tested up to 1000 nodes
- **Concurrent Users**: Limited by Neo4j connection pool

## Security Considerations

### Authentication & Authorization
- TokenAuthentication required
- IsAuthenticated permission enforced
- User context passed to service

### Input Validation
- All inputs validated via DRF serializers
- No raw SQL/Cypher injection possible (using neomodel ORM)

### Data Privacy
- Student profiles stored in isolated JSON files
- No sensitive data logged
- Graph IDs used (not exposing internal structure)

## Future Enhancements

### 1. Enable Student-Knowledge Relationships
- Implement optimized linking logic
- Add relationship properties (score, timestamp)
- Create visualization endpoints

### 2. Real-time Updates
- WebSocket support for live score updates
- Push notifications for achievements

### 3. Advanced Analytics
- Track helper usage patterns
- Analyze time-to-answer correlations
- Predict knowledge gaps

### 4. Performance Optimization
- Redis caching for profiles and graphs
- Batch Neo4j operations
- Async processing for large submissions

