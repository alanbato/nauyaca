"""Request handlers for Gemini server.

This module provides request handler classes for processing Gemini requests
and generating responses, including Titan upload handlers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from ..content.gemtext import generate_directory_listing
from ..protocol.constants import (
    DEFAULT_MAX_FILE_SIZE,
    MIME_TYPE_GEMTEXT,
    MIME_TYPE_PLAIN_TEXT,
)
from ..protocol.request import GeminiRequest
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode

if TYPE_CHECKING:
    from ..protocol.request import TitanRequest


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
        default_indices: List of index filenames to try for directory requests.
        max_file_size: Maximum file size to serve (in bytes).

    Examples:
        >>> handler = StaticFileHandler(Path("/var/gemini/capsule"))
        >>> request = GeminiRequest.from_line("gemini://example.com/file.gmi")
        >>> response = handler.handle(request)
    """

    def __init__(
        self,
        document_root: Path | str,
        default_indices: list[str] | None = None,
        enable_directory_listing: bool = False,
        max_file_size: int | None = None,
    ) -> None:
        """Initialize the static file handler.

        Args:
            document_root: Path to the directory containing files to serve.
            default_indices: List of index filenames to try for directory requests
                (default: ["index.gmi", "index.gemini"]).
            enable_directory_listing: If True, generate directory listings for
                directories without an index file (default: False).
            max_file_size: Maximum file size to serve in bytes
                (default: 100 MiB per Gemini best practices).
        """
        self.document_root = Path(document_root).resolve()
        self.default_indices = default_indices or ["index.gmi", "index.gemini"]
        self.enable_directory_listing = enable_directory_listing
        self.max_file_size = max_file_size or DEFAULT_MAX_FILE_SIZE

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

        # If path is a directory, try to serve an index file or generate listing
        if file_path.is_dir():
            # Try each index filename in order (per Gemini best practices)
            index_found = False
            for index_name in self.default_indices:
                index_path = file_path / index_name
                if index_path.exists() and index_path.is_file():
                    file_path = index_path
                    index_found = True
                    break

            if not index_found:
                if self.enable_directory_listing:
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

        # Check file size (per Gemini best practices, avoid files >100 MiB)
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            return GeminiResponse(
                status=StatusCode.PERMANENT_FAILURE.value,
                meta="File too large - use alternative protocol",
            )

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


class UploadHandler(ABC):
    """Abstract base class for Titan upload handlers.

    Implementations can save uploads to filesystem, database, cloud storage, etc.
    All upload handlers should inherit from this class and implement
    the handle_upload() method.
    """

    @abstractmethod
    async def handle_upload(self, request: "TitanRequest") -> GeminiResponse:
        """Handle a Titan upload request.

        Args:
            request: The Titan upload request with content.

        Returns:
            A GeminiResponse indicating success or failure.
        """
        pass


