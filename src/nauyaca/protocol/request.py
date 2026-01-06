"""Gemini and Titan protocol request representation.

This module provides request dataclasses for representing
Gemini and Titan protocol requests with a shared base class.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..utils.url import ParsedURL, parse_url, validate_url

if TYPE_CHECKING:
    from cryptography.x509 import Certificate


@dataclass
class BaseRequest:
    """Abstract base class for Gemini and Titan requests.

    Contains common fields shared between both protocols.

    Attributes:
        raw_url: The original URL string from the request line.
        parsed_url: Parsed URL components (scheme, hostname, port, path, query).
        client_cert: Optional client certificate (if provided via TLS).
        client_cert_fingerprint: SHA-256 fingerprint of client certificate.
    """

    raw_url: str
    parsed_url: ParsedURL
    client_cert: "Certificate | None" = field(default=None, compare=False)
    client_cert_fingerprint: str | None = field(default=None, compare=False)

    @property
    def scheme(self) -> str:
        """Get the URL scheme ('gemini' or 'titan')."""
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


@dataclass
class GeminiRequest(BaseRequest):
    """Represents a Gemini protocol request.

    A Gemini request consists of a single line containing a URL followed by CRLF.
    The URL must be absolute and include the scheme (gemini://).

    Inherits from BaseRequest: raw_url, parsed_url, client_cert,
    client_cert_fingerprint, scheme, hostname, port, path.

    Examples:
        >>> request = GeminiRequest.from_line('gemini://example.com/hello')
        >>> request.path
        '/hello'
        >>> request.hostname
        'example.com'
        >>> request.port
        1965
    """

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
        validate_url(line)
        parsed = parse_url(line)

        return cls(raw_url=line, parsed_url=parsed)

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


@dataclass
class TitanRequest(BaseRequest):
    """Represents a Titan protocol upload request.

    A Titan request consists of a URL with parameters followed by CRLF,
    then the upload content. URL format: titan://host/path;size=X;mime=Y;token=Z

    Inherits from BaseRequest: raw_url, parsed_url, client_cert,
    client_cert_fingerprint, scheme, hostname, port, path.

    Attributes:
        size: Content size in bytes (mandatory).
        mime_type: Content MIME type (default: text/gemini).
        token: Authentication token (optional).
        content: The uploaded content bytes.

    Examples:
        >>> request = TitanRequest.from_line('titan://example.com/file.gmi;size=12')
        >>> request.size
        12
        >>> request.mime_type
        'text/gemini'
    """

    size: int = 0
    mime_type: str = "text/gemini"
    token: str | None = None
    content: bytes = field(default=b"", repr=False)

    @classmethod
    def from_line(cls, line: str) -> "TitanRequest":
        """Parse a Titan request from a request line.

        Args:
            line: The request line (URL with parameters, without CRLF).

        Returns:
            A TitanRequest instance.

        Raises:
            ValueError: If the request line is invalid or malformed.

        Examples:
            >>> request = TitanRequest.from_line(
            ...     'titan://example.com/upload;size=100;mime=text/plain'
            ... )
            >>> request.size
            100
        """
        if not line.startswith("titan://"):
            raise ValueError("Titan URL must start with titan://")

        # Split URL from parameters at first semicolon
        if ";" not in line:
            raise ValueError("Titan URL must contain parameters (;size=...)")

        # Find the path end and params start
        # Format: titan://host/path;size=X;mime=Y;token=Z
        url_part, params_str = line.split(";", 1)

        # Parse parameters
        params = _parse_titan_params(params_str)

        if "size" not in params:
            raise ValueError("Titan URL must contain size parameter")

        try:
            size = int(params["size"])
        except ValueError as e:
            raise ValueError(f"Invalid size parameter: {params['size']}") from e

        if size < 0:
            raise ValueError(f"Size must be non-negative: {size}")

        # Parse the base URL (convert to gemini:// for parsing, then fix scheme)
        gemini_url = "gemini://" + url_part[8:]  # Replace titan:// with gemini://
        parsed = parse_url(gemini_url)
        # Create new ParsedURL with titan scheme
        parsed = ParsedURL(
            scheme="titan",
            hostname=parsed.hostname,
            port=parsed.port,
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
            normalized=line.split(";")[0],  # Base URL without params
        )

        return cls(
            raw_url=line,
            parsed_url=parsed,
            size=size,
            mime_type=params.get("mime", "text/gemini"),
            token=params.get("token"),
        )

    def is_delete(self) -> bool:
        """Check if this is a delete request (zero-byte upload)."""
        return self.size == 0

    @property
    def normalized_url(self) -> str:
        """Get the normalized URL with parameters."""
        base = self.parsed_url.normalized
        params = f";size={self.size};mime={self.mime_type}"
        if self.token:
            params += f";token={self.token}"
        return base + params

    def __str__(self) -> str:
        """Return a human-readable string representation of the request."""
        parts = [
            f"Titan Request: {self.raw_url}",
            f"Size: {self.size} bytes",
            f"MIME: {self.mime_type}",
        ]
        if self.token:
            parts.append(f"Token: {self.token[:8]}...")
        return "\n".join(parts)


def _parse_titan_params(params_str: str) -> dict[str, str]:
    """Parse semicolon-separated Titan parameters.

    Args:
        params_str: String like "size=123;mime=text/plain;token=secret"

    Returns:
        Dictionary of parameter name to value.
    """
    params: dict[str, str] = {}
    for part in params_str.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            params[key.strip()] = value.strip()
    return params
