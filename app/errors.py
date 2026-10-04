from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Raise this anywhere to send a Hub Contract error response."""

    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        # FastAPI's default is 422; the contract requires 400 VALIDATION_FAILED
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(x) for x in first.get("loc", [])[1:])
        reason = str(first.get("msg", "The input is missing or wrong.")).replace("Value error, ", "")
        message = f"{field}: {reason}" if field else reason
        return error_response(400, "VALIDATION_FAILED", message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException):
        codes = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT"}
        code = codes.get(exc.status_code, "SERVER_ERROR" if exc.status_code >= 500 else "REQUEST_FAILED")
        return error_response(exc.status_code, code, "The request could not be completed.")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Never show stack traces or SQL errors to the client
        return error_response(500, "SERVER_ERROR", "Something went wrong on the server.")
