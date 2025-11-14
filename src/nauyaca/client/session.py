"""High-level Gemini client API.

This module provides a high-level async/await interface for making
Gemini requests, built on top of the low-level GeminiClientProtocol.
"""

import asyncio
import ssl
from pathlib import Path

from ..protocol.constants import MAX_REDIRECTS
from ..protocol.response import GeminiResponse
from ..protocol.status import is_redirect
from ..security.certificates import get_certificate_fingerprint
from ..security.tls import create_client_context
from ..security.tofu import CertificateChangedError, TOFUDatabase
from ..utils.url import parse_url, validate_url
from .protocol import GeminiClientProtocol


class GeminiClient:
    """High-level Gemini client with async/await API.

    This class provides a simple, high-level interface for getting Gemini
    resources. It handles connection management, TLS, redirects, and timeouts.

    Examples:
        >>> # Basic usage
        >>> async with GeminiClient() as client:
        ...     response = await client.get('gemini://example.com/')
        ...     print(response.body)

        >>> # With custom timeout and redirect settings
        >>> client = GeminiClient(timeout=30, max_redirects=3)
        >>> response = await client.get('gemini://example.com/')

        >>> # Disable redirect following
        >>> response = await client.get(
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
        trust_on_first_use: bool = True,
        tofu_db_path: Path | None = None,
    ):
        """Initialize the Gemini client.

        Args:
            timeout: Request timeout in seconds. Default is 30 seconds.
            max_redirects: Maximum number of redirects to follow. Default is 5.
            ssl_context: Custom SSL context. If None, a default context will be
                created based on verify_ssl and trust_on_first_use settings.
            verify_ssl: Whether to verify SSL certificates using CA validation.
                Default is False. For Gemini, you should use TOFU instead.
            trust_on_first_use: Whether to use TOFU certificate validation.
                Default is True. This is the recommended mode for Gemini.
            tofu_db_path: Path to TOFU database. If None, uses default location
                (~/.nauyaca/tofu.db).
        """
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.verify_ssl = verify_ssl
        self.trust_on_first_use = trust_on_first_use

        # Initialize TOFU database if needed
        if self.trust_on_first_use:
            self.tofu_db: TOFUDatabase | None = TOFUDatabase(tofu_db_path)
        else:
            self.tofu_db = None

        # Create SSL context if not provided
        if ssl_context is None:
            if verify_ssl:
                # CA-based verification (not recommended for Gemini)
                self.ssl_context = create_client_context(
                    verify_mode=ssl.CERT_REQUIRED,
                    check_hostname=True,
                )
            else:
                # TOFU mode or testing mode - accept all certificates
                # TOFU validation happens after connection is established
                self.ssl_context = create_client_context(
                    verify_mode=ssl.CERT_NONE,
                    check_hostname=False,
                )
        else:
            self.ssl_context = ssl_context

    async def __aenter__(self) -> "GeminiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        pass

    async def get(
        self,
        url: str,
        follow_redirects: bool = True,
    ) -> GeminiResponse:
        """Get a Gemini resource.

        Args:
            url: The Gemini URL to get.
            follow_redirects: Whether to automatically follow redirects.
                Default is True.

        Returns:
            A GeminiResponse object with status, meta, and optional body.

        Raises:
            ValueError: If the URL is invalid.
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.

        Examples:
            >>> response = await client.get('gemini://example.com/')
            >>> if response.is_success():
            ...     print(response.body)
        """
        # Validate URL
        validate_url(url)

        # Get with redirect following if enabled
        if follow_redirects:
            return await self._get_with_redirects(url, max_redirects=self.max_redirects)
        else:
            return await self._get_single(url)

    async def _get_single(self, url: str) -> GeminiResponse:
        """Get a single URL without following redirects.

        Args:
            url: The Gemini URL to get.

        Returns:
            A GeminiResponse object.

        Raises:
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.
            CertificateChangedError: If certificate has changed (TOFU).
        """
        # Parse URL to get host and port
        parsed = parse_url(url)

        # Get event loop
        loop = asyncio.get_running_loop()

        # Create future for response
        response_future: asyncio.Future = loop.create_future()

        # Create protocol instance with normalized URL
        # Per spec: "client SHOULD add trailing '/' for empty paths"
        protocol = GeminiClientProtocol(parsed.normalized, response_future)

        # Create connection using Protocol/Transport pattern
        try:
            transport, protocol = await asyncio.wait_for(
                loop.create_connection(
                    lambda: protocol,
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
            # If TOFU is enabled, verify the certificate
            if self.tofu_db:
                cert = protocol.get_peer_certificate()
                if cert:
                    is_valid, message = self.tofu_db.verify(
                        parsed.hostname, parsed.port, cert
                    )

                    if not is_valid and message == "changed":
                        # Certificate changed - get old info and raise error
                        old_info = self.tofu_db.get_host_info(
                            parsed.hostname, parsed.port
                        )
                        old_fingerprint = (
                            old_info["fingerprint"] if old_info else "unknown"
                        )
                        new_fingerprint = get_certificate_fingerprint(cert)
                        raise CertificateChangedError(
                            parsed.hostname,
                            parsed.port,
                            old_fingerprint,
                            new_fingerprint,
                        )
                    elif message == "first_use":
                        # First time seeing this host - trust it
                        self.tofu_db.trust(parsed.hostname, parsed.port, cert)

            # Wait for response with timeout
            response: GeminiResponse = await asyncio.wait_for(
                response_future, timeout=self.timeout
            )
            return response
        except TimeoutError as e:
            raise TimeoutError(f"Request timeout: {url}") from e
        finally:
            # Ensure transport is closed
            transport.close()

    async def _get_with_redirects(
        self,
        url: str,
        max_redirects: int,
        redirect_chain: list | None = None,
    ) -> GeminiResponse:
        """Get a URL and follow redirects.

        Args:
            url: The Gemini URL to get.
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

        # Get the URL
        response = await self._get_single(url)

        # If it's a redirect, follow it
        if is_redirect(response.status):
            redirect_url = response.redirect_url
            if not redirect_url:
                raise ValueError(f"Redirect response missing URL: {response.meta}")

            # Add current URL to chain and follow redirect
            redirect_chain.append(url)
            return await self._get_with_redirects(
                redirect_url,
                max_redirects=max_redirects,
                redirect_chain=redirect_chain,
            )

        # Not a redirect, return the response
        return response
