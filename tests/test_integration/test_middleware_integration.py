"""Integration tests for middleware with real server-client interactions.

These tests verify that middleware (rate limiting, access control, etc.) works
correctly in a real end-to-end scenario with actual network connections.
"""

import asyncio
import ssl
from pathlib import Path

import pytest

from nauyaca.client.session import GeminiClient
from nauyaca.security.certificates import generate_self_signed_cert
from nauyaca.server.config import ServerConfig
from nauyaca.server.middleware import AccessControl, MiddlewareChain, RateLimiter
from nauyaca.server.protocol import GeminiServerProtocol
from nauyaca.server.server import start_server


def create_test_capsule(path: Path) -> None:
    """Create a standard test capsule directory with content.

    Args:
        path: Directory path where capsule will be created
    """
    path.mkdir(parents=True, exist_ok=True)

    # Create index page
    (path / "index.gmi").write_text(
        "# Welcome to Gemini\n\n"
        "This is a test Gemini capsule.\n\n"
        "=> /about.gmi About this server\n"
    )

    # Create about page
    (path / "about.gmi").write_text(
        "# About\n\nThis is the about page for the test server.\n"
    )


@pytest.fixture
async def server_with_rate_limiting(unused_tcp_port, tmp_path):
    """Start server with rate limiting enabled.

    Yields:
        tuple[int, RateLimiter]: Port number and rate limiter instance
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate self-signed certificate
    cert_pem, key_pem = generate_self_signed_cert("localhost")
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    # Create server configuration with rate limiting
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=cert_file,
        keyfile=key_file,
        enable_rate_limiting=True,
        rate_limit_capacity=3,  # Very low for testing
        rate_limit_refill_rate=1.0,  # 1 token per second
    )

    # Start server in background task with proper config
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=config.enable_rate_limiting,
            rate_limit_config=config.get_rate_limit_config(),
            access_control_config=config.get_access_control_config(),
        )
    )

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield unused_tcp_port

    # Cleanup: cancel server task
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def server_with_access_control(unused_tcp_port, tmp_path):
    """Start server with access control enabled.

    Yields:
        int: Port number
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate self-signed certificate
    cert_pem, key_pem = generate_self_signed_cert("localhost")
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    # Create server configuration with access control
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=cert_file,
        keyfile=key_file,
        enable_rate_limiting=False,
        access_control_allow_list=["127.0.0.1"],  # Only allow localhost
    )

    # Start server in background task with proper config
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=config.enable_rate_limiting,
            rate_limit_config=config.get_rate_limit_config(),
            access_control_config=config.get_access_control_config(),
        )
    )

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield unused_tcp_port

    # Cleanup: cancel server task
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def server_with_deny_list(unused_tcp_port, tmp_path):
    """Start server with deny list access control.

    Yields:
        int: Port number
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate self-signed certificate
    cert_pem, key_pem = generate_self_signed_cert("localhost")
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    # Create server configuration with deny list
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=cert_file,
        keyfile=key_file,
        enable_rate_limiting=False,
        access_control_deny_list=["127.0.0.1"],  # Deny localhost
    )

    # Start server in background task with proper config
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=config.enable_rate_limiting,
            rate_limit_config=config.get_rate_limit_config(),
            access_control_config=config.get_access_control_config(),
        )
    )

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield unused_tcp_port

    # Cleanup: cancel server task
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def server_with_all_middleware(unused_tcp_port, tmp_path):
    """Start server with both rate limiting and access control enabled.

    Yields:
        int: Port number
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate self-signed certificate
    cert_pem, key_pem = generate_self_signed_cert("localhost")
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    # Create server configuration with all middleware
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=cert_file,
        keyfile=key_file,
        enable_rate_limiting=True,
        rate_limit_capacity=5,
        rate_limit_refill_rate=1.0,
        access_control_allow_list=["127.0.0.1"],
    )

    # Start server in background task with proper config
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=config.enable_rate_limiting,
            rate_limit_config=config.get_rate_limit_config(),
            access_control_config=config.get_access_control_config(),
        )
    )

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield unused_tcp_port

    # Cleanup: cancel server task
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


# Rate Limiting Tests


@pytest.mark.integration
@pytest.mark.network
async def test_rate_limiting_allows_within_limit(server_with_rate_limiting):
    """Test that requests within rate limit are allowed."""
    port = server_with_rate_limiting

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # First request should succeed
        response1 = await client.get(f"gemini://127.0.0.1:{port}/")
        assert response1.status == 20
        assert "Welcome to Gemini" in response1.body

        # Second request should also succeed (within capacity)
        response2 = await client.get(f"gemini://127.0.0.1:{port}/about.gmi")
        assert response2.status == 20
        assert "About" in response2.body


