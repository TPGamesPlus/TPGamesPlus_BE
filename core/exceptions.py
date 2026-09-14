from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Normalize every DRF error response to {"error": {"code": <status>, "message": <str>}}."""
    response = drf_exception_handler(exc, context)

    if response is None:
        return Response(
            {"error": {"code": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": "Internal server error."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response.data = {"error": {"code": response.status_code, "message": _flatten(response.data)}}
    return response


def _flatten(detail):
    if isinstance(detail, dict):
        if set(detail.keys()) == {"detail"}:
            return str(detail["detail"])
        parts = [
            f"{field}: {err}"
            for field, errors in detail.items()
            for err in (errors if isinstance(errors, (list, tuple)) else [errors])
        ]
        return "; ".join(parts) if parts else "Invalid request."
    if isinstance(detail, (list, tuple)):
        return "; ".join(str(item) for item in detail)
    return str(detail)
