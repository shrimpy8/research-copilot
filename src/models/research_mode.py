"""
Research mode configuration for Research Copilot.

Single source of truth for research mode definitions per PRD §4.5.2.
Prompts are externalized in prompts/ directory for easy editing.
"""

from dataclasses import dataclass
from typing import Dict
from pathlib import Path
from functools import lru_cache

# Base path for prompt files
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=10)
def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory. Cached for performance."""
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    else:
        # Fallback to empty string if file doesn't exist
        return ""


@dataclass(frozen=True)
class ResearchModeConfig:
    """Configuration for a research mode."""
    key: str  # Internal key: "quick" or "deep"
    ui_label: str  # Display label: "Quick Summary" or "Deep Dive"
    search_limit: int  # Max search results
    fetch_limit: int  # Max pages to fetch
    description: str  # Short description
    prompt_file: str  # Filename for prompt in prompts/ directory

    @property
    def prompt_context(self) -> str:
        """Load prompt context from external file."""
        return _load_prompt_file(self.prompt_file)


# Define all research modes in one place
# NOTE: Limits increased from (3,2) to (5,3) for better source coverage per user feedback
QUICK_MODE = ResearchModeConfig(
    key="quick",
    ui_label="Quick Summary",
    search_limit=5,
    fetch_limit=3,
    description="Quick summary with up to 5 sources, bullet points, < 250 words",
    prompt_file="quick_mode.md"
)

DEEP_MODE = ResearchModeConfig(
    key="deep",
    ui_label="Deep Dive",
    search_limit=7,
    fetch_limit=5,
    description="Deep dive with up to 7 sources, detailed analysis, action items",
    prompt_file="deep_mode.md"
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
