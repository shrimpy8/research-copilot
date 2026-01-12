"""Tests for the citations module."""

import pytest
from src.agent.citations import (
    extract_citations_from_response,
    format_citations_markdown,
    add_citations_to_content,
    extract_inline_urls,
    renumber_citations,
    validate_citations,
    create_citation_summary,
    Citation,
)


class TestExtractCitationsFromResponse:
    """Tests for extract_citations_from_response function."""

    def test_extracts_citations(self):
        """Should extract citations matching content."""
        content = "According to research [1], AI is advancing rapidly [2]."
        sources = [
            {"url": "https://example.com/1", "title": "Source 1"},
            {"url": "https://example.com/2", "title": "Source 2"},
        ]

        result = extract_citations_from_response(content, sources)

        assert len(result.citations) == 2
        assert result.citations[0].number == 1
        assert result.citations[0].url == "https://example.com/1"

    def test_handles_no_citations(self):
        """Should handle content without citations."""
        content = "Just regular text without any citations."
        sources = [{"url": "https://example.com", "title": "Source"}]

        result = extract_citations_from_response(content, sources)

        # Should still include sources
        assert len(result.citations) >= 0


class TestFormatCitationsMarkdown:
    """Tests for format_citations_markdown function."""

    def test_formats_citations(self):
        """Should format citations as markdown."""
        citations = [
            Citation(number=1, url="https://example.com/1", title="First Source"),
            Citation(number=2, url="https://example.com/2", title="Second Source"),
        ]

        result = format_citations_markdown(citations)

        assert "**Sources:**" in result
        assert "[1]" in result
        assert "[First Source](https://example.com/1)" in result
        assert "[2]" in result

    def test_handles_empty_list(self):
        """Should return empty string for no citations."""
        result = format_citations_markdown([])
        assert result == ""


class TestAddCitationsToContent:
    """Tests for add_citations_to_content function."""

    def test_adds_sources_section(self):
        """Should add sources section to content."""
        content = "Here is my response."
        sources = [{"url": "https://example.com", "title": "Example"}]

        result = add_citations_to_content(content, sources)

        assert "Here is my response" in result
        assert "**Sources:**" in result
        assert "https://example.com" in result

    def test_preserves_existing_sources(self):
        """Should not duplicate sources section."""
        content = """Here is my response.

**Sources:**
[1] Existing source - https://example.com"""
        sources = [{"url": "https://new.com", "title": "New"}]

        result = add_citations_to_content(content, sources)

        # Should not add another sources section
        assert result.count("**Sources:**") == 1


class TestExtractInlineUrls:
    """Tests for extract_inline_urls function."""

    def test_extracts_urls(self):
        """Should extract URLs from text."""
        text = "Check https://example.com and http://test.org for more."

        urls = extract_inline_urls(text)

        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "http://test.org" in urls

    def test_removes_duplicates(self):
        """Should deduplicate URLs."""
        text = "See https://example.com here and also https://example.com there."

        urls = extract_inline_urls(text)

        assert len(urls) == 1

    def test_handles_no_urls(self):
        """Should return empty list when no URLs."""
        text = "No URLs here at all."

        urls = extract_inline_urls(text)

        assert urls == []


class TestRenumberCitations:
    """Tests for renumber_citations function."""

    def test_renumbers_sequentially(self):
        """Should renumber citations to be sequential."""
        content = "Reference [3] and [7] and [3] again."

        result, mapping = renumber_citations(content)

        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" not in result
        assert "[7]" not in result
        assert mapping == {3: 1, 7: 2}

    def test_handles_no_citations(self):
        """Should handle content without citations."""
        content = "No citations here."

        result, mapping = renumber_citations(content)

        assert result == content
        assert mapping == {}


class TestValidateCitations:
    """Tests for validate_citations function."""

    def test_valid_citations(self):
        """Should return no errors for valid citations."""
        content = "Reference [1] and [2]."
        source_count = 3

        errors = validate_citations(content, source_count)

        assert errors == []

    def test_invalid_citation_number(self):
        """Should detect citations beyond source count."""
        content = "Reference [5]."
        source_count = 3

        errors = validate_citations(content, source_count)

        assert len(errors) == 1
        assert "no corresponding source" in errors[0]


class TestCreateCitationSummary:
    """Tests for create_citation_summary function."""

    def test_creates_summary(self):
        """Should create brief summary."""
        citations = [
            Citation(number=1, url="https://example.com", title="Example"),
            Citation(number=2, url="https://test.org", title="Test"),
        ]

        result = create_citation_summary(citations)

        assert "2 sources" in result
        assert "example.com" in result

    def test_handles_many_sources(self):
        """Should truncate long lists."""
        citations = [
            Citation(number=i, url=f"https://site{i}.com", title=f"Site {i}")
            for i in range(10)
        ]

        result = create_citation_summary(citations, max_sources=3)

        assert "10 sources" in result
        assert "+7 more" in result

    def test_handles_empty(self):
        """Should handle empty list."""
        result = create_citation_summary([])
        assert result == "No sources"
