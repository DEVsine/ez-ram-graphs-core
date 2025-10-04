"""
Serializers for student API endpoints.
"""

from rest_framework import serializers


class StudentInputSerializer(serializers.Serializer):
    """Serializer for student input data in suggest-quiz request."""

    id = serializers.CharField(
        required=False, allow_blank=True, help_text="Student database ID"
    )
    db_id = serializers.CharField(
        required=False, allow_blank=True, help_text="Student database ID (alternative)"
    )
    username = serializers.CharField(required=True, help_text="Student username")

    def validate(self, data):
        """Ensure at least one ID field is provided."""
        if not data.get("username"):
            raise serializers.ValidationError("username is required")
        return data


class SuggestQuizRequestSerializer(serializers.Serializer):
    """Serializer for suggest-quiz POST request."""

    student = StudentInputSerializer(required=True)
    quiz_limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=100,
        help_text="Maximum number of quizzes to suggest",
    )
    scope_topic = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Optional topic to scope quiz suggestions",
    )
    replay = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to allow replaying previously seen quizzes",
    )


class AnswerSubmissionSerializer(serializers.Serializer):
    """Serializer for a single answer submission."""

    quiz_gid = serializers.CharField(required=True, help_text="Quiz graph ID")
    answer_gid = serializers.CharField(
        required=True, help_text="Chosen answer graph ID"
    )
    time_to_answer = serializers.IntegerField(
        required=False, min_value=0, help_text="Time to answer in seconds"
    )
    use_helper = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of helpers used (e.g., 'cut-choice', 'two-answer')",
    )
    time_read_answer = serializers.IntegerField(
        required=False, min_value=0, help_text="Time spent reading answer in seconds"
    )
    choice_cutting = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of choice graph IDs that were cut/eliminated",
    )


class SubmitAnswersRequestSerializer(serializers.Serializer):
    """Serializer for submit-answers POST request."""

    student_id = serializers.CharField(required=True, help_text="Student identifier")
    answers = serializers.ListField(
        child=AnswerSubmissionSerializer(),
        required=True,
        min_length=1,
        help_text="List of answer submissions",
    )


class GetStudentGraphRequestSerializer(serializers.Serializer):
    """Serializer for get-student-graph POST request."""

    student_id = serializers.CharField(required=True, help_text="Student ID (db_id)")
