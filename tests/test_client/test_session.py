"""Tests for GeminiClient session."""

import asyncio
import ssl
from unittest.mock import patch

import pytest

from nauyaca.client.session import GeminiClient
from nauyaca.protocol.response import GeminiResponse


class TestGeminiClient:
    """Test GeminiClient high-level API."""

    def test_client_initialization(self):
        """Test client initialization with default settings."""
        client = GeminiClient()

        assert client.timeout == 30.0
        assert client.max_redirects == 5
        assert client.ssl_context is not None

    def test_client_custom_settings(self):
        """Test client initialization with custom settings."""
        client = GeminiClient(timeout=60.0, max_redirects=3)

        assert client.timeout == 60.0
        assert client.max_redirects == 3

    def test_client_with_custom_ssl_context(self):
        """Test client initialization with custom SSL context."""
        custom_context = ssl.create_default_context()
        client = GeminiClient(ssl_context=custom_context)

        assert client.ssl_context is custom_context

    def test_client_with_verify_ssl_enabled(self, tmp_path):
        """Test client initialization with SSL verification enabled."""
        client = GeminiClient(verify_ssl=True, tofu_db_path=tmp_path / "tofu.db")

        assert client.ssl_context is not None
        # Context should be configured for verification

    async def test_client_context_manager(self):
        """Test client as async context manager."""
        async with GeminiClient() as client:
            assert client is not None
            assert isinstance(client, GeminiClient)

    async def test_fetch_invalid_url(self):
        """Test getting with invalid URL raises ValueError."""
        async with GeminiClient() as client:
            with pytest.raises(ValueError):
                await client.get("http://example.com/")

    async def test_fetch_connection_timeout(self):
        """Test get handles connection timeout."""
        async with GeminiClient(timeout=0.1) as client:
            # Mock _get_single to raise timeout error (simulating connection timeout)
            async def timeout_fetch(url):
                raise TimeoutError("Connection timeout")

            with patch.object(client, "_get_single", new=timeout_fetch):
                with pytest.raises(TimeoutError, match="Connection timeout"):
                    await client.get("gemini://example.com/")

    async def test_fetch_connection_refused(self):
        """Test get handles connection refused."""
        loop = asyncio.get_running_loop()

        # Mock create_connection to raise OSError
        async def mock_create_connection(*args, **kwargs):
            raise OSError("Connection refused")

        with patch.object(loop, "create_connection", side_effect=mock_create_connection):
            client = GeminiClient(timeout=1.0)
            with pytest.raises(ConnectionError, match="Connection failed"):
                await client._get_single("gemini://example.com/")

    async def test_fetch_response_timeout(self):
        """Test get handles response timeout."""
        client = GeminiClient(timeout=0.1)

        # Mock _get_single to timeout by raising TimeoutError
        async def slow_fetch(url):
            raise TimeoutError("Request timeout")

        with patch.object(client, "_get_single", new=slow_fetch):
            with pytest.raises(TimeoutError, match="Request timeout"):
                await client.get("gemini://example.com/")

    async def test_redirect_loop_detection(self):
        """Test that redirect loops are detected."""
        client = GeminiClient()

        call_count = [0]

        # Mock _get_single to create a redirect loop: A -> B -> A
        async def mock_fetch_loop(url):
            call_count[0] += 1
            if "start" in url:
                # First URL redirects to second
                return GeminiResponse(
                    status=30, meta="gemini://example.com/second", url=url
                )
            else:
                # Second URL redirects back to first (loop)
                return GeminiResponse(
                    status=30, meta="gemini://example.com/start", url=url
                )

        with patch.object(client, "_get_single", new=mock_fetch_loop):
            with pytest.raises(ValueError, match="Redirect loop detected"):
                await client.get("gemini://example.com/start")

    async def test_max_redirects_exceeded(self):
        """Test that max redirects limit is enforced."""
        client = GeminiClient(max_redirects=2)

        # Mock _get_single to always return redirects to different URLs
        call_count = [0]

        async def mock_fetch(url):
            call_count[0] += 1
            return GeminiResponse(
                status=30,
                meta=f"gemini://example.com/redirect{call_count[0]}",
                url=url,
            )

        with patch.object(client, "_get_single", new=mock_fetch):
            with pytest.raises(ValueError, match="Maximum redirects.*exceeded"):
                await client.get("gemini://example.com/start")

    async def test_redirect_following_success(self):
        """Test successful redirect following."""
        client = GeminiClient()

        call_count = [0]

        async def mock_fetch(url):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: redirect
                return GeminiResponse(
                    status=30,
                    meta="gemini://example.com/final",
                    url=url,
                )
            else:
                # Second call: success
                return GeminiResponse(
                    status=20,
                    meta="text/gemini",
                    body="Success",
                    url=url,
                )

        with patch.object(client, "_get_single", new=mock_fetch):
            response = await client.get("gemini://example.com/start")

        assert response.status == 20
        assert response.body == "Success"
        assert call_count[0] == 2

    async def test_redirect_without_url(self):
        """Test redirect response without URL raises error."""
        client = GeminiClient()

        # Create redirect response with empty meta (invalid)
        async def mock_fetch_empty_redirect(url):
            return GeminiResponse(status=30, meta="", url=url)

        with patch.object(client, "_get_single", new=mock_fetch_empty_redirect):
            with pytest.raises(ValueError, match="Redirect response missing URL"):
                await client.get("gemini://example.com/")

    async def test_fetch_no_redirect_following(self):
        """Test get with redirect following disabled."""
        client = GeminiClient()

        async def mock_fetch_redirect(url):
            return GeminiResponse(
                status=30,
                meta="gemini://example.com/other",
                url=url,
            )

        with patch.object(client, "_get_single", new=mock_fetch_redirect):
            response = await client.get("gemini://example.com/", follow_redirects=False)

        # Should return the redirect response without following
        assert response.status == 30
        assert response.meta == "gemini://example.com/other"

    async def test_cross_protocol_redirect_not_followed(self):
        """Test that redirects to non-gemini protocols are not followed.

        Per Gemini best practices, clients should not follow redirects to
        unencrypted protocols like HTTP. Instead, return the redirect response.
        """
        client = GeminiClient()

        async def mock_fetch_http_redirect(url):
            return GeminiResponse(
                status=30,
                meta="https://example.com/moved",
                url=url,
            )

        with patch.object(client, "_get_single", new=mock_fetch_http_redirect):
            response = await client.get("gemini://example.com/")

        # Should return the redirect response without following
        assert response.status == 30
        assert response.meta == "https://example.com/moved"

    async def test_gemini_redirect_is_followed(self):
        """Test that redirects to gemini:// URLs are followed normally."""
        client = GeminiClient()

        call_count = [0]

        async def mock_fetch(url):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: redirect to another gemini URL
                return GeminiResponse(
                    status=30,
                    meta="gemini://other.example.com/page",
                    url=url,
                )
            else:
                # Second call: success
                return GeminiResponse(
                    status=20,
                    meta="text/gemini",
                    body="Followed gemini redirect",
                    url=url,
                )

        with patch.object(client, "_get_single", new=mock_fetch):
            response = await client.get("gemini://example.com/")

        # Should have followed the gemini:// redirect
        assert response.status == 20
        assert response.body == "Followed gemini redirect"
        assert call_count[0] == 2

    async def test_client_normalizes_url_before_sending(self, mocker):
        """Test that client normalizes URL (adds trailing /) before sending to server.

        Per Gemini spec: "If a client is making a request with an empty path,
        the client SHOULD add a trailing '/' to the request"
        """
        client = GeminiClient(verify_ssl=False, trust_on_first_use=False)

        # Mock the create_connection to capture what URL is actually sent
        sent_url = None

        async def mock_create_connection(protocol_factory, **kwargs):
            nonlocal sent_url
            # Create the protocol instance to capture the URL
            protocol = protocol_factory()
            sent_url = protocol.url

            # Mock transport and future
            transport = mocker.Mock()
            protocol.connection_made(transport)

            # Return mock transport and protocol
            return transport, protocol

        with patch("asyncio.get_running_loop") as mock_loop:
            loop = asyncio.get_event_loop()
            mock_loop.return_value = loop

            with patch.object(
                loop, "create_connection", side_effect=mock_create_connection
            ):
                try:
                    # Get URL without trailing slash
                    await client._get_single("gemini://example.com")
                except Exception:
                    # We expect this to fail since we're not completing the protocol
                    # but we've captured the URL that was sent
                    pass

        # Verify the URL sent to the protocol has trailing /
        assert sent_url == "gemini://example.com/", (
            f"Expected normalized URL with trailing /, got: {sent_url}"
        )
