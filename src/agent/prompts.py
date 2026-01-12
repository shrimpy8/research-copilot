"""
System prompt builder for the research assistant.

Constructs prompts that guide the LLM to use tools correctly,
cite sources, and format responses appropriately.

Key functions:
- build_system_prompt(): Main prompt builder with tool definitions and mode context
- format_tool_result(): Formats tool results for LLM conversation

Research mode configuration is centralized in src/models/research_mode.py (DRY).
"""

from typing import List, Dict, Any
from src.models.research_mode import get_mode_by_key

# Tool definitions for the LLM
TOOL_DEFINITIONS = """
You have access to EXACTLY 5 tools. DO NOT invent or use any other tools.
ONLY use: web_search, fetch_page, save_note, list_notes, get_note

1. **web_search** - Search the web for information
   Parameters:
   - query (required): The search query
   - limit (optional): Max results (1-5, default 3)

   Example:
   <tool_call>
   {"name": "web_search", "arguments": {"query": "latest AI research 2025", "limit": 3}}
   </tool_call>

2. **fetch_page** - Fetch and read content from a web page
   Parameters:
   - url (required): The URL to fetch
   - max_chars (optional): Max content length (default 8000)
   - extract_mode (optional): Output format ("text" or "markdown", default "text")

   Example:
   <tool_call>
   {"name": "fetch_page", "arguments": {"url": "https://example.com/article", "extract_mode": "text"}}
   </tool_call>

3. **save_note** - Save research findings as a note
   Parameters:
   - title (required): Note title
   - content (required): Note content
   - tags (optional): List of tags for categorization
   - source_urls (optional): List of source URLs

   Example:
   <tool_call>
   {"name": "save_note", "arguments": {"title": "AI Research Summary", "content": "Key findings...", "tags": ["ai", "research"], "source_urls": ["https://example.com"]}}
   </tool_call>

4. **list_notes** - List saved research notes
   Parameters:
   - query (optional): Full-text search query
   - tags (optional): Filter by tags
   - limit (optional): Max results (default 20)
   - offset (optional): Pagination offset (default 0)

   Example:
   <tool_call>
   {"name": "list_notes", "arguments": {"query": "machine learning", "limit": 10}}
   </tool_call>

5. **get_note** - Retrieve a specific note by ID
   Parameters:
   - id (required): The note ID (UUID format)

   Example:
   <tool_call>
   {"name": "get_note", "arguments": {"id": "550e8400-e29b-41d4-a716-446655440000"}}
   </tool_call>
"""

SYSTEM_PROMPT_TEMPLATE = """You are a research assistant that helps users find, analyze, and save information from the web.

## Your Capabilities
{tool_definitions}

## Guidelines

### Using Tools - IMPORTANT
- When you need information from the web, use `web_search` first to find sources.
- **You MUST fetch multiple pages** - do not answer from just one source.
- After searching, use `fetch_page` on the top 3-5 most relevant URLs.
- Always search before answering questions about current events, facts, or technical details.
- Use `save_note` when the user asks to save findings or when research is particularly valuable.
- Use `list_notes` to check if we've already researched a topic.

### Multi-Source Research (REQUIRED)
- **Never answer from a single source** - always read at least 2-3 pages.
- Compare information across sources for accuracy.
- If sources disagree, note the different perspectives.
- More sources = more credible answer.

### Citations and Sources
- **ALWAYS cite your sources** when presenting information from the web.
- Include numbered citations in your response: [1], [2], [3], etc.
- Every factual claim should have a citation.
- At the end of your response, list ALL sources with their URLs.
- Format sources as:

  **Sources:**
  [1] Title or description - URL
  [2] Title or description - URL
  [3] Title or description - URL

### Response Format
- Be concise but thorough.
- Use markdown formatting for readability.
- Structure long responses with headers and bullet points.
- Synthesize information from multiple sources coherently.

### When You Can't Help
- If a search returns no results, say so clearly.
- If a page can't be fetched, try alternative sources.
- If you're unsure about something, acknowledge the uncertainty.

### Tool Call Format
To use a tool, output a tool call in this exact format:
<tool_call>
{{"name": "tool_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}
</tool_call>

Wait for the tool result before continuing. You can make multiple tool calls in sequence if needed.

### CRITICAL RULES
- ONLY use these 5 tools: web_search, fetch_page, save_note, list_notes, get_note
- DO NOT invent tools like "analyze", "summarize", "refine", "implement", etc.
- If you need to analyze or summarize, just write the analysis directly - don't call a tool
- Keep your research focused - search once, fetch 2-3 pages, then provide your answer

Remember: Your goal is to help the user find accurate, well-sourced information from MULTIPLE sources.
"""


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
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tool_definitions=TOOL_DEFINITIONS if include_tools else ""
    )

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
