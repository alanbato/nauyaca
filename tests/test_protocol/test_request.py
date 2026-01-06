"""Tests for GeminiRequest and TitanRequest dataclasses."""

import pytest

from nauyaca.protocol.request import GeminiRequest, TitanRequest


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


class TestTitanRequest:
    """Test TitanRequest dataclass."""

    def test_from_line_basic(self):
        """Test creating a Titan request from a basic URL."""
        request = TitanRequest.from_line("titan://example.com/upload;size=100")

        assert request.raw_url == "titan://example.com/upload;size=100"
        assert request.hostname == "example.com"
        assert request.port == 1965
        assert request.path == "/upload"
        assert request.scheme == "titan"
        assert request.size == 100
        assert request.mime_type == "text/gemini"  # Default
        assert request.token is None

    def test_from_line_with_all_parameters(self):
        """Test creating a Titan request with all parameters."""
        request = TitanRequest.from_line(
            "titan://example.com/upload;size=50;mime=text/plain;token=secret123"
        )

        assert request.size == 50
        assert request.mime_type == "text/plain"
        assert request.token == "secret123"

    def test_from_line_with_path(self):
        """Test creating a Titan request with a longer path."""
        request = TitanRequest.from_line(
            "titan://example.com/uploads/docs/file.gmi;size=200"
        )

        assert request.path == "/uploads/docs/file.gmi"
        assert request.size == 200

    def test_from_line_with_custom_port(self):
        """Test creating a Titan request with a custom port."""
        request = TitanRequest.from_line("titan://example.com:1234/upload;size=100")

        assert request.port == 1234
        assert request.hostname == "example.com"

    def test_from_line_missing_scheme(self):
        """Test that non-titan scheme raises ValueError."""
        with pytest.raises(ValueError, match="Titan URL must start with titan://"):
            TitanRequest.from_line("gemini://example.com/;size=100")

    def test_from_line_missing_parameters(self):
        """Test that missing parameters raises ValueError."""
        with pytest.raises(ValueError, match="must contain parameters"):
            TitanRequest.from_line("titan://example.com/upload")

    def test_from_line_missing_size(self):
        """Test that missing size parameter raises ValueError."""
        with pytest.raises(ValueError, match="must contain size parameter"):
            TitanRequest.from_line("titan://example.com/upload;mime=text/plain")

    def test_from_line_invalid_size(self):
        """Test that invalid size raises ValueError."""
        with pytest.raises(ValueError, match="Invalid size parameter"):
            TitanRequest.from_line("titan://example.com/upload;size=notanumber")

    def test_from_line_negative_size(self):
        """Test that negative size raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            TitanRequest.from_line("titan://example.com/upload;size=-10")

    def test_is_delete_true(self):
        """Test is_delete returns True for zero-byte requests."""
        request = TitanRequest.from_line("titan://example.com/file.gmi;size=0")

        assert request.is_delete() is True

    def test_is_delete_false(self):
        """Test is_delete returns False for non-zero-byte requests."""
        request = TitanRequest.from_line("titan://example.com/file.gmi;size=100")

        assert request.is_delete() is False

    def test_normalized_url(self):
        """Test normalized_url includes parameters."""
        request = TitanRequest.from_line(
            "titan://example.com/upload;size=100;mime=text/plain"
        )

        assert (
            request.normalized_url
            == "titan://example.com/upload;size=100;mime=text/plain"
        )

    def test_normalized_url_with_token(self):
        """Test normalized_url includes token when present."""
        request = TitanRequest.from_line(
            "titan://example.com/upload;size=100;mime=text/gemini;token=abc"
        )

        assert ";token=abc" in request.normalized_url

    def test_str_representation(self):
        """Test string representation."""
        request = TitanRequest.from_line("titan://example.com/upload;size=100")
        str_repr = str(request)

        assert "Titan Request:" in str_repr
        assert "100 bytes" in str_repr
        assert "text/gemini" in str_repr

    def test_str_representation_with_token(self):
        """Test string representation includes truncated token line."""
        request = TitanRequest.from_line(
            "titan://example.com/upload;size=100;token=verylongsecrettoken"
        )
        str_repr = str(request)

        assert "Token:" in str_repr
        # Token line should show truncated version
        assert "Token: verylong..." in str_repr

    def test_content_field_default(self):
        """Test content field defaults to empty bytes."""
        request = TitanRequest.from_line("titan://example.com/upload;size=100")

        assert request.content == b""

    def test_content_field_can_be_set(self):
        """Test content field can be set after creation."""
        request = TitanRequest.from_line("titan://example.com/upload;size=5")
        request.content = b"hello"

        assert request.content == b"hello"

    def test_mutable_cert_fields(self):
        """Test that certificate fields can be set after creation."""
        request = TitanRequest.from_line("titan://example.com/upload;size=100")

        # Initially no cert
        assert request.client_cert is None
        assert request.client_cert_fingerprint is None

        # Can set cert fingerprint
        request.client_cert_fingerprint = "sha256:abc123"
        assert request.client_cert_fingerprint == "sha256:abc123"

    def test_parameters_order_independent(self):
        """Test parameters can be in any order."""
        # mime before size
        request1 = TitanRequest.from_line(
            "titan://example.com/upload;mime=text/plain;size=100"
        )
        # token before size
        request2 = TitanRequest.from_line("titan://example.com/upload;token=abc;size=100")

        assert request1.size == 100
        assert request1.mime_type == "text/plain"
        assert request2.size == 100
        assert request2.token == "abc"
