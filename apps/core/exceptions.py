"""Consistent, non-sensitive API error responses."""

from uuid import uuid4

from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    details = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
    api_error_code = getattr(exc, "api_error_code", None)
    error_code = api_error_code or (
        "validation_error" if response.status_code == 400 else "request_error"
    )
    response.data = {
        "error": {
            "code": error_code,
            "message": (
                str(exc.default_detail)
                if api_error_code and hasattr(exc, "default_detail")
                else "The request could not be processed."
            ),
            "details": details,
            "correlation_id": str(uuid4()),
        }
    }
    return response
