from typing import Any, Dict, List

from core.api import APIError
from core.services import BaseService, ServiceContext
from student.neo_models import Student as NeoStudent
from quiz.neo_models import Quiz


class SuggestQuizService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """Class-based service for suggesting quizzes."""

    def run(self) -> Dict[str, Any]:
        data = self.inp or {}
        student_inp = data.get("student") or {}
        quiz_limit = int(data.get("quiz_limit", 10) or 10)

        username = (student_inp or {}).get("username") or ""
        db_id = (student_inp or {}).get("id") or (student_inp or {}).get("db_id") or ""

        if quiz_limit < 1:
            raise APIError("quiz_limit must be >= 1", code="invalid", status_code=400)

        # Optional context access: self.ctx.user, self.ctx.ram_id
        _ctx: ServiceContext = self.ctx

        # Find/create Student node (best‑effort)
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
                student_node = None

        quizzes_out: List[Dict[str, Any]] = []
        try:
            count = 0
            for q in Quiz.nodes.all():
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
                                "answer_explanation": getattr(
                                    c, "answer_explanation", ""
                                )
                                or "",
                                "related_to": rel_k,
                            }
                        )
                except Exception:
                    choices_data = []

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

        return {"student": resp_student, "quiz": quizzes_out}
