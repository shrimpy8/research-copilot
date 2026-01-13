"""
Reusable UI components for the Research Copilot Streamlit app.

This module provides all Streamlit UI rendering functions including:
- Source rendering: render_source_card, render_sources_section, render_source_comparison
- Citations: render_content_with_citations, format_source_link
- Notes: render_note_card, render_save_note_dialog
- Research: render_research_trail, render_confidence_meter, render_followup_chips
- Errors: render_error_message, get_error_recovery_steps
- Helpers: render_tags (DRY helper using design_tokens)

All styling uses centralized design tokens from src/ui/design_tokens.py.
"""

import re
import streamlit as st
from typing import List, Dict, Any, Optional

from src.ui.design_tokens import Colors, BorderRadius, Typography, Spacing, tag_style


def render_tags(tags: List[str], max_tags: int = 3) -> str:
    """
    Render tags as styled HTML pills.

    DRY helper for consistent tag rendering throughout the app.

    Args:
        tags: List of tag strings
        max_tags: Maximum number of tags to display

    Returns:
        HTML string with styled tag pills
    """
    if not tags:
        return ""
    return " ".join([
        f'<span style="{tag_style()}">{tag}</span>'
        for tag in tags[:max_tags]
    ])


def format_source_link(
    number: int,
    title: str,
    url: str,
    max_title_len: int = 40
) -> str:
    """
    Format a source as a numbered markdown link.

    DRY helper used by multiple source rendering functions.

    Args:
        number: Citation number (1-based)
        title: Source title
        url: Source URL
        max_title_len: Max characters for title truncation

    Returns:
        Markdown formatted link string: "[1] [Title...](url)"
    """
    truncated_title = title[:max_title_len]
    if len(title) > max_title_len:
        truncated_title += "..."
    return f"[{number}] [{truncated_title}]({url})"


def get_source_type_badge(url: str) -> Dict[str, str]:
    """
    Determine source type from URL and return badge info.

    Per PRD §5.10 Demo Polish Pack - Source quality badges.

    Args:
        url: The source URL

    Returns:
        Dict with 'type', 'label', 'color' keys
    """
    url_lower = url.lower()

    # Documentation sites
    docs_patterns = [
        "docs.", "documentation", ".readthedocs", "developer.", "api.",
        "wiki.", "manual.", "/docs/", "/guide/", "/reference/"
    ]
    for pattern in docs_patterns:
        if pattern in url_lower:
            return {"type": "docs", "label": "📚 Docs", "color": "#198754"}

    # Official sources
    official_patterns = [".gov", ".edu", ".org"]
    for pattern in official_patterns:
        if pattern in url_lower:
            return {"type": "official", "label": "✓ Official", "color": "#0066CC"}

    # News sites
    news_patterns = [
        "news.", "bbc.", "cnn.", "reuters.", "nytimes.", "washingtonpost.",
        "techcrunch.", "theverge.", "arstechnica.", "/news/"
    ]
    for pattern in news_patterns:
        if pattern in url_lower:
            return {"type": "news", "label": "📰 News", "color": "#6C757D"}

    # Blog patterns
    blog_patterns = [
        "blog.", "medium.com", "dev.to", "hashnode.", "/blog/", "/posts/",
        "substack.", "wordpress."
    ]
    for pattern in blog_patterns:
        if pattern in url_lower:
            return {"type": "blog", "label": "✍️ Blog", "color": "#FFC107"}

    # GitHub/code
    code_patterns = ["github.com", "gitlab.com", "stackoverflow.com", "stackexchange."]
    for pattern in code_patterns:
        if pattern in url_lower:
            return {"type": "code", "label": "💻 Code", "color": "#6F42C1"}

    # Default
    return {"type": "web", "label": "🌐 Web", "color": "#6C757D"}


