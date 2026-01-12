"""
Source citation extraction and formatting.

Extracts citations from LLM responses and formats them for display.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Citation:
    """A citation with number and source information."""
    number: int
    url: str
    title: str
    snippet: str = ""


@dataclass
class CitedContent:
    """Content with inline citations and a sources list."""
    content: str
    citations: List[Citation]


# Patterns for citation extraction
CITATION_PATTERN = re.compile(r'\[(\d+)\]')
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')\]]+',
    re.IGNORECASE
)
SOURCE_BLOCK_PATTERN = re.compile(
    r'\*\*Sources?:?\*\*:?|\*\*Sources?:\*\*',
    re.IGNORECASE
)


def extract_citations_from_response(
    content: str,
    sources: List[Dict[str, str]]
) -> CitedContent:
    """
    Extract and validate citations from an LLM response.

    Args:
        content: The LLM response text
        sources: List of source dicts with 'url' and 'title' keys

    Returns:
        CitedContent with the content and matched citations
    """
    # Find all citation numbers in the content
    citation_numbers = set(int(m.group(1)) for m in CITATION_PATTERN.finditer(content))

    # Build citation list matching numbers to sources
    citations = []
    for i, source in enumerate(sources, 1):
        if i in citation_numbers or not citation_numbers:
            citations.append(Citation(
                number=i,
                url=source.get("url", ""),
                title=source.get("title", ""),
                snippet=source.get("snippet", "")[:200] if source.get("snippet") else ""
            ))

    return CitedContent(
        content=content,
        citations=citations
    )


def format_citations_markdown(citations: List[Citation]) -> str:
    """
    Format citations as a markdown list.

    Args:
        citations: List of Citation objects

    Returns:
        Markdown formatted sources section
    """
    if not citations:
        return ""

    lines = ["", "**Sources:**"]
    for citation in citations:
        if citation.url:
            lines.append(f"[{citation.number}] [{citation.title}]({citation.url})")
        else:
            lines.append(f"[{citation.number}] {citation.title}")

    return "\n".join(lines)


def add_citations_to_content(
    content: str,
    sources: List[Dict[str, str]]
) -> str:
    """
    Add a sources section to content if not already present.

    Args:
        content: The response content
        sources: List of source dicts

    Returns:
        Content with sources section appended
    """
    # Check if content already has a sources section
    if SOURCE_BLOCK_PATTERN.search(content):
        return content

    # Create citations from sources
    citations = [
        Citation(
            number=i,
            url=source.get("url", ""),
            title=source.get("title", source.get("url", "Unknown")),
            snippet=source.get("snippet", "")
        )
        for i, source in enumerate(sources, 1)
    ]

    # Add sources section
    sources_section = format_citations_markdown(citations)
    if sources_section:
        return content.rstrip() + "\n" + sources_section

    return content


def extract_inline_urls(text: str) -> List[str]:
    """
    Extract all URLs from text content.

    Args:
        text: Text that may contain URLs

    Returns:
        List of unique URLs found
    """
    urls = URL_PATTERN.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        # Clean up trailing punctuation
        url = url.rstrip('.,;:!?)')
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def renumber_citations(content: str) -> Tuple[str, Dict[int, int]]:
    """
    Renumber citations to be sequential starting from 1.

    Args:
        content: Content with potentially non-sequential citations

    Returns:
        Tuple of (renumbered content, old->new number mapping)
    """
    # Find all citation numbers
    numbers = sorted(set(int(m.group(1)) for m in CITATION_PATTERN.finditer(content)))

    if not numbers:
        return content, {}

    # Create mapping
    mapping = {old: new for new, old in enumerate(numbers, 1)}

    # Replace citations
    def replace_citation(match):
        old_num = int(match.group(1))
        return f"[{mapping[old_num]}]"

    renumbered = CITATION_PATTERN.sub(replace_citation, content)
    return renumbered, mapping


def validate_citations(content: str, source_count: int) -> List[str]:
    """
    Validate that all citations in content have corresponding sources.

    Args:
        content: The content to validate
        source_count: Number of available sources

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    citation_numbers = set(int(m.group(1)) for m in CITATION_PATTERN.finditer(content))

    for num in citation_numbers:
        if num < 1:
            errors.append(f"Invalid citation number: [{num}]")
        elif num > source_count:
            errors.append(f"Citation [{num}] has no corresponding source (only {source_count} sources available)")

    return errors


def create_citation_summary(
    citations: List[Citation],
    max_sources: int = 5
) -> str:
    """
    Create a brief summary of sources for display.

    Args:
        citations: List of Citation objects
        max_sources: Maximum sources to include

    Returns:
        Brief formatted string of sources
    """
    if not citations:
        return "No sources"

    if len(citations) <= max_sources:
        domains = [_extract_domain(c.url) for c in citations if c.url]
        return f"{len(citations)} sources: " + ", ".join(domains)
    else:
        domains = [_extract_domain(c.url) for c in citations[:max_sources] if c.url]
        return f"{len(citations)} sources: " + ", ".join(domains) + f" (+{len(citations) - max_sources} more)"


def _extract_domain(url: str) -> str:
    """Extract domain from URL for display."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url[:30]
