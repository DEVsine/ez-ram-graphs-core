"""
Student app URL configuration.

All URLs in this file are prefixed with 'student/' when included in core/urls.py
"""

from django.urls import path
from student.api_views import SuggestQuizAPI, SubmitAnswersAPI, GetStudentGraphAPI

app_name = "student"

urlpatterns = [
    # POST /student/v1/<ram_id>/suggest-quiz/
    path(
        "v1/<str:ram_id>/suggest-quiz/",
        SuggestQuizAPI.as_view(),
        name="suggest-quiz",
    ),
    # POST /student/v1/<ram_id>/submit-answers/
    path(
        "v1/<str:ram_id>/submit-answers/",
        SubmitAnswersAPI.as_view(),
        name="submit-answers",
    ),
    # POST /student/v1/<ram_id>/get-student-graph/
    path(
        "v1/<str:ram_id>/get-student-graph/",
        GetStudentGraphAPI.as_view(),
        name="get-student-graph",
    ),
]
