from neomodel import (
    StructuredNode,
    StringProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)
from quiz.neo_models import Quiz, Choice


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
    related_quizzes = RelationshipFrom("Quiz", "RELATED_TO")
    related_choices = RelationshipFrom("Choice", "RELATED_TO")
