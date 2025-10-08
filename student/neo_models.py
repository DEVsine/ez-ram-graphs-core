from neomodel import (
    StructuredNode,
    StructuredRel,
    StringProperty,
    FloatProperty,
    IntegerProperty,
    DateTimeProperty,
    BooleanProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)


class StudentKnowledgeRel(StructuredRel):
    """
    Relationship between Student and Knowledge with learning metadata.

    This relationship tracks a student's engagement with a knowledge topic,
    including their current mastery level and learning history.
    """

    last_score = FloatProperty()
    last_updated = DateTimeProperty()
    total_attempts = IntegerProperty(default=0)
    total_correct = IntegerProperty(default=0)


class StudentQuizRel(StructuredRel):
    """
    Relationship between Student and Quiz tracking quiz attempts.

    This relationship tracks when a student attempted a quiz for quiz history
    and deduplication in quiz suggestions.
    """

    attempted_at = DateTimeProperty()
    is_correct = BooleanProperty()


class Student(StructuredNode):
    """
    A student user who takes quizzes and learns knowledge topics.
    """

    username = StringProperty(required=True)
    db_id = StringProperty(required=True)

    # Relationship to Knowledge with properties tracking learning progress
    related_to = RelationshipTo(
        "knowledge.neo_models.Knowledge", "RELATED_TO", model=StudentKnowledgeRel
    )

    # Relationship to Quiz tracking quiz attempts (for history and deduplication)
    attempted = RelationshipTo(
        "quiz.neo_models.Quiz", "ATTEMPTED", model=StudentQuizRel
    )
