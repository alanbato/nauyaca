"""Tests for URL parsing and validation."""

import pytest

from nauyaca.protocol.constants import MAX_REQUEST_SIZE
from nauyaca.utils.url import (
    is_gemini_url,
    normalize_url,
    parse_url,
    validate_url,
)


class TestParseURL:
    """Test parse_url function."""

    def test_parse_simple_url(self):
        """Test parsing a simple Gemini URL."""
        parsed = parse_url("gemini://example.com/")

        assert parsed.scheme == "gemini"
        assert parsed.hostname == "example.com"
        assert parsed.port == 1965
        assert parsed.path == "/"
        assert parsed.query == ""

    def test_parse_url_with_path(self):
        """Test parsing URL with path."""
        parsed = parse_url("gemini://example.com/hello/world")

        assert parsed.path == "/hello/world"

    def test_parse_url_with_port(self):
        """Test parsing URL with custom port."""
        parsed = parse_url("gemini://example.com:2000/")

        assert parsed.port == 2000

    def test_parse_url_with_query(self):
        """Test parsing URL with query string."""
        parsed = parse_url("gemini://example.com/search?query=hello")

        assert parsed.path == "/search"
        assert parsed.query == "query=hello"

    def test_parse_url_no_path(self):
        """Test parsing URL without path defaults to /."""
        parsed = parse_url("gemini://example.com")

        assert parsed.path == "/"

    def test_parse_url_empty(self):
        """Test parsing empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            parse_url("")

    def test_parse_url_missing_scheme(self):
        """Test parsing URL without scheme raises ValueError."""
        with pytest.raises(ValueError, match="URL missing scheme"):
            parse_url("example.com/")

    def test_parse_url_invalid_scheme(self):
        """Test parsing URL with invalid scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid scheme"):
            parse_url("http://example.com/")

    def test_parse_url_missing_hostname(self):
        """Test parsing URL without hostname raises ValueError."""
        with pytest.raises(ValueError, match="URL missing hostname"):
            parse_url("gemini:///path")

    def test_normalized_url_default_port(self):
        """Test normalized URL omits default port."""
        parsed = parse_url("gemini://example.com:1965/")

        assert parsed.normalized == "gemini://example.com/"

    def test_normalized_url_custom_port(self):
        """Test normalized URL includes custom port."""
        parsed = parse_url("gemini://example.com:2000/")

        assert parsed.normalized == "gemini://example.com:2000/"


class TestValidateURL:
    """Test validate_url function."""

    def test_validate_valid_url(self):
        """Test validating a valid URL."""
        validate_url("gemini://example.com/")  # Should not raise

    def test_validate_url_too_long(self):
        """Test validating URL that exceeds max size."""
        # Create a URL that's too long (> 1024 bytes including CRLF)
        long_url = "gemini://example.com/" + "a" * (MAX_REQUEST_SIZE - 20)

        with pytest.raises(ValueError, match="URL too long"):
            validate_url(long_url)

    def test_validate_invalid_url(self):
        """Test validating invalid URL."""
        with pytest.raises(ValueError):
            validate_url("http://example.com/")


class TestNormalizeURL:
    """Test normalize_url function."""

    def test_normalize_adds_trailing_slash(self):
        """Test normalization adds trailing slash."""
        normalized = normalize_url("gemini://example.com")

        assert normalized == "gemini://example.com/"

    def test_normalize_removes_default_port(self):
        """Test normalization removes default port."""
        normalized = normalize_url("gemini://example.com:1965/path")

        assert normalized == "gemini://example.com/path"

    def test_normalize_keeps_custom_port(self):
        """Test normalization keeps custom port."""
        normalized = normalize_url("gemini://example.com:2000/path")

        assert normalized == "gemini://example.com:2000/path"


class TestIsGeminiURL:
    """Test is_gemini_url function."""

    @pytest.mark.parametrize(
        "url",
        [
            "gemini://example.com/",
            "gemini://example.com:1965/path",
            "gemini://example.com/path?query=test",
        ],
    )
    def test_is_gemini_url_valid(self, url):
        """Test is_gemini_url returns True for valid URLs."""
        assert is_gemini_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com/",
            "https://example.com/",
            "ftp://example.com/",
            "gemini://",  # Missing hostname
            "",  # Empty string
            "gemini://example.com/" + "a" * 2000,  # Too long
        ],
    )
    def test_is_gemini_url_invalid(self, url):
        """Test is_gemini_url returns False for invalid URLs."""
        assert is_gemini_url(url) is False
