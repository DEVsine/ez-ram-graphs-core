---
feature: submit-answer
type: adr
status: implemented
owners: ["@ceofourfactplus"]
code_refs: ["student/services/submit_answers_service.py", "student/services/adjust_knowledge_service.py", "student/neo_models.py"]
related_docs: ["../requirements/submit-answer-requirements.md", "../design/submit-answer-design-2025-10-08.md"]
last_validated: "2025-10-08"
---

# ADR 0001: Student-Knowledge Relationship Tracking in Neo4j

## Status

**✅ IMPLEMENTED** (2025-10-08)

## Context

When students submit quiz answers, the system updates their learning profile (stored in JSON files) with score adjustments for related knowledge nodes. This ADR documents the decision to enable persistent graph relationships in Neo4j between Student nodes and Knowledge nodes to track which topics a student has engaged with.

**Implementation completed on 2025-10-08** with both automatic (quiz submission) and manual (API endpoint) update capabilities.

### Current Implementation

- Student learning data is stored in JSON files (`data/profiles/{student_id}.json`)
- UserProfile contains scores for knowledge nodes (identified by element_id)
- No graph relationships exist between Student and Knowledge nodes in Neo4j
- Code exists to create these relationships but is commented out (lines 94-101 in `submit_answers_service.py`)

### Problem

Without Student-Knowledge relationships in the graph:

1. **No visual learning path**: Cannot visualize what topics a student has studied
2. **Limited graph queries**: Cannot use Cypher to find students by knowledge area
3. **No relationship-based analytics**: Cannot analyze learning patterns across students
4. **Disconnected data**: Student nodes exist in isolation from the knowledge graph

### Commented Code

```python
# link student to knowledge nodes
# for node_id in all_adjustments:
#     try:
#         knowledge_node = NeoKnowledge.nodes.get(name=node_id)
#         student_node.related_to.connect(knowledge_node)
#     except Exception as e:
#         logger.error(f"Failed to link student to knowledge node {node_id}: {e}")
#         continue
```

## Decision

**We propose to ENABLE Student-Knowledge relationship tracking with the following improvements:**

### 1. Create RELATED_TO Relationships

When a student submits answers that affect knowledge node scores, create `Student -[RELATED_TO]-> Knowledge` relationships in Neo4j.

### 2. Add Relationship Properties

Store metadata on the relationship:

- `last_score`: Most recent score for this knowledge node
- `last_updated`: Timestamp of last interaction
- `total_attempts`: Number of quizzes attempted for this knowledge
- `total_correct`: Number of correct answers for this knowledge

### 3. Implement Upsert Logic

- Check if relationship already exists before creating
- Update relationship properties if it exists
- Create new relationship if it doesn't exist

### 4. Use Element ID for Matching

- Match knowledge nodes by `element_id` (not `name`)
- Ensures correct node identification in Neo4j v5+

### 5. Batch Operations

- Collect all relationship updates
- Execute in a single transaction
- Minimize Neo4j round trips

### 6. Manual Adjustment via Function Input

Allow external systems, teachers, or administrators to manually adjust student-knowledge relationships through a dedicated function interface.

**Use Cases**:

- Teacher manually adjusts student mastery level
- Bulk import of student knowledge from external systems
- Administrative corrections or overrides
- Integration with other learning platforms
- Placement test results initialization

**Design Principles**:

- Accept explicit adjustment parameters (not derived from quiz answers)
- Support both score updates and relationship metadata updates
- Validate input to prevent invalid states
- Log all manual adjustments for audit trail
- Maintain consistency with automatic updates

## Proposed Implementation

