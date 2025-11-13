"""Server middleware for rate limiting, access control, and request processing.

Middleware components can be chained together to process requests before
they reach handlers.
"""

import asyncio
import time
from dataclasses import dataclass
from ipaddress import (
    IPv4Network,
    IPv6Network,
    ip_address,
    ip_network,
)
from typing import Protocol


class Middleware(Protocol):
    """Protocol for middleware components."""

    async def process_request(
        self, request_url: str, client_ip: str
    ) -> tuple[bool, str | None]:
        """Process a request.

        Args:
            request_url: The requested URL.
            client_ip: The client's IP address.

        Returns:
            Tuple of (allow, error_response):
            - (True, None) if request should proceed
            - (False, gemini_response) if request should be rejected
        """
        ...


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Token bucket parameters
    capacity: int = 10  # Maximum burst size
    refill_rate: float = 1.0  # Tokens per second

    # Rate limit response
    retry_after: int = 30  # Seconds to wait before retrying


class TokenBucket:
    """Token bucket for rate limiting a single client."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (burst size).
            refill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were available and consumed, False otherwise.
        """
        now = time.monotonic()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_update = now

        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False


class RateLimiter:
    """Rate limiting middleware using token bucket algorithm.

    Tracks per-IP request rates and returns status 44 (SLOW DOWN) when
    limits are exceeded.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration. Uses defaults if None.
        """
        self.config = config or RateLimitConfig()
        self.buckets: dict[str, TokenBucket] = {}
        self._cleanup_task: asyncio.Task | None = None

    def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Periodically clean up old token buckets."""
        while True:
            await asyncio.sleep(300)  # Clean every 5 minutes

            now = time.monotonic()
            to_remove = [
                ip
                for ip, bucket in self.buckets.items()
                if now - bucket.last_update > 600  # 10 minutes idle
            ]

            for ip in to_remove:
                del self.buckets[ip]

    async def process_request(
        self, request_url: str, client_ip: str
    ) -> tuple[bool, str | None]:
        """Process request with rate limiting.

        Args:
            request_url: The requested URL.
            client_ip: The client's IP address.

        Returns:
            Tuple of (allow, error_response).
        """
        # Get or create token bucket for this IP
        if client_ip not in self.buckets:
            self.buckets[client_ip] = TokenBucket(
                self.config.capacity, self.config.refill_rate
            )

        bucket = self.buckets[client_ip]

        # Try to consume token
        if bucket.consume():
            return True, None

        # Rate limit exceeded - return 44 SLOW DOWN
        retry_after = self.config.retry_after
        response = f"44 Rate limit exceeded. Retry after {retry_after} seconds\r\n"
        return False, response


@dataclass
class AccessControlConfig:
    """Configuration for IP-based access control."""

    # Allow/deny lists (CIDR notation supported)
    allow_list: list[str] | None = None  # If set, only these IPs allowed
    deny_list: list[str] | None = None  # If set, these IPs denied

    # Default policy when not in any list
    default_allow: bool = True


class AccessControl:
    """IP-based access control middleware.

    Supports allow/deny lists with CIDR notation.
    Returns status 53 (PROXY REQUEST REFUSED) for blocked IPs.
    """

    def __init__(self, config: AccessControlConfig | None = None):
        """Initialize access control.

        Args:
            config: Access control configuration. Uses defaults if None.
        """
        self.config = config or AccessControlConfig()

        # Parse allow list
        self.allow_networks: list[IPv4Network | IPv6Network] = []
        if self.config.allow_list:
            for cidr in self.config.allow_list:
                try:
                    self.allow_networks.append(ip_network(cidr))
                except ValueError:
                    # Try as single IP
                    try:
                        self.allow_networks.append(ip_network(f"{cidr}/32"))
                    except ValueError:
                        # Try IPv6
                        self.allow_networks.append(ip_network(f"{cidr}/128"))

        # Parse deny list
        self.deny_networks: list[IPv4Network | IPv6Network] = []
        if self.config.deny_list:
            for cidr in self.config.deny_list:
                try:
                    self.deny_networks.append(ip_network(cidr))
                except ValueError:
                    # Try as single IP
                    try:
                        self.deny_networks.append(ip_network(f"{cidr}/32"))
                    except ValueError:
                        # Try IPv6
                        self.deny_networks.append(ip_network(f"{cidr}/128"))

    def _is_allowed(self, ip: str) -> bool:
        """Check if an IP is allowed.

        Args:
            ip: IP address string.

        Returns:
            True if allowed, False if denied.
        """
        try:
            ip_obj = ip_address(ip)
        except ValueError:
            # Invalid IP - deny
            return False

        # Check deny list first (takes precedence)
        for network in self.deny_networks:
            if ip_obj in network:
                return False

        # Check allow list
        if self.allow_networks:
            for network in self.allow_networks:
                if ip_obj in network:
                    return True
            # Not in allow list
            return False

        # No allow list - use default policy
        return self.config.default_allow

    async def process_request(
        self, request_url: str, client_ip: str
    ) -> tuple[bool, str | None]:
        """Process request with access control.

        Args:
            request_url: The requested URL.
            client_ip: The client's IP address.

        Returns:
            Tuple of (allow, error_response).
        """
        if self._is_allowed(client_ip):
            return True, None

        # IP is blocked
        response = "53 Access denied\r\n"
        return False, response


class MiddlewareChain:
    """Chain multiple middleware components together."""

    def __init__(self, middlewares: list[Middleware]):
        """Initialize middleware chain.

        Args:
            middlewares: List of middleware instances.
        """
        self.middlewares = middlewares

    async def process_request(
        self, request_url: str, client_ip: str
    ) -> tuple[bool, str | None]:
        """Process request through all middleware.

        Args:
            request_url: The requested URL.
            client_ip: The client's IP address.

        Returns:
            Tuple of (allow, error_response). Returns first rejection.
        """
        for middleware in self.middlewares:
            allow, response = await middleware.process_request(request_url, client_ip)
            if not allow:
                return False, response

        return True, None
