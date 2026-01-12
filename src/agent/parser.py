"""
Tool call parser for extracting structured tool calls from LLM output.

Parses <tool_call> tags and extracts the tool name and arguments.
"""

import re
import json
from typing import List, Optional, Tuple
from dataclasses import dataclass
from src.errors import ValidationError

# Regex patterns for tool call extraction
TOOL_CALL_PATTERN = re.compile(
    r'<tool_call>\s*(.*?)\s*</tool_call>',
    re.DOTALL | re.IGNORECASE
)

# Pattern to detect incomplete tool calls (streaming)
INCOMPLETE_TOOL_CALL_PATTERN = re.compile(
    r'<tool_call>\s*(?!.*</tool_call>)',
    re.DOTALL | re.IGNORECASE
)


@dataclass
class ToolCall:
    """Represents a parsed tool call."""
    name: str
    arguments: dict
    raw: str  # The raw JSON string for debugging

    def __repr__(self) -> str:
        return f"ToolCall(name={self.name!r}, arguments={self.arguments!r})"


@dataclass
class ParseResult:
    """Result of parsing LLM output for tool calls."""
    tool_calls: List[ToolCall]
    text_before: str  # Text before any tool calls
    text_after: str   # Text after all tool calls
    has_incomplete: bool  # Whether there's an incomplete tool call (streaming)


def parse_tool_calls(text: str) -> ParseResult:
    """
    Parse LLM output to extract tool calls.

    Args:
        text: The raw LLM output text

    Returns:
        ParseResult with extracted tool calls and surrounding text
    """
    tool_calls: List[ToolCall] = []
    matches = list(TOOL_CALL_PATTERN.finditer(text))

    if not matches:
        # Check for incomplete tool call (streaming scenario)
        has_incomplete = bool(INCOMPLETE_TOOL_CALL_PATTERN.search(text))

        # If incomplete, extract text up to the tool_call tag
        if has_incomplete:
            incomplete_match = INCOMPLETE_TOOL_CALL_PATTERN.search(text)
            text_before = text[:incomplete_match.start()] if incomplete_match else text
            return ParseResult(
                tool_calls=[],
                text_before=text_before.strip(),
                text_after="",
                has_incomplete=True
            )

        return ParseResult(
            tool_calls=[],
            text_before=text.strip(),
            text_after="",
            has_incomplete=False
        )

    # Extract text before first match
    first_match = matches[0]
    text_before = text[:first_match.start()].strip()

    # Extract text after last match
    last_match = matches[-1]
    text_after = text[last_match.end():].strip()

    # Check for incomplete tool call after last complete one
    has_incomplete = bool(INCOMPLETE_TOOL_CALL_PATTERN.search(text_after))

    # Parse each tool call
    for match in matches:
        raw_json = match.group(1).strip()
        try:
            tool_call = _parse_single_tool_call(raw_json)
            tool_calls.append(tool_call)
        except (json.JSONDecodeError, ValidationError) as e:
            # Log but continue - don't fail on one bad tool call
            # In production, we might want to include this error in the response
            continue

    return ParseResult(
        tool_calls=tool_calls,
        text_before=text_before,
        text_after=text_after,
        has_incomplete=has_incomplete
    )


def _parse_single_tool_call(raw_json: str) -> ToolCall:
    """
    Parse a single tool call JSON string.

    Args:
        raw_json: The JSON string inside <tool_call> tags

    Returns:
        ToolCall object

    Raises:
        ValidationError: If the JSON is invalid or missing required fields
    """
    # Try to fix common JSON issues
    cleaned_json = _clean_json(raw_json)

    try:
        data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Invalid JSON in tool call: {e}",
            details={"raw": raw_json[:100]}
        )

    # Validate required fields
    if not isinstance(data, dict):
        raise ValidationError(
            "Tool call must be a JSON object",
            details={"type": type(data).__name__}
        )

    name = data.get("name")
    if not name or not isinstance(name, str):
        raise ValidationError(
            "Tool call must have a 'name' field",
            details={"data": str(data)[:100]}
        )

    arguments = data.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ValidationError(
            "Tool call 'arguments' must be an object",
            details={"arguments_type": type(arguments).__name__}
        )

    return ToolCall(
        name=name,
        arguments=arguments,
        raw=raw_json
    )


def _clean_json(raw: str) -> str:
    """
    Clean up common JSON formatting issues from LLM output.

    Args:
        raw: The raw JSON string

    Returns:
        Cleaned JSON string
    """
    # Remove any leading/trailing whitespace
    cleaned = raw.strip()

    # Sometimes LLMs add markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    # Handle single quotes (convert to double quotes for valid JSON)
    # But be careful not to break strings that contain quotes
    # This is a simple heuristic - not perfect but handles common cases
    if "'" in cleaned and '"' not in cleaned:
        cleaned = cleaned.replace("'", '"')

    return cleaned


def extract_text_content(text: str) -> str:
    """
    Extract just the text content, removing all tool call tags.

    Args:
        text: The raw LLM output

    Returns:
        Text with tool calls removed
    """
    # Remove complete tool calls
    result = TOOL_CALL_PATTERN.sub("", text)

    # Remove incomplete tool calls
    result = re.sub(r'<tool_call>.*$', '', result, flags=re.DOTALL)

    # Clean up extra whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def has_tool_call(text: str) -> bool:
    """
    Check if text contains a complete tool call.

    Args:
        text: The LLM output to check

    Returns:
        True if there's at least one complete tool call
    """
    return bool(TOOL_CALL_PATTERN.search(text))


def is_waiting_for_tool_call(text: str) -> bool:
    """
    Check if text has an incomplete tool call (still being generated).

    Args:
        text: The LLM output to check

    Returns:
        True if there's an incomplete tool call tag
    """
    return bool(INCOMPLETE_TOOL_CALL_PATTERN.search(text)) and not bool(TOOL_CALL_PATTERN.search(text))


def split_at_tool_call(text: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Split text at the first tool call.

    Returns:
        Tuple of (text_before, tool_call_content, text_after)
        If no tool call, returns (full_text, None, None)
    """
    match = TOOL_CALL_PATTERN.search(text)
    if not match:
        return (text.strip(), None, None)

    text_before = text[:match.start()].strip()
    tool_call_content = match.group(1).strip()
    text_after = text[match.end():].strip()

    return (text_before, tool_call_content, text_after)
