"""Tests for GeminiClient session."""

import asyncio
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_client_with_verify_ssl_enabled(self):
        """Test client initialization with SSL verification enabled."""
        client = GeminiClient(verify_ssl=True)

        assert client.ssl_context is not None
        # Context should be configured for verification

    async def test_client_context_manager(self):
        """Test client as async context manager."""
        async with GeminiClient() as client:
            assert client is not None
            assert isinstance(client, GeminiClient)

    async def test_fetch_invalid_url(self):
        """Test fetching with invalid URL raises ValueError."""
        async with GeminiClient() as client:
            with pytest.raises(ValueError):
                await client.fetch("http://example.com/")

    async def test_fetch_connection_timeout(self):
        """Test fetch handles connection timeout."""
        client = GeminiClient(timeout=0.1)

        # Mock _fetch_single to raise timeout error (simulating connection timeout)
        async def timeout_fetch(url):
            raise TimeoutError("Connection timeout")

        with patch.object(client, "_fetch_single", new=timeout_fetch):
            with pytest.raises(TimeoutError, match="Connection timeout"):
                await client.fetch("gemini://example.com/")

    async def test_fetch_connection_refused(self):
        """Test fetch handles connection refused."""
        loop = asyncio.get_running_loop()

        # Mock create_connection to raise OSError
        async def mock_create_connection(*args, **kwargs):
            raise OSError("Connection refused")

        with patch.object(
            loop, "create_connection", side_effect=mock_create_connection
        ):
            client = GeminiClient(timeout=1.0)
            with pytest.raises(ConnectionError, match="Connection failed"):
                await client._fetch_single("gemini://example.com/")

    async def test_fetch_response_timeout(self):
        """Test fetch handles response timeout."""
        client = GeminiClient(timeout=0.1)

        # Mock _fetch_single to timeout by raising TimeoutError
        async def slow_fetch(url):
            raise TimeoutError("Request timeout")

        with patch.object(client, "_fetch_single", new=slow_fetch):
            with pytest.raises(TimeoutError, match="Request timeout"):
                await client.fetch("gemini://example.com/")

    async def test_redirect_loop_detection(self):
        """Test that redirect loops are detected."""
        client = GeminiClient()

        call_count = [0]

        # Mock _fetch_single to create a redirect loop: A -> B -> A
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

        with patch.object(client, "_fetch_single", new=mock_fetch_loop):
            with pytest.raises(ValueError, match="Redirect loop detected"):
                await client.fetch("gemini://example.com/start")

    async def test_max_redirects_exceeded(self):
        """Test that max redirects limit is enforced."""
        client = GeminiClient(max_redirects=2)

        # Mock _fetch_single to always return redirects to different URLs
        call_count = [0]

        async def mock_fetch(url):
            call_count[0] += 1
            return GeminiResponse(
                status=30,
                meta=f"gemini://example.com/redirect{call_count[0]}",
                url=url,
            )

        with patch.object(client, "_fetch_single", new=mock_fetch):
            with pytest.raises(ValueError, match="Maximum redirects.*exceeded"):
                await client.fetch("gemini://example.com/start")

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

        with patch.object(client, "_fetch_single", new=mock_fetch):
            response = await client.fetch("gemini://example.com/start")

        assert response.status == 20
        assert response.body == "Success"
        assert call_count[0] == 2

    async def test_redirect_without_url(self):
        """Test redirect response without URL raises error."""
        client = GeminiClient()

        # Create redirect response with empty meta (invalid)
        async def mock_fetch_empty_redirect(url):
            return GeminiResponse(status=30, meta="", url=url)

        with patch.object(client, "_fetch_single", new=mock_fetch_empty_redirect):
            with pytest.raises(ValueError, match="Redirect response missing URL"):
                await client.fetch("gemini://example.com/")

    async def test_fetch_no_redirect_following(self):
        """Test fetch with redirect following disabled."""
        client = GeminiClient()

        async def mock_fetch_redirect(url):
            return GeminiResponse(
                status=30,
                meta="gemini://example.com/other",
                url=url,
            )

        with patch.object(client, "_fetch_single", new=mock_fetch_redirect):
            response = await client.fetch(
                "gemini://example.com/", follow_redirects=False
            )

        # Should return the redirect response without following
        assert response.status == 30
        assert response.meta == "gemini://example.com/other"
