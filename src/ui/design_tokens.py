"""
Design tokens for Research Copilot UI.

Centralized design values per PRD §7 and CLAUDE.md.
Use these constants throughout the UI for consistency.
"""


class Colors:
    """Color palette from PRD Design Tokens."""
    # Backgrounds
    BACKGROUND_PRIMARY = "#FFFFFF"
    BACKGROUND_SECONDARY = "#F8F9FA"

    # Text
    TEXT_PRIMARY = "#1A1A1A"
    TEXT_SECONDARY = "#6C757D"

    # Accent colors
    ACCENT = "#0066CC"
    ERROR = "#DC3545"
    SUCCESS = "#198754"
    WARNING = "#FFC107"

    # UI elements
    BORDER = "#E9ECEF"
    SOURCE_PILL = "#E7F1FF"
    TAG_BACKGROUND = "#E7F1FF"
    TAG_COLOR = "#0066CC"

    # Code badge colors
    CODE_PURPLE = "#6F42C1"

    # Error backgrounds
    ERROR_BACKGROUND = "#FDF2F2"


class Spacing:
    """Spacing values from PRD Design Tokens."""
    # Tight
    TIGHT_SM = "4px"
    TIGHT_MD = "8px"

    # Normal
    NORMAL_SM = "12px"
    NORMAL_MD = "16px"

    # Loose
    LOOSE_SM = "24px"
    LOOSE_MD = "32px"


class Typography:
    """Typography values from PRD Design Tokens."""
    BODY_SIZE = "16px"
    BODY_WEIGHT = "400"
    SMALL_SIZE = "14px"
    TINY_SIZE = "12px"
    MONO_SIZE = "13px"

    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif"


class BorderRadius:
    """Border radius values."""
    SMALL = "4px"
    MEDIUM = "8px"
    PILL = "12px"
    LARGE = "16px"


# CSS Helpers
def card_style(
    background: str = Colors.BACKGROUND_SECONDARY,
    border_color: str = Colors.BORDER
) -> str:
    """Generate card styling."""
    return f"""
        border: 1px solid {border_color};
        border-radius: {BorderRadius.MEDIUM};
        padding: {Spacing.NORMAL_SM};
        margin: {Spacing.TIGHT_MD} 0;
        background: {background};
    """


def tag_style(
    background: str = Colors.TAG_BACKGROUND,
    color: str = Colors.TAG_COLOR
) -> str:
    """Generate tag pill styling."""
    return f"""
        background: {background};
        padding: 2px 8px;
        border-radius: {BorderRadius.PILL};
        font-size: {Typography.TINY_SIZE};
        margin-right: {Spacing.TIGHT_SM};
        color: {color};
    """


def badge_style(color: str) -> str:
    """Generate badge styling with given color."""
    return f"""
        background: {color}20;
        color: {color};
        padding: 2px 8px;
        border-radius: {BorderRadius.PILL};
        font-size: 11px;
        margin-left: {Spacing.TIGHT_MD};
    """


# Source type badge configurations
SOURCE_BADGES = {
    "docs": {"label": "📚 Docs", "color": Colors.SUCCESS},
    "official": {"label": "✓ Official", "color": Colors.ACCENT},
    "news": {"label": "📰 News", "color": Colors.TEXT_SECONDARY},
    "blog": {"label": "✍️ Blog", "color": Colors.WARNING},
    "code": {"label": "💻 Code", "color": Colors.CODE_PURPLE},
    "web": {"label": "🌐 Web", "color": Colors.TEXT_SECONDARY},
}


# Tool icon mapping
TOOL_ICONS = {
    "web_search": "🔍",
    "fetch_page": "📄",
    "save_note": "💾",
    "list_notes": "📝",
    "get_note": "📖",
}
