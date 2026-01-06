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
from .protocol import GeminiClientProtocol, TitanClientProtocol


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
        client_cert: Path | str | None = None,
        client_key: Path | str | None = None,
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
            client_cert: Path to client certificate file (PEM format) for
                authentication with servers that require client certificates.
            client_key: Path to client private key file (PEM format). Required
                if client_cert is provided.
        """
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.verify_ssl = verify_ssl
        self.trust_on_first_use = trust_on_first_use

        # Validate client cert/key pair
        if client_cert and not client_key:
            raise ValueError("client_key is required when client_cert is provided")
        if client_key and not client_cert:
            raise ValueError("client_cert is required when client_key is provided")

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
                    certfile=str(client_cert) if client_cert else None,
                    keyfile=str(client_key) if client_key else None,
                )
            else:
                # TOFU mode or testing mode - accept all certificates
                # TOFU validation happens after connection is established
                self.ssl_context = create_client_context(
                    verify_mode=ssl.CERT_NONE,
                    check_hostname=False,
                    certfile=str(client_cert) if client_cert else None,
                    keyfile=str(client_key) if client_key else None,
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

            # Only follow gemini:// redirects (per Gemini best practices)
            # Return non-gemini redirects as-is, letting caller decide
            if not redirect_url.startswith("gemini://"):
                return response

            # Add current URL to chain and follow redirect
            redirect_chain.append(url)
            return await self._get_with_redirects(
                redirect_url,
                max_redirects=max_redirects,
                redirect_chain=redirect_chain,
            )

        # Not a redirect, return the response
        return response

    async def upload(
        self,
        url: str,
        content: bytes | str,
        mime_type: str = "text/gemini",
        token: str | None = None,
    ) -> GeminiResponse:
        """Upload content to a Gemini server via the Titan protocol.

        Titan is Gemini's upload companion protocol. It uses the same port (1965)
        and TLS requirements as Gemini, but allows uploading content.

        Args:
            url: The target URL. Can be either gemini:// or titan:// scheme.
                If gemini://, it will be converted to titan://.
            content: The content to upload. Can be bytes or str (will be
                encoded as UTF-8).
            mime_type: MIME type of the content. Default is "text/gemini".
            token: Optional authentication token for the server.

        Returns:
            A GeminiResponse from the server indicating success or failure.

        Raises:
            ValueError: If the URL is invalid.
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.

        Examples:
            >>> # Upload text content
            >>> response = await client.upload(
            ...     'gemini://example.com/uploads/note.gmi',
            ...     '# My Note\\n\\nHello, Geminispace!',
            ... )

            >>> # Upload binary content
            >>> with open('image.png', 'rb') as f:
            ...     response = await client.upload(
            ...         'gemini://example.com/uploads/image.png',
            ...         f.read(),
            ...         mime_type='image/png',
            ...     )

            >>> # Upload with authentication
            >>> response = await client.upload(
            ...     'gemini://example.com/uploads/file.txt',
            ...     'Hello!',
            ...     token='secret-token',
            ... )
        """
        # Convert content to bytes if string
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        # Convert gemini:// to titan:// if needed
        if url.startswith("gemini://"):
            titan_url_base = "titan://" + url[9:]
        elif url.startswith("titan://"):
            titan_url_base = url
        else:
            raise ValueError("URL must use gemini:// or titan:// scheme")

        # Build Titan URL with parameters
        # Format: titan://host/path;size=N;mime=TYPE;token=TOKEN
        titan_url = f"{titan_url_base};size={len(content_bytes)};mime={mime_type}"
        if token:
            titan_url += f";token={token}"

        # Parse URL to get host and port (use the base URL without params)
        parsed = parse_url(titan_url_base.replace("titan://", "gemini://"))

        # Get event loop
        loop = asyncio.get_running_loop()

        # Create future for response
        response_future: asyncio.Future = loop.create_future()

        # Create protocol instance
        protocol = TitanClientProtocol(titan_url, content_bytes, response_future)

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
            raise TimeoutError(f"Upload timeout: {url}") from e
        finally:
            # Ensure transport is closed
            transport.close()

    async def delete(
        self,
        url: str,
        token: str | None = None,
    ) -> GeminiResponse:
        """Delete a resource via zero-byte Titan upload.

        In the Titan protocol, a zero-byte upload indicates deletion.
        The server may or may not support delete operations.

        Args:
            url: The target URL. Can be either gemini:// or titan:// scheme.
            token: Optional authentication token for the server.

        Returns:
            A GeminiResponse from the server indicating success or failure.

        Raises:
            ValueError: If the URL is invalid.
            asyncio.TimeoutError: If the request times out.
            ConnectionError: If the connection fails.

        Examples:
            >>> # Delete a resource
            >>> response = await client.delete(
            ...     'gemini://example.com/uploads/old-file.gmi',
            ...     token='secret-token',
            ... )
            >>> if response.is_success():
            ...     print("Resource deleted")
        """
        return await self.upload(url, b"", mime_type="text/gemini", token=token)
