"""
Unified Error Handlers for PopCorn API
Provides consistent error responses and logging
"""

import logging
import traceback
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

# Optional SQLAlchemy support
try:
    from sqlalchemy.exc import SQLAlchemyError
    HAS_SQLALCHEMY = True
except ImportError:
    SQLAlchemyError = Exception
    HAS_SQLALCHEMY = False

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standard error response format"""

    @staticmethod
    def create(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: dict = None
    ) -> JSONResponse:
        """
        Create a standardized error response.

        Args:
            error_code: Machine-readable error code
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details

        Returns:
            JSONResponse with error information
        """
        content = {
            "error": error_code,
            "message": message,
            "status_code": status_code
        }

        if details:
            content["details"] = details

        return JSONResponse(
            status_code=status_code,
            content=content
        )


# ══════════════════════════════════════════════════════════════════════
# Database Error Handlers
# ══════════════════════════════════════════════════════════════════════

async def database_exception_handler(
        request: Request,
        exc: Exception) -> JSONResponse:
    """
    Handle database-related errors.

    Args:
        request: The FastAPI request
        exc: The exception that occurred

    Returns:
        JSONResponse with error details
    """
    error_msg = str(exc)
    client_ip = request.client.host if request.client else "unknown"

    # Log the error with full traceback
    logger.error(
        f"Database error on {request.url.path} from {client_ip}: {error_msg}",
        exc_info=True
    )

    # Check for specific database errors
    if "database is locked" in error_msg.lower():
        return ErrorResponse.create(
            error_code="database_locked",
            message="Database is temporarily busy. Please try again in a moment.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "retry_after": 5})

    elif "unable to open database" in error_msg.lower():
        return ErrorResponse.create(
            error_code="database_unavailable",
            message="Database is currently unavailable. Please try again later.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    elif "no such table" in error_msg.lower():
        return ErrorResponse.create(
            error_code="database_schema_error",
            message="Database schema error. Please contact support.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    elif "constraint" in error_msg.lower():
        return ErrorResponse.create(
            error_code="database_constraint_violation",
            message="Data constraint violation. The operation could not be completed.",
            status_code=status.HTTP_409_CONFLICT)

    else:
        # Generic database error
        return ErrorResponse.create(
            error_code="database_error",
            message="A database error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ══════════════════════════════════════════════════════════════════════
# Validation Error Handlers
# ══════════════════════════════════════════════════════════════════════

async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle request validation errors.

    Args:
        request: The FastAPI request
        exc: The validation exception

    Returns:
        JSONResponse with validation error details
    """
    client_ip = request.client.host if request.client else "unknown"

    # Extract validation errors
    errors = []
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
    else:
        errors = [{"message": str(exc)}]

    logger.warning(
        f"Validation error on {request.url.path} from {client_ip}: {errors}"
    )

    return ErrorResponse.create(
        error_code="validation_error",
        message="Invalid request data. Please check your input.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": errors}
    )


# ══════════════════════════════════════════════════════════════════════
# HTTP Error Handlers
# ══════════════════════════════════════════════════════════════════════

async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 Not Found errors"""
    return ErrorResponse.create(
        error_code="not_found",
        message=f"The requested resource was not found: {request.url.path}",
        status_code=status.HTTP_404_NOT_FOUND
    )


async def method_not_allowed_handler(
        request: Request,
        exc: Exception) -> JSONResponse:
    """Handle 405 Method Not Allowed errors"""
    return ErrorResponse.create(
        error_code="method_not_allowed",
        message=f"Method {request.method} is not allowed for {request.url.path}",
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 429 Rate Limit Exceeded errors"""
    return ErrorResponse.create(
        error_code="rate_limit_exceeded",
        message="Too many requests. Please slow down and try again later.",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        details={"retry_after": 60}
    )


# ══════════════════════════════════════════════════════════════════════
# General Error Handler
# ══════════════════════════════════════════════════════════════════════

async def general_exception_handler(
        request: Request,
        exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions.

    Args:
        request: The FastAPI request
        exc: The exception that occurred

    Returns:
        JSONResponse with error details
    """
    client_ip = request.client.host if request.client else "unknown"
    error_msg = str(exc)

    # Log the full error with traceback
    logger.error(
        f"Unhandled exception on {request.url.path} from {client_ip}: {error_msg}",
        exc_info=True)

    # Log the full traceback for debugging
    tb = traceback.format_exc()
    logger.debug(f"Full traceback:\n{tb}")

    # Check for specific error types
    if isinstance(exc, ValueError):
        return ErrorResponse.create(
            error_code="invalid_value",
            message="Invalid value provided in request.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"error": error_msg}
        )

    elif isinstance(exc, KeyError):
        return ErrorResponse.create(
            error_code="missing_key",
            message="Required data is missing from request.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"error": error_msg}
        )

    elif isinstance(exc, PermissionError):
        return ErrorResponse.create(
            error_code="permission_denied",
            message="You don't have permission to perform this action.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    elif isinstance(exc, TimeoutError):
        return ErrorResponse.create(
            error_code="timeout",
            message="The request timed out. Please try again.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT
        )

    else:
        # Generic internal server error
        return ErrorResponse.create(
            error_code="internal_error",
            message="An unexpected error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ══════════════════════════════════════════════════════════════════════
# WebSocket Error Handler
# ══════════════════════════════════════════════════════════════════════

async def websocket_error_handler(websocket, error: Exception):
    """
    Handle WebSocket errors.

    Args:
        websocket: The WebSocket connection
        error: The exception that occurred
    """
    error_msg = str(error)
    logger.error(f"WebSocket error: {error_msg}", exc_info=True)

    try:
        await websocket.send_json({
            "type": "error",
            "error": "websocket_error",
            "message": "An error occurred with the WebSocket connection.",
            "details": error_msg
        })
    except Exception as e:
        logger.error(f"Failed to send WebSocket error message: {e}")


# ══════════════════════════════════════════════════════════════════════
# Error Handler Registration
# ══════════════════════════════════════════════════════════════════════

def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError

    # Validation errors
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # Database errors (if SQLAlchemy is available)
    if HAS_SQLALCHEMY:
        app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    # HTTP errors
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(405, method_not_allowed_handler)
    app.add_exception_handler(429, rate_limit_handler)

    # General exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("✅ Error handlers registered successfully")


# ══════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════

def log_error_context(request: Request, error: Exception):
    """
    Log detailed error context for debugging.

    Args:
        request: The FastAPI request
        error: The exception that occurred
    """
    context = {
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "query_params": dict(request.query_params),
        "error_type": type(error).__name__,
        "error_message": str(error)
    }

    logger.error(f"Error context: {context}")


# Made with ❤️ by Bob

# Made with Bob
