from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.api import BaseAPIView
from core.services import ServiceContext
from student.services.suggest_quiz_service import SuggestQuizService


class SuggestQuizAPI(BaseAPIView):
    """POST /student/v1/<ram_id>/suggest-quiz/"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, ram_id: str):
        ctx = ServiceContext(user=request.user, ram_id=ram_id)
        return self.ok(SuggestQuizService.execute(request.data, ctx=ctx))

