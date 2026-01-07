"""Proxy handler for forwarding Gemini requests to upstream servers.

This module provides the ProxyHandler class for reverse proxying
Gemini requests to upstream Gemini servers.
"""

import logging

from ..client.session import GeminiClient
from ..protocol.request import GeminiRequest
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode
from .handler import RequestHandler

logger = logging.getLogger(__name__)


class ProxyHandler(RequestHandler):
    """Handler that proxies requests to an upstream Gemini server.

    This handler forwards requests to a configured upstream server and
    returns the upstream's response to the client. Useful for reverse
    proxies, load balancing, and capsule aggregation.

    The handler passes through all response types from upstream including
    redirects (3x), input requests (1x), errors (4x/5x), and success (2x).

    Attributes:
        upstream: Upstream server URL (e.g., "gemini://backend.example.com:1965").
        prefix: The path prefix this handler matches (for strip_prefix logic).
        strip_prefix: If True, remove the matched prefix from the path before
            forwarding to upstream.
        timeout: Request timeout in seconds.

    Examples:
        >>> # Simple reverse proxy
        >>> handler = ProxyHandler(
        ...     upstream="gemini://backend:1965",
        ...     prefix="/api/",
        ...     strip_prefix=True,
        ... )
        >>> # Request to /api/resource -> forwards as /resource to backend

        >>> # Mirror proxy (keep path as-is)
        >>> handler = ProxyHandler(
        ...     upstream="gemini://mirror:1965",
        ...     prefix="/mirror/",
        ...     strip_prefix=False,
        ... )
        >>> # Request to /mirror/resource -> forwards as /mirror/resource
    """

    def __init__(
        self,
        upstream: str,
        prefix: str = "/",
        strip_prefix: bool = False,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the proxy handler.

        Args:
            upstream: Upstream server URL (must use gemini:// scheme).
            prefix: The path prefix this handler matches.
            strip_prefix: Whether to strip matched prefix from forwarded path.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If upstream URL doesn't use gemini:// scheme.
        """
        if not upstream.startswith("gemini://"):
            raise ValueError("Upstream URL must use gemini:// scheme")

        # Remove trailing slash for consistent path joining
        self.upstream = upstream.rstrip("/")
        self.prefix = prefix
        self.strip_prefix = strip_prefix
        self.timeout = timeout

        # Create client for upstream requests
        # Disable TOFU - proxy acts as transparent relay, not validator
        self._client = GeminiClient(
            timeout=timeout,
            verify_ssl=False,
            trust_on_first_use=False,
        )

        logger.debug(
            "ProxyHandler initialized: upstream=%s, prefix=%s, strip_prefix=%s",
            self.upstream,
            self.prefix,
            self.strip_prefix,
        )

    def handle(self, request: GeminiRequest) -> GeminiResponse:
        """Handle request by forwarding to upstream server.

        This method returns a coroutine that will be detected and awaited
        by the protocol layer.

        Args:
            request: The incoming request to proxy.

        Returns:
            Coroutine that resolves to response from upstream or error response.
        """
        # Return the coroutine - protocol layer will await it
        return self._handle_async(request)  # type: ignore[return-value]

    async def _handle_async(self, request: GeminiRequest) -> GeminiResponse:
        """Async implementation of request proxying.

        Args:
            request: The incoming request.

        Returns:
            Response from upstream server, or error response on failure.
        """
        # Build upstream path
        path = request.path

        # Strip prefix if configured
        # Only strip if it's a true path prefix (not partial like /api matching /apikey)
        if self.strip_prefix and path.startswith(self.prefix):
            remaining = path[len(self.prefix) :]
            # If prefix ends with /, any remaining is valid (e.g., /api/ + resource)
            # If prefix doesn't end with /, remaining must be empty or start with /
            # (e.g., /api -> /api or /api/resource, but not /apikey)
            prefix_ends_with_slash = self.prefix.endswith("/")
            is_valid_match = (
                prefix_ends_with_slash or remaining == "" or remaining.startswith("/")
            )
            if is_valid_match:
                path = remaining
                # Ensure path starts with /
                if not path.startswith("/"):
                    path = "/" + path

        # Build full upstream URL
        upstream_url = f"{self.upstream}{path}"

        # Add query string if present
        if request.query:
            upstream_url += f"?{request.query}"

        logger.info(
            "Proxying request: %s -> %s",
            request.raw_url,
            upstream_url,
        )

        try:
            # Forward request to upstream
            # Don't follow redirects - pass them through to client
            response = await self._client.get(
                upstream_url,
                follow_redirects=False,
            )

            logger.info(
                "Upstream response: %s -> status=%d",
                upstream_url,
                response.status,
            )

            # Pass through the response as-is
            return response

        except TimeoutError:
            logger.warning(
                "Upstream timeout: %s (timeout=%ss)",
                upstream_url,
                self.timeout,
            )
            return GeminiResponse(
                status=StatusCode.PROXY_ERROR.value,
                meta="Upstream timeout",
            )

        except ConnectionError as e:
            logger.warning(
                "Upstream connection failed: %s - %s",
                upstream_url,
                str(e),
            )
            return GeminiResponse(
                status=StatusCode.PROXY_ERROR.value,
                meta=f"Upstream connection failed: {str(e)}",
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(
                "Proxy error: %s - %s",
                upstream_url,
                str(e),
            )
            return GeminiResponse(
                status=StatusCode.PROXY_ERROR.value,
                meta=f"Proxy error: {str(e)}",
            )
