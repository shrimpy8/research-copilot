"""
URL and input validation utilities.

Per PRD §10.2 - Provides security validation for URLs to prevent SSRF attacks.
"""

import re
from urllib.parse import urlparse
from typing import Tuple

# Blocked URL schemes per PRD §10.2
BLOCKED_SCHEMES = {'javascript', 'data', 'file', 'ftp'}

# Blocked hosts for security
BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}

# Private IP patterns per PRD §10.2
PRIVATE_IP_PATTERNS = [
    r'^10\.',                          # 10.0.0.0/8
    r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0/12
    r'^192\.168\.',                     # 192.168.0.0/16
    r'^169\.254\.',                     # Link-local
    r'^fc00:',                          # IPv6 unique local
    r'^fe80:',                          # IPv6 link-local
]


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate a URL for safety against SSRF and DNS rebinding attacks.

    Per PRD §10.2 - Security requirements for URL validation.

    Args:
        url: The URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if URL is safe to fetch
        - error_message: Empty string if valid, error description if invalid
    """
    if not url:
        return False, "URL is required"

    try:
        parsed = urlparse(url)

        # Check scheme
        if not parsed.scheme:
            return False, "URL must have a scheme (http or https)"

        if parsed.scheme.lower() not in {'http', 'https'}:
            return False, f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed."

        if parsed.scheme.lower() in BLOCKED_SCHEMES:
            return False, f"URL scheme '{parsed.scheme}' is not allowed"

        # Check host
        host = parsed.hostname or ''
        if not host:
            return False, "URL must have a hostname"

        # Block localhost and loopback
        if host.lower() in BLOCKED_HOSTS:
            return False, "Cannot fetch localhost URLs"

        # Check for private IP ranges
        for pattern in PRIVATE_IP_PATTERNS:
            if re.match(pattern, host, re.IGNORECASE):
                return False, "Cannot fetch private network URLs"

        # Check for numeric IP addresses (additional security)
        if _is_numeric_ip(host):
            # Allow public IPs but be more restrictive
            if _is_private_ip(host):
                return False, "Cannot fetch private IP addresses"

        # Check for suspicious patterns
        if '..' in host or host.startswith('-') or host.endswith('-'):
            return False, "Invalid hostname format"

        return True, ""

    except ValueError as e:
        return False, f"Invalid URL format: {str(e)}"
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def _is_numeric_ip(host: str) -> bool:
    """Check if host is a numeric IP address (v4 or v6)."""
    # IPv4 check
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host):
        return True
    # IPv6 check (simplified)
    if ':' in host and re.match(r'^[0-9a-fA-F:]+$', host.replace('[', '').replace(']', '')):
        return True
    return False


def _is_private_ip(ip: str) -> bool:
    """Check if an IP address is in a private range."""
    for pattern in PRIVATE_IP_PATTERNS:
        if re.match(pattern, ip, re.IGNORECASE):
            return True
    return False


def sanitize_search_query(query: str, max_length: int = 500) -> str:
    """
    Sanitize a search query for safe use.

    Args:
        query: The search query to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized query string
    """
    if not query:
        return ""

    # Remove control characters
    query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)

    # Normalize whitespace
    query = ' '.join(query.split())

    # Truncate to max length
    if len(query) > max_length:
        query = query[:max_length]

    return query.strip()


def validate_note_title(title: str) -> Tuple[bool, str]:
    """
    Validate a note title.

    Per PRD §7.2.3 - Note title max 200 chars.

    Args:
        title: The note title to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not title or not title.strip():
        return False, "Note title is required"

    if len(title) > 200:
        return False, "Note title must be 200 characters or less"

    return True, ""


def validate_note_content(content: str) -> Tuple[bool, str]:
    """
    Validate note content.

    Per PRD §7.2.3 - Note content max 50000 chars.

    Args:
        content: The note content to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Note content is required"

    if len(content) > 50000:
        return False, "Note content must be 50000 characters or less"

    return True, ""


def validate_tags(tags: list) -> Tuple[bool, str]:
    """
    Validate note tags.

    Per PRD §7.2.3 - Max 10 tags, each max 50 chars.

    Args:
        tags: List of tag strings

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tags:
        return True, ""  # Tags are optional

    if len(tags) > 10:
        return False, "Maximum 10 tags allowed"

    for tag in tags:
        if len(tag) > 50:
            return False, f"Tag '{tag[:20]}...' exceeds 50 character limit"

    return True, ""
