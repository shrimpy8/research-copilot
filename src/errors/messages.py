"""
User-friendly error messages for Research Copilot.

Each error code maps to a dictionary containing:
- title: Short error title
- message: Human-readable explanation
- suggestion: Recovery action for the user
- icon: Emoji for visual indication
- steps: Optional recovery steps (for service errors)
"""

from typing import Any

from src.errors.codes import ErrorCodes


ERROR_MESSAGES: dict[str, dict[str, Any]] = {
    # Search Errors
    ErrorCodes.SEARCH_FAILED: {
        "title": "Search Failed",
        "message": "Unable to search the web right now.",
        "suggestion": "Try again in a moment, or rephrase your query.",
        "icon": "🔍",
    },
    ErrorCodes.SEARCH_TIMEOUT: {
        "title": "Search Timeout",
        "message": "The search took too long to complete.",
        "suggestion": "Try a simpler query or wait and try again.",
        "icon": "⏱️",
    },
    ErrorCodes.SEARCH_NO_RESULTS: {
        "title": "No Results Found",
        "message": "Your search didn't return any results.",
        "suggestion": "Try different keywords or a broader search term.",
        "icon": "🔍",
    },
    ErrorCodes.SEARCH_RATE_LIMITED: {
        "title": "Search Limit Reached",
        "message": "Too many searches in a short time.",
        "suggestion": "Wait a minute before searching again.",
        "icon": "⏳",
    },

    # Fetch Errors
    ErrorCodes.FETCH_FAILED: {
        "title": "Could Not Load Page",
        "message": "Unable to fetch the requested URL.",
        "suggestion": "Check that the URL is correct and the site is accessible.",
        "icon": "📄",
    },
    ErrorCodes.FETCH_TIMEOUT: {
        "title": "Page Load Timeout",
        "message": "The page took too long to load.",
        "suggestion": "The site may be slow. Try again or use a different source.",
        "icon": "⏱️",
    },
    ErrorCodes.FETCH_BLOCKED: {
        "title": "Access Blocked",
        "message": "This site doesn't allow automated access.",
        "suggestion": "Try opening the link directly in your browser instead.",
        "icon": "🚫",
    },
    ErrorCodes.FETCH_INVALID_URL: {
        "title": "Invalid URL",
        "message": "The provided URL is not valid.",
        "suggestion": "Check the URL format and try again.",
        "icon": "🔗",
    },
    ErrorCodes.FETCH_CONTENT_TYPE: {
        "title": "Unsupported Content Type",
        "message": "This URL does not point to an HTML page.",
        "suggestion": "Try a different page or paste an HTML article URL.",
        "icon": "📄",
    },

    # Note Errors
    ErrorCodes.NOTE_NOT_FOUND: {
        "title": "Note Not Found",
        "message": "The requested note doesn't exist.",
        "suggestion": "It may have been deleted. Try searching your notes.",
        "icon": "📝",
    },
    ErrorCodes.NOTE_SAVE_FAILED: {
        "title": "Note Save Failed",
        "message": "Unable to save your note.",
        "suggestion": "Try again in a moment.",
        "icon": "📝",
    },
    ErrorCodes.NOTE_TITLE_REQUIRED: {
        "title": "Note Title Required",
        "message": "A note title is required.",
        "suggestion": "Add a title and try saving again.",
        "icon": "📝",
    },
    ErrorCodes.NOTE_CONTENT_REQUIRED: {
        "title": "Note Content Required",
        "message": "Notes cannot be empty.",
        "suggestion": "Add some content and try saving again.",
        "icon": "📝",
    },
    ErrorCodes.NOTE_TITLE_TOO_LONG: {
        "title": "Note Title Too Long",
        "message": "The note title exceeds the allowed length.",
        "suggestion": "Shorten the title to 200 characters or less.",
        "icon": "📝",
    },
    ErrorCodes.NOTE_TOO_MANY_TAGS: {
        "title": "Too Many Tags",
        "message": "The note has too many tags.",
        "suggestion": "Keep up to 10 tags and try again.",
        "icon": "📝",
    },
    ErrorCodes.NOTES_DB_UNAVAILABLE: {
        "title": "Notes Unavailable",
        "message": "Unable to access your saved notes.",
        "suggestion": "The notes database may need to restart.",
        "icon": "💾",
    },
    ErrorCodes.NOTES_QUERY_FAILED: {
        "title": "Notes Search Failed",
        "message": "Unable to search your notes.",
        "suggestion": "Try a simpler search query.",
        "icon": "🔍",
    },

    # Validation Errors
    ErrorCodes.INVALID_REQUEST: {
        "title": "Invalid Request",
        "message": "The request could not be processed.",
        "suggestion": "Check your input and try again.",
        "icon": "⚠️",
    },
    ErrorCodes.MISSING_PARAMETER: {
        "title": "Missing Information",
        "message": "Some required information is missing.",
        "suggestion": "Please provide all required fields.",
        "icon": "⚠️",
    },
    ErrorCodes.INVALID_URL: {
        "title": "Invalid URL",
        "message": "The provided URL is not valid or not allowed.",
        "suggestion": "Please provide a valid HTTP or HTTPS URL.",
        "icon": "🔗",
    },

    # Service Errors
    ErrorCodes.OLLAMA_UNAVAILABLE: {
        "title": "Ollama Not Running",
        "message": "Cannot connect to the Ollama service.",
        "suggestion": "Make sure Ollama is installed and running.",
        "icon": "🤖",
        "steps": [
            "Open Terminal",
            "Run: ollama serve",
            "Wait for 'Listening on...' message",
            "Refresh this page",
        ],
    },
    ErrorCodes.OLLAMA_MODEL_NOT_FOUND: {
        "title": "Model Not Found",
        "message": "The selected model is not installed.",
        "suggestion": "Install the model or choose a different one.",
        "icon": "🤖",
        "steps": [
            "Open Terminal",
            "Run: ollama pull {model_name}",
            "Wait for download to complete",
            "Refresh this page",
        ],
    },
    ErrorCodes.OLLAMA_TIMEOUT: {
        "title": "Model Response Timeout",
        "message": "The AI model took too long to respond.",
        "suggestion": "Try a shorter query or wait and try again.",
        "icon": "⏱️",
    },
    ErrorCodes.MCP_SERVER_UNAVAILABLE: {
        "title": "Research Tools Offline",
        "message": "The MCP server is not responding.",
        "suggestion": "The research tools need to be restarted.",
        "icon": "🔧",
        "steps": [
            "Open Terminal in the project directory",
            "Run: cd mcp_server && npm start",
            "Wait for 'MCP server ready' message",
            "Refresh this page",
        ],
    },
    ErrorCodes.MCP_TOOL_FAILED: {
        "title": "Tool Execution Failed",
        "message": "A research tool encountered an error.",
        "suggestion": "Try again or use a different approach.",
        "icon": "🔧",
    },

    # Internal Errors
    ErrorCodes.INTERNAL_ERROR: {
        "title": "Something Went Wrong",
        "message": "An unexpected error occurred.",
        "suggestion": "Please try again. If the problem persists, restart the application.",
        "icon": "⚠️",
    },
    ErrorCodes.ORCHESTRATION_FAILED: {
        "title": "Processing Error",
        "message": "Unable to process your request.",
        "suggestion": "Try rephrasing your question or breaking it into smaller parts.",
        "icon": "⚠️",
    },
}


def get_error_message(code: str) -> dict[str, Any]:
    """
    Get the user-friendly error message for an error code.

    Args:
        code: The error code

    Returns:
        Dictionary containing title, message, suggestion, icon, and optional steps
    """
    return ERROR_MESSAGES.get(
        code,
        {
            "title": "Something Went Wrong",
            "message": "An unexpected error occurred.",
            "suggestion": "Please try again.",
            "icon": "⚠️",
        },
    )


def format_error_for_display(
    code: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Format an error for display in the UI.

    Args:
        code: The error code
        details: Optional additional details to interpolate into the message

    Returns:
        Formatted error dictionary ready for UI display
    """
    error_info = get_error_message(code).copy()

    # Interpolate details into recovery steps if present
    if details and "steps" in error_info:
        error_info["steps"] = [
            step.format(**details) for step in error_info["steps"]
        ]

    return error_info
