from typing import Any, Dict

from django.conf import settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
    ParseError,
    NotFound,
    MethodNotAllowed,
    NotAcceptable,
    UnsupportedMediaType,
    Throttled,
)


ERROR_DEFAULT_CODE = "error"


def _error_payload(code: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def custom_exception_handler(exc, context):
    """
    Global DRF exception handler that enforces a consistent error envelope:
    {"error": {"code": "<slug>", "message": "...", "details": {}}}
    """
    # First, let DRF create a standard response (to extract status code, etc.)
    response = drf_exception_handler(exc, context)

    # Map known exception types to standardized codes/messages
    code = ERROR_DEFAULT_CODE
    message = str(exc)
    details: Dict[str, Any] | None = None
    status_code = response.status_code if response is not None else status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, ValidationError):
        code = "invalid"
        message = "Validation error"
        # DRF includes detail structure in response.data; keep in details
        details = {"fields": response.data} if response is not None else None
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        code = "unauthorized"
        message = "Authentication credentials were not provided or are invalid"
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, PermissionDenied):
        code = "forbidden"
        message = "You do not have permission to perform this action"
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, NotFound):
        code = "not_found"
        message = "Resource not found"
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, MethodNotAllowed):
        code = "method_not_allowed"
        message = "Method not allowed"
        status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    elif isinstance(exc, NotAcceptable):
        code = "not_acceptable"
        message = "Not acceptable"
        status_code = status.HTTP_406_NOT_ACCEPTABLE
    elif isinstance(exc, UnsupportedMediaType):
        code = "unsupported_media_type"
        message = "Unsupported media type"
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif isinstance(exc, ParseError):
        code = "parse_error"
        message = "Malformed request"
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, Throttled):
        code = "throttled"
        message = "Request was throttled. Expected available in %d second(s)." % getattr(exc, 'wait', 0)
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, APIException):
        # Generic DRF APIException fallback
        code = getattr(exc, "default_code", ERROR_DEFAULT_CODE)
        message = getattr(exc, "detail", str(exc))
        if hasattr(message, "__iter__") and not isinstance(message, str):
            details = {"detail": message}
            message = "Error"
        status_code = getattr(exc, "status_code", status_code)
    else:
        # Unhandled exception → 500; hide internals unless DEBUG
        code = "server_error"
        message = "Internal server error"
        if getattr(settings, "DEBUG", False):
            details = {"exception": str(exc)}
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    payload = _error_payload(code, message, details)
    return Response(payload, status=status_code)

