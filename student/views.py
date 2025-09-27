from typing import Any, Dict, List

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from student.neo_models import Student as NeoStudent
from quiz.neo_models import Quiz


@api_view(["POST"])  # /student/v1/<ram_id>/suggest-quiz/
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def suggest_quiz(request, ram_id: str):
    data: Dict[str, Any] = request.data or {}
    student_inp: Dict[str, Any] = data.get("student", {}) or {}
    quiz_limit: int = int(data.get("quiz_limit", 10) or 10)

    username = student_inp.get("username") or ""
    db_id = student_inp.get("id") or student_inp.get("db_id") or ""

    # Find or create a Student node in Neo4j (optional if no student info is provided)
    student_node = None
    if username and db_id:
        try:
            qs = NeoStudent.nodes.filter(username=username, db_id=db_id)
            student_node = (
                qs.first() if hasattr(qs, "first") else (qs[0] if qs else None)
            )
            if student_node is None:
                student_node = NeoStudent(username=username, db_id=db_id).save()
        except Exception:
            student_node = None  # Don’t fail the whole request if graph is unavailable

    # Collect quizzes from graph, limited by quiz_limit
    quizzes_out: List[Dict[str, Any]] = []
    try:
        count = 0
        for q in Quiz.nodes.all():
            # choices
            choices_data: List[Dict[str, Any]] = []
            try:
                for c in q.has_choice.all():
                    rel_k = [
                        {"graph_id": k.id, "knowledge": getattr(k, "name", "")}
                        for k in c.related_to.all()
                    ]
                    choices_data.append(
                        {
                            "graph_id": c.id,
                            "choice_text": getattr(c, "choice_text", ""),
                            "is_correct": bool(getattr(c, "is_correct", False)),
                            "answer_explanation": getattr(c, "answer_explanation", "")
                            or "",
                            "related_to": rel_k,
                        }
                    )
            except Exception:
                choices_data = []

            # quiz-level related knowledge
            try:
                rel_k_q = [
                    {"graph_id": k.id, "knowledge": getattr(k, "name", "")}
                    for k in q.related_to.all()
                ]
            except Exception:
                rel_k_q = []

            quizzes_out.append(
                {
                    "graph_id": q.id,
                    "quiz_text": getattr(q, "quiz_text", ""),
                    "choices": choices_data,
                    "related_to": rel_k_q,
                }
            )
            count += 1
            if count >= quiz_limit:
                break
    except Exception:
        quizzes_out = []

    resp_student = {
        "name": username or "",
        "graph_id": str(getattr(student_node, "id", "")) if student_node else None,
    }

    return Response(
        {"student": resp_student, "quiz": quizzes_out}, status=status.HTTP_200_OK
    )
