"""
Error handlers for Research Copilot.

Provides error normalization and centralized error handling utilities.
"""

import traceback
from typing import Any, Optional

from src.errors.codes import ErrorCodes, get_error_type
from src.errors.exceptions import ResearchError
from src.errors.messages import get_error_message
from src.utils.logger import setup_logger

logger = setup_logger("research_copilot.errors")


def normalize_error(
    error: Exception,
    default_code: str = ErrorCodes.INTERNAL_ERROR,
    context: Optional[dict[str, Any]] = None,
) -> ResearchError:
    """
    Normalize any exception to a ResearchError.

    This ensures all errors have consistent structure for handling
    and display, regardless of their original type.

    Args:
        error: The original exception
        default_code: Default error code if not a ResearchError
        context: Optional context to include in error details

    Returns:
        A normalized ResearchError instance
    """
    # If already a ResearchError, return as-is (optionally add context)
    if isinstance(error, ResearchError):
        if context:
            error.details.update(context)
        return error

    # Get error message info for default code
    error_info = get_error_message(default_code)

    # Create normalized error
    return ResearchError(
        code=default_code,
        message=str(error) or error_info["message"],
        suggestion=error_info.get("suggestion"),
        details={
            "original_type": type(error).__name__,
            "original_message": str(error),
            **(context or {}),
        },
    )


def handle_http_error(status_code: int, url: str) -> ResearchError:
    """
    Convert HTTP status codes to appropriate ResearchError instances.

    Args:
        status_code: HTTP status code
        url: The URL that returned the error

    Returns:
        Appropriate ResearchError for the status code
    """
    error_map = {
        400: (ErrorCodes.INVALID_REQUEST, "Bad request"),
        401: (ErrorCodes.FETCH_BLOCKED, "Authentication required"),
        403: (ErrorCodes.FETCH_BLOCKED, "Access forbidden"),
        404: (ErrorCodes.FETCH_FAILED, "Page not found"),
        429: (ErrorCodes.SEARCH_RATE_LIMITED, "Rate limited"),
        500: (ErrorCodes.FETCH_FAILED, "Server error"),
        502: (ErrorCodes.FETCH_FAILED, "Bad gateway"),
        503: (ErrorCodes.FETCH_FAILED, "Service unavailable"),
        504: (ErrorCodes.FETCH_TIMEOUT, "Gateway timeout"),
    }

    code, message = error_map.get(
        status_code,
        (ErrorCodes.FETCH_FAILED, f"HTTP error {status_code}"),
    )

    error_info = get_error_message(code)

    return ResearchError(
        code=code,
        message=f"{message}: {url}",
        suggestion=error_info.get("suggestion"),
        details={"status_code": status_code, "url": url},
    )


def log_error(
    error: Exception,
    request_id: Optional[str] = None,
    include_traceback: bool = True,
) -> None:
    """
    Log an error with appropriate context.

    Args:
        error: The error to log
        request_id: Optional request ID for tracing
        include_traceback: Whether to include full traceback
    """
    extra = {}
    if request_id:
        extra["request_id"] = request_id

    if isinstance(error, ResearchError):
        extra["error_code"] = error.code
        extra["error_type"] = error.error_type

    # Log at appropriate level based on error type
    if isinstance(error, ResearchError):
        if error.error_type == "internal_error":
            logger.error(f"Internal error: {error.message}", extra=extra)
            if include_traceback:
                logger.debug(traceback.format_exc())
        else:
            logger.warning(f"Application error: {error.message}", extra=extra)
    else:
        logger.error(f"Unexpected error: {str(error)}", extra=extra)
        if include_traceback:
            logger.debug(traceback.format_exc())


def create_error_response(error: ResearchError) -> dict[str, Any]:
    """
    Create a standardized error response dictionary.

    Args:
        error: The ResearchError to convert

    Returns:
        Dictionary suitable for JSON serialization and API responses
    """
    error_info = get_error_message(error.code)

    return {
        "success": False,
        "error": {
            "code": error.code,
            "type": error.error_type,
            "title": error_info.get("title", "Error"),
            "message": error.message,
            "suggestion": error.suggestion or error_info.get("suggestion"),
            "icon": error_info.get("icon", "⚠️"),
            "steps": error_info.get("steps"),
            "details": error.details if error.details else None,
        },
    }


class ErrorHandler:
    """
    Context manager for centralized error handling.

    Usage:
        with ErrorHandler(request_id="abc123") as handler:
            # Do something that might raise
            result = risky_operation()

        if handler.error:
            # Handle the error
            display_error(handler.error)
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        default_code: str = ErrorCodes.INTERNAL_ERROR,
        reraise: bool = False,
    ):
        """
        Initialize the error handler.

        Args:
            request_id: Optional request ID for tracing
            default_code: Default error code for unknown errors
            reraise: Whether to re-raise errors after handling
        """
        self.request_id = request_id
        self.default_code = default_code
        self.reraise = reraise
        self.error: Optional[ResearchError] = None

    def __enter__(self) -> "ErrorHandler":
        """Enter the context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> bool:
        """
        Exit the context, handling any exceptions.

        Returns:
            True to suppress the exception, False to propagate
        """
        if exc_val is not None:
            # Normalize and store the error
            self.error = normalize_error(exc_val, self.default_code)

            # Log the error
            log_error(self.error, self.request_id)

            # Return True to suppress unless reraise is set
            return not self.reraise

        return False
