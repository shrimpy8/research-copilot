"""
Agent module for the research assistant.

Contains the orchestrator, prompts, and tool parsing logic.
"""

from .orchestrator import (
    Orchestrator,
    ResearchResponse,
    ToolExecution,
    Source,
    Message,
)
from .parser import (
    parse_tool_calls,
    ToolCall,
    ParseResult,
    has_tool_call,
    extract_text_content,
)
from .prompts import (
    build_system_prompt,
    format_tool_result,
)

__all__ = [
    # Orchestrator
    "Orchestrator",
    "ResearchResponse",
    "ToolExecution",
    "Source",
    "Message",
    # Parser
    "parse_tool_calls",
    "ToolCall",
    "ParseResult",
    "has_tool_call",
    "extract_text_content",
    # Prompts
    "build_system_prompt",
    "format_tool_result",
]
