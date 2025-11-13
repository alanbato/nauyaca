"""URL parsing and validation utilities for Gemini protocol.

This module provides functions for parsing, validating, and normalizing
Gemini URLs according to the protocol specification.
"""

from typing import NamedTuple
from urllib.parse import urlparse, urlunparse

from ..protocol.constants import DEFAULT_PORT, MAX_REQUEST_SIZE


class ParsedURL(NamedTuple):
    """Represents a parsed Gemini URL.

    Attributes:
        scheme: URL scheme (should be 'gemini').
        hostname: Server hostname or IP address.
        port: Server port (defaults to 1965 if not specified).
        path: URL path component (defaults to '/' if empty).
        query: URL query string (optional).
        fragment: URL fragment (not used in Gemini, but preserved).
        normalized: The normalized string representation of the URL.
    """

    scheme: str
    hostname: str
    port: int
    path: str
    query: str
    fragment: str
    normalized: str


def parse_url(url: str) -> ParsedURL:
    """Parse and normalize a Gemini URL.

    Args:
        url: A Gemini URL string (e.g., 'gemini://example.com/path').

    Returns:
        A ParsedURL named tuple with all URL components.

    Raises:
        ValueError: If the URL is invalid or malformed.

    Examples:
        >>> parsed = parse_url('gemini://example.com/hello')
        >>> parsed.hostname
        'example.com'
        >>> parsed.port
        1965
        >>> parsed.path
        '/hello'
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Parse the URL
    parsed = urlparse(url)

    # Validate scheme
    if not parsed.scheme:
        raise ValueError(f"URL missing scheme: {url}")

    if parsed.scheme != "gemini":
        raise ValueError(f"Invalid scheme '{parsed.scheme}': expected 'gemini'")

    # Validate hostname
    if not parsed.hostname:
        raise ValueError(f"URL missing hostname: {url}")

    # Reject userinfo (per Gemini spec: userinfo portions are forbidden)
    if parsed.username or parsed.password:
        raise ValueError(f"URL must not contain userinfo (user:password): {url}")

    # Reject fragments (per Gemini spec: fragments cannot be included)
    if parsed.fragment:
        raise ValueError(f"URL must not contain fragment: {url}")

    # Get port (default to 1965)
    port = parsed.port if parsed.port is not None else DEFAULT_PORT

    # Normalize path (default to '/')
    path = parsed.path if parsed.path else "/"

    # Construct normalized URL
    normalized = urlunparse(
        (
            "gemini",  # Always use 'gemini' scheme
            f"{parsed.hostname}:{port}" if port != DEFAULT_PORT else parsed.hostname,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    return ParsedURL(
        scheme="gemini",
        hostname=parsed.hostname,
        port=port,
        path=path,
        query=parsed.query or "",
        fragment=parsed.fragment or "",
        normalized=normalized,
    )


def validate_url(url: str) -> None:
    """Validate a Gemini URL for protocol compliance.

    Args:
        url: A Gemini URL string to validate.

    Raises:
        ValueError: If the URL is invalid or exceeds protocol limits.

    Examples:
        >>> validate_url('gemini://example.com/')  # OK
        >>> validate_url('http://example.com/')  # Raises ValueError
        >>> validate_url('gemini://' + 'a' * 2000)  # Raises ValueError (too long)
    """
    # Check maximum request size (URL + CRLF must be <= 1024 bytes)
    if len(url.encode("utf-8")) + 2 > MAX_REQUEST_SIZE:  # +2 for CRLF
        raise ValueError(
            f"URL too long: {len(url.encode('utf-8'))} bytes "
            f"(max {MAX_REQUEST_SIZE - 2} bytes)"
        )

    # Parse to validate structure
    parse_url(url)


def normalize_url(url: str) -> str:
    """Normalize a Gemini URL to its canonical form.

    Args:
        url: A Gemini URL string to normalize.

    Returns:
        The normalized URL string.

    Raises:
        ValueError: If the URL is invalid.

    Examples:
        >>> normalize_url('gemini://example.com')
        'gemini://example.com/'
        >>> normalize_url('gemini://example.com:1965/path')
        'gemini://example.com/path'
    """
    parsed = parse_url(url)
    return parsed.normalized


def is_gemini_url(url: str) -> bool:
    """Check if a string is a valid Gemini URL.

    Args:
        url: A URL string to check.

    Returns:
        True if the URL is a valid Gemini URL, False otherwise.

    Examples:
        >>> is_gemini_url('gemini://example.com/')
        True
        >>> is_gemini_url('http://example.com/')
        False
    """
    try:
        validate_url(url)
        return True
    except ValueError:
        return False
