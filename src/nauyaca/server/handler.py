"""Request handlers for Gemini server.

This module provides request handler classes for processing Gemini requests
and generating responses.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..content.gemtext import generate_directory_listing
from ..protocol.constants import MIME_TYPE_GEMTEXT, MIME_TYPE_PLAIN_TEXT
from ..protocol.request import GeminiRequest
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode


class RequestHandler(ABC):
    """Abstract base class for request handlers.

    All request handlers should inherit from this class and implement
    the handle() method.
    """

    @abstractmethod
    def handle(self, request: GeminiRequest) -> GeminiResponse:
        """Handle a Gemini request and return a response.

        Args:
            request: The incoming request to handle.

        Returns:
            A GeminiResponse object.
        """
        pass


class StaticFileHandler(RequestHandler):
    """Handler for serving static files from a document root.

    This handler serves files from a specified directory with path traversal
    protection and automatic MIME type detection.

    Attributes:
        document_root: Path to the directory containing files to serve.
        default_index: Default file to serve for directory requests.

    Examples:
        >>> handler = StaticFileHandler(Path("/var/gemini/capsule"))
        >>> request = GeminiRequest.from_line("gemini://example.com/file.gmi")
        >>> response = handler.handle(request)
    """

    def __init__(
        self,
        document_root: Path | str,
        default_index: str = "index.gmi",
        enable_directory_listing: bool = False,
    ) -> None:
        """Initialize the static file handler.

        Args:
            document_root: Path to the directory containing files to serve.
            default_index: Default file to serve for directory requests
                (default: "index.gmi").
            enable_directory_listing: If True, generate directory listings for
                directories without an index file (default: False).
        """
        self.document_root = Path(document_root).resolve()
        self.default_index = default_index
        self.enable_directory_listing = enable_directory_listing

        if not self.document_root.exists():
            raise ValueError(f"Document root does not exist: {self.document_root}")
        if not self.document_root.is_dir():
            raise ValueError(f"Document root is not a directory: {self.document_root}")

    def handle(self, request: GeminiRequest) -> GeminiResponse:
        """Handle a request for a static file.

        Args:
            request: The incoming request.

        Returns:
            A GeminiResponse with the file contents or an error.
        """
        # Get the requested path (remove leading slash)
        requested_path = request.path.lstrip("/")

        # Construct the full file path
        file_path = (self.document_root / requested_path).resolve()

        # Path traversal protection: ensure the resolved path is within document root
        if not self._is_safe_path(file_path):
            return GeminiResponse(status=StatusCode.NOT_FOUND.value, meta="Not found")

        # If path is a directory, try to serve the default index or generate listing
        if file_path.is_dir():
            index_path = file_path / self.default_index

            if index_path.exists() and index_path.is_file():
                # Serve the index file
                file_path = index_path
            elif self.enable_directory_listing:
                # Generate directory listing
                try:
                    listing = generate_directory_listing(file_path, request.path)
                    return GeminiResponse(
                        status=StatusCode.SUCCESS.value,
                        meta=MIME_TYPE_GEMTEXT,
                        body=listing,
                    )
                except Exception as e:
                    return GeminiResponse(
                        status=StatusCode.TEMPORARY_FAILURE.value,
                        meta=f"Error generating directory listing: {str(e)}",
                    )
            else:
                # No index and directory listing disabled
                return GeminiResponse(
                    status=StatusCode.NOT_FOUND.value, meta="Not found"
                )

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return GeminiResponse(status=StatusCode.NOT_FOUND.value, meta="Not found")

        try:
            # Read file contents
            content = file_path.read_text(encoding="utf-8")

            # Determine MIME type
            mime_type = self._get_mime_type(file_path)

            return GeminiResponse(
                status=StatusCode.SUCCESS.value, meta=mime_type, body=content
            )

        except UnicodeDecodeError:
            # File is not valid UTF-8
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta="File encoding error (not UTF-8)",
            )
        except PermissionError:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta="Permission denied",
            )
        except Exception as e:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta=f"Server error: {str(e)}",
            )

    def _is_safe_path(self, file_path: Path) -> bool:
        """Check if a file path is within the document root (path traversal protection).

        Args:
            file_path: The resolved file path to check.

        Returns:
            True if the path is safe, False otherwise.
        """
        try:
            # Check if the resolved path is relative to document_root
            file_path.relative_to(self.document_root)
            return True
        except ValueError:
            # Path is not within document_root
            return False

    def _get_mime_type(self, file_path: Path) -> str:
        """Determine MIME type from file extension.

        Args:
            file_path: Path to the file.

        Returns:
            The MIME type string.
        """
        suffix = file_path.suffix.lower()

        # Gemini-specific
        if suffix in (".gmi", ".gemini"):
            return MIME_TYPE_GEMTEXT

        # Text files
        if suffix in (".txt", ".md"):
            return MIME_TYPE_PLAIN_TEXT

        # Default to plain text for other files
        return MIME_TYPE_PLAIN_TEXT


class ErrorHandler(RequestHandler):
    """Handler that returns error responses.

    Useful for handling 404 Not Found and other error cases.

    Examples:
        >>> handler = ErrorHandler(StatusCode.NOT_FOUND, "Page not found")
        >>> response = handler.handle(request)
        >>> response.status
        51
    """

    def __init__(self, status: StatusCode, message: str):
        """Initialize the error handler.

        Args:
            status: The error status code to return.
            message: The error message (becomes the meta field).
        """
        self.status = status
        self.message = message

    def handle(self, request: GeminiRequest) -> GeminiResponse:
        """Return an error response.

        Args:
            request: The incoming request (ignored).

        Returns:
            A GeminiResponse with the configured error.
        """
        return GeminiResponse(status=self.status.value, meta=self.message)
