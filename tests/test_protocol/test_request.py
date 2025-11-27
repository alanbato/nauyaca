"""Tests for GeminiRequest dataclass."""

import pytest

from nauyaca.protocol.request import GeminiRequest


class TestGeminiRequest:
    """Test GeminiRequest dataclass."""

    def test_from_line_basic(self):
        """Test creating a request from a basic URL."""
        request = GeminiRequest.from_line("gemini://example.com/")

        assert request.raw_url == "gemini://example.com/"
        assert request.hostname == "example.com"
        assert request.port == 1965
        assert request.path == "/"
        assert request.scheme == "gemini"
        assert request.query == ""

    def test_from_line_with_path(self):
        """Test creating a request with a path."""
        request = GeminiRequest.from_line("gemini://example.com/hello/world")

        assert request.path == "/hello/world"
        assert request.hostname == "example.com"

    def test_from_line_with_query(self):
        """Test creating a request with a query string."""
        request = GeminiRequest.from_line("gemini://example.com/search?q=test")

        assert request.path == "/search"
        assert request.query == "q=test"

    def test_from_line_with_port(self):
        """Test creating a request with a custom port."""
        request = GeminiRequest.from_line("gemini://example.com:1234/")

        assert request.port == 1234
        assert request.hostname == "example.com"

    def test_from_line_invalid_scheme(self):
        """Test that invalid scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid scheme"):
            GeminiRequest.from_line("http://example.com/")

    def test_from_line_missing_hostname(self):
        """Test that missing hostname raises ValueError."""
        with pytest.raises(ValueError, match="missing hostname"):
            GeminiRequest.from_line("gemini:///path")

    def test_from_line_empty_url(self):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            GeminiRequest.from_line("")

    def test_from_line_url_too_long(self):
        """Test that URLs exceeding 1024 bytes raise ValueError."""
        # Create a URL that's over 1024 bytes (including CRLF)
        # MAX_REQUEST_SIZE is 1024, which includes the URL + CRLF (2 bytes)
        # So the URL itself can be max 1022 bytes
        long_path = "a" * 1010
        long_url = f"gemini://example.com/{long_path}"

        with pytest.raises(ValueError, match="too long"):
            GeminiRequest.from_line(long_url)

    def test_normalized_url(self):
        """Test normalized_url property."""
        request = GeminiRequest.from_line("gemini://example.com:1965/path")

        # Default port should be omitted in normalized form
        assert request.normalized_url == "gemini://example.com/path"

    def test_normalized_url_custom_port(self):
        """Test normalized_url with custom port."""
        request = GeminiRequest.from_line("gemini://example.com:1234/path")

        # Custom port should be included
        assert ":1234" in request.normalized_url

    def test_str_representation(self):
        """Test string representation."""
        request = GeminiRequest.from_line("gemini://example.com/hello")
        str_repr = str(request)

        assert "gemini://example.com/hello" in str_repr
        assert "Request:" in str_repr

    def test_str_representation_with_query(self):
        """Test string representation with query."""
        request = GeminiRequest.from_line("gemini://example.com/search?q=test")
        str_repr = str(request)

        assert "Query:" in str_repr
        assert "q=test" in str_repr

    def test_mutable_cert_fields(self):
        """Test that certificate fields can be set after creation.

        GeminiRequest is mutable to allow the server protocol to attach
        client certificate information after parsing the request URL.
        """
        request = GeminiRequest.from_line("gemini://example.com/")

        # Initially no cert
        assert request.client_cert is None
        assert request.client_cert_fingerprint is None

        # Can set cert fingerprint (server protocol does this)
        request.client_cert_fingerprint = "sha256:abc123"
        assert request.client_cert_fingerprint == "sha256:abc123"

    def test_property_access(self):
        """Test all property accessors work correctly."""
        request = GeminiRequest.from_line("gemini://example.com:7000/path?key=value")

        assert request.scheme == "gemini"
        assert request.hostname == "example.com"
        assert request.port == 7000
        assert request.path == "/path"
        assert request.query == "key=value"

    def test_from_line_with_userinfo_rejected(self):
        """Test that URLs with userinfo are rejected per Gemini spec."""
        with pytest.raises(ValueError, match="userinfo"):
            GeminiRequest.from_line("gemini://user:pass@example.com/path")

    def test_from_line_with_username_only_rejected(self):
        """Test that URLs with username only are rejected per Gemini spec."""
        with pytest.raises(ValueError, match="userinfo"):
            GeminiRequest.from_line("gemini://user@example.com/path")

    def test_from_line_with_fragment_rejected(self):
        """Test that URLs with fragments are rejected per Gemini spec."""
        with pytest.raises(ValueError, match="fragment"):
            GeminiRequest.from_line("gemini://example.com/path#section")
