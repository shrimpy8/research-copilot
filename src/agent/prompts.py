"""
System prompt builder for the research assistant.

Constructs prompts that guide the LLM to use tools correctly,
cite sources, and format responses appropriately.

Key functions:
- build_system_prompt(): Main prompt builder with tool definitions and mode context
- format_tool_result(): Formats tool results for LLM conversation

Research mode configuration is centralized in src/models/research_mode.py (DRY).
Prompts are externalized in prompts/ directory for easy editing.
"""

from typing import List, Dict, Any
from pathlib import Path
from functools import lru_cache
from src.models.research_mode import get_mode_by_key

# Base path for prompt files
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=10)
def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory. Cached for performance."""
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    else:
        raise FileNotFoundError(f"Prompt file not found: {filepath}")


def get_tool_definitions() -> str:
    """Load tool definitions from external file."""
    return _load_prompt_file("tool_definitions.md")


def get_system_prompt_template() -> str:
    """Load system prompt template from external file."""
    return _load_prompt_file("system_prompt.md")


# Convenience aliases for backward compatibility
TOOL_DEFINITIONS = property(lambda self: get_tool_definitions())
SYSTEM_PROMPT_TEMPLATE = property(lambda self: get_system_prompt_template())


def build_system_prompt(
    include_tools: bool = True,
    additional_context: str = "",
    research_mode: str = "quick"
) -> str:
    """
    Build the system prompt for the research assistant.

    Args:
        include_tools: Whether to include tool definitions
        additional_context: Extra context to append to the prompt
        research_mode: "quick" or "deep" - affects response style

    Returns:
        The complete system prompt string
    """
    template = get_system_prompt_template()
    tool_defs = get_tool_definitions() if include_tools else ""
    prompt = template.format(tool_definitions=tool_defs)

    # Add research mode instructions from centralized config (DRY)
    mode_config = get_mode_by_key(research_mode)
    prompt += "\n" + mode_config.prompt_context

    if additional_context:
        prompt += f"\n\n## Additional Context\n{additional_context}"

    return prompt.strip()


def format_tool_result(
    tool_name: str,
    result: Dict[str, Any],
    success: bool = True
) -> str:
    """
    Format a tool result for inclusion in the conversation.

    Args:
        tool_name: Name of the tool that was called
        result: The result data from the tool
        success: Whether the tool call succeeded

    Returns:
        Formatted string for the tool result
    """
    if success:
        return f"""<tool_result name="{tool_name}">
{_format_result_content(tool_name, result)}
</tool_result>"""
    else:
        error_msg = result.get("message", "Unknown error")
        error_code = result.get("code", "error")
        return f"""<tool_error name="{tool_name}" code="{error_code}">
{error_msg}
</tool_error>"""


def _format_result_content(tool_name: str, result: Dict[str, Any]) -> str:
    """Format the content of a tool result based on tool type."""
    if tool_name == "web_search":
        results = result.get("results", [])
        if not results:
            return "No results found."

        lines = [f"Found {len(results)} results:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', 'Untitled')}")
            lines.append(f"    URL: {r.get('url', '')}")
            snippet = r.get("snippet", "")
            if snippet:
                lines.append(f"    {snippet[:200]}...")
            lines.append("")
        return "\n".join(lines)

    elif tool_name == "fetch_page":
        title = result.get("title", "Untitled")
        content = result.get("content", "")
        url = result.get("url", "")
        truncated = result.get("truncated", False)

        lines = [
            f"Title: {title}",
            f"URL: {url}",
            "",
            "Content:",
            content[:5000] + ("..." if len(content) > 5000 else ""),
        ]
        if truncated:
            lines.append("\n(Content was truncated)")
        return "\n".join(lines)

    elif tool_name == "save_note":
        note = result.get("note", {})
        return f"Note saved successfully.\nID: {note.get('id')}\nTitle: {note.get('title')}"

    elif tool_name == "list_notes":
        notes = result.get("notes", [])
        count = result.get("count", 0)

        if not notes:
            return "No notes found."

        lines = [f"Found {count} notes:\n"]
        for note in notes:
            lines.append(f"- {note.get('title')} (ID: {note.get('id')[:8]}...)")
            tags = note.get("tags", [])
            if tags:
                lines.append(f"  Tags: {', '.join(tags)}")
        return "\n".join(lines)

    elif tool_name == "get_note":
        note = result.get("note", {})
        lines = [
            f"Title: {note.get('title')}",
            f"ID: {note.get('id')}",
            f"Created: {note.get('created_at')}",
            f"Tags: {', '.join(note.get('tags', []))}",
            "",
            "Content:",
            note.get("content", ""),
        ]
        source_urls = note.get("source_urls", [])
        if source_urls:
            lines.append("\nSources:")
            for url in source_urls:
                lines.append(f"- {url}")
        return "\n".join(lines)

    else:
        # Generic JSON formatting for unknown tools
        import json
        return json.dumps(result, indent=2)


# Note: Unused convenience functions (get_research_prompt, get_note_review_prompt,
# get_quick_search_prompt) were removed per DRY audit. Use build_system_prompt()
# directly with appropriate parameters.
