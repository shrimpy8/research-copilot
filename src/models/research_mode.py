"""
Research mode configuration for Research Copilot.

Single source of truth for research mode definitions per PRD §4.5.2.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ResearchModeConfig:
    """Configuration for a research mode."""
    key: str  # Internal key: "quick" or "deep"
    ui_label: str  # Display label: "Quick Summary" or "Deep Dive"
    search_limit: int  # Max search results
    fetch_limit: int  # Max pages to fetch
    description: str  # Short description
    prompt_context: str  # Instructions for LLM


# Define all research modes in one place
# NOTE: Limits increased from (3,2) to (5,3) for better source coverage per user feedback
QUICK_MODE = ResearchModeConfig(
    key="quick",
    ui_label="Quick Summary",
    search_limit=5,
    fetch_limit=3,
    description="Quick summary with up to 5 sources, bullet points, < 250 words",
    prompt_context="""## Research Mode: Quick Summary
- Search for up to 5 sources
- You MUST fetch and read at least 3 relevant pages before answering
- Provide a concise summary with bullet points
- Keep response under 250 words
- Focus on key facts and main takeaways
- Cite ALL sources you read with numbered citations [1], [2], [3]"""
)

DEEP_MODE = ResearchModeConfig(
    key="deep",
    ui_label="Deep Dive",
    search_limit=7,
    fetch_limit=5,
    description="Deep dive with up to 7 sources, detailed analysis, action items",
    prompt_context="""## Research Mode: Deep Dive
- Search for up to 7 sources
- You MUST fetch and read at least 5 relevant pages before answering
- Provide detailed analysis with supporting evidence from multiple sources
- Include actionable insights and recommendations
- Compare perspectives from different sources
- Cite ALL sources you read with numbered citations [1], [2], [3], etc."""
)

# Lookup dictionaries
RESEARCH_MODES: Dict[str, ResearchModeConfig] = {
    "quick": QUICK_MODE,
    "deep": DEEP_MODE,
}

# For UI dropdowns
RESEARCH_MODE_OPTIONS = [QUICK_MODE.ui_label, DEEP_MODE.ui_label]


def get_mode_by_key(key: str) -> ResearchModeConfig:
    """Get mode config by internal key."""
    return RESEARCH_MODES.get(key, QUICK_MODE)


def get_mode_by_label(label: str) -> ResearchModeConfig:
    """Get mode config by UI label."""
    for mode in RESEARCH_MODES.values():
        if mode.ui_label == label:
            return mode
    return QUICK_MODE


def get_mode_key_from_label(label: str) -> str:
    """Convert UI label to internal key."""
    return get_mode_by_label(label).key
