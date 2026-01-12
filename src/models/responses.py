"""
Response models for Research Copilot.

Per PRD §8.1 - Pydantic response/request models.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class ResponseMeta:
    """Metadata for API responses."""
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0


@dataclass
class ApiError:
    """
    Structured error information.

    Per PRD §6 - Every error has: code, message, type, suggestion.
    """
    code: str  # Machine-readable code, e.g. "search_failed"
    message: str  # Human-readable message
    type: str = "error"  # Error category
    param: Optional[str] = None  # Parameter that caused the error
    details: Optional[Dict[str, Any]] = None  # Extra error details
    suggestion: str = ""  # Recovery suggestion


@dataclass
class ApiResponse:
    """
    Standard API response wrapper.

    Per PRD - All responses follow this structure.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ApiError] = None
    meta: Optional[ResponseMeta] = None


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str = ""
    rank: int = 0


@dataclass
class SearchResponse:
    """Response from web search tool."""
    results: List[SearchResult]
    query: str
    provider: str = "duckduckgo"
    total_results: int = 0


@dataclass
class FetchResponse:
    """Response from page fetch tool."""
    url: str
    title: str
    content: str
    content_length: int = 0
    truncated: bool = False


@dataclass
class NoteResponse:
    """Response containing a note."""
    note: Dict[str, Any]


@dataclass
class NotesListResponse:
    """Response containing list of notes."""
    notes: List[Dict[str, Any]]
    count: int = 0
    has_more: bool = False


@dataclass
class HealthResponse:
    """Health check response."""
    available: bool
    tools: List[str] = field(default_factory=list)
    version: str = "1.0.0"


@dataclass
class ToolCallResponse:
    """Response from a tool call."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ApiError] = None
    duration_ms: float = 0
