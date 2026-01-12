"""
Models module for Research Copilot.

Exports all data models, response types, and configuration.
"""

from .responses import (
    ResponseMeta,
    ApiError,
    ApiResponse,
    SearchResult,
    SearchResponse,
    FetchResponse,
    NoteResponse,
    NotesListResponse,
    HealthResponse,
    ToolCallResponse,
)

from src.errors import ErrorCodes

from .notes import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteQuery,
    NoteConstraints
)

from .research_mode import (
    ResearchModeConfig,
    QUICK_MODE,
    DEEP_MODE,
    RESEARCH_MODES,
    RESEARCH_MODE_OPTIONS,
    get_mode_by_key,
    get_mode_by_label,
    get_mode_key_from_label,
)

__all__ = [
    # Response models
    "ResponseMeta",
    "ApiError",
    "ApiResponse",
    "SearchResult",
    "SearchResponse",
    "FetchResponse",
    "NoteResponse",
    "NotesListResponse",
    "HealthResponse",
    "ToolCallResponse",
    "ErrorCodes",
    # Note models
    "Note",
    "NoteCreate",
    "NoteUpdate",
    "NoteQuery",
    "NoteConstraints",
    # Research mode config
    "ResearchModeConfig",
    "QUICK_MODE",
    "DEEP_MODE",
    "RESEARCH_MODES",
    "RESEARCH_MODE_OPTIONS",
    "get_mode_by_key",
    "get_mode_by_label",
    "get_mode_key_from_label",
]
