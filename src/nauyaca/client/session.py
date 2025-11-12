"""High-level Gemini client API.

This module provides a high-level async/await interface for making
Gemini requests, built on top of the low-level GeminiClientProtocol.
"""

import asyncio
import ssl

from ..protocol.constants import MAX_REDIRECTS
from ..protocol.response import GeminiResponse
from ..protocol.status import is_redirect
from ..security.tls import create_client_context
from ..utils.url import parse_url, validate_url
from .protocol import GeminiClientProtocol


class GeminiClient:
    """High-level Gemini client with async/await API.

    This class provides a simple, high-level interface for fetching Gemini
    resources. It handles connection management, TLS, redirects, and timeouts.

    Examples:
        >>> # Basic usage
        >>> async with GeminiClient() as client:
        ...     response = await client.fetch('gemini://example.com/')
        ...     print(response.body)

        >>> # With custom timeout and redirect settings
        >>> client = GeminiClient(timeout=30, max_redirects=3)
        >>> response = await client.fetch('gemini://example.com/')

        >>> # Disable redirect following
        >>> response = await client.fetch(
        ...     'gemini://example.com/',
        ...     follow_redirects=False
        ... )
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_redirects: int = MAX_REDIRECTS,
        ssl_context: ssl.SSLContext | None = None,
        verify_ssl: bool = False,
    ):
        """Initialize the Gemini client.

        Args:
            timeout: Request timeout in seconds. Default is 30 seconds.
            max_redirects: Maximum number of redirects to follow. Default is 5.
            ssl_context: Custom SSL context. If None, a default context will be
                created based on verify_ssl setting.
            verify_ssl: Whether to verify SSL certificates. Default is False
                (testing mode). Set to True for production with TOFU.
        """
        self.timeout = timeout
        self.max_redirects = max_redirects

        # Create SSL context if not provided
        if ssl_context is None:
            if verify_ssl:
                self.ssl_context = create_client_context(
                    verify_mode=ssl.CERT_REQUIRED,
                    check_hostname=True,
                )
            else:
                # Testing mode - accept all certificates
                self.ssl_context = create_client_context(
                    verify_mode=ssl.CERT_NONE,
                    check_hostname=False,
                )
        else:
            self.ssl_context = ssl_context

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # No cleanup needed for now
        pass

    async def fetch(
        self,
        url: str,
        follow_redirects: bool = True,
    ) -> GeminiResponse:
        """Fetch a Gemini resource.

        Args:
            url: The Gemini URL to fetch.
            follow_redirects: Whether to automatically follow redirects.
                Default is True.

        Returns:
            A GeminiResponse object with status, meta, and optional body.

        Raises:
            ValueError: If the URL is invalid.
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.

        Examples:
            >>> response = await client.fetch('gemini://example.com/')
            >>> if response.is_success():
            ...     print(response.body)
        """
        # Validate URL
        validate_url(url)

        # Fetch with redirect following if enabled
        if follow_redirects:
            return await self._fetch_with_redirects(
                url, max_redirects=self.max_redirects
            )
        else:
            return await self._fetch_single(url)

    async def _fetch_single(self, url: str) -> GeminiResponse:
        """Fetch a single URL without following redirects.

        Args:
            url: The Gemini URL to fetch.

        Returns:
            A GeminiResponse object.

        Raises:
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.
        """
        # Parse URL to get host and port
        parsed = parse_url(url)

        # Get event loop
        loop = asyncio.get_running_loop()

        # Create future for response
        response_future: asyncio.Future = loop.create_future()

        # Create connection using Protocol/Transport pattern
        try:
            transport, protocol = await asyncio.wait_for(
                loop.create_connection(
                    lambda: GeminiClientProtocol(url, response_future),
                    host=parsed.hostname,
                    port=parsed.port,
                    ssl=self.ssl_context,
                    server_hostname=parsed.hostname,
                ),
                timeout=self.timeout,
            )
        except TimeoutError as e:
            raise TimeoutError(f"Connection timeout: {url}") from e
        except OSError as e:
            raise ConnectionError(f"Connection failed: {e}") from e

        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=self.timeout)
            return response
        except TimeoutError as e:
            raise TimeoutError(f"Request timeout: {url}") from e
        finally:
            # Ensure transport is closed
            transport.close()

    async def _fetch_with_redirects(
        self,
        url: str,
        max_redirects: int,
        redirect_chain: list | None = None,
    ) -> GeminiResponse:
        """Fetch a URL and follow redirects.

        Args:
            url: The Gemini URL to fetch.
            max_redirects: Maximum number of redirects to follow.
            redirect_chain: List of URLs already visited (for loop detection).

        Returns:
            A GeminiResponse object (final response after all redirects).

        Raises:
            ValueError: If redirect loop detected or max redirects exceeded.
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.
        """
        if redirect_chain is None:
            redirect_chain = []

        # Check for redirect loop
        if url in redirect_chain:
            raise ValueError(f"Redirect loop detected: {url}")

        # Check max redirects
        if len(redirect_chain) >= max_redirects:
            raise ValueError(f"Maximum redirects ({max_redirects}) exceeded at: {url}")

        # Fetch the URL
        response = await self._fetch_single(url)

        # If it's a redirect, follow it
        if is_redirect(response.status):
            redirect_url = response.redirect_url
            if not redirect_url:
                raise ValueError(f"Redirect response missing URL: {response.meta}")

            # Add current URL to chain and follow redirect
            redirect_chain.append(url)
            return await self._fetch_with_redirects(
                redirect_url,
                max_redirects=max_redirects,
                redirect_chain=redirect_chain,
            )

        # Not a redirect, return the response
        return response
