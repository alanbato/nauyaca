"""Tests for GeminiResponse dataclass."""

import pytest

from nauyaca.protocol.response import GeminiResponse


class TestGeminiResponse:
    """Test GeminiResponse dataclass."""

    def test_create_success_response(self):
        """Test creating a success response."""
        response = GeminiResponse(
            status=20,
            meta="text/gemini",
            body="# Hello World",
            url="gemini://example.com/",
        )

        assert response.status == 20
        assert response.meta == "text/gemini"
        assert response.body == "# Hello World"
        assert response.url == "gemini://example.com/"

    def test_is_success(self):
        """Test is_success method."""
        success = GeminiResponse(status=20, meta="text/gemini")
        not_success = GeminiResponse(status=51, meta="Not found")

        assert success.is_success() is True
        assert not_success.is_success() is False

    def test_is_redirect(self):
        """Test is_redirect method."""
        redirect = GeminiResponse(status=30, meta="gemini://example.com/new")
        not_redirect = GeminiResponse(status=20, meta="text/gemini")

        assert redirect.is_redirect() is True
        assert not_redirect.is_redirect() is False

    def test_mime_type(self):
        """Test mime_type property."""
        # Success response with MIME type
        response = GeminiResponse(status=20, meta="text/gemini")
        assert response.mime_type == "text/gemini"

        # Success response with MIME type and parameters
        response = GeminiResponse(status=20, meta="text/gemini; charset=utf-8")
        assert response.mime_type == "text/gemini"

        # Non-success response
        response = GeminiResponse(status=51, meta="Not found")
        assert response.mime_type is None

    def test_redirect_url(self):
        """Test redirect_url property."""
        # Redirect response
        redirect = GeminiResponse(status=30, meta="gemini://example.com/new")
        assert redirect.redirect_url == "gemini://example.com/new"

        # Non-redirect response
        not_redirect = GeminiResponse(status=20, meta="text/gemini")
        assert not_redirect.redirect_url is None

    def test_charset_default(self):
        """Test charset property defaults to utf-8."""
        response = GeminiResponse(status=20, meta="text/gemini")
        assert response.charset == "utf-8"

    def test_charset_from_meta(self):
        """Test charset property extracts from meta."""
        response = GeminiResponse(status=20, meta="text/gemini; charset=iso-8859-1")
        assert response.charset == "iso-8859-1"

    def test_charset_non_success(self):
        """Test charset for non-success responses."""
        response = GeminiResponse(status=51, meta="Not found")
        assert response.charset == "utf-8"

    def test_str_representation(self):
        """Test string representation."""
        response = GeminiResponse(
            status=20,
            meta="text/gemini",
            body="# Hello",
            url="gemini://example.com/",
        )
        str_repr = str(response)

        assert "20" in str_repr
        assert "text/gemini" in str_repr
        assert "gemini://example.com/" in str_repr
        assert "bytes" in str_repr

    def test_frozen_dataclass(self):
        """Test that GeminiResponse is frozen (immutable)."""
        response = GeminiResponse(status=20, meta="text/gemini")

        with pytest.raises(AttributeError):
            response.status = 30  # type: ignore
