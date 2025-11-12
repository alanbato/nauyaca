"""Content templates for Gemini server.

This module provides functions for generating error pages and other
template-based content in gemtext format.
"""

from ..protocol.status import StatusCode


def error_page(status: StatusCode, message: str, details: str | None = None) -> str:
    """Generate an error page in gemtext format.

    Args:
        status: The error status code.
        message: Brief error message.
        details: Optional detailed error information.

    Returns:
        A gemtext-formatted error page.

    Examples:
        >>> page = error_page(StatusCode.NOT_FOUND, "Page not found")
        >>> "404" in page
        True
    """
    lines = [
        f"# Error {status.value}",
        "",
        message,
    ]

    if details:
        lines.extend(["", details])

    return "\n".join(lines)


def error_404(path: str = "/") -> str:
    """Generate a 404 Not Found error page.

    Args:
        path: The requested path that was not found.

    Returns:
        A gemtext-formatted 404 error page.
    """
    return error_page(
        StatusCode.NOT_FOUND,
        "The requested resource was not found.",
        f"Path: {path}",
    )


def error_500(error_message: str = "An internal server error occurred.") -> str:
    """Generate a 500 Internal Server Error page.

    Args:
        error_message: Description of the error.

    Returns:
        A gemtext-formatted 500 error page.
    """
    return error_page(
        StatusCode.TEMPORARY_FAILURE,
        "Internal Server Error",
        error_message,
    )


def error_400(reason: str = "Invalid request.") -> str:
    """Generate a 400 Bad Request error page.

    Args:
        reason: Reason why the request was invalid.

    Returns:
        A gemtext-formatted 400 error page.
    """
    return error_page(StatusCode.BAD_REQUEST, "Bad Request", reason)
