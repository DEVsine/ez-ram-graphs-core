"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/

Each app has its own urls.py file that is included here with a prefix.
This follows the pattern: /<app>/<version>/<resource>/

Examples:
    - /student/v1/RAM123/suggest-quiz/
    - /quiz/v1/RAM123/questions/
    - /knowledge/v1/RAM123/topics/
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # App-specific URLs (each app has its own urls.py)
    path("student/", include("student.urls")),
    path("quiz/", include("quiz.urls")),
    path("knowledge/", include("knowledge.urls")),
]