@pytest.mark.integration
@pytest.mark.network
async def test_rate_limiting_blocks_excessive_requests(server_with_rate_limiting):
    """Test that requests exceeding rate limit are blocked with 44 status."""
    port = server_with_rate_limiting

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Make many rapid requests - capacity is 3, so eventually we'll hit the limit
        # Token bucket starts full with 3 tokens and refills at 1 token/second
        rate_limited = False
        for _i in range(10):  # Make 10 rapid requests
            response = await client.get(
                f"gemini://127.0.0.1:{port}/", follow_redirects=False
            )
            if response.status == 44:
                rate_limited = True
                assert (
                    "rate limit" in response.meta.lower()
                    or "slow down" in response.meta.lower()
                )
                break

        assert rate_limited, "Should have been rate limited within 10 rapid requests"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
async def test_rate_limiting_refills_over_time(server_with_rate_limiting):
    """Test that rate limit tokens refill over time."""
    port = server_with_rate_limiting

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Exhaust the rate limit with rapid requests
        rate_limited = False
        for _i in range(10):
            response = await client.get(
                f"gemini://127.0.0.1:{port}/", follow_redirects=False
            )
            if response.status == 44:
                rate_limited = True
                break

        assert rate_limited, "Should have been rate limited"

        # Wait for tokens to refill (refill rate is 1 token/second, wait for 2 tokens)
        await asyncio.sleep(2.5)

        # Should now be able to make requests again
        response = await client.get(f"gemini://127.0.0.1:{port}/", follow_redirects=False)
        assert response.status == 20


# Access Control Tests


@pytest.mark.integration
@pytest.mark.network
async def test_access_control_allows_permitted_ip(server_with_access_control):
    """Test that allowed IPs can access the server."""
    port = server_with_access_control

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # 127.0.0.1 is in allowed_ips, so this should succeed
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        assert response.status == 20
        assert "Welcome to Gemini" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_access_control_blocks_denied_ip(server_with_deny_list):
    """Test that denied IPs are blocked with 53 status."""
    port = server_with_deny_list

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # 127.0.0.1 is in denied_ips, so this should be blocked
        response = await client.get(f"gemini://127.0.0.1:{port}/", follow_redirects=False)
        # PROXY REQUEST REFUSED (used for access denied)
        assert response.status == 53
        assert (
            "access denied" in response.meta.lower()
            or "forbidden" in response.meta.lower()
        )


# Middleware Chain Tests


@pytest.mark.integration
@pytest.mark.network
async def test_middleware_chain_access_control_first(server_with_all_middleware):
    """Test middleware chain order (access control before rate limiting)."""
    port = server_with_all_middleware

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # With both middleware enabled and IP allowed, requests should succeed
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        assert response.status == 20
        assert "Welcome to Gemini" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_middleware_chain_both_active(server_with_all_middleware):
    """Test that both middleware components work together correctly."""
    port = server_with_all_middleware

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Make rapid requests - should eventually hit rate limit
        # (not access denied)
        rate_limited = False
        successful_requests = 0

        for _i in range(15):  # Make enough requests to exceed capacity
            response = await client.get(
                f"gemini://127.0.0.1:{port}/", follow_redirects=False
            )
            if response.status == 20:
                successful_requests += 1
            elif response.status == 44:
                rate_limited = True
                break
            elif response.status == 53:
                msg = "Got access denied (53) instead of rate limit (44)"
                pytest.fail(msg)

        assert rate_limited, "Should have been rate limited"
        assert successful_requests >= 5, (
            f"Should have had at least 5 successful requests, got {successful_requests}"
        )


@pytest.mark.integration
@pytest.mark.network
async def test_different_paths_with_middleware(server_with_rate_limiting):
    """Test that middleware applies to all paths, not just index."""
    port = server_with_rate_limiting

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Test that rate limiting works across different paths
        paths = ["/", "/about.gmi", "/notfound.gmi", "/"]

        # Make requests to different paths rapidly
        rate_limited = False
        for i in range(10):
            path = paths[i % len(paths)]
            response = await client.get(
                f"gemini://127.0.0.1:{port}{path}",
                follow_redirects=False,
            )
            if response.status == 44:
                rate_limited = True
                break
            # Other status codes (20, 51) are fine, checking for rate limit

        assert rate_limited, "Should have been rate limited across different paths"


@pytest.mark.integration
@pytest.mark.network
async def test_error_responses_with_middleware(server_with_rate_limiting):
    """Test that error responses (like 51 NOT FOUND) still count against rate limit."""
    port = server_with_rate_limiting

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Make rapid requests to non-existent pages
        # Should eventually hit rate limit
        rate_limited = False
        not_found_count = 0

        for i in range(10):
            response = await client.get(
                f"gemini://127.0.0.1:{port}/missing{i}.gmi",
                follow_redirects=False,
            )
            if response.status == 51:
                not_found_count += 1
            elif response.status == 44:
                rate_limited = True
                break

        assert rate_limited, "Should have been rate limited even for 404 requests"
        assert not_found_count > 0, (
            "Should have received some NOT FOUND responses before rate limiting"
        )
