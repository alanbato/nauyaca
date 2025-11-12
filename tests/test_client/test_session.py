"""Tests for GeminiClient session."""

import pytest

from nauyaca.client.session import GeminiClient


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

    # Note: Additional tests for actual fetching are in integration tests
    # since they require a real server or more complex mocking
