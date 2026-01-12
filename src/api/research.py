"""
Research API interface for Research Copilot.

Per PRD §8.1 - Internal API routes.
Provides a clean interface between UI and orchestrator.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

import time

from src.agent import Orchestrator
from src.errors import ErrorCodes
from src.models import ApiResponse
from src.api.responses import success_response, error_response


@dataclass
class ResearchRequest:
    """Request for research query."""
    query: str
    mode: str = "quick"  # "quick" or "deep"
    max_sources: int = 5


@dataclass
class ResearchResult:
    """Result from research API."""
    success: bool
    content: str = ""
    sources: List[Dict[str, str]] = None
    tool_trace: List[Dict[str, Any]] = None
    error: Optional[ApiError] = None
    can_save: bool = True
    suggested_title: str = ""

    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if self.tool_trace is None:
            self.tool_trace = []


class ResearchAPI:
    """
    High-level API for research operations.

    Wraps the orchestrator with a cleaner interface.
    """

    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        """Initialize the research API."""
        self._orchestrator = orchestrator

    @property
    def orchestrator(self) -> Orchestrator:
        """Get or create orchestrator instance."""
        if self._orchestrator is None:
            self._orchestrator = Orchestrator()
        return self._orchestrator

    async def research(
        self,
        request: ResearchRequest,
        on_progress: Optional[Callable[[str, Dict], None]] = None
    ) -> ApiResponse:
        """
        Execute a research query.

        Args:
            request: Research request parameters
            on_progress: Optional callback for progress updates

        Returns:
            ApiResponse with content, sources, and metadata
        """
        start_time = time.time()

        try:
            # Set research mode
            self.orchestrator.set_research_mode(request.mode)

            # Execute research
            response = await self.orchestrator.research(
                request.query,
                on_tool_start=on_progress,
                on_tool_complete=on_progress
            )

            data = {
                "content": response.content,
                "sources": [
                    {"url": s.url, "title": s.title, "tool": s.tool}
                    for s in response.sources
                ],
                "tool_trace": [
                    {
                        "tool_name": t.tool_name,
                        "success": t.success,
                        "duration_ms": t.duration_ms,
                    }
                    for t in response.tool_trace
                ],
                "can_save": response.can_save_as_note,
                "suggested_title": response.suggested_title,
            }

            return success_response(
                data=data,
                start_time=start_time,
            )

        except Exception as e:
            return error_response(
                code=ErrorCodes.SERVICE_ERROR,
                message=str(e),
                error_type="research_error",
                suggestion="Check if Ollama and MCP server are running.",
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services."""
        return await self.orchestrator.health_check()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.orchestrator.clear_history()
