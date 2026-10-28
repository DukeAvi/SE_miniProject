"""Consistent, non-sensitive API error responses."""

from uuid import uuid4

from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    details = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
    response.data = {
        "error": {
            "code": "validation_error" if response.status_code == 400 else "request_error",
            "message": "The request could not be processed.",
            "details": details,
            "correlation_id": str(uuid4()),
        }
    }
    return response
