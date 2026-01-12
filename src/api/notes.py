"""
Notes API interface for Research Copilot.

Per PRD §8.1 - Internal API routes for note operations.
"""

import time
from typing import Optional

from src.clients.mcp_client import MCPClient
from src.errors import ErrorCodes
from src.models import NoteCreate, NoteQuery, ApiResponse
from src.api.responses import success_response, error_response
from src.utils.validators import validate_note_title, validate_note_content, validate_tags


class NotesAPI:
    """
    High-level API for note operations.

    Wraps MCP client with validation and error handling.
    """

    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """Initialize the notes API."""
        self._mcp = mcp_client

    @property
    def mcp(self) -> MCPClient:
        """Get or create MCP client instance."""
        if self._mcp is None:
            self._mcp = MCPClient()
        return self._mcp

    async def create_note(self, note: NoteCreate) -> ApiResponse:
        """
        Create a new note.

        Args:
            note: Note creation request

        Returns:
            ApiResponse with created note or error
        """
        # Validate inputs per PRD §7.2.3
        start_time = time.time()
        valid, error = validate_note_title(note.title)
        if not valid:
            return error_response(
                code=ErrorCodes.INVALID_REQUEST,
                message=error,
                error_type="validation_error",
                suggestion="Note title must be 1-200 characters.",
            )

        valid, error = validate_note_content(note.content)
        if not valid:
            return error_response(
                code=ErrorCodes.INVALID_REQUEST,
                message=error,
                error_type="validation_error",
                suggestion="Note content must be 1-50000 characters.",
            )

        valid, error = validate_tags(note.tags)
        if not valid:
            return error_response(
                code=ErrorCodes.INVALID_REQUEST,
                message=error,
                error_type="validation_error",
                suggestion="Max 10 tags, each max 50 characters.",
            )

        try:
            result = await self.mcp.save_note(
                title=note.title,
                content=note.content,
                tags=note.tags,
                source_urls=note.source_urls
            )

            if result.success:
                return success_response(data=result.data, start_time=start_time)
            return error_response(
                code=ErrorCodes.NOTE_SAVE_FAILED,
                message=result.error.message if result.error else "Failed to save note",
                error_type="tool_error",
                suggestion="Check MCP server status.",
            )

        except Exception as e:
            return error_response(
                code=ErrorCodes.MCP_SERVER_UNAVAILABLE,
                message=str(e),
                error_type="service_error",
                suggestion="Check MCP server connection.",
            )

    async def get_note(self, note_id: str) -> ApiResponse:
        """
        Get a note by ID.

        Args:
            note_id: UUID of the note

        Returns:
            ApiResponse with note data or error
        """
        try:
            result = await self.mcp.get_note(note_id)

            if result.success:
                return success_response(data=result.data)
            return error_response(
                code=ErrorCodes.NOTE_NOT_FOUND,
                message="Note not found",
                error_type="tool_error",
                suggestion="The note may have been deleted.",
            )

        except Exception as e:
            return error_response(
                code=ErrorCodes.MCP_SERVER_UNAVAILABLE,
                message=str(e),
                error_type="service_error",
            )

    async def list_notes(self, query: NoteQuery) -> ApiResponse:
        """
        List notes with optional filtering.

        Args:
            query: Query parameters

        Returns:
            ApiResponse with list of notes or error
        """
        try:
            result = await self.mcp.list_notes(
                query=query.query,
                tags=query.tags,
                limit=query.limit,
                offset=query.offset
            )

            if result.success:
                return success_response(data=result.data)
            return error_response(
                code=ErrorCodes.NOTES_QUERY_FAILED,
                message="Failed to list notes",
                error_type="tool_error",
            )

        except Exception as e:
            return error_response(
                code=ErrorCodes.MCP_SERVER_UNAVAILABLE,
                message=str(e),
                error_type="service_error",
            )

    async def search_notes(self, search_query: str, limit: int = 20) -> ApiResponse:
        """
        Search notes by full-text query.

        Args:
            search_query: Search query string
            limit: Max results

        Returns:
            ApiResponse with matching notes
        """
        return await self.list_notes(NoteQuery(query=search_query, limit=limit))
