"""
Streamlit UI components for Research Copilot.

Exports reusable components and design tokens for UI consistency.
"""

from .design_tokens import (
    Colors,
    Spacing,
    Typography,
    BorderRadius,
    card_style,
    tag_style,
    badge_style,
    SOURCE_BADGES,
    TOOL_ICONS,
)

from .components import (
    render_tags,
    format_source_link,
    get_source_type_badge,
    render_source_card,
    render_sources_section,
    render_source_comparison,
    render_note_card,
    render_error_message,
    get_error_recovery_steps,
    render_loading_state,
    render_confidence_meter,
    render_save_note_dialog,
    render_content_with_citations,
    render_followup_chips,
    generate_followup_suggestions,
    render_research_trail,
    render_chat_message,
)

from .state import (
    AppState,
    init_state,
    get_state,
    add_message,
    add_tool_trace,
    set_researching,
    set_error,
    set_current_sources,
    clear_history,
    show_save_dialog,
    hide_save_dialog,
    get_tool_traces,
    set_selected_note,
)

__all__ = [
    # Design tokens
    "Colors",
    "Spacing",
    "Typography",
    "BorderRadius",
    "card_style",
    "tag_style",
    "badge_style",
    "SOURCE_BADGES",
    "TOOL_ICONS",
    # Components
    "render_tags",
    "format_source_link",
    "get_source_type_badge",
    "render_source_card",
    "render_sources_section",
    "render_source_comparison",
    "render_note_card",
    "render_error_message",
    "get_error_recovery_steps",
    "render_loading_state",
    "render_confidence_meter",
    "render_save_note_dialog",
    "render_content_with_citations",
    "render_followup_chips",
    "generate_followup_suggestions",
    "render_research_trail",
    "render_chat_message",
    # State
    "AppState",
    "init_state",
    "get_state",
    "add_message",
    "add_tool_trace",
    "set_researching",
    "set_error",
    "set_current_sources",
    "clear_history",
    "show_save_dialog",
    "hide_save_dialog",
    "get_tool_traces",
    "set_selected_note",
]
