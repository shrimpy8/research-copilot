"""
Note models for Research Copilot.

Per PRD §7.2.3 - Note persistence with SQLite.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class Note:
    """
    A saved research note.

    Per PRD §7.2.3 - Note fields and constraints.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""  # Max 200 chars per PRD
    content: str = ""  # Max 50000 chars per PRD
    tags: List[str] = field(default_factory=list)  # Max 10 tags, each max 50 chars
    source_urls: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert note to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "source_urls": self.source_urls,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create note from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            source_urls=data.get("source_urls", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


@dataclass
class NoteCreate:
    """Request model for creating a note."""
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)


@dataclass
class NoteUpdate:
    """Request model for updating a note."""
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class NoteQuery:
    """Query parameters for listing notes."""
    query: Optional[str] = None  # Full-text search
    tags: Optional[List[str]] = None  # Filter by tags
    limit: int = 20  # Max results
    offset: int = 0  # Pagination offset


# Validation constraints per PRD §7.2.3
class NoteConstraints:
    """Validation constraints for notes."""
    MAX_TITLE_LENGTH = 200
    MAX_CONTENT_LENGTH = 50000
    MAX_TAGS = 10
    MAX_TAG_LENGTH = 50
    MAX_SOURCE_URLS = 20
