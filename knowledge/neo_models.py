from neomodel import (
    StructuredNode,
    StringProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)


class TopicKnowledge(StructuredNode):
    """
    Represents a topic of knowledge, e.g. 'Present Perfect Tense'
    """

    name = StringProperty(required=True)  # "Present Perfect Tense"
    description = StringProperty()  # long text
    example = StringProperty()  # e.g., "I have went -> I have gone"

    # relationships
    # Knowledge.depends_on -> Knowledge (self)
    has_knowledge = RelationshipTo("Knowledge", "HAS_KNOWLEDGE")
    has_subtopic = RelationshipTo("TopicKnowledge", "HAS_SUBTOPIC")


class Knowledge(StructuredNode):
    """
    Represents a knowledge item, e.g. 'Common Errors'
    """

    name = StringProperty(required=True)  # "Common Errors"
    description = StringProperty()  # long text
    example = StringProperty()  # e.g., "I have went -> I have gone"

    # relationships
    # Knowledge.depends_on -> Knowledge (self)
    depends_on = RelationshipTo("Knowledge", "DEPENDS_ON")

    # Reverse edges for convenience/introspection
    related_quizzes = RelationshipFrom("quiz.neo_models.Quiz", "RELATED_TO")
    related_choices = RelationshipFrom("quiz.neo_models.Choice", "RELATED_TO")
