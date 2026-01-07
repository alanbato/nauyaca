"""Tests for proxy handler and location configuration."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nauyaca.protocol.request import GeminiRequest
from nauyaca.protocol.response import GeminiResponse
from nauyaca.protocol.status import StatusCode
from nauyaca.server.location import HandlerType, LocationConfig
from nauyaca.server.proxy import ProxyHandler


class TestLocationConfig:
    """Test LocationConfig class."""

    def test_static_location_from_dict(self, tmp_path):
        """Test creating static location from dict."""
        config = LocationConfig.from_dict(
            {
                "prefix": "/static/",
                "handler": "static",
                "document_root": str(tmp_path),
                "enable_directory_listing": True,
            }
        )

        assert config.prefix == "/static/"
        assert config.handler_type == HandlerType.STATIC
        assert config.document_root == tmp_path
        assert config.enable_directory_listing is True

    def test_proxy_location_from_dict(self):
        """Test creating proxy location from dict."""
        config = LocationConfig.from_dict(
            {
                "prefix": "/api/",
                "handler": "proxy",
                "upstream": "gemini://backend:1965",
                "strip_prefix": True,
                "timeout": 60.0,
            }
        )

        assert config.prefix == "/api/"
        assert config.handler_type == HandlerType.PROXY
        assert config.upstream == "gemini://backend:1965"
        assert config.strip_prefix is True
        assert config.timeout == 60.0

    def test_default_handler_is_static(self, tmp_path):
        """Test that default handler is static."""
        config = LocationConfig.from_dict({"prefix": "/", "document_root": str(tmp_path)})

        assert config.handler_type == HandlerType.STATIC

    def test_prefix_normalized(self):
        """Test that prefix without leading slash is normalized."""
        config = LocationConfig.from_dict(
            {"prefix": "api/", "handler": "proxy", "upstream": "gemini://backend:1965"}
        )

        assert config.prefix == "/api/"

    def test_unknown_handler_raises_error(self):
        """Test that unknown handler type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown handler type"):
            LocationConfig.from_dict(
                {"prefix": "/", "handler": "unknown", "document_root": "./capsule"}
            )

    def test_static_requires_document_root(self):
        """Test that static handler requires document_root."""
        with pytest.raises(ValueError, match="requires document_root"):
            LocationConfig.from_dict({"prefix": "/", "handler": "static"})

    def test_proxy_requires_upstream(self):
        """Test that proxy handler requires upstream."""
        with pytest.raises(ValueError, match="requires upstream"):
            LocationConfig.from_dict({"prefix": "/api/", "handler": "proxy"})

    def test_proxy_requires_gemini_scheme(self):
        """Test that proxy upstream must use gemini:// scheme."""
        with pytest.raises(ValueError, match="gemini:// scheme"):
            LocationConfig.from_dict(
                {
                    "prefix": "/api/",
                    "handler": "proxy",
                    "upstream": "https://backend:443",
                }
            )

    def test_static_document_root_must_exist(self, tmp_path):
        """Test that static handler requires document_root to exist."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="does not exist"):
            LocationConfig.from_dict(
                {
                    "prefix": "/",
                    "handler": "static",
                    "document_root": str(nonexistent),
                }
            )

    def test_static_document_root_must_be_directory(self, tmp_path):
        """Test that static handler requires document_root to be a directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(ValueError, match="not a directory"):
            LocationConfig.from_dict(
                {
                    "prefix": "/",
                    "handler": "static",
                    "document_root": str(file_path),
                }
            )


