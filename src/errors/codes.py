"""
Error code constants for Research Copilot.

Error codes follow these conventions:
- Use snake_case: search_failed, fetch_timeout
- Be specific: ollama_unavailable not service_error
- Match the tool: note_not_found, search_no_results
"""


class ErrorCodes:
    """Machine-readable error codes for Research Copilot."""

    # Validation Errors
    INVALID_REQUEST = "invalid_request"
    MISSING_PARAMETER = "missing_parameter"
    INVALID_URL = "invalid_url"

    # Search Errors
    SEARCH_FAILED = "search_failed"
    SEARCH_TIMEOUT = "search_timeout"
    SEARCH_NO_RESULTS = "search_no_results"
    SEARCH_RATE_LIMITED = "search_rate_limited"

    # Fetch Errors
    FETCH_FAILED = "fetch_failed"
    FETCH_TIMEOUT = "fetch_timeout"
    FETCH_BLOCKED = "fetch_blocked"
    FETCH_INVALID_URL = "fetch_invalid_url"
    FETCH_CONTENT_TYPE = "fetch_content_type"

    # Note Errors
    NOTE_NOT_FOUND = "note_not_found"
    NOTE_SAVE_FAILED = "note_save_failed"
    NOTE_TITLE_REQUIRED = "note_title_required"
    NOTE_CONTENT_REQUIRED = "note_content_required"
    NOTE_TITLE_TOO_LONG = "note_title_too_long"
    NOTE_TOO_MANY_TAGS = "note_too_many_tags"
    NOTES_DB_UNAVAILABLE = "notes_db_unavailable"
    NOTES_QUERY_FAILED = "notes_query_failed"

    # Service Errors
    OLLAMA_UNAVAILABLE = "ollama_unavailable"
    OLLAMA_MODEL_NOT_FOUND = "ollama_model_not_found"
    OLLAMA_TIMEOUT = "ollama_timeout"
    MCP_SERVER_UNAVAILABLE = "mcp_server_unavailable"
    MCP_TOOL_FAILED = "mcp_tool_failed"

    # Internal Errors
    INTERNAL_ERROR = "internal_error"
    ORCHESTRATION_FAILED = "orchestration_failed"


class ErrorTypes:
    """Error type categories for grouping related errors."""

    VALIDATION = "validation_error"
    TOOL = "tool_error"
    SERVICE = "service_error"
    INTERNAL = "internal_error"


# Mapping of error codes to their types
ERROR_TYPE_MAP = {
    # Validation errors
    ErrorCodes.INVALID_REQUEST: ErrorTypes.VALIDATION,
    ErrorCodes.MISSING_PARAMETER: ErrorTypes.VALIDATION,
    ErrorCodes.INVALID_URL: ErrorTypes.VALIDATION,

    # Tool errors (search)
    ErrorCodes.SEARCH_FAILED: ErrorTypes.TOOL,
    ErrorCodes.SEARCH_TIMEOUT: ErrorTypes.TOOL,
    ErrorCodes.SEARCH_NO_RESULTS: ErrorTypes.TOOL,
    ErrorCodes.SEARCH_RATE_LIMITED: ErrorTypes.TOOL,

    # Tool errors (fetch)
    ErrorCodes.FETCH_FAILED: ErrorTypes.TOOL,
    ErrorCodes.FETCH_TIMEOUT: ErrorTypes.TOOL,
    ErrorCodes.FETCH_BLOCKED: ErrorTypes.TOOL,
    ErrorCodes.FETCH_INVALID_URL: ErrorTypes.TOOL,
    ErrorCodes.FETCH_CONTENT_TYPE: ErrorTypes.TOOL,

    # Tool errors (notes)
    ErrorCodes.NOTE_NOT_FOUND: ErrorTypes.TOOL,
    ErrorCodes.NOTE_SAVE_FAILED: ErrorTypes.TOOL,
    ErrorCodes.NOTE_TITLE_REQUIRED: ErrorTypes.VALIDATION,
    ErrorCodes.NOTE_CONTENT_REQUIRED: ErrorTypes.VALIDATION,
    ErrorCodes.NOTE_TITLE_TOO_LONG: ErrorTypes.VALIDATION,
    ErrorCodes.NOTE_TOO_MANY_TAGS: ErrorTypes.VALIDATION,
    ErrorCodes.NOTES_DB_UNAVAILABLE: ErrorTypes.SERVICE,
    ErrorCodes.NOTES_QUERY_FAILED: ErrorTypes.TOOL,

    # Service errors
    ErrorCodes.OLLAMA_UNAVAILABLE: ErrorTypes.SERVICE,
    ErrorCodes.OLLAMA_MODEL_NOT_FOUND: ErrorTypes.SERVICE,
    ErrorCodes.OLLAMA_TIMEOUT: ErrorTypes.SERVICE,
    ErrorCodes.MCP_SERVER_UNAVAILABLE: ErrorTypes.SERVICE,
    ErrorCodes.MCP_TOOL_FAILED: ErrorTypes.TOOL,

    # Internal errors
    ErrorCodes.INTERNAL_ERROR: ErrorTypes.INTERNAL,
    ErrorCodes.ORCHESTRATION_FAILED: ErrorTypes.INTERNAL,
}


def get_error_type(code: str) -> str:
    """
    Get the error type for a given error code.

    Args:
        code: The error code

    Returns:
        The error type, defaults to INTERNAL if not found
    """
    return ERROR_TYPE_MAP.get(code, ErrorTypes.INTERNAL)
