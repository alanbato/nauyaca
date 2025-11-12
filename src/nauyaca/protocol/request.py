"""Gemini protocol request representation.

This module provides the GeminiRequest dataclass for representing
Gemini protocol requests.
"""

from dataclasses import dataclass

from ..utils.url import ParsedURL, parse_url, validate_url


@dataclass(frozen=True)
class GeminiRequest:
    """Represents a Gemini protocol request.

    A Gemini request consists of a single line containing a URL followed by CRLF.
    The URL must be absolute and include the scheme (gemini://).

    Attributes:
        raw_url: The original URL string from the request line.
        parsed_url: Parsed URL components (scheme, hostname, port, path, query).

    Examples:
        >>> request = GeminiRequest.from_line('gemini://example.com/hello')
        >>> request.path
        '/hello'
        >>> request.hostname
        'example.com'
        >>> request.port
        1965
    """

    raw_url: str
    parsed_url: ParsedURL

    @classmethod
    def from_line(cls, line: str) -> "GeminiRequest":
        """Parse a Gemini request from a request line.

        Args:
            line: The request line (URL without CRLF).

        Returns:
            A GeminiRequest instance.

        Raises:
            ValueError: If the request line is invalid or malformed.

        Examples:
            >>> request = GeminiRequest.from_line('gemini://example.com/')
            >>> request.raw_url
            'gemini://example.com/'
        """
        # Validate and parse the URL
        validate_url(line)
        parsed = parse_url(line)

        return cls(raw_url=line, parsed_url=parsed)

    @property
    def scheme(self) -> str:
        """Get the URL scheme (always 'gemini')."""
        return self.parsed_url.scheme

    @property
    def hostname(self) -> str:
        """Get the server hostname."""
        return self.parsed_url.hostname

    @property
    def port(self) -> int:
        """Get the server port."""
        return self.parsed_url.port

    @property
    def path(self) -> str:
        """Get the URL path component."""
        return self.parsed_url.path

    @property
    def query(self) -> str:
        """Get the URL query string (empty if not present)."""
        return self.parsed_url.query

    @property
    def normalized_url(self) -> str:
        """Get the normalized URL string."""
        return self.parsed_url.normalized

    def __str__(self) -> str:
        """Return a human-readable string representation of the request."""
        parts = [f"Request: {self.raw_url}"]
        if self.query:
            parts.append(f"Query: {self.query}")
        return "\n".join(parts)
