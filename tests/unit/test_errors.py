"""Unit tests for error handling module."""

import pytest

from src.errors import (
    ErrorCodes,
    ErrorTypes,
    FetchError,
    MCPError,
    NoteError,
    OllamaError,
    ResearchError,
    SearchError,
    ServiceError,
    ValidationError,
    create_error_response,
    format_error_for_display,
    get_error_message,
    get_error_type,
    normalize_error,
)


class TestErrorCodes:
    """Tests for error code constants."""

    def test_search_error_codes_exist(self):
        """Test that search error codes are defined."""
        assert ErrorCodes.SEARCH_FAILED == "search_failed"
        assert ErrorCodes.SEARCH_TIMEOUT == "search_timeout"
        assert ErrorCodes.SEARCH_NO_RESULTS == "search_no_results"
        assert ErrorCodes.SEARCH_RATE_LIMITED == "search_rate_limited"

    def test_fetch_error_codes_exist(self):
        """Test that fetch error codes are defined."""
        assert ErrorCodes.FETCH_FAILED == "fetch_failed"
        assert ErrorCodes.FETCH_TIMEOUT == "fetch_timeout"
        assert ErrorCodes.FETCH_BLOCKED == "fetch_blocked"
        assert ErrorCodes.FETCH_INVALID_URL == "fetch_invalid_url"
        assert ErrorCodes.FETCH_CONTENT_TYPE == "fetch_content_type"

    def test_note_error_codes_exist(self):
        """Test that note error codes are defined."""
        assert ErrorCodes.NOTE_NOT_FOUND == "note_not_found"
        assert ErrorCodes.NOTE_SAVE_FAILED == "note_save_failed"
        assert ErrorCodes.NOTE_TITLE_REQUIRED == "note_title_required"
        assert ErrorCodes.NOTE_CONTENT_REQUIRED == "note_content_required"

    def test_service_error_codes_exist(self):
        """Test that service error codes are defined."""
        assert ErrorCodes.OLLAMA_UNAVAILABLE == "ollama_unavailable"
        assert ErrorCodes.OLLAMA_MODEL_NOT_FOUND == "ollama_model_not_found"
        assert ErrorCodes.MCP_SERVER_UNAVAILABLE == "mcp_server_unavailable"


class TestErrorTypes:
    """Tests for error type classification."""

    def test_error_type_constants(self):
        """Test that error types are defined."""
        assert ErrorTypes.VALIDATION == "validation_error"
        assert ErrorTypes.TOOL == "tool_error"
        assert ErrorTypes.SERVICE == "service_error"
        assert ErrorTypes.INTERNAL == "internal_error"

    def test_get_error_type_for_search_errors(self):
        """Test error type mapping for search errors."""
        assert get_error_type(ErrorCodes.SEARCH_FAILED) == ErrorTypes.TOOL
        assert get_error_type(ErrorCodes.SEARCH_TIMEOUT) == ErrorTypes.TOOL

    def test_get_error_type_for_service_errors(self):
        """Test error type mapping for service errors."""
        assert get_error_type(ErrorCodes.OLLAMA_UNAVAILABLE) == ErrorTypes.SERVICE
        assert get_error_type(ErrorCodes.MCP_SERVER_UNAVAILABLE) == ErrorTypes.SERVICE

    def test_get_error_type_unknown_defaults_to_internal(self):
        """Test that unknown error codes default to internal."""
        assert get_error_type("unknown_error") == ErrorTypes.INTERNAL


