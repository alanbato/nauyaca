"""Tests for request handlers."""

import tempfile
from pathlib import Path

import pytest

from nauyaca.protocol.request import GeminiRequest, TitanRequest
from nauyaca.protocol.status import StatusCode
from nauyaca.server.handler import ErrorHandler, FileUploadHandler, StaticFileHandler


class TestStaticFileHandler:
    """Test StaticFileHandler class."""

    def test_initialization(self, tmp_path):
        """Test handler initialization."""
        handler = StaticFileHandler(tmp_path)

        assert handler.document_root == tmp_path.resolve()
        assert handler.default_indices == ["index.gmi", "index.gemini"]

    def test_initialization_with_custom_indices(self, tmp_path):
        """Test handler initialization with custom indices."""
        handler = StaticFileHandler(tmp_path, default_indices=["home.gmi"])

        assert handler.default_indices == ["home.gmi"]

    def test_initialization_nonexistent_root(self):
        """Test that nonexistent document root raises ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            StaticFileHandler("/nonexistent/path")

    def test_initialization_file_as_root(self, tmp_path):
        """Test that file as document root raises ValueError."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="not a directory"):
            StaticFileHandler(test_file)

    def test_serve_simple_file(self, tmp_path):
        """Test serving a simple text file."""
        # Create a test file
        test_file = tmp_path / "test.gmi"
        test_file.write_text("# Hello World\nWelcome!")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/test.gmi")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.meta == "text/gemini"
        assert response.body == "# Hello World\nWelcome!"

    def test_serve_file_in_subdirectory(self, tmp_path):
        """Test serving a file in a subdirectory."""
        # Create subdirectory and file
        subdir = tmp_path / "docs"
        subdir.mkdir()
        test_file = subdir / "readme.txt"
        test_file.write_text("Documentation")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/docs/readme.txt")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.meta == "text/plain"
        assert response.body == "Documentation"

    def test_serve_index_file(self, tmp_path):
        """Test serving default index file for directory."""
        # Create index file
        index_file = tmp_path / "index.gmi"
        index_file.write_text("# Home\nWelcome to the homepage")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "# Home\nWelcome to the homepage"

    def test_serve_custom_index_file(self, tmp_path):
        """Test serving custom index file for directory."""
        # Create custom index file
        index_file = tmp_path / "home.gmi"
        index_file.write_text("# Custom Home")

        handler = StaticFileHandler(tmp_path, default_indices=["home.gmi"])
        request = GeminiRequest.from_line("gemini://example.com/")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "# Custom Home"

    def test_file_not_found(self, tmp_path):
        """Test response for nonexistent file."""
        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/nonexistent.gmi")

        response = handler.handle(request)

        assert response.status == StatusCode.NOT_FOUND.value
        assert response.meta == "Not found"

    def test_path_traversal_protection(self, tmp_path):
        """Test protection against path traversal attacks."""
        # Create a file outside the document root
        outside_dir = tmp_path.parent
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("Secret data")

        handler = StaticFileHandler(tmp_path)
        # Try to access file using path traversal
        request = GeminiRequest.from_line("gemini://example.com/../secret.txt")

        response = handler.handle(request)

        # Should return 404, not the secret file
        assert response.status == StatusCode.NOT_FOUND.value
        assert response.body is None

    def test_mime_type_gemtext(self, tmp_path):
        """Test MIME type detection for gemtext files."""
        test_file = tmp_path / "test.gmi"
        test_file.write_text("# Test")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/test.gmi")

        response = handler.handle(request)

        assert response.meta == "text/gemini"

    def test_mime_type_gemini_extension(self, tmp_path):
        """Test MIME type detection for .gemini files."""
        test_file = tmp_path / "test.gemini"
        test_file.write_text("# Test")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/test.gemini")

        response = handler.handle(request)

        assert response.meta == "text/gemini"

    def test_mime_type_plain_text(self, tmp_path):
        """Test MIME type detection for plain text files."""
        test_file = tmp_path / "readme.txt"
        test_file.write_text("Read me")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/readme.txt")

        response = handler.handle(request)

        assert response.meta == "text/plain"

    def test_mime_type_markdown(self, tmp_path):
        """Test MIME type detection for markdown files."""
        test_file = tmp_path / "README.md"
        test_file.write_text("# README")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/README.md")

        response = handler.handle(request)

        assert response.meta == "text/plain"

    def test_unicode_file_content(self, tmp_path):
        """Test serving files with Unicode content."""
        test_file = tmp_path / "unicode.gmi"
        test_file.write_text("# 你好世界\nこんにちは 🌍", encoding="utf-8")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/unicode.gmi")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert "你好世界" in response.body
        assert "こんにちは" in response.body

    def test_directory_without_index(self, tmp_path):
        """Test accessing directory without index file."""
        # Create empty subdirectory
        subdir = tmp_path / "empty"
        subdir.mkdir()

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/empty/")

        response = handler.handle(request)

        # Should return 404 since no index.gmi exists
        assert response.status == StatusCode.NOT_FOUND.value

    def test_serve_index_gemini_fallback(self, tmp_path):
        """Test serving index.gemini when index.gmi doesn't exist."""
        # Create only index.gemini (not index.gmi)
        index_file = tmp_path / "index.gemini"
        index_file.write_text("# Welcome via index.gemini")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "# Welcome via index.gemini"

    def test_serve_index_gmi_preferred_over_gemini(self, tmp_path):
        """Test that index.gmi is preferred over index.gemini."""
        # Create both index files
        (tmp_path / "index.gmi").write_text("# From index.gmi")
        (tmp_path / "index.gemini").write_text("# From index.gemini")

        handler = StaticFileHandler(tmp_path)
        request = GeminiRequest.from_line("gemini://example.com/")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "# From index.gmi"

    def test_file_too_large(self, tmp_path):
        """Test that files larger than max_file_size are rejected."""
        # Create a file larger than our small limit
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1000)  # 1000 bytes

        # Use a small max_file_size for testing
        handler = StaticFileHandler(tmp_path, max_file_size=500)
        request = GeminiRequest.from_line("gemini://example.com/large.txt")

        response = handler.handle(request)

        assert response.status == StatusCode.PERMANENT_FAILURE.value
        assert "too large" in response.meta.lower()

    def test_file_within_size_limit(self, tmp_path):
        """Test that files within max_file_size are served."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Small content")

        # Use a generous limit
        handler = StaticFileHandler(tmp_path, max_file_size=1000)
        request = GeminiRequest.from_line("gemini://example.com/small.txt")

        response = handler.handle(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "Small content"

    def test_default_max_file_size(self, tmp_path):
        """Test that default max_file_size is 100 MiB."""
        from nauyaca.protocol.constants import DEFAULT_MAX_FILE_SIZE

        handler = StaticFileHandler(tmp_path)

        assert handler.max_file_size == DEFAULT_MAX_FILE_SIZE
        assert handler.max_file_size == 100 * 1024 * 1024  # 100 MiB


class TestErrorHandler:
    """Test ErrorHandler class."""

    def test_error_handler_404(self):
        """Test error handler for 404 Not Found."""
        handler = ErrorHandler(StatusCode.NOT_FOUND, "Page not found")
        request = GeminiRequest.from_line("gemini://example.com/notfound")

        response = handler.handle(request)

        assert response.status == StatusCode.NOT_FOUND.value
        assert response.meta == "Page not found"

    def test_error_handler_temporary_failure(self):
        """Test error handler for temporary failure."""
        handler = ErrorHandler(
            StatusCode.TEMPORARY_FAILURE, "Service temporarily unavailable"
        )
        request = GeminiRequest.from_line("gemini://example.com/")

        response = handler.handle(request)

        assert response.status == StatusCode.TEMPORARY_FAILURE.value
        assert response.meta == "Service temporarily unavailable"

    def test_error_handler_ignores_request(self):
        """Test that error handler returns same response regardless of request."""
        handler = ErrorHandler(StatusCode.NOT_FOUND, "Not found")

        request1 = GeminiRequest.from_line("gemini://example.com/page1")
        request2 = GeminiRequest.from_line("gemini://example.com/page2")

        response1 = handler.handle(request1)
        response2 = handler.handle(request2)

        assert response1.status == response2.status
        assert response1.meta == response2.meta


class TestFileUploadHandler:
    """Test FileUploadHandler class for Titan uploads."""

    def test_initialization(self, tmp_path):
        """Test handler initialization."""
        handler = FileUploadHandler(tmp_path)

        assert handler.upload_dir == tmp_path.resolve()
        assert handler.max_size == 10 * 1024 * 1024  # 10 MiB default
        assert handler.enable_delete is False  # Disabled by default

    def test_initialization_creates_directory(self, tmp_path):
        """Test handler creates upload directory if it doesn't exist."""
        upload_dir = tmp_path / "new_uploads"
        handler = FileUploadHandler(upload_dir)

        assert upload_dir.exists()
        assert handler.upload_dir == upload_dir.resolve()

    def test_initialization_with_custom_settings(self, tmp_path):
        """Test handler initialization with custom settings."""
        handler = FileUploadHandler(
            tmp_path,
            max_size=5000,
            allowed_types=["text/plain"],
            auth_tokens={"token123"},
            enable_delete=True,
        )

        assert handler.max_size == 5000
        assert handler.allowed_types == ["text/plain"]
        assert handler.auth_tokens == {"token123"}
        assert handler.enable_delete is True

    @pytest.mark.asyncio
    async def test_upload_basic(self, tmp_path):
        """Test basic file upload."""
        handler = FileUploadHandler(tmp_path)

        request = TitanRequest.from_line("titan://example.com/test.gmi;size=12")
        request.content = b"Hello World!"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.SUCCESS.value
        assert (tmp_path / "test.gmi").exists()
        assert (tmp_path / "test.gmi").read_bytes() == b"Hello World!"

    @pytest.mark.asyncio
    async def test_upload_with_subdirectory(self, tmp_path):
        """Test upload creates parent directories."""
        handler = FileUploadHandler(tmp_path)

        request = TitanRequest.from_line("titan://example.com/docs/notes/file.gmi;size=5")
        request.content = b"hello"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.SUCCESS.value
        assert (tmp_path / "docs" / "notes" / "file.gmi").exists()
        assert (tmp_path / "docs" / "notes" / "file.gmi").read_bytes() == b"hello"

    @pytest.mark.asyncio
    async def test_upload_size_exceeded(self, tmp_path):
        """Test upload rejection when size exceeds limit."""
        handler = FileUploadHandler(tmp_path, max_size=10)

        request = TitanRequest.from_line("titan://example.com/large.txt;size=100")
        request.content = b"x" * 100

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.PERMANENT_FAILURE.value
        assert "exceeds" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_upload_mime_type_validation(self, tmp_path):
        """Test upload rejection for disallowed MIME types."""
        handler = FileUploadHandler(tmp_path, allowed_types=["text/gemini"])

        request = TitanRequest.from_line(
            "titan://example.com/image.png;size=5;mime=image/png"
        )
        request.content = b"12345"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.BAD_REQUEST.value
        assert "not allowed" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_upload_auth_required(self, tmp_path):
        """Test upload rejection without valid auth token."""
        handler = FileUploadHandler(tmp_path, auth_tokens={"valid-token"})

        # No token
        request = TitanRequest.from_line("titan://example.com/file.txt;size=5")
        request.content = b"hello"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.CLIENT_CERT_REQUIRED.value
        assert "token required" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_upload_auth_invalid_token(self, tmp_path):
        """Test upload rejection with invalid auth token."""
        handler = FileUploadHandler(tmp_path, auth_tokens={"valid-token"})

        request = TitanRequest.from_line(
            "titan://example.com/file.txt;size=5;token=wrong-token"
        )
        request.content = b"hello"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.CLIENT_CERT_REQUIRED.value

    @pytest.mark.asyncio
    async def test_upload_auth_valid_token(self, tmp_path):
        """Test upload success with valid auth token."""
        handler = FileUploadHandler(tmp_path, auth_tokens={"valid-token"})

        request = TitanRequest.from_line(
            "titan://example.com/file.txt;size=5;token=valid-token"
        )
        request.content = b"hello"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.SUCCESS.value
        assert (tmp_path / "file.txt").exists()

    @pytest.mark.asyncio
    async def test_upload_path_traversal_protection(self, tmp_path):
        """Test path traversal attack is blocked."""
        handler = FileUploadHandler(tmp_path)

        request = TitanRequest.from_line("titan://example.com/../secret.txt;size=5")
        request.content = b"hello"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.BAD_REQUEST.value
        assert "invalid path" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_delete_disabled_by_default(self, tmp_path):
        """Test delete operations are disabled by default."""
        # Create a file to delete
        test_file = tmp_path / "deleteme.txt"
        test_file.write_text("delete me")

        handler = FileUploadHandler(tmp_path)

        # Zero-byte upload = delete request
        request = TitanRequest.from_line("titan://example.com/deleteme.txt;size=0")
        request.content = b""

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.PERMANENT_FAILURE.value
        assert "disabled" in response.meta.lower()
        # File should still exist
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_enabled(self, tmp_path):
        """Test delete operations when enabled."""
        # Create a file to delete
        test_file = tmp_path / "deleteme.txt"
        test_file.write_text("delete me")

        handler = FileUploadHandler(tmp_path, enable_delete=True)

        request = TitanRequest.from_line("titan://example.com/deleteme.txt;size=0")
        request.content = b""

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.SUCCESS.value
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, tmp_path):
        """Test delete for nonexistent file returns 404."""
        handler = FileUploadHandler(tmp_path, enable_delete=True)

        request = TitanRequest.from_line("titan://example.com/nosuchfile.txt;size=0")
        request.content = b""

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_delete_path_traversal_protection(self, tmp_path):
        """Test path traversal is blocked for delete operations."""
        # Create file outside upload dir
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("outside")

        handler = FileUploadHandler(tmp_path, enable_delete=True)

        request = TitanRequest.from_line("titan://example.com/../outside.txt;size=0")
        request.content = b""

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.BAD_REQUEST.value
        # File should still exist
        assert outside_file.exists()
        outside_file.unlink()  # Cleanup

    @pytest.mark.asyncio
    async def test_upload_overwrites_existing(self, tmp_path):
        """Test upload overwrites existing file."""
        existing_file = tmp_path / "file.txt"
        existing_file.write_text("old content")

        handler = FileUploadHandler(tmp_path)

        request = TitanRequest.from_line("titan://example.com/file.txt;size=11")
        request.content = b"new content"

        response = await handler.handle_upload(request)

        assert response.status == StatusCode.SUCCESS.value
        assert existing_file.read_bytes() == b"new content"
