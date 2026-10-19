import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_payload(code: str, message: str, details: list[dict[str, str]] | None = None) -> dict:
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    messages = {404: "Resource not found", 405: "Method not allowed"}
    message = messages.get(exc.status_code, "Request could not be processed")
    return JSONResponse(status_code=exc.status_code, content=error_payload("HTTP_ERROR", message))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"location": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload("VALIDATION_ERROR", "Request validation failed", details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled request exception", extra={"event": "request_error", "error_type": type(exc).__name__})
    return JSONResponse(
        status_code=500,
        content=error_payload("INTERNAL_ERROR", "An internal error occurred"),
    )
