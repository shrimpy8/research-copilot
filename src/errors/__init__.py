"""Error handling for Research Copilot."""

from src.errors.codes import ErrorCodes, ErrorTypes, get_error_type
from src.errors.exceptions import (
    FetchError,
    MCPError,
    NoteError,
    OllamaError,
    ResearchError,
    SearchError,
    ServiceError,
    ValidationError,
)
from src.errors.handlers import (
    ErrorHandler,
    create_error_response,
    handle_http_error,
    log_error,
    normalize_error,
)
from src.errors.messages import format_error_for_display, get_error_message

__all__ = [
    # Codes
    "ErrorCodes",
    "ErrorTypes",
    "get_error_type",
    # Exceptions
    "ResearchError",
    "ValidationError",
    "SearchError",
    "FetchError",
    "NoteError",
    "ServiceError",
    "OllamaError",
    "MCPError",
    # Handlers
    "normalize_error",
    "handle_http_error",
    "log_error",
    "create_error_response",
    "ErrorHandler",
    # Messages
    "get_error_message",
    "format_error_for_display",
]
