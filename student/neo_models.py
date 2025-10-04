from neomodel import (
    StructuredNode,
    StringProperty,
    BooleanProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)


class Student(StructuredNode):
    """
    A quiz question text that may relate to Knowledge and has Choices
    """

    username = StringProperty(required=True)
    db_id = StringProperty(required=True)

    related_to = RelationshipTo("knowledge.neo_models.Knowledge", "RELATED_TO")
