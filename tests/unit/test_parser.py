"""Tests for the tool call parser."""

import pytest
from src.agent.parser import (
    parse_tool_calls,
    ToolCall,
    has_tool_call,
    extract_text_content,
    split_at_tool_call,
    is_waiting_for_tool_call,
)


class TestParseToolCalls:
    """Tests for parse_tool_calls function."""

    def test_no_tool_calls(self):
        """Should handle text without tool calls."""
        text = "This is a regular response without any tool calls."
        result = parse_tool_calls(text)

        assert len(result.tool_calls) == 0
        assert result.text_before == text
        assert result.text_after == ""
        assert not result.has_incomplete

    def test_single_tool_call(self):
        """Should parse a single tool call."""
        text = '''Here's my response.
<tool_call>
{"name": "web_search", "arguments": {"query": "test query"}}
</tool_call>
After the tool call.'''

        result = parse_tool_calls(text)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "web_search"
        assert result.tool_calls[0].arguments == {"query": "test query"}
        assert "Here's my response" in result.text_before
        assert "After the tool call" in result.text_after

    def test_multiple_tool_calls(self):
        """Should parse multiple tool calls."""
        text = '''Let me search for that.
<tool_call>
{"name": "web_search", "arguments": {"query": "first query"}}
</tool_call>
Now let me fetch a page.
<tool_call>
{"name": "fetch_page", "arguments": {"url": "https://example.com"}}
</tool_call>
Done.'''

        result = parse_tool_calls(text)

        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "web_search"
        assert result.tool_calls[1].name == "fetch_page"

    def test_incomplete_tool_call(self):
        """Should detect incomplete tool calls (streaming scenario)."""
        text = '''Starting to respond...
<tool_call>
{"name": "web_search", "arguments": {"query": "test'''

        result = parse_tool_calls(text)

        assert len(result.tool_calls) == 0
        assert result.has_incomplete
        assert "Starting to respond" in result.text_before

    def test_tool_call_with_complex_arguments(self):
        """Should handle complex nested arguments."""
        text = '''<tool_call>
{"name": "save_note", "arguments": {"title": "Test", "content": "Content here", "tags": ["tag1", "tag2"], "source_urls": ["https://example.com"]}}
</tool_call>'''

        result = parse_tool_calls(text)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].arguments["tags"] == ["tag1", "tag2"]
        assert result.tool_calls[0].arguments["source_urls"] == ["https://example.com"]

    def test_case_insensitive_tags(self):
        """Should handle different case tool_call tags."""
        text = '''<TOOL_CALL>
{"name": "web_search", "arguments": {"query": "test"}}
</TOOL_CALL>'''

        result = parse_tool_calls(text)
        assert len(result.tool_calls) == 1

    def test_malformed_json(self):
        """Should skip malformed JSON tool calls."""
        text = '''<tool_call>
not valid json
</tool_call>
<tool_call>
{"name": "web_search", "arguments": {"query": "test"}}
</tool_call>'''

        result = parse_tool_calls(text)

        # Should only have the valid one
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "web_search"

    def test_missing_name_field(self):
        """Should skip tool calls without name field."""
        text = '''<tool_call>
{"arguments": {"query": "test"}}
</tool_call>'''

        result = parse_tool_calls(text)
        assert len(result.tool_calls) == 0


class TestHasToolCall:
    """Tests for has_tool_call function."""

    def test_with_tool_call(self):
        """Should return True when tool call present."""
        text = '<tool_call>{"name": "test", "arguments": {}}</tool_call>'
        assert has_tool_call(text) is True

    def test_without_tool_call(self):
        """Should return False when no tool call."""
        text = "Just regular text"
        assert has_tool_call(text) is False

    def test_incomplete_tool_call(self):
        """Should return False for incomplete tool call."""
        text = '<tool_call>{"name": "test"'
        assert has_tool_call(text) is False


class TestExtractTextContent:
    """Tests for extract_text_content function."""

    def test_removes_tool_calls(self):
        """Should remove tool calls from text."""
        text = '''Before
<tool_call>
{"name": "test", "arguments": {}}
</tool_call>
After'''

        result = extract_text_content(text)
        assert "Before" in result
        assert "After" in result
        assert "<tool_call>" not in result

    def test_preserves_text(self):
        """Should preserve non-tool-call text."""
        text = "Just regular text here."
        result = extract_text_content(text)
        assert result == text


class TestIsWaitingForToolCall:
    """Tests for is_waiting_for_tool_call function."""

    def test_incomplete_tool_call(self):
        """Should return True for incomplete tool call."""
        text = '<tool_call>{"name":'
        assert is_waiting_for_tool_call(text) is True

    def test_complete_tool_call(self):
        """Should return False for complete tool call."""
        text = '<tool_call>{"name": "test", "arguments": {}}</tool_call>'
        assert is_waiting_for_tool_call(text) is False

    def test_no_tool_call(self):
        """Should return False when no tool call."""
        text = "Regular text"
        assert is_waiting_for_tool_call(text) is False


class TestSplitAtToolCall:
    """Tests for split_at_tool_call function."""

    def test_splits_correctly(self):
        """Should split at first tool call."""
        text = 'Before <tool_call>{"name": "test", "arguments": {}}</tool_call> After'

        before, tool_content, after = split_at_tool_call(text)

        assert before == "Before"
        assert '"name": "test"' in tool_content
        assert after == "After"

    def test_no_tool_call(self):
        """Should return full text when no tool call."""
        text = "Just text"

        before, tool_content, after = split_at_tool_call(text)

        assert before == "Just text"
        assert tool_content is None
        assert after is None