class TestResearchError:
    """Tests for the base ResearchError exception."""

    def test_create_basic_error(self):
        """Test creating a basic ResearchError."""
        error = ResearchError(
            code="test_error",
            message="Test error message",
        )
        assert error.code == "test_error"
        assert error.message == "Test error message"
        assert error.suggestion is None
        assert error.details == {}

    def test_create_error_with_suggestion(self):
        """Test creating an error with a suggestion."""
        error = ResearchError(
            code="test_error",
            message="Test error",
            suggestion="Try this instead",
        )
        assert error.suggestion == "Try this instead"

    def test_create_error_with_details(self):
        """Test creating an error with details."""
        error = ResearchError(
            code="test_error",
            message="Test error",
            details={"key": "value"},
        )
        assert error.details == {"key": "value"}

    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        error = ResearchError(
            code="test_error",
            message="Test error",
            suggestion="Try again",
            details={"param": "value"},
        )
        result = error.to_dict()

        assert result["code"] == "test_error"
        assert result["message"] == "Test error"
        assert result["suggestion"] == "Try again"
        assert result["details"] == {"param": "value"}


class TestSpecificExceptions:
    """Tests for specific exception types."""

    def test_validation_error_with_param(self):
        """Test ValidationError includes param in details."""
        error = ValidationError(
            message="Invalid parameter",
            param="query",
        )
        assert error.details["param"] == "query"

    def test_search_error_with_query(self):
        """Test SearchError includes query in details."""
        error = SearchError(
            message="Search failed",
            query="test query",
        )
        assert error.details["query"] == "test query"

    def test_fetch_error_with_url(self):
        """Test FetchError includes URL in details."""
        error = FetchError(
            message="Fetch failed",
            url="https://example.com",
        )
        assert error.details["url"] == "https://example.com"

    def test_note_error_with_note_id(self):
        """Test NoteError includes note_id in details."""
        error = NoteError(
            message="Note not found",
            note_id="abc123",
        )
        assert error.details["note_id"] == "abc123"

    def test_ollama_error_with_model(self):
        """Test OllamaError includes model in details."""
        error = OllamaError(
            message="Model not found",
            model="ministral-3:8b",
        )
        assert error.details["model"] == "ministral-3:8b"

    def test_mcp_error_with_tool(self):
        """Test MCPError includes tool in details."""
        error = MCPError(
            message="Tool failed",
            tool="web_search",
        )
        assert error.details["tool"] == "web_search"


class TestErrorMessages:
    """Tests for error message retrieval."""

    def test_get_error_message_returns_dict(self):
        """Test that get_error_message returns a dictionary."""
        message = get_error_message(ErrorCodes.SEARCH_FAILED)
        assert isinstance(message, dict)
        assert "title" in message
        assert "message" in message
        assert "suggestion" in message
        assert "icon" in message

    def test_get_error_message_unknown_returns_default(self):
        """Test that unknown codes return a default message."""
        message = get_error_message("unknown_code")
        assert message["title"] == "Something Went Wrong"

    def test_format_error_for_display(self):
        """Test formatting error for UI display."""
        error_info = format_error_for_display(ErrorCodes.OLLAMA_MODEL_NOT_FOUND)
        assert "title" in error_info
        assert "steps" in error_info


class TestNormalizeError:
    """Tests for error normalization."""

    def test_normalize_research_error_passthrough(self):
        """Test that ResearchError passes through unchanged."""
        original = ResearchError(code="test", message="Test")
        normalized = normalize_error(original)
        assert normalized is original

    def test_normalize_generic_exception(self):
        """Test normalizing a generic exception."""
        original = ValueError("Something went wrong")
        normalized = normalize_error(original)

        assert isinstance(normalized, ResearchError)
        assert normalized.code == ErrorCodes.INTERNAL_ERROR
        assert "Something went wrong" in normalized.message

    def test_normalize_with_context(self):
        """Test normalizing with additional context."""
        original = ValueError("Error")
        normalized = normalize_error(
            original,
            context={"request_id": "abc123"},
        )

        assert normalized.details["request_id"] == "abc123"


class TestCreateErrorResponse:
    """Tests for error response creation."""

    def test_create_error_response_structure(self):
        """Test error response has correct structure."""
        error = ResearchError(
            code=ErrorCodes.SEARCH_FAILED,
            message="Search failed",
        )
        response = create_error_response(error)

        assert response["success"] is False
        assert "error" in response
        assert response["error"]["code"] == ErrorCodes.SEARCH_FAILED
        assert "title" in response["error"]
        assert "icon" in response["error"]
