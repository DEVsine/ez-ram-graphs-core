from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    BooleanProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)


class Quiz(StructuredNode):
    """
    A quiz question text that may relate to Knowledge and has Choices
    """

    quiz_text = StringProperty(required=True)  # e.g., "She is ___ for class."

    # Quiz suggestion engine fields
    difficulty_level = IntegerProperty(default=3)  # 1-5 scale (1=easiest, 5=hardest)
    quiz_type = StringProperty(
        default="multiple_choice"
    )  # "multiple_choice" or "fill_in_blank"

    # relationships
    has_choice = RelationshipTo("Choice", "HAS_CHOICE")
    related_to = RelationshipTo("knowledge.neo_models.Knowledge", "RELATED_TO")


class Choice(StructuredNode):
    """
    A specific answer choice for a Quiz, possibly related to Knowledge
    """

    # Fields from README
    question_id = (
        StringProperty()
    )  # keep if you also store an external/question string id
    choice_text = StringProperty(required=True)
    is_correct = BooleanProperty(default=False)
    answer_explanation = StringProperty()  # why this is right/wrong

    # relationships
    # Choice <-HAS_CHOICE- Quiz (reverse)
    belongs_to = RelationshipFrom("Quiz", "HAS_CHOICE")
    related_to = RelationshipTo("knowledge.neo_models.Knowledge", "RELATED_TO")
