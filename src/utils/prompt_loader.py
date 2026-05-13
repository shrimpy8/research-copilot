"""
Shared prompt file loader for Research Copilot.

Single source of truth for loading prompt files from the prompts/ directory.
Used by both src/agent/prompts.py and src/models/research_mode.py.
"""

import logging
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_log = logging.getLogger("research_copilot")


@lru_cache(maxsize=20)
def load_prompt_file(filename: str, *, raise_on_missing: bool = False) -> str:
    """
    Load a prompt file from the prompts directory. Result is cached.

    Args:
        filename: Filename within the prompts/ directory
        raise_on_missing: If True, raises FileNotFoundError when file is absent.
                          If False (default), logs a warning and returns "".

    Returns:
        File contents stripped of leading/trailing whitespace, or "" if missing
        and raise_on_missing is False.
    """
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    if raise_on_missing:
        raise FileNotFoundError(f"Prompt file not found: {filepath}")
    _log.warning("Prompt file not found: %s, using empty prompt", filepath)
    return ""
