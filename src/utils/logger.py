"""
Logging infrastructure for Research Copilot.

Provides structured logging with JSON and Pretty formatters,
log redaction for sensitive data, and request tracing support.
"""

import json
import logging
import re
import sys
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

from src.utils.config import settings

# Maximum length for content in logs (per PRD: truncate fetched content to 200 chars)
MAX_CONTENT_LOG_LENGTH = 200


class LogRedactor:
    """
    Redacts sensitive information from log messages.

    Follows PRD section 11.1.1 Log Redaction Rules:
    - Never log API keys or auth headers
    - Truncate fetched page content to 200 characters
    - Redact full URLs with query parameters; keep hostname + path only
    """

    # Patterns for sensitive data with their replacements
    API_KEY_PATTERNS = [
        # Pattern with capture group for the key name
        (
            r"(?i)(api[_-]?key|apikey|secret|password|token|auth)[\"']?\s*[:=]\s*[\"']?([^\s\"',}]+)",
            r"\1: [REDACTED]",
        ),
        # Patterns without capture groups - use fixed replacement
        (r"(?i)bearer\s+[^\s]+", "[BEARER REDACTED]"),
        (r"(?i)basic\s+[^\s]+", "[BASIC REDACTED]"),
    ]

    @classmethod
    def redact_api_keys(cls, message: str) -> str:
        """Redact API keys and secrets from log messages."""
        result = message
        for pattern, replacement in cls.API_KEY_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    @classmethod
    def redact_urls(cls, message: str) -> str:
        """Redact query parameters from URLs in a message."""
        def _replace(match: re.Match) -> str:
            return cls.redact_url(match.group(0))

        return re.sub(r'https?://[^\s)]+', _replace, message)

    @classmethod
    def redact_url(cls, url: str) -> str:
        """
        Redact URL query parameters while keeping hostname + path.

        Args:
            url: Full URL potentially containing query parameters

        Returns:
            URL with query parameters removed
        """
        try:
            parsed = urlparse(url)
            # Keep only scheme, netloc, and path
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        except Exception:
            return "[INVALID_URL]"

    @classmethod
    def truncate_content(cls, content: str, max_length: int = MAX_CONTENT_LOG_LENGTH) -> str:
        """
        Truncate content for logging.

        Args:
            content: Content to truncate
            max_length: Maximum length (default 200 per PRD)

        Returns:
            Truncated content with ellipsis if truncated
        """
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    @classmethod
    def redact(cls, message: str) -> str:
        """Apply all redaction rules to a message."""
        result = cls.redact_api_keys(message)
        return cls.redact_urls(result)


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Produces machine-readable logs suitable for log aggregation systems.
    Includes request_id, tool_name, and duration_ms when available.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": LogRedactor.redact(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add request tracing fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        if hasattr(record, "tool_name"):
            log_obj["tool_name"] = record.tool_name

        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        if hasattr(record, "success"):
            log_obj["success"] = record.success

        return json.dumps(log_obj)


class PrettyFormatter(logging.Formatter):
    """
    Pretty log formatter for human-readable console output.

    Uses colors for different log levels and includes timing information.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors and timing."""
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Build the log line parts
        parts = [
            f"{color}{timestamp}{self.RESET}",
            f"{color}{record.levelname:8}{self.RESET}",
            f"{record.name}:",
            LogRedactor.redact(record.getMessage()),
        ]

        # Add duration if present
        if hasattr(record, "duration_ms"):
            parts.append(f"({record.duration_ms}ms)")

        # Add request_id if present
        if hasattr(record, "request_id"):
            parts.append(f"[{record.request_id[:8]}]")

        return " ".join(parts)


def setup_logger(name: str) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: Logger name (e.g., "research_copilot.agent")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Map log level string to logging constant
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR,
    }
    logger.setLevel(level_map.get(settings.log_level, logging.INFO))

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if settings.log_format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(PrettyFormatter())

        logger.addHandler(handler)

    return logger


class LogContext:
    """
    Context manager for adding extra fields to log records.

    Usage:
        with LogContext(logger, request_id="abc123", tool_name="web_search"):
            logger.info("Starting search")  # Will include request_id and tool_name
    """

    def __init__(self, logger: logging.Logger, **kwargs: Any):
        """
        Initialize the log context.

        Args:
            logger: Logger to add context to
            **kwargs: Extra fields to add to log records
        """
        self.logger = logger
        self.extra = kwargs
        self._old_factory: Optional[Any] = None

    def __enter__(self) -> "LogContext":
        """Enter the context and add extra fields to log records."""
        old_factory = logging.getLogRecordFactory()
        extra = self.extra

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            for key, value in extra.items():
                setattr(record, key, value)
            return record

        self._old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context and restore the original log record factory."""
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)


# Pre-configured loggers for common modules
app_logger = setup_logger("research_copilot")
agent_logger = setup_logger("research_copilot.agent")
mcp_logger = setup_logger("research_copilot.mcp")
ollama_logger = setup_logger("research_copilot.ollama")
