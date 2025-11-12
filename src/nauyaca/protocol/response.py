"""Gemini protocol response representation.

This module provides the GeminiResponse dataclass for representing
Gemini protocol responses.
"""

from dataclasses import dataclass

from .status import is_redirect, is_success


@dataclass(frozen=True)
class GeminiResponse:
    """Represents a Gemini protocol response.

    Attributes:
        status: Two-digit status code (10-69).
        meta: Status-dependent metadata string. For success (2x), this is the
            MIME type. For redirects (3x), this is the redirect URL. For errors,
            this is an error message. For input (1x), this is the prompt.
        body: Response body content (only present for 2x success responses).
        url: The URL this response came from (useful for tracking redirects).

    Examples:
        >>> response = GeminiResponse(
        ...     status=20,
        ...     meta='text/gemini',
        ...     body='# Hello World\\nWelcome to Gemini!',
        ...     url='gemini://example.com/'
        ... )
        >>> response.is_success()
        True
        >>> response.mime_type
        'text/gemini'
    """

    status: int
    meta: str
    body: str | None = None
    url: str | None = None

    def is_success(self) -> bool:
        """Check if this response indicates success (2x status code)."""
        return is_success(self.status)

    def is_redirect(self) -> bool:
        """Check if this response indicates a redirect (3x status code)."""
        return is_redirect(self.status)

    @property
    def mime_type(self) -> str | None:
        """Get the MIME type from a success response.

        Returns:
            The MIME type if this is a success response, None otherwise.
        """
        if self.is_success():
            # Meta for success responses is the MIME type, possibly with parameters
            # e.g., "text/gemini; charset=utf-8"
            return self.meta.split(";")[0].strip()
        return None

    @property
    def redirect_url(self) -> str | None:
        """Get the redirect URL from a redirect response.

        Returns:
            The redirect URL if this is a redirect response, None otherwise.
        """
        if self.is_redirect():
            return self.meta
        return None

    @property
    def charset(self) -> str:
        """Extract charset from MIME type parameters, defaulting to utf-8.

        Returns:
            The charset specified in the meta field, or 'utf-8' if not specified.
        """
        if not self.is_success():
            return "utf-8"

        # Look for charset parameter in meta (e.g., "text/gemini; charset=iso-8859-1")
        parts = self.meta.split(";")
        for part in parts[1:]:  # Skip the MIME type itself
            key_value = part.strip().split("=", 1)
            if len(key_value) == 2:
                key, value = key_value
                if key.strip().lower() == "charset":
                    return value.strip()

        return "utf-8"  # Default charset per Gemini spec

    def __str__(self) -> str:
        """Return a human-readable string representation of the response."""
        lines = [f"Status: {self.status} - {self.meta}"]
        if self.url:
            lines.append(f"URL: {self.url}")
        if self.body:
            lines.append(f"Body: {len(self.body)} bytes")
        return "\n".join(lines)
