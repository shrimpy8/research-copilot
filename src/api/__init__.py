"""
API module for Research Copilot.

Per PRD §8.1 - Internal API routes and interfaces.
Provides clean separation between UI and business logic.
"""

from .research import ResearchAPI, ResearchRequest, ResearchResult
from .notes import NotesAPI

__all__ = [
    "ResearchAPI",
    "ResearchRequest",
    "ResearchResult",
    "NotesAPI",
]
