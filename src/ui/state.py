"""
Streamlit session state management.

Provides type-safe access to session state and initialization.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """A chat message."""
    role: str
    content: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # PRD §5.10 - Additional fields for note saving
    can_save_as_note: bool = True
    suggested_title: str = ""
    followup_questions: List[str] = field(default_factory=list)  # LLM-generated follow-ups
    # Tool traces associated with this message (for assistant messages)
    tool_traces: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""  # The original query (for assistant messages)


@dataclass
class ToolTrace:
    """A tool execution trace."""
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    duration_ms: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = None  # MCP request ID for traceability


@dataclass
class AppState:
    """Application state container."""
    messages: List[Message] = field(default_factory=list)
    tool_traces: List[ToolTrace] = field(default_factory=list)
    current_sources: List[Dict[str, str]] = field(default_factory=list)
    research_mode: str = "quick"
    model: str = "ministral-3:8b"
    temperature: float = 0.4  # LLM temperature (0.0-1.0, lower = more focused)
    is_researching: bool = False
    error: Optional[str] = None
    notes_search_query: str = ""
    notes_offset: int = 0
    notes_page_size: int = 10
    fetch_extract_mode: str = "text"
    selected_note_id: Optional[str] = None
    show_save_dialog: bool = False
    save_note_prefill: Dict[str, Any] = field(default_factory=dict)


def init_state() -> None:
    """Initialize session state with default values."""
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()

    # Also maintain backward compatibility with flat state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_trace" not in st.session_state:
        st.session_state.tool_trace = []
    if "research_mode" not in st.session_state:
        st.session_state.research_mode = "quick"


def get_state() -> AppState:
    """Get the current app state."""
    init_state()
    return st.session_state.app_state


def add_message(
    role: str,
    content: str,
    sources: List[Dict[str, str]] = None,
    can_save_as_note: bool = True,
    suggested_title: str = "",
    followup_questions: List[str] = None,
    tool_traces: List[Dict[str, Any]] = None,
    query: str = ""
) -> None:
    """Add a message to the chat history."""
    state = get_state()
    message = Message(
        role=role,
        content=content,
        sources=sources or [],
        can_save_as_note=can_save_as_note,
        suggested_title=suggested_title,
        followup_questions=followup_questions or [],
        tool_traces=tool_traces or [],
        query=query
    )
    state.messages.append(message)

    # Also update flat state for compatibility (PRD §5.10)
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "sources": sources or [],
        "can_save_as_note": can_save_as_note,
        "suggested_title": suggested_title,
        "followup_questions": followup_questions or [],
        "tool_traces": tool_traces or [],
        "query": query
    })


def add_tool_trace(
    tool_name: str,
    arguments: Dict[str, Any],
    success: bool,
    duration_ms: float,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Add a tool execution trace."""
    state = get_state()
    trace = ToolTrace(
        tool_name=tool_name,
        arguments=arguments,
        success=success,
        duration_ms=duration_ms,
        result=result,
        error=error,
        request_id=request_id
    )
    state.tool_traces.append(trace)

    # Also update flat state
    st.session_state.tool_trace.append({
        "tool_name": tool_name,
        "status": "success" if success else "error",
        "duration_ms": duration_ms,
        "request_id": request_id
    })


def set_researching(is_researching: bool) -> None:
    """Set the researching state."""
    get_state().is_researching = is_researching


def set_error(error: Optional[str]) -> None:
    """Set or clear the error state."""
    get_state().error = error


def set_current_sources(sources: List[Dict[str, str]]) -> None:
    """Set the current sources from the latest research."""
    get_state().current_sources = sources


def clear_history() -> None:
    """Clear chat history and tool traces."""
    state = get_state()
    state.messages = []
    state.tool_traces = []
    state.current_sources = []
    state.error = None

    # Also clear flat state
    st.session_state.messages = []
    st.session_state.tool_trace = []


def show_save_dialog(
    title: str = "",
    content: str = "",
    tags: List[str] = None,
    source_urls: List[str] = None
) -> None:
    """Show the save note dialog with prefilled values."""
    state = get_state()
    state.show_save_dialog = True
    state.save_note_prefill = {
        "title": title,
        "content": content,
        "tags": tags or [],
        "source_urls": source_urls or []
    }


def hide_save_dialog() -> None:
    """Hide the save note dialog."""
    state = get_state()
    state.show_save_dialog = False
    state.save_note_prefill = {}


def set_selected_note(note_id: Optional[str]) -> None:
    """Set the selected note ID for viewing."""
    get_state().selected_note_id = note_id


def get_messages() -> List[Dict[str, Any]]:
    """Get messages in the format expected by the orchestrator."""
    state = get_state()
    return [
        {"role": m.role, "content": m.content}
        for m in state.messages
    ]


def get_tool_traces() -> List[Dict[str, Any]]:
    """Get tool traces for display (legacy - returns all traces)."""
    state = get_state()
    return [
        {
            "tool_name": t.tool_name,
            "arguments": t.arguments,
            "success": t.success,
            "duration_ms": t.duration_ms,
            "result_summary": _summarize_result(t.tool_name, t.result) if t.result else t.error or "",
            "request_id": t.request_id or f"mcp_{i+1}"
        }
        for i, t in enumerate(state.tool_traces)
    ]


def get_tool_traces_by_query() -> List[Dict[str, Any]]:
    """Get tool traces grouped by query for display."""
    messages = st.session_state.get("messages", [])

    grouped = []
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_traces"):
            grouped.append({
                "query": msg.get("query", "Unknown query"),
                "traces": msg.get("tool_traces", []),
                "timestamp": msg.get("timestamp", "")
            })

    return grouped


def get_latest_tool_traces(max_queries: int = 1) -> List[Dict[str, Any]]:
    """
    Get tool traces for the most recent N queries.

    Args:
        max_queries: Maximum number of queries to return traces for (default: 1)

    Returns:
        List of dicts with 'query' and 'traces' keys, most recent first.
        Includes queries without tool calls (traces will be empty list).
    """
    messages = st.session_state.get("messages", [])

    results = []
    for msg in reversed(messages):
        # Include ALL assistant messages with a query, not just ones with tool_traces
        if msg.get("role") == "assistant" and msg.get("query"):
            results.append({
                "query": msg.get("query", "Unknown query"),
                "traces": msg.get("tool_traces", [])
            })
            if len(results) >= max_queries:
                break

    return results


def _summarize_result(tool_name: str, result: Dict[str, Any]) -> str:
    """Create a brief summary of a tool result."""
    if tool_name == "web_search":
        count = len(result.get("results", []))
        return f"Found {count} results"
    elif tool_name == "fetch_page":
        title = result.get("title", "Unknown")
        length = result.get("content_length", 0)
        return f"{title[:30]}... ({length} chars)"
    elif tool_name == "save_note":
        note = result.get("note", {})
        return f"Saved: {note.get('title', 'Untitled')}"
    elif tool_name == "list_notes":
        count = result.get("count", 0)
        return f"Found {count} notes"
    elif tool_name == "get_note":
        note = result.get("note", {})
        return f"Retrieved: {note.get('title', 'Untitled')}"
    else:
        return str(result)[:100]