```python
def _update_student_knowledge_links(
    self,
    student_node: NeoStudent,
    adjustments: Dict[str, float],
    profile: UserProfile
):
    """
    Create/update Student-Knowledge relationships in Neo4j.

    Args:
        student_node: Student node in Neo4j
        adjustments: Dict mapping knowledge node IDs to score adjustments
        profile: Updated user profile with current scores
    """
    if not student_node:
        logger.warning("No student node provided, skipping relationship updates")
        return

    updated_count = 0
    created_count = 0

    # Get all knowledge nodes once (avoid N queries)
    knowledge_nodes_map = {}
    for k_node in NeoKnowledge.nodes.all():
        element_id = getattr(k_node, "element_id", None)
        if element_id:
            knowledge_nodes_map[element_id] = k_node

    for node_id, adjustment in adjustments.items():
        try:
            knowledge_node = knowledge_nodes_map.get(node_id)
            if not knowledge_node:
                logger.warning(f"Knowledge node {node_id} not found in graph")
                continue

            # Check if relationship exists
            if student_node.related_to.is_connected(knowledge_node):
                # Update existing relationship properties
                rel = student_node.related_to.relationship(knowledge_node)
                rel.last_score = profile.get_score(node_id)
                rel.last_updated = datetime.now(timezone.utc)
                rel.total_attempts = getattr(rel, 'total_attempts', 0) + 1
                # Note: We don't know if this specific attempt was correct here
                rel.save()
                updated_count += 1
            else:
                # Create new relationship with properties
                student_node.related_to.connect(
                    knowledge_node,
                    {
                        'last_score': profile.get_score(node_id),
                        'last_updated': datetime.now(timezone.utc),
                        'total_attempts': 1,
                        'total_correct': 0  # Will be updated on subsequent attempts
                    }
                )
                created_count += 1

            logger.debug(f"Linked student to knowledge: {knowledge_node.name}")

        except Exception as e:
            logger.error(f"Failed to link knowledge {node_id}: {e}", exc_info=True)
            continue

    logger.info(
        f"Updated student-knowledge links: "
        f"{created_count} created, {updated_count} updated"
    )
```

### Manual Adjustment Function