class FileUploadHandler(UploadHandler):
    """Upload handler that saves files to disk.

    This handler saves uploaded content to a specified directory with
    path traversal protection, size limits, and optional authentication.

    Attributes:
        upload_dir: Directory for storing uploads.
        max_size: Maximum upload size in bytes.
        allowed_types: List of allowed MIME types (None = all allowed).
        auth_tokens: Set of valid authentication tokens.
        enable_delete: Whether to allow zero-byte delete requests.

    Examples:
        >>> handler = FileUploadHandler(
        ...     upload_dir=Path("/var/gemini/uploads"),
        ...     max_size=10 * 1024 * 1024,  # 10 MiB
        ...     auth_tokens={"secret123"},
        ... )
    """

    def __init__(
        self,
        upload_dir: Path | str,
        max_size: int = 10 * 1024 * 1024,  # 10 MiB default
        allowed_types: list[str] | None = None,
        auth_tokens: set[str] | None = None,
        enable_delete: bool = False,  # Disabled by default for safety
    ) -> None:
        """Initialize the file upload handler.

        Args:
            upload_dir: Directory for storing uploads.
            max_size: Maximum upload size in bytes (default: 10 MiB).
            allowed_types: List of allowed MIME types (None = all allowed).
            auth_tokens: Set of valid authentication tokens (None = no auth).
            enable_delete: Whether to allow zero-byte delete requests
                (default: False for safety).
        """
        self.upload_dir = Path(upload_dir).resolve()
        self.max_size = max_size
        self.allowed_types = allowed_types
        self.auth_tokens = auth_tokens or set()
        self.enable_delete = enable_delete

        # Create upload directory if it doesn't exist
        if not self.upload_dir.exists():
            self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def handle_upload(self, request: "TitanRequest") -> GeminiResponse:
        """Handle a Titan upload request.

        Validates authentication, size, MIME type, and path before saving.

        Args:
            request: The Titan upload request with content.

        Returns:
            A GeminiResponse indicating success or failure.
        """
        # Import here to avoid circular imports
        from ..protocol.request import TitanRequest

        if not isinstance(request, TitanRequest):
            return GeminiResponse(
                status=StatusCode.BAD_REQUEST.value,
                meta="Invalid request type",
            )

        # 1. Validate authentication (if tokens configured)
        if self.auth_tokens:
            if not request.token or request.token not in self.auth_tokens:
                return GeminiResponse(
                    status=StatusCode.CLIENT_CERT_REQUIRED.value,
                    meta="Valid authentication token required",
                )

        # 2. Validate content size
        if request.size > self.max_size:
            return GeminiResponse(
                status=StatusCode.PERMANENT_FAILURE.value,
                meta=f"Upload exceeds maximum size ({self.max_size} bytes)",
            )

        # 3. Validate MIME type
        if self.allowed_types and request.mime_type not in self.allowed_types:
            return GeminiResponse(
                status=StatusCode.BAD_REQUEST.value,
                meta=f"MIME type '{request.mime_type}' not allowed",
            )

        # 4. Handle zero-byte delete request
        if request.is_delete():
            return await self._handle_delete(request.path)

        # 5. Validate path (path traversal protection)
        target = (self.upload_dir / request.path.lstrip("/")).resolve()
        if not self._is_safe_path(target):
            return GeminiResponse(
                status=StatusCode.BAD_REQUEST.value,
                meta="Invalid path",
            )

        # 6. Save file
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(request.content)

            return GeminiResponse(
                status=StatusCode.SUCCESS.value,
                meta=MIME_TYPE_GEMTEXT,
                body=f"# Upload Successful\n\n=> {request.path} View uploaded content\n",
            )
        except PermissionError:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta="Permission denied",
            )
        except Exception as e:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta=f"Upload failed: {str(e)}",
            )

    async def _handle_delete(self, path: str) -> GeminiResponse:
        """Handle a zero-byte delete request.

        Args:
            path: The path to delete.

        Returns:
            A GeminiResponse indicating success or failure.
        """
        if not self.enable_delete:
            return GeminiResponse(
                status=StatusCode.PERMANENT_FAILURE.value,
                meta="Delete operations are disabled",
            )

        target = (self.upload_dir / path.lstrip("/")).resolve()

        if not self._is_safe_path(target):
            return GeminiResponse(
                status=StatusCode.BAD_REQUEST.value,
                meta="Invalid path",
            )

        if not target.exists():
            return GeminiResponse(
                status=StatusCode.NOT_FOUND.value,
                meta="Resource not found",
            )

        try:
            target.unlink()
            return GeminiResponse(
                status=StatusCode.SUCCESS.value,
                meta=MIME_TYPE_GEMTEXT,
                body=f"# Deleted\n\nResource '{path}' has been removed.\n",
            )
        except PermissionError:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta="Permission denied",
            )
        except Exception as e:
            return GeminiResponse(
                status=StatusCode.TEMPORARY_FAILURE.value,
                meta=f"Delete failed: {str(e)}",
            )

    def _is_safe_path(self, file_path: Path) -> bool:
        """Check if a file path is within the upload directory.

        Args:
            file_path: The resolved file path to check.

        Returns:
            True if the path is safe, False otherwise.
        """
        try:
            file_path.relative_to(self.upload_dir)
            return True
        except ValueError:
            return False