def render_source_card(
    number: int,
    title: str,
    url: str,
    snippet: str = "",
    show_badge: bool = True
) -> None:
    """Render a source citation card with quality badge."""
    # Get source type badge
    badge = get_source_type_badge(url) if show_badge else None

    badge_html = ""
    if badge:
        badge_html = f"""
            <span style="
                background: {badge['color']}20;
                color: {badge['color']};
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                margin-left: 8px;
            ">{badge['label']}</span>
        """

    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid #E9ECEF;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                background: #F8F9FA;
            ">
                <div style="font-weight: 600; color: #0066CC;">
                    [{number}] {title[:60]}{'...' if len(title) > 60 else ''}
                    {badge_html}
                </div>
                <div style="font-size: 12px; color: #6C757D; margin-top: 4px;">
                    <a href="{url}" target="_blank" style="color: #0066CC;">{url[:50]}{'...' if len(url) > 50 else ''}</a>
                </div>
                {f'<div style="font-size: 14px; margin-top: 8px; color: #1A1A1A;">{snippet[:150]}...</div>' if snippet else ''}
            </div>
            """,
            unsafe_allow_html=True
        )


def render_sources_section(sources: List[Dict[str, str]], show_compare: bool = True) -> None:
    """Render the sources section with optional comparison view."""
    if not sources:
        return

    st.markdown("### 📚 Sources")
    for i, source in enumerate(sources, 1):
        render_source_card(
            number=i,
            title=source.get("title", "Untitled"),
            url=source.get("url", ""),
            snippet=source.get("snippet", "")
        )

    # Compare sources view (PRD §5.10 Demo Polish Pack)
    if show_compare and len(sources) > 1:
        render_source_comparison(sources)


def render_source_comparison(sources: List[Dict[str, str]]) -> None:
    """
    Render a collapsible source comparison view.

    Per PRD §5.10 Demo Polish Pack - Compare sources (collapsed bullets per source).

    Args:
        sources: List of source dicts with url, title, snippet keys
    """
    if len(sources) < 2:
        return

    with st.expander("📊 **Compare Sources**", expanded=False):
        st.markdown(
            """
            <style>
            .compare-source {
                border-left: 3px solid #0066CC;
                padding-left: 12px;
                margin-bottom: 16px;
            }
            .compare-title {
                font-weight: 600;
                color: #1A1A1A;
                font-size: 14px;
                margin-bottom: 4px;
            }
            .compare-type {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                margin-left: 8px;
            }
            .compare-snippet {
                color: #6C757D;
                font-size: 13px;
                margin-top: 4px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Create columns for side-by-side view (max 3 columns)
        num_cols = min(len(sources), 3)
        cols = st.columns(num_cols)

        for i, (col, source) in enumerate(zip(cols, sources[:3])):
            with col:
                badge = get_source_type_badge(source.get("url", ""))
                title = source.get("title", "Untitled")[:40]
                snippet = source.get("snippet", "No preview available")[:100]
                url = source.get("url", "")

                st.markdown(
                    f"""
                    <div class="compare-source">
                        <div class="compare-title">
                            [{i+1}] {title}...
                            <span class="compare-type" style="background: {badge['color']}20; color: {badge['color']};">
                                {badge['label']}
                            </span>
                        </div>
                        <div class="compare-snippet">{snippet}...</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # If more than 3 sources, show note
        if len(sources) > 3:
            st.caption(f"_+ {len(sources) - 3} more sources_")


def render_note_card(
    note_id: str,
    title: str,
    tags: List[str],
    created_at: str,
    snippet: str = "",
    on_click: Optional[callable] = None
) -> None:
    """Render a note preview card."""
    with st.container():
        cols = st.columns([0.8, 0.2])

        with cols[0]:
            st.markdown(f"**{title}**")
            if tags:
                st.markdown(render_tags(tags, max_tags=3), unsafe_allow_html=True)
            if snippet:
                st.caption(snippet)
            st.caption(created_at[:10])

        with cols[1]:
            if st.button("View", key=f"view_{note_id}"):
                if on_click:
                    on_click(note_id)


def render_error_message(
    message: str,
    suggestion: str = "",
    error_code: str = "",
    recovery_steps: List[str] = None,
    title: str = "Error"
) -> None:
    """
    Render an error message with recovery steps.

    Per PRD §6 - Every error has: title, message, suggestion, recovery steps.

    Args:
        message: The error message
        suggestion: A brief suggestion
        error_code: Machine-readable error code
        recovery_steps: List of recovery steps to try
        title: Error title
    """
    # Error container with styling
    st.markdown(
        f"""
        <div style="
            background: #FDF2F2;
            border: 1px solid #DC3545;
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
        ">
            <div style="color: #DC3545; font-weight: 600; margin-bottom: 8px;">
                ❌ {title}
            </div>
            <div style="color: #1A1A1A; margin-bottom: 8px;">
                {message}
            </div>
            {f'<div style="color: #6C757D; font-size: 12px;">Error code: <code>{error_code}</code></div>' if error_code else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

    if suggestion:
        st.info(f"💡 **Suggestion:** {suggestion}")

    # Recovery steps in expander (PRD §6)
    if recovery_steps:
        with st.expander("🔧 **Recovery Steps**", expanded=False):
            for i, step in enumerate(recovery_steps, 1):
                st.markdown(f"{i}. {step}")


def get_error_recovery_steps(error_code: str) -> List[str]:
    """
    Get recovery steps for a given error code.

    Per PRD §6 - Errors guide recovery.

    Args:
        error_code: The error code

    Returns:
        List of recovery steps
    """
    recovery_map = {
        "ollama_unavailable": [
            "Check if Ollama is running: `ollama list`",
            "Start Ollama service: `ollama serve`",
            "Verify the model is installed: `ollama pull ministral-3:8b`"
        ],
        "mcp_server_unavailable": [
            "Check if MCP server is running",
            "Start the MCP server: `cd mcp_server && npm start`",
            "Verify port 3001 is not in use"
        ],
        "search_failed": [
            "Check your internet connection",
            "Try a different search query",
            "Wait a moment and retry"
        ],
        "fetch_timeout": [
            "The page took too long to load",
            "Try fetching a different URL",
            "Check if the site is accessible in your browser"
        ],
        "fetch_failed": [
            "The URL could not be reached",
            "Verify the URL is correct",
            "Check if the site requires authentication"
        ],
        "note_not_found": [
            "The note may have been deleted",
            "Search for the note by title",
            "Check the notes list in the sidebar"
        ],
        "validation_error": [
            "Check the input format",
            "Ensure required fields are filled",
            "Review the error message for specifics"
        ],
        "rate_limited": [
            "Wait a moment before trying again",
            "Reduce the frequency of requests",
            "Consider using a different search provider"
        ]
    }

    return recovery_map.get(error_code, [
        "Try refreshing the page",
        "Check if all services are running",
        "Review the error message for details"
    ])


def render_loading_state(message: str = "Researching...") -> None:
    """Render a loading state indicator."""
    with st.spinner(message):
        st.empty()


def render_confidence_meter(source_count: int, max_sources: int = 5) -> None:
    """Render a confidence meter based on source count."""
    confidence = min(source_count / max_sources, 1.0)

    if confidence >= 0.8:
        color = "green"
        label = "High confidence"
    elif confidence >= 0.4:
        color = "orange"
        label = "Moderate confidence"
    else:
        color = "red"
        label = "Low confidence"

    st.progress(confidence)
    st.caption(f":{color}[{label}] ({source_count} sources)")


def render_save_note_dialog(
    prefill_title: str = "",
    prefill_content: str = "",
    prefill_tags: List[str] = None,
    source_urls: List[str] = None
) -> Optional[Dict[str, Any]]:
    """Render the save note dialog and return note data if submitted."""
    with st.form("save_note_form"):
        st.markdown("### 📝 Save as Note")

        title = st.text_input("Title", value=prefill_title)
        content = st.text_area("Content", value=prefill_content, height=200)
        tags_input = st.text_input(
            "Tags (comma-separated)",
            value=", ".join(prefill_tags or [])
        )

        if source_urls:
            st.markdown("**Attached Sources:**")
            for url in source_urls[:5]:
                st.caption(f"• {url[:50]}...")

        submitted = st.form_submit_button("Save Note", type="primary")

        if submitted and title and content:
            tags = [t.strip().lower() for t in tags_input.split(",") if t.strip()]
            return {
                "title": title,
                "content": content,
                "tags": tags,
                "source_urls": source_urls or []
            }

    return None


def render_content_with_citations(
    content: str,
    sources: List[Dict[str, str]]
) -> str:
    """
    Convert inline citations [1], [2] to clickable links.

    Per PRD §5.10 - Inline numbered citations linking to Sources.

    Args:
        content: The response content with [1], [2], etc.
        sources: List of source dicts with 'url' and 'title' keys

    Returns:
        HTML content with citations as clickable superscript links
    """
    if not content:
        return ""

    if not sources:
        return content

    # Pattern to match citation numbers like [1], [2], etc.
    citation_pattern = re.compile(r'\[(\d+)\]')

    def replace_citation(match):
        num = int(match.group(1))
        if 1 <= num <= len(sources):
            source = sources[num - 1]
            url = source.get('url', '')
            title = source.get('title', f'Source {num}')
            # Escape title for HTML attribute
            import html
            escaped_title = html.escape(title, quote=True)
            # Create a superscript link
            return f'<a href="{url}" target="_blank" title="{escaped_title}" style="color: #0066CC; text-decoration: none; font-size: 0.75em; vertical-align: super;">[{num}]</a>'
        return match.group(0)  # Return unchanged if no matching source

    return citation_pattern.sub(replace_citation, content)


def render_followup_chips(
    suggestions: List[str],
    key_prefix: str = "followup"
) -> Optional[str]:
    """
    Render follow-up question suggestion chips.

    Per PRD §5.10 Demo Polish Pack - 3 suggested follow-up questions.

    Args:
        suggestions: List of suggested follow-up questions
        key_prefix: Unique prefix for button keys

    Returns:
        The selected suggestion text if clicked, None otherwise
    """
    if not suggestions:
        return None

    st.markdown(
        """
        <style>
        .followup-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
            margin-bottom: 8px;
        }
        .followup-chip {
            background: #E7F1FF;
            color: #0066CC;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 13px;
            cursor: pointer;
            border: 1px solid #0066CC20;
            transition: background 0.2s;
        }
        .followup-chip:hover {
            background: #D0E4FF;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.caption("💡 **Suggested follow-ups:**")
    cols = st.columns(len(suggestions[:3]))  # Max 3 suggestions

    selected = None
    for i, (col, suggestion) in enumerate(zip(cols, suggestions[:3])):
        with col:
            # Truncate long suggestions for display
            display_text = suggestion[:40] + "..." if len(suggestion) > 40 else suggestion
            if st.button(display_text, key=f"{key_prefix}_{i}", help=suggestion):
                selected = suggestion

    return selected


def generate_followup_suggestions(
    query: str,
    response_content: str,
    sources: List[Dict[str, str]] = None
) -> List[str]:
    """
    Generate follow-up question suggestions based on query and response.

    DEPRECATED: This rule-based function is superseded by LLM-generated follow-ups
    in src/agent/orchestrator.py:_generate_followup_questions().
    Use ResearchResponse.followup_questions instead.

    Kept for backward compatibility only.

    Args:
        query: Original user query
        response_content: The research response content (unused in rule-based)
        sources: List of sources used

    Returns:
        List of 3 suggested follow-up questions
    """
    suggestions = []

    # Extract key topic from query
    query_lower = query.lower()

    # Pattern-based suggestions
    if "what is" in query_lower or "what are" in query_lower:
        topic = query.replace("what is", "").replace("what are", "").strip("? ")
        suggestions.append(f"How does {topic} work in practice?")
        suggestions.append(f"What are the pros and cons of {topic}?")
        suggestions.append(f"Compare {topic} with alternatives")
    elif "how to" in query_lower or "how do" in query_lower:
        suggestions.append("What are common mistakes to avoid?")
        suggestions.append("Are there any best practices?")
        suggestions.append("What tools or resources can help?")
    elif "why" in query_lower:
        suggestions.append("What are the implications?")
        suggestions.append("How has this changed over time?")
        suggestions.append("What do experts say about this?")
    else:
        # Generic follow-ups based on having sources
        if sources and len(sources) > 1:
            suggestions.append("Can you compare these sources?")
        suggestions.append("What are the key takeaways?")
        suggestions.append("Are there any recent developments?")
        suggestions.append("What should I know next?")

    # Ensure we have exactly 3 unique suggestions
    return list(dict.fromkeys(suggestions))[:3]


def render_research_trail(
    query_groups: List[Dict[str, Any]],
    expanded: bool = False,
    mcp_endpoint: str = "http://localhost:3001"
) -> None:
    """
    Render the Research Trail panel - a timeline of MCP tool executions.

    Per PRD §5.10 Demo Polish Pack - shows tool activity timeline.
    Enhanced to clearly demonstrate MCP server integration.
    Supports multiple query groups (last N queries).

    Args:
        query_groups: List of dicts with 'query' and 'traces' keys (most recent first)
        expanded: Whether to expand by default
        mcp_endpoint: The MCP server endpoint URL
    """
    if not query_groups:
        return

    # Calculate total stats across all queries
    all_traces = []
    for group in query_groups:
        all_traces.extend(group.get("traces", []))

    total_calls = len(all_traces)
    successful_calls = sum(1 for t in all_traces if t.get("success", True))
    total_duration = sum(t.get("duration_ms", 0) for t in all_traces)
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

    num_queries = len(query_groups)
    title_suffix = f"from {num_queries} {'query' if num_queries == 1 else 'queries'}"

    with st.expander(f"🔬 Research Trail ({total_calls} MCP calls {title_suffix})", expanded=expanded):
        # MCP Server Header using Streamlit native components
        st.markdown("##### 🖥️ MCP Server Connection")

        # Server info in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Queries", num_queries)
        with col2:
            st.metric("Tool Calls", total_calls)
        with col3:
            st.metric("Success Rate", f"{success_rate:.0f}%")
        with col4:
            st.metric("Total Time", f"{total_duration:.0f}ms")

        # Endpoint info
        st.code(f"MCP Endpoint: {mcp_endpoint}/mcp\nProtocol: JSON-RPC 2.0", language="text")

        st.markdown("---")

        # Render each query group
        for group_idx, group in enumerate(query_groups):
            query = group.get("query", "Unknown query")
            traces = group.get("traces", [])

            # Truncate query for display
            display_query = query[:80] + "..." if len(query) > 80 else query

            # Query header with recency indicator
            recency = "🔵 Latest" if group_idx == 0 else f"⚪ Query {group_idx + 1}"
            st.markdown(f"##### {recency}")
            st.info(f"**Query:** {display_query}")

            # Query-specific stats
            q_calls = len(traces)
            q_success = sum(1 for t in traces if t.get("success", True))
            q_duration = sum(t.get("duration_ms", 0) for t in traces)

            st.caption(f"📊 {q_calls} calls | ✅ {q_success} success | ⏱️ {q_duration:.0f}ms")

            # Handle queries with no tool calls
            if not traces:
                st.caption("💬 _Answered from context/knowledge (no MCP tools used)_")
                if group_idx < len(query_groups) - 1:
                    st.markdown("---")
                continue

            # Tool call timeline for this query
            for i, trace in enumerate(traces):
                tool_name = trace.get("tool_name", "unknown")
                success = trace.get("success", True)
                duration = trace.get("duration_ms", 0)
                result_summary = trace.get("result_summary", "")
                request_id = trace.get("request_id", f"req_{i+1}")

                # Status indicator
                status_icon = "✅" if success else "❌"

                # Tool-specific icon
                tool_icons = {
                    "web_search": "🔍",
                    "fetch_page": "📄",
                    "save_note": "💾",
                    "list_notes": "📝",
                    "get_note": "📖"
                }
                tool_icon = tool_icons.get(tool_name, "⚙️")

                # Use columns for clean layout
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{status_icon} {tool_icon} **{tool_name}** `MCP TOOL`")
                    if result_summary:
                        st.caption(result_summary[:100] + ("..." if len(result_summary) > 100 else ""))
                    st.caption(f"`request_id: {request_id}`")
                with col2:
                    if success:
                        st.success(f"{duration:.0f}ms")
                    else:
                        st.error(f"{duration:.0f}ms")

                # Show arguments on click
                with st.expander(f"Show request details", expanded=False):
                    args = trace.get("arguments", {})
                    st.markdown("**MCP Request Payload:**")
                    st.json({
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": args
                        },
                        "id": request_id
                    })

            # Separator between query groups
            if group_idx < len(query_groups) - 1:
                st.markdown("---")


def render_chat_message(
    role: str,
    content: str,
    sources: List[Dict[str, str]] = None,
    show_sources: bool = True,
    sources_title: str = "📚 Sources",
    show_save_button: bool = False,
    save_button_label: str = "💾 Save as Note",
    save_button_key: Optional[str] = None,
    save_button_disabled: bool = False,
) -> bool:
    """
    Render a chat message with optional sources and save button.

    Returns True if save button clicked, False otherwise
    """
    with st.chat_message(role):
        # Render content with clickable inline citations if sources exist
        if content and content.strip():
            if sources and role == "assistant":
                rendered_content = render_content_with_citations(content, sources)
                st.markdown(rendered_content, unsafe_allow_html=True)
            else:
                st.markdown(content)
        elif role == "assistant":
            # Handle empty content case - show placeholder
            st.markdown("*Research completed but no summary was generated. Check the sources below.*")

        if sources and show_sources:
            with st.expander(sources_title, expanded=False):
                for i, source in enumerate(sources, 1):
                    st.markdown(format_source_link(
                        i, source.get('title', 'Link'), source.get('url', '')
                    ))

        if show_save_button and role == "assistant":
            key = save_button_key or f"save_{id(content)}"
            if st.button(save_button_label, key=key, disabled=save_button_disabled):
                return True

    return False


def render_how_it_works() -> None:
    """
    Render the 'How It Works' tab content.

    Provides a condensed overview of the Research Copilot architecture
    and key concepts for users to understand the system.
    """
    st.header("How It Works")
    st.markdown("Research Copilot is a **local AI research assistant** that demonstrates modern AI agent architecture patterns.")

    # Architecture Overview
    st.subheader("Architecture Overview")

    # Visual diagram using columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**You**")
        st.markdown("Ask a question")
        st.markdown(":arrow_down:")
    with col2:
        st.markdown("**AI Agent**")
        st.markdown("Decides what tools to use")
        st.markdown(":arrows_counterclockwise:")
    with col3:
        st.markdown("**Tools (MCP)**")
        st.markdown("Search, fetch, save notes")
        st.markdown(":arrow_down:")

    st.info("The AI agent loops: **Ask LLM** :arrow_right: **Execute Tools** :arrow_right: **Feed Results Back** :arrow_right: **Repeat until answer ready**")

    st.divider()

    # Key Concepts
    st.subheader("Key Concepts")

    with st.expander("**1. AI Agent with Tool Calling**", expanded=True):
        st.markdown("""
Unlike simple chatbots that only generate text, Research Copilot is an **AI agent** that can take actions.

The LLM decides *when* and *which* tools to use based on your question:
- "What is quantum computing?" :arrow_right: Web search + page fetch
- "Summarize this URL" :arrow_right: Page fetch only
- "Find my notes about AI" :arrow_right: Notes search
        """)

    with st.expander("**2. Model Context Protocol (MCP)**"):
        st.markdown("""
MCP is a standardized way for AI agents to access tools. Think of it as a **"USB for AI tools"**:

- **Standardized Interface**: Any MCP tool works with any MCP agent
- **JSON-RPC 2.0**: Industry-standard protocol
- **Tool Discovery**: Agents can query available tools dynamically
        """)

        st.code("""
Agent                    MCP Server
  │                         │
  ├── web_search ──────────►│ Execute search
  │◄── results ─────────────┤
  │                         │
  ├── fetch_page ──────────►│ Read URL content
  │◄── page content ────────┤
        """, language="text")

    with st.expander("**3. Local-First Architecture**"):
        st.markdown("""
**Everything runs on your machine:**

| Component | Location | Purpose |
|-----------|----------|---------|
| Ollama | Local | LLM inference (no cloud AI) |
| MCP Server | Local | Tool execution |
| SQLite | Local | Notes storage |
| Streamlit | Local | User interface |

**Only external calls**: Web search API and fetching web pages (visible in Research Trail)
        """)

    with st.expander("**4. Transparency Through Traceability**"):
        st.markdown("""
Every action is visible to build trust:

- **Research Trail**: Shows all MCP tool calls with timing
- **Source Citations**: Inline numbered references [1], [2], [3]
- **Tool Arguments**: Expandable details for each call

You can verify *exactly* what the AI did to answer your question.
        """)

    st.divider()

    # Available Tools
    st.subheader("Available MCP Tools")

    tools_col1, tools_col2 = st.columns(2)

    with tools_col1:
        st.markdown("**:mag: web_search**")
        st.caption("Search the web using Serper API or DuckDuckGo")

        st.markdown("**:page_facing_up: fetch_page**")
        st.caption("Read and extract content from URLs")

        st.markdown("**:floppy_disk: save_note**")
        st.caption("Save research findings for later")

    with tools_col2:
        st.markdown("**:scroll: list_notes**")
        st.caption("Search saved notes with full-text search")

        st.markdown("**:bookmark: get_note**")
        st.caption("Retrieve a specific note by ID")

    st.divider()

    # API Design
    st.subheader("API Design")

    st.markdown("The system uses a **layered API architecture** with consistent patterns across all services.")

    with st.expander("**API Response Pattern (Stripe-style)**", expanded=False):
        st.markdown("""
Every API response follows a consistent, predictable structure:

```python
{
    "success": True,        # Did it work?
    "data": {...},          # Payload (null on error)
    "error": None,          # Error details (null on success)
    "meta": {
        "request_id": "abc123",
        "duration_ms": 245
    }
}
```

**Benefits:**
- Never guess if something worked
- Rich metadata for debugging
- Errors include recovery suggestions
        """)

    with st.expander("**Python Client Layer**", expanded=False):
        st.markdown("""
Two main clients communicate with backend services:

**OllamaClient** - Local LLM inference
```python
client = OllamaClient()
health = await client.health()      # Check availability
response = await client.chat(...)   # Generate response
```

**MCPClient** - Tool execution via MCP
```python
client = MCPClient()
result = await client.web_search("AI news", limit=5)
page = await client.fetch_page("https://example.com")
note = await client.save_note("Title", "Content", tags=["ai"])
```
        """)

    with st.expander("**MCP Server Protocol (JSON-RPC 2.0)**", expanded=False):
        st.markdown("**Endpoint:** `POST /mcp`")

        st.markdown("**Request:**")
        st.code("""{
    "jsonrpc": "2.0",
    "id": "req_123",
    "method": "tools/call",
    "params": {
        "name": "web_search",
        "arguments": {"query": "quantum computing"}
    }
}""", language="json")

        st.markdown("**Response:**")
        st.code("""{
    "jsonrpc": "2.0",
    "id": "req_123",
    "result": {
        "content": [{"type": "text", "text": "..."}]
    }
}""", language="json")

    with st.expander("**Request Tracing**", expanded=False):
        st.markdown("""
Every request is traceable through the entire system:

```
User Query: "What is quantum computing?"
    │
    ├── request_id: "req_abc123"
    │
    ├── Tool 1: web_search (712ms)
    │   └── mcp_request_id: "mcp_1"
    │
    ├── Tool 2: fetch_page (523ms)
    │   └── mcp_request_id: "mcp_2"
    │
    └── Total: 2847ms, 5 sources cited
```

This enables the **Research Trail** panel to show exactly what happened.
        """)

    with st.expander("**Error Handling**", expanded=False):
        st.markdown("""
Errors are designed to be **actionable**:

```python
{
    "code": "search_failed",
    "type": "tool_error",
    "message": "Web search failed",
    "suggestion": "Check internet connection"
}
```

| Error Type | Description |
|------------|-------------|
| `service_error` | External service unavailable |
| `tool_error` | Tool execution failed |
| `validation_error` | Invalid input |
| `not_found` | Resource doesn't exist |
        """)

    st.divider()

    # Research Modes
    st.subheader("Research Modes")

    mode_col1, mode_col2 = st.columns(2)

    with mode_col1:
        st.markdown("**Quick Summary**")
        st.markdown("- 5 search results max")
        st.markdown("- 3 pages fetched")
        st.markdown("- Fast answers")

    with mode_col2:
        st.markdown("**Deep Dive**")
        st.markdown("- 7 search results max")
        st.markdown("- 5 pages fetched")
        st.markdown("- Thorough research")

    st.divider()

    # Why This Matters
    st.subheader("Why This Architecture?")

    why_col1, why_col2 = st.columns(2)

    with why_col1:
        st.markdown("**:jigsaw: Modular**")
        st.caption("Each component has a single responsibility")

        st.markdown("**:lock: Private**")
        st.caption("No data sent to cloud AI services")

    with why_col2:
        st.markdown("**:electric_plug: Extensible**")
        st.caption("Add new tools without changing the agent")

        st.markdown("**:eyes: Transparent**")
        st.caption("Every action is visible and verifiable")

    st.divider()

    # Learn More
    st.subheader("Learn More")
    st.markdown("""
- [MCP Specification](https://modelcontextprotocol.io) - Official MCP documentation
- [Ollama](https://ollama.ai) - Local LLM runtime
- [Full Technical Documentation](https://github.com/shrimpy8/research-copilot/blob/main/docs/HOW_IT_WORKS.md) - Detailed architecture guide
    """)