class TestProxyHandler:
    """Test ProxyHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/api/",
            strip_prefix=True,
            timeout=30.0,
        )

        assert handler.upstream == "gemini://backend:1965"
        assert handler.prefix == "/api/"
        assert handler.strip_prefix is True
        assert handler.timeout == 30.0

    def test_upstream_trailing_slash_removed(self):
        """Test that trailing slash is removed from upstream."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965/",
            prefix="/",
        )

        assert handler.upstream == "gemini://backend:1965"

    def test_invalid_upstream_scheme_raises_error(self):
        """Test that non-gemini scheme raises ValueError."""
        with pytest.raises(ValueError, match="gemini:// scheme"):
            ProxyHandler(upstream="https://backend:443", prefix="/")

    @pytest.mark.asyncio
    async def test_forward_request_success(self):
        """Test forwarding request to upstream successfully."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
            strip_prefix=False,
        )

        # Mock the client
        mock_response = GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body="# Hello from upstream",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        request = GeminiRequest.from_line("gemini://frontend/page.gmi")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.SUCCESS.value
        assert response.body == "# Hello from upstream"
        handler._client.get.assert_called_once_with(
            "gemini://backend:1965/page.gmi",
            follow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_forward_with_strip_prefix(self):
        """Test forwarding request with prefix stripping."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/api/",
            strip_prefix=True,
        )

        mock_response = GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body="API response",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        request = GeminiRequest.from_line("gemini://frontend/api/resource")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.SUCCESS.value
        # Should strip /api/ prefix
        handler._client.get.assert_called_once_with(
            "gemini://backend:1965/resource",
            follow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_forward_with_query_string(self):
        """Test forwarding request preserves query string."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
            strip_prefix=False,
        )

        mock_response = GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body="Search results",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        request = GeminiRequest.from_line("gemini://frontend/search?q=test")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.SUCCESS.value
        handler._client.get.assert_called_once_with(
            "gemini://backend:1965/search?q=test",
            follow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_pass_through_redirect(self):
        """Test that redirects are passed through to client."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
        )

        mock_response = GeminiResponse(
            status=StatusCode.REDIRECT_TEMPORARY.value,
            meta="gemini://other-host/new-path",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        request = GeminiRequest.from_line("gemini://frontend/old-path")
        response = await handler._handle_async(request)

        # Redirect should be passed through as-is
        assert response.status == StatusCode.REDIRECT_TEMPORARY.value
        assert response.meta == "gemini://other-host/new-path"

    @pytest.mark.asyncio
    async def test_upstream_timeout_returns_proxy_error(self):
        """Test that upstream timeout returns 43 PROXY_ERROR."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
        )

        handler._client = MagicMock()
        handler._client.get = AsyncMock(side_effect=TimeoutError("Connection timed out"))

        request = GeminiRequest.from_line("gemini://frontend/page.gmi")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.PROXY_ERROR.value
        assert "timeout" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_upstream_connection_error_returns_proxy_error(self):
        """Test that upstream connection error returns 43 PROXY_ERROR."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
        )

        handler._client = MagicMock()
        handler._client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))

        request = GeminiRequest.from_line("gemini://frontend/page.gmi")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.PROXY_ERROR.value
        assert "connection" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_proxy_error(self):
        """Test that unexpected errors return 43 PROXY_ERROR."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
        )

        handler._client = MagicMock()
        handler._client.get = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        request = GeminiRequest.from_line("gemini://frontend/page.gmi")
        response = await handler._handle_async(request)

        assert response.status == StatusCode.PROXY_ERROR.value
        assert "error" in response.meta.lower()

    @pytest.mark.asyncio
    async def test_strip_prefix_ensures_leading_slash(self):
        """Test that stripped path always has leading slash."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/api",  # No trailing slash
            strip_prefix=True,
        )

        mock_response = GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body="OK",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        # Request path is /api (exact match with prefix)
        request = GeminiRequest.from_line("gemini://frontend/api")
        await handler._handle_async(request)

        # After stripping /api, should get / not empty string
        handler._client.get.assert_called_once_with(
            "gemini://backend:1965/",
            follow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_strip_prefix_does_not_match_partial(self):
        """Test that /api prefix does not incorrectly match /apikey."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/api",
            strip_prefix=True,
        )

        mock_response = GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body="OK",
        )
        handler._client = MagicMock()
        handler._client.get = AsyncMock(return_value=mock_response)

        # Request path is /apikey - should NOT strip /api prefix
        request = GeminiRequest.from_line("gemini://frontend/apikey")
        await handler._handle_async(request)

        # Path should remain /apikey, not become /key
        handler._client.get.assert_called_once_with(
            "gemini://backend:1965/apikey",
            follow_redirects=False,
        )


class TestProxyHandlerIntegration:
    """Integration tests for ProxyHandler with real requests."""

    @pytest.mark.asyncio
    async def test_handle_returns_awaitable(self):
        """Test that handle() returns an awaitable for async handling."""
        handler = ProxyHandler(
            upstream="gemini://backend:1965",
            prefix="/",
        )

        request = GeminiRequest.from_line("gemini://frontend/page.gmi")

        # Mock the client to avoid real network calls
        handler._client = MagicMock()
        handler._client.get = AsyncMock(
            return_value=GeminiResponse(
                status=StatusCode.SUCCESS.value,
                meta="text/gemini",
                body="OK",
            )
        )

        result = handler.handle(request)

        # Result should be a coroutine
        assert asyncio.iscoroutine(result)

        # Await it to prevent warning and verify it works
        response = await result
        assert response.status == StatusCode.SUCCESS.value
