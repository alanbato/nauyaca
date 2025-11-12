"""Tests for request handlers."""

import tempfile
from pathlib import Path

import pytest

from nauyaca.protocol.request import GeminiRequest
from nauyaca.protocol.status import StatusCode
from nauyaca.server.handler import ErrorHandler, StaticFileHandler


class TestStaticFileHandler:
    """Test StaticFileHandler class."""

    def test_initialization(self, tmp_path):
        """Test handler initialization."""
        handler = StaticFileHandler(tmp_path)

        assert handler.document_root == tmp_path.resolve()
        assert handler.default_index == "index.gmi"

    def test_initialization_with_custom_index(self, tmp_path):
        """Test handler initialization with custom index."""
        handler = StaticFileHandler(tmp_path, default_index="home.gmi")

        assert handler.default_index == "home.gmi"

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

        handler = StaticFileHandler(tmp_path, default_index="home.gmi")
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