```python
def adjust_student_knowledge(
    student_id: str,
    knowledge_adjustments: List[Dict[str, Any]],
    source: str = "manual",
    adjusted_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manually adjust student-knowledge relationships.

    This function allows external systems, teachers, or administrators to
    directly update student knowledge scores and relationships without
    going through the quiz submission flow.

    Args:
        student_id: Student database ID
        knowledge_adjustments: List of adjustments, each containing:
            - knowledge_id: Knowledge node element_id or name
            - score: New score value (optional, if updating score)
            - score_delta: Score adjustment amount (optional, alternative to score)
            - total_attempts: Override total attempts (optional)
            - total_correct: Override total correct (optional)
            - metadata: Additional metadata dict (optional)
        source: Source of adjustment ("manual", "import", "placement_test", etc.)
        adjusted_by: User/system making the adjustment (for audit trail)

    Returns:
        Dict containing:
            - updated_count: Number of relationships updated
            - created_count: Number of relationships created
            - adjustments: List of applied adjustments with details

    Raises:
        APIError: If student not found or invalid input

    Example:
        result = adjust_student_knowledge(
            student_id="123-ceo",
            knowledge_adjustments=[
                {
                    "knowledge_id": "4:node:123",
                    "score": 7.5,  # Set absolute score
                    "total_attempts": 10,
                    "total_correct": 8
                },
                {
                    "knowledge_id": "Simple Tense",  # Can use name
                    "score_delta": 2.0,  # Or adjust by delta
                }
            ],
            source="teacher_override",
            adjusted_by="teacher@example.com"
        )
    """
    from student.neo_models import Student as NeoStudent
    from knowledge.neo_models import Knowledge as NeoKnowledge
    from student.quiz_suggestion import UserProfile
    from pathlib import Path
    from datetime import datetime, timezone

    # Validate input
    if not student_id:
        raise APIError("student_id is required", code="invalid_input", status_code=400)

    if not knowledge_adjustments:
        raise APIError(
            "At least one knowledge adjustment is required",
            code="invalid_input",
            status_code=400
        )

    # Get student node
    try:
        student_node = NeoStudent.nodes.filter(db_id=student_id).first()
        if not student_node:
            raise APIError(
                f"Student {student_id} not found",
                code="student_not_found",
                status_code=404
            )
    except Exception as e:
        logger.error(f"Failed to get student: {e}")
        raise APIError(
            "Failed to retrieve student",
            code="database_error",
            status_code=500
        )

    # Load or create user profile
    profile_path = Path("data/profiles") / f"{student_id}.json"
    if profile_path.exists():
        profile = UserProfile.load_from_file(profile_path)
    else:
        profile = UserProfile(user_id=student_id)

    # Build knowledge nodes map
    knowledge_nodes_map = {}
    for k_node in NeoKnowledge.nodes.all():
        element_id = getattr(k_node, "element_id", None)
        name = getattr(k_node, "name", None)
        if element_id:
            knowledge_nodes_map[element_id] = k_node
        if name:
            knowledge_nodes_map[name] = k_node

    updated_count = 0
    created_count = 0
    applied_adjustments = []

    for adjustment in knowledge_adjustments:
        knowledge_id = adjustment.get("knowledge_id")
        if not knowledge_id:
            logger.warning("Skipping adjustment with missing knowledge_id")
            continue

        knowledge_node = knowledge_nodes_map.get(knowledge_id)
        if not knowledge_node:
            logger.warning(f"Knowledge node {knowledge_id} not found")
            continue

        # Get actual element_id for profile storage
        node_element_id = getattr(knowledge_node, "element_id", knowledge_id)

        # Calculate new score
        current_score = profile.get_score(node_element_id)

        if "score" in adjustment:
            # Absolute score
            new_score = float(adjustment["score"])
        elif "score_delta" in adjustment:
            # Relative adjustment
            new_score = current_score + float(adjustment["score_delta"])
        else:
            # No score change, just update metadata
            new_score = current_score

        # Update profile
        profile.set_score(node_element_id, new_score)

        # Update or create relationship
        try:
            if student_node.related_to.is_connected(knowledge_node):
                # Update existing relationship
                rel = student_node.related_to.relationship(knowledge_node)
                rel.last_score = new_score
                rel.last_updated = datetime.now(timezone.utc)

                if "total_attempts" in adjustment:
                    rel.total_attempts = int(adjustment["total_attempts"])

                if "total_correct" in adjustment:
                    rel.total_correct = int(adjustment["total_correct"])

                # Store adjustment metadata
                if "metadata" in adjustment:
                    for key, value in adjustment["metadata"].items():
                        setattr(rel, key, value)

                rel.save()
                updated_count += 1
                action = "updated"
            else:
                # Create new relationship
                rel_props = {
                    'last_score': new_score,
                    'last_updated': datetime.now(timezone.utc),
                    'total_attempts': adjustment.get('total_attempts', 0),
                    'total_correct': adjustment.get('total_correct', 0),
                }

                # Add metadata if provided
                if "metadata" in adjustment:
                    rel_props.update(adjustment["metadata"])

                student_node.related_to.connect(knowledge_node, rel_props)
                created_count += 1
                action = "created"

            applied_adjustments.append({
                "knowledge_id": node_element_id,
                "knowledge_name": knowledge_node.name,
                "old_score": current_score,
                "new_score": new_score,
                "action": action
            })

            logger.info(
                f"Manual adjustment: {action} relationship for student {student_id} "
                f"to knowledge {knowledge_node.name}, score: {current_score} -> {new_score}, "
                f"source: {source}, adjusted_by: {adjusted_by}"
            )

        except Exception as e:
            logger.error(f"Failed to update relationship for {knowledge_id}: {e}")
            continue

    # Save updated profile
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile.save_to_file(profile_path)

    logger.info(
        f"Manual adjustment completed for {student_id}: "
        f"{created_count} created, {updated_count} updated, "
        f"source: {source}, adjusted_by: {adjusted_by}"
    )

    return {
        "student_id": student_id,
        "updated_count": updated_count,
        "created_count": created_count,
        "adjustments": applied_adjustments,
        "source": source,
        "adjusted_by": adjusted_by,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### Updated Neo4j Relationship Model

```python
# In student/neo_models.py
class Student(StructuredNode):
    username = StringProperty(required=True)
    db_id = StringProperty(required=True)

    # Relationship with properties
    related_to = RelationshipTo(
        "knowledge.neo_models.Knowledge",
        "RELATED_TO",
        model=StudentKnowledgeRel  # Custom relationship model
    )

