"""Tests for error page templates."""

from nauyaca.content.templates import error_400, error_404, error_500, error_page
from nauyaca.protocol.status import StatusCode


class TestTemplates:
    """Test template generation functions."""

    def test_error_page_basic(self):
        """Test basic error page generation."""
        page = error_page(StatusCode.NOT_FOUND, "Not found")

        assert "# Error 51" in page
        assert "Not found" in page

    def test_error_page_with_details(self):
        """Test error page with details."""
        page = error_page(StatusCode.NOT_FOUND, "Not found", "Additional details here")

        assert "# Error 51" in page
        assert "Not found" in page
        assert "Additional details" in page

    def test_error_404(self):
        """Test 404 error page generation."""
        page = error_404("/missing/page")

        assert "# Error 51" in page
        assert "not found" in page.lower()
        assert "/missing/page" in page

    def test_error_404_default_path(self):
        """Test 404 error page with default path."""
        page = error_404()

        assert "# Error 51" in page
        assert "/" in page

    def test_error_500(self):
        """Test 500 error page generation."""
        page = error_500("Database connection failed")

        assert "# Error 40" in page  # TEMPORARY_FAILURE
        assert "Internal Server Error" in page
        assert "Database connection failed" in page

    def test_error_500_default_message(self):
        """Test 500 error page with default message."""
        page = error_500()

        assert "# Error 40" in page
        assert "internal server error" in page.lower()

    def test_error_400(self):
        """Test 400 error page generation."""
        page = error_400("Invalid URL format")

        assert "# Error 59" in page  # BAD_REQUEST
        assert "Bad Request" in page
        assert "Invalid URL format" in page

    def test_error_400_default_reason(self):
        """Test 400 error page with default reason."""
        page = error_400()

        assert "# Error 59" in page
        assert "Invalid request" in page

    def test_error_pages_are_gemtext(self):
        """Test that error pages are valid gemtext format."""
        page = error_404("/test")

        # Should start with a heading
        lines = page.split("\n")
        assert lines[0].startswith("#")
        # Should have blank line after heading
        assert lines[1] == ""
