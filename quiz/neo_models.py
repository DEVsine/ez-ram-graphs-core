from neomodel import (
    StructuredNode,
    StringProperty,
    BooleanProperty,
    FloatProperty,
    DateTimeProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)


class Quiz(StructuredNode):
    """
    A quiz question text that may relate to Knowledge and has Choices
    """

    # Basic question data
    quiz_text = StringProperty(required=True)  # e.g., "She is ___ for class."
    question_style = StringProperty(required=True)  # multiple_choice, fill_in_blank, missing_word

    # Generation metadata
    generation_session_id = StringProperty()
    created_at = StringProperty()  # ISO format datetime
    ai_model_used = StringProperty()
    generation_time = FloatProperty()
    generation_success_rate = FloatProperty()

    # Validation data
    validation_score = FloatProperty()
    is_validated = BooleanProperty(default=False)
    spelling_grammar_score = FloatProperty()
    explanation_quality_score = FloatProperty()
    knowledge_relevance_score = FloatProperty()
    clarity_score = FloatProperty()
    single_correct_answer = BooleanProperty()

    # relationships
    has_choice = RelationshipTo("Choice", "HAS_CHOICE")
    related_to = RelationshipTo("Knowledge", "RELATED_TO")


class Choice(StructuredNode):
    """
    A specific answer choice for a Quiz, possibly related to Knowledge
    """

    # Fields from README
    question_id = (
        StringProperty()
    )  # keep if you also store an external/question string id
    choice_letter = StringProperty(required=True)
    choice_text = StringProperty(required=True)
    is_correct = BooleanProperty(default=False)
    answer_explanation = StringProperty()  # why this is right/wrong

    # relationships
    # Choice <-HAS_CHOICE- Quiz (reverse)
    belongs_to = RelationshipFrom("Quiz", "HAS_CHOICE")
    related_to = RelationshipTo("Knowledge", "RELATED_TO")
