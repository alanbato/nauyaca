"""Gemini protocol status codes.

This module provides the StatusCode enum with all Gemini protocol status codes
and utility functions for interpreting them.
"""

from enum import IntEnum


class StatusCode(IntEnum):
    """Gemini protocol status codes.

    Status codes are two-digit integers where the first digit represents the
    general category of the response.
    """

    # 1x - INPUT
    INPUT = 10
    """Server needs additional input from client."""

    SENSITIVE_INPUT = 11
    """Server needs sensitive input (e.g., password) - client should not echo."""

    # 2x - SUCCESS
    SUCCESS = 20
    """Request successful, response body follows."""

    # 3x - REDIRECT
    REDIRECT_TEMPORARY = 30
    """Resource temporarily available at a different URL."""

    REDIRECT_PERMANENT = 31
    """Resource permanently moved to a different URL."""

    # 4x - TEMPORARY FAILURE
    TEMPORARY_FAILURE = 40
    """Generic temporary failure."""

    SERVER_UNAVAILABLE = 41
    """Server is unavailable due to overload or maintenance."""

    CGI_ERROR = 42
    """CGI process error."""

    PROXY_ERROR = 43
    """Proxying error (bad upstream connection, timeout, etc.)."""

    SLOW_DOWN = 44
    """Rate limiting - client should slow down requests."""

    # 5x - PERMANENT FAILURE
    PERMANENT_FAILURE = 50
    """Generic permanent failure."""

    NOT_FOUND = 51
    """Resource not found."""

    GONE = 52
    """Resource previously existed but is now permanently gone."""

    PROXY_REQUEST_REFUSED = 53
    """Proxy request refused."""

    BAD_REQUEST = 59
    """Malformed or invalid request."""

    # 6x - CLIENT CERTIFICATE REQUIRED
    CLIENT_CERT_REQUIRED = 60
    """Valid client certificate required."""

    CERT_NOT_AUTHORIZED = 61
    """Certificate not authorized for the requested resource."""

    CERT_NOT_VALID = 62
    """Certificate not valid (expired, wrong domain, etc.)."""


def interpret_status(status: int) -> str:
    """Interpret a status code and return its category name.

    Args:
        status: A two-digit Gemini status code (10-69).

    Returns:
        A string describing the general category of the status code.

    Examples:
        >>> interpret_status(20)
        'SUCCESS'
        >>> interpret_status(51)
        'PERMANENT FAILURE'
        >>> interpret_status(30)
        'REDIRECT'
    """
    if 10 <= status < 20:
        return "INPUT"
    elif 20 <= status < 30:
        return "SUCCESS"
    elif 30 <= status < 40:
        return "REDIRECT"
    elif 40 <= status < 50:
        return "TEMPORARY FAILURE"
    elif 50 <= status < 60:
        return "PERMANENT FAILURE"
    elif 60 <= status < 70:
        return "CLIENT CERTIFICATE REQUIRED"
    else:
        return "UNKNOWN"


def is_success(status: int) -> bool:
    """Check if a status code indicates success (2x).

    Args:
        status: A two-digit Gemini status code.

    Returns:
        True if the status code is in the success range (20-29).
    """
    return 20 <= status < 30


def is_redirect(status: int) -> bool:
    """Check if a status code indicates a redirect (3x).

    Args:
        status: A two-digit Gemini status code.

    Returns:
        True if the status code is in the redirect range (30-39).
    """
    return 30 <= status < 40


def is_input_required(status: int) -> bool:
    """Check if a status code indicates input is required (1x).

    Args:
        status: A two-digit Gemini status code.

    Returns:
        True if the status code is in the input range (10-19).
    """
    return 10 <= status < 20


def is_error(status: int) -> bool:
    """Check if a status code indicates an error (4x, 5x, or 6x).

    Args:
        status: A two-digit Gemini status code.

    Returns:
        True if the status code indicates any type of error.
    """
    return 40 <= status < 70
