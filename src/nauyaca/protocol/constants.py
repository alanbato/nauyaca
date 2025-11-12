"""Gemini protocol constants.

This module defines the core constants for the Gemini protocol as specified
in the Gemini protocol specification.
"""

# Network constants
DEFAULT_PORT = 1965
"""Default TCP port for Gemini protocol."""

# Protocol limits
MAX_REQUEST_SIZE = 1024
"""Maximum size of a Gemini request in bytes (including URL and CRLF)."""

MAX_RESPONSE_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
"""Recommended maximum response body size (not enforced by protocol)."""

MAX_REDIRECTS = 5
"""Maximum number of redirects to follow before stopping."""

# Protocol markers
CRLF = b"\r\n"
"""Carriage Return Line Feed - protocol line terminator."""

# MIME types
MIME_TYPE_GEMTEXT = "text/gemini"
"""MIME type for Gemini's native markup format (gemtext)."""

MIME_TYPE_PLAIN_TEXT = "text/plain"
"""MIME type for plain text."""

# Status code ranges
STATUS_INPUT = range(10, 20)
"""Status codes 10-19: INPUT - Server needs additional input from client."""

STATUS_SUCCESS = range(20, 30)
"""Status codes 20-29: SUCCESS - Request completed successfully, body follows."""

STATUS_REDIRECT = range(30, 40)
"""Status codes 30-39: REDIRECT - Resource is available at a different URL."""

STATUS_TEMPORARY_FAILURE = range(40, 50)
"""Status codes 40-49: TEMPORARY FAILURE - Request failed but may succeed later."""

STATUS_PERMANENT_FAILURE = range(50, 60)
"""Status codes 50-59: PERMANENT FAILURE - Request failed and should not be retried."""

STATUS_CLIENT_CERT_REQUIRED = range(60, 70)
"""Status codes 60-69: CLIENT CERTIFICATE REQUIRED - Authentication needed."""
