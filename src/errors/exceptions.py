"""
Custom exceptions for Research Copilot.

All application errors should use these exception classes for consistent
error handling and user-friendly error messages.
"""

from typing import Any, Optional

from src.errors.codes import ErrorCodes, ErrorTypes, get_error_type


class ResearchError(Exception):
    """
    Base exception for Research Copilot errors.

    All application errors should inherit from this class to ensure
    consistent error handling and message formatting.

    Attributes:
        code: Machine-readable error code (e.g., "search_failed")
        message: Human-readable error message
        error_type: Error category (validation, tool, service, internal)
        suggestion: Optional recovery suggestion for the user
        details: Optional additional details about the error
    """

    def __init__(
        self,
        code: str,
        message: str,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the ResearchError.

        Args:
            code: Machine-readable error code
            message: Human-readable error message
            suggestion: Optional recovery suggestion
            details: Optional additional error details
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.error_type = get_error_type(code)
        self.suggestion = suggestion
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a dictionary for JSON serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "type": self.error_type,
            "suggestion": self.suggestion,
            "details": self.details,
        }


class ValidationError(ResearchError):
    """Exception for validation errors (invalid input, missing parameters)."""

    def __init__(
        self,
        code: str = ErrorCodes.INVALID_REQUEST,
        message: str = "Invalid request",
        param: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the ValidationError.

        Args:
            code: Error code (defaults to invalid_request)
            message: Error message
            param: Name of the invalid parameter
            suggestion: Recovery suggestion
            details: Additional details
        """
        if param:
            details = details or {}
            details["param"] = param
        super().__init__(code, message, suggestion, details)


class SearchError(ResearchError):
    """Exception for web search errors."""

    def __init__(
        self,
        code: str = ErrorCodes.SEARCH_FAILED,
        message: str = "Search failed",
        query: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the SearchError.

        Args:
            code: Error code (defaults to search_failed)
            message: Error message
            query: The search query that failed
            suggestion: Recovery suggestion
            details: Additional details
        """
        if query:
            details = details or {}
            details["query"] = query
        super().__init__(code, message, suggestion, details)


class FetchError(ResearchError):
    """Exception for page fetch errors."""

    def __init__(
        self,
        code: str = ErrorCodes.FETCH_FAILED,
        message: str = "Failed to fetch page",
        url: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the FetchError.

        Args:
            code: Error code (defaults to fetch_failed)
            message: Error message
            url: The URL that failed to fetch
            suggestion: Recovery suggestion
            details: Additional details
        """
        if url:
            details = details or {}
            details["url"] = url
        super().__init__(code, message, suggestion, details)


class NoteError(ResearchError):
    """Exception for note-related errors."""

    def __init__(
        self,
        code: str = ErrorCodes.NOTE_SAVE_FAILED,
        message: str = "Note operation failed",
        note_id: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the NoteError.

        Args:
            code: Error code (defaults to note_save_failed)
            message: Error message
            note_id: The ID of the affected note
            suggestion: Recovery suggestion
            details: Additional details
        """
        if note_id:
            details = details or {}
            details["note_id"] = note_id
        super().__init__(code, message, suggestion, details)


class ServiceError(ResearchError):
    """Exception for external service errors (Ollama, MCP server)."""

    def __init__(
        self,
        code: str = ErrorCodes.INTERNAL_ERROR,
        message: str = "Service error",
        service: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the ServiceError.

        Args:
            code: Error code
            message: Error message
            service: Name of the failing service
            suggestion: Recovery suggestion
            details: Additional details
        """
        if service:
            details = details or {}
            details["service"] = service
        super().__init__(code, message, suggestion, details)


class OllamaError(ServiceError):
    """Exception for Ollama-specific errors."""

    def __init__(
        self,
        code: str = ErrorCodes.OLLAMA_UNAVAILABLE,
        message: str = "Ollama error",
        model: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the OllamaError.

        Args:
            code: Error code (defaults to ollama_unavailable)
            message: Error message
            model: The model that caused the error
            suggestion: Recovery suggestion
            details: Additional details
        """
        if model:
            details = details or {}
            details["model"] = model
        super().__init__(code, message, "ollama", suggestion, details)


class MCPError(ServiceError):
    """Exception for MCP server errors."""

    def __init__(
        self,
        code: str = ErrorCodes.MCP_SERVER_UNAVAILABLE,
        message: str = "MCP server error",
        tool: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the MCPError.

        Args:
            code: Error code (defaults to mcp_server_unavailable)
            message: Error message
            tool: The MCP tool that caused the error
            suggestion: Recovery suggestion
            details: Additional details
        """
        if tool:
            details = details or {}
            details["tool"] = tool
        super().__init__(code, message, "mcp_server", suggestion, details)
