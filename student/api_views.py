from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.api import BaseAPIView
from core.services import ServiceContext
from student.services.suggest_quiz_service import SuggestQuizService
from student.services.submit_answers_service import SubmitAnswersService
from student.services.get_student_graph_service import GetStudentGraphService
from student.serializers import (
    SuggestQuizRequestSerializer,
    SubmitAnswersRequestSerializer,
    GetStudentGraphRequestSerializer,
)


class SuggestQuizAPI(BaseAPIView):
    """
    POST /student/v1/<ram_id>/suggest-quiz/

    Suggest quizzes for a student using the adaptive quiz suggestion engine.

    Request body:
        {
            "student": {
                "id": "123-ceo",
                "username": "ceo",
                ...
            },
            "quiz_limit": 10,
            "scope_topic": "Simple Tense",  // optional
            "replay": false  // optional
        }

    Response:
        {
            "student": {
                "name": "ceo",
                "graph_id": "uuid"
            },
            "quiz": [
                {
                    "graph_id": 123,
                    "quiz_text": "...",
                    "choices": [...],
                    "related_to": [...]
                },
                ...
            ]
        }
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, ram_id: str):
        # Validate request data
        serializer = SuggestQuizRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Execute service with validated data
        ctx = ServiceContext(user=request.user, ram_id=ram_id)
        result = SuggestQuizService.execute(serializer.validated_data, ctx=ctx)

        return self.ok(result)


class SubmitAnswersAPI(BaseAPIView):
    """
    POST /student/v1/<ram_id>/submit-answers/

    Submit quiz answers and update student learning progress.

    Request body:
        {
            "student_id": "123-ceo",
            "answers": [
                {
                    "quiz_gid": "4:abc:123",
                    "answer_gid": "4:def:456",
                    "time_to_answer": 123,
                    "use_helper": ["cut-choice", "two-answer"],
                    "time_read_answer": 123,
                    "choice_cutting": ["4:ghi:789", "4:jkl:012"]
                },
                ...
            ]
        }

    Response:
        {
            "student": {
                "name": "ceo",
                "graph_id": "4:xyz:999"
            },
            "graph_update": [
                {
                    "graph_id": "4:node:123",
                    "knowledge": "Simple Tense",
                    "adjustment": 1.0
                },
                {
                    "graph_id": "4:node:124",
                    "knowledge": "Perfect Tense",
                    "adjustment": -1.0
                }
            ]
        }
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, ram_id: str):
        # Validate request data
        serializer = SubmitAnswersRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Execute service with validated data
        ctx = ServiceContext(user=request.user, ram_id=ram_id)
        result = SubmitAnswersService.execute(serializer.validated_data, ctx=ctx)

        return self.ok(result)


class GetStudentGraphAPI(BaseAPIView):
    """
    POST /student/v1/<ram_id>/get-student-graph/

    Get a student's knowledge graph with their learning scores.
    Returns a hierarchical tree: Subject (ram_id) -> Topics (nested) -> Knowledge (nested).

    Request body:
        {
            "student_id": "123-ceo"  // known as db_id
        }

    Response:
        {
            "student": {
                "name": "ceo",
                "db_id": "123-ceo"
            },
            "student_knowledge_graph": [
                {
                    "graph_id": "4:topic:001",
                    "topic": "Tense",
                    "score": 1.5,  // average score of all descendant nodes
                    "child": [
                        {
                            "graph_id": "4:topic:002",
                            "topic": "Simple Tense",  // nested Topic
                            "score": 1.2,
                            "child": [
                                {
                                    "graph_id": "4:knowledge:003",
                                    "knowledge": "Plural subjects use base form",
                                    "score": 1.0,
                                    "child": [...]  // nested Knowledge nodes
                                }
                            ]
                        }
                    ]
                },
                {
                    "graph_id": "4:topic:004",
                    "topic": "Perfect Tense",
                    "score": -1.0,
                    "child": [...]
                }
            ]
        }

    Note: Topics can be nested multiple levels deep via has_subtopic relationships.
          Each Topic's score is the average of all its descendant nodes (Topics + Knowledge).
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, ram_id: str):
        # Validate request data
        serializer = GetStudentGraphRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Execute service with validated data
        ctx = ServiceContext(user=request.user, ram_id=ram_id)
        result = GetStudentGraphService.execute(serializer.validated_data, ctx=ctx)

        return self.ok(result)
