from typing import Any, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class APIError(Exception):
    """Domain-level error that maps cleanly to an HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class BaseAPIView(APIView):
    """
    Project-standard API base class.
    - Thin controllers: validate -> delegate to service -> shape response
    - Use ok()/created()/no_content() helpers
    - Raise APIError from services for predictable error mapping
    """

    def ok(self, data: Any, *, headers: Optional[dict] = None) -> Response:
        return Response(data, status=status.HTTP_200_OK, headers=headers)

    def created(self, data: Any, *, headers: Optional[dict] = None) -> Response:
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def no_content(self) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)

    def error(
        self,
        *,
        status_code: int,
        message: str,
        code: str = "error",
        details: Optional[dict] = None,
    ) -> Response:
        payload = {"error": {"code": code, "message": message, "details": details or {}}}
        return Response(payload, status=status_code)

    def handle_exception(self, exc):  # type: ignore[override]
        if isinstance(exc, APIError):
            return self.error(
                status_code=exc.status_code,
                message=exc.message,
                code=exc.code,
                details=exc.details,
            )
        return super().handle_exception(exc)