# New relationship model
class StudentKnowledgeRel(StructuredRel):
    """Relationship between Student and Knowledge with learning metadata."""
    last_score = FloatProperty()
    last_updated = DateTimeProperty()
    total_attempts = IntegerProperty(default=0)
    total_correct = IntegerProperty(default=0)
```

## Consequences

### Positive

1. **Rich Graph Queries**: Can query students by knowledge area

   ```cypher
   MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge {name: "Simple Tense"})
   WHERE r.last_score > 5
   RETURN s.username, r.last_score
   ```

2. **Learning Path Visualization**: Can visualize student's learning journey

   ```cypher
   MATCH (s:Student {db_id: "123-ceo"})-[r:RELATED_TO]->(k:Knowledge)
   RETURN k.name, r.last_score, r.last_updated
   ORDER BY r.last_updated DESC
   ```

3. **Analytics**: Can analyze learning patterns across students

   ```cypher
   MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
   RETURN k.name, AVG(r.last_score) as avg_score, COUNT(s) as student_count
   ORDER BY avg_score DESC
   ```

4. **Cohort Analysis**: Can find students with similar knowledge profiles

   ```cypher
   MATCH (s1:Student)-[:RELATED_TO]->(k:Knowledge)<-[:RELATED_TO]-(s2:Student)
   WHERE s1.db_id = "123-ceo" AND s1 <> s2
   RETURN s2.username, COUNT(k) as shared_knowledge
   ORDER BY shared_knowledge DESC
   ```

5. **Data Consistency**: Single source of truth in graph database

### Negative

1. **Performance Impact**: Additional Neo4j operations per submission
   - Mitigation: Batch operations, use transactions
2. **Complexity**: Need to maintain relationship properties
   - Mitigation: Encapsulate in service method
3. **Data Duplication**: Scores stored in both JSON and graph
   - Mitigation: JSON is source of truth, graph is for relationships
4. **Migration Needed**: Existing students need backfill
   - Mitigation: Create migration script to populate from JSON profiles

### Neutral

1. **Storage Increase**: More relationships in Neo4j
2. **Maintenance**: Need to keep relationship properties in sync

## Alternatives Considered

### Alternative 1: Keep JSON-Only Storage

**Pros**: Simple, no graph complexity, fast writes
**Cons**: No graph queries, no visualization, limited analytics
**Decision**: Rejected - loses value of graph database

### Alternative 2: Store All Scores in Neo4j (No JSON)

**Pros**: Single source of truth, full graph power
**Cons**: Complex queries for score retrieval, performance concerns
**Decision**: Rejected - JSON is better for profile data

### Alternative 3: Relationship Without Properties

**Pros**: Simpler implementation
**Cons**: Loses valuable metadata (when, how many attempts)
**Decision**: Rejected - properties add significant value

### Alternative 4: Separate Analytics Database

**Pros**: Optimized for analytics queries
**Cons**: Additional infrastructure, data sync complexity
**Decision**: Rejected - premature optimization

## API Endpoint for Manual Adjustment

To support manual adjustments, we propose adding a new API endpoint:

```
POST /student/v1/<ram_id>/adjust-knowledge/
```

**Request Body**:

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

**Response**:

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

**Authorization**:

- Requires elevated permissions (teacher, admin)
- Regular students cannot adjust their own knowledge
- Audit log required for all manual adjustments

**Use Cases**:

1. **Teacher Override**: Teacher manually adjusts student mastery after assessment
2. **Placement Test**: Initialize student knowledge based on placement test results
3. **Bulk Import**: Import student knowledge from external learning management system
4. **Administrative Correction**: Fix incorrect scores or data migration issues
5. **External Integration**: Allow other platforms to update student knowledge

## Implementation Plan

### Phase 1: Enable Basic Relationships (Week 1)

- [ ] Uncomment and refactor relationship creation code
- [ ] Add element_id matching logic
- [ ] Add duplicate check before creating
- [ ] Add comprehensive logging
- [ ] Test with small dataset

### Phase 2: Add Relationship Properties (Week 2)

- [ ] Define StudentKnowledgeRel model
- [ ] Update Student model to use relationship model
- [ ] Implement property updates on existing relationships
- [ ] Add migration for existing relationships

### Phase 3: Manual Adjustment Function (Week 3)

- [ ] Implement `adjust_student_knowledge()` function
- [ ] Add input validation and error handling
- [ ] Support both absolute scores and score deltas
- [ ] Support knowledge lookup by element_id or name
- [ ] Create API endpoint `/student/v1/<ram_id>/adjust-knowledge/`
- [ ] Add serializers for adjustment requests
- [ ] Add permission checks (teacher/admin only)
- [ ] Implement audit logging with source and adjusted_by tracking
- [ ] Write unit tests for manual adjustment function
- [ ] Write API tests for adjustment endpoint
- [ ] Document API in OpenAPI/Swagger

### Phase 4: Optimize Performance (Week 4)

- [ ] Implement batch operations for relationship updates
- [ ] Add transaction support for atomic updates
- [ ] Cache knowledge nodes map to reduce queries
- [ ] Performance testing with 1000+ students
- [ ] Optimize manual adjustment for bulk operations

### Phase 5: Backfill Existing Data (Week 5)

- [ ] Create management command to backfill relationships
- [ ] Read all JSON profiles
- [ ] Create relationships for all student-knowledge pairs
- [ ] Validate data consistency between JSON and graph
- [ ] Handle edge cases (missing nodes, invalid scores)

### Phase 6: Analytics & Visualization (Future)

- [ ] Create API endpoints for student learning path
- [ ] Build visualization dashboard
- [ ] Implement cohort analysis queries
- [ ] Add recommendation engine based on relationships
- [ ] Bulk adjustment interface for administrators
- [ ] Export/import student knowledge data
- [ ] Integration with external learning platforms

## Monitoring & Rollback

### Monitoring

- Track relationship creation/update counts
- Monitor Neo4j query performance
- Alert on relationship creation failures
- Dashboard for relationship growth over time

### Rollback Plan

If performance issues arise:

1. Add feature flag to disable relationship creation
2. Keep existing relationships (don't delete)
3. Investigate and optimize
4. Re-enable when fixed

### Success Metrics

- 95%+ relationship creation success rate
- < 500ms additional latency per submission
- Zero data inconsistencies between JSON and graph
- Successful backfill of all existing students

## References

- [Neo4j Relationship Properties](https://neo4j.com/docs/cypher-manual/current/syntax/relationships/)
- [Neomodel Relationship Models](https://neomodel.readthedocs.io/en/latest/relationships.html)
- Student Neo4j Model: `student/neo_models.py`
- Submit Answers Service: `student/services/submit_answers_service.py`
- Requirements: `docs/submit-answer/requirements/submit-answer-requirements.md`

## Decision Date

2025-10-08

## Decision Makers

- @ceofourfactplus (Product Owner)
- Engineering Team

## Review Date

2025-11-08 (1 month after implementation)

---

## Summary of Key Decisions

### 1. Automatic Relationship Creation

When students submit quiz answers, automatically create/update `Student -[RELATED_TO]-> Knowledge` relationships in Neo4j with properties tracking learning progress.

### 2. Manual Adjustment Capability

Provide a dedicated function and API endpoint (`adjust_student_knowledge()` and `/adjust-knowledge/`) to allow:

- Teachers to override student knowledge scores
- Administrators to bulk import/correct student data
- External systems to integrate and update student knowledge
- Placement tests to initialize student profiles

### 3. Dual Storage Strategy

- **JSON files**: Source of truth for student profiles (fast access, simple structure)
- **Neo4j relationships**: Enable graph queries, analytics, and visualization
- Relationships store metadata: `last_score`, `last_updated`, `total_attempts`, `total_correct`

### 4. Flexible Input Methods

Support multiple ways to adjust student knowledge:

- **Automatic**: Via quiz answer submission (existing flow)
- **Manual**: Via `adjust_student_knowledge()` function with explicit parameters
- **Absolute scores**: Set exact score value
- **Score deltas**: Adjust by relative amount
- **Metadata updates**: Update attempts/correct counts independently

### 5. Audit Trail

All manual adjustments logged with:

- Source (e.g., "teacher_override", "placement_test", "bulk_import")
- Adjusted by (user/system identifier)
- Timestamp
- Old and new values

This enables full traceability and accountability for all knowledge adjustments.
