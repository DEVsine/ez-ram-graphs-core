"""
Quiz app URL configuration.

All URLs in this file are prefixed with 'quiz/' when included in core/urls.py
"""

from django.urls import path

app_name = "quiz"

urlpatterns = [
    # Add quiz API endpoints here
    # Example:
    # path("v1/<str:ram_id>/questions/", QuestionListAPI.as_view(), name="question-list"),
]

