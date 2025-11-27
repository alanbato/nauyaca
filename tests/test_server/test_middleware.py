"""Tests for server middleware."""

import asyncio
import time

import pytest

from nauyaca.server.middleware import (
    AccessControl,
    AccessControlConfig,
    CertificateAuth,
    CertificateAuthConfig,
    MiddlewareChain,
    RateLimitConfig,
    RateLimiter,
    TokenBucket,
)


def test_token_bucket_consume():
    """Test token bucket consumption."""
    bucket = TokenBucket(capacity=5, refill_rate=1.0)

    # Should be able to consume up to capacity
    assert bucket.consume(1)
    assert bucket.consume(1)
    assert bucket.consume(1)
    assert bucket.consume(1)
    assert bucket.consume(1)

    # Should fail when empty
    assert not bucket.consume(1)


def test_token_bucket_refill():
    """Test token bucket refilling."""
    bucket = TokenBucket(capacity=5, refill_rate=10.0)  # Fast refill

    # Consume all
    for _ in range(5):
        assert bucket.consume(1)

    # Should be empty now
    assert not bucket.consume(1)

    # Wait for refill (0.2s should refill 2 tokens at 10 tokens/sec)
    time.sleep(0.2)

    assert bucket.consume(1)
    assert bucket.consume(1)
    assert not bucket.consume(1)  # Only 2 refilled


def test_token_bucket_max_capacity():
    """Test that token bucket doesn't exceed capacity."""
    bucket = TokenBucket(capacity=3, refill_rate=100.0)  # Very fast refill

    # Consume 1 token
    assert bucket.consume(1)

    # Wait long enough to refill much more than capacity
    time.sleep(0.1)  # Should try to refill 10 tokens, but capped at 3

    # Should only have capacity tokens available (started with 3, used 1, refilled to 3)
    assert bucket.consume(1)
    assert bucket.consume(1)
    assert bucket.consume(1)
    assert not bucket.consume(1)  # Only 3 available, not more


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    """Test rate limiter allows requests within limit."""
    config = RateLimitConfig(capacity=3, refill_rate=1.0)
    limiter = RateLimiter(config)

    # First 3 requests should succeed
    for _ in range(3):
        allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
        assert allow


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Test rate limiter blocks requests over limit."""
    config = RateLimitConfig(capacity=2, refill_rate=1.0)
    limiter = RateLimiter(config)

    # First 2 requests succeed
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert allow
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert allow

    # Third request blocked
    allow, response = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert not allow
    assert response is not None
    assert "44" in response
    assert "Rate limit exceeded" in response


@pytest.mark.asyncio
async def test_rate_limiter_per_ip():
    """Test rate limiter tracks per-IP."""
    config = RateLimitConfig(capacity=1, refill_rate=1.0)
    limiter = RateLimiter(config)

    # Different IPs should have separate buckets
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert allow

    # First IP exhausted, but second IP should still work
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.2")
    assert allow  # Different IP, should succeed

    # Both IPs should now be exhausted
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert not allow

    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.2")
    assert not allow


@pytest.mark.asyncio
async def test_rate_limiter_cleanup():
    """Test rate limiter cleanup task can be started and stopped."""
    config = RateLimitConfig(capacity=10, refill_rate=1.0)
    limiter = RateLimiter(config)

    # Start cleanup task
    limiter.start()
    assert limiter._cleanup_task is not None

    # Add some IPs
    await limiter.process_request("gemini://test/", "192.168.1.1")
    await limiter.process_request("gemini://test/", "192.168.1.2")

    # Stop cleanup task
    await limiter.stop()
    assert limiter._cleanup_task.cancelled() or limiter._cleanup_task.done()


@pytest.mark.asyncio
async def test_access_control_allow_list():
    """Test access control with allow list."""
    config = AccessControlConfig(allow_list=["192.168.1.0/24"], default_allow=False)
    acl = AccessControl(config)

    # IP in allow list should be allowed
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.100")
    assert allow

    # IP not in allow list should be denied
    allow, response = await acl.process_request("gemini://test/", "10.0.0.1")
    assert not allow
    assert response is not None
    assert "53" in response
    assert "Access denied" in response


@pytest.mark.asyncio
async def test_access_control_deny_list():
    """Test access control with deny list."""
    config = AccessControlConfig(deny_list=["203.0.113.0/24"], default_allow=True)
    acl = AccessControl(config)

    # IP in deny list should be blocked
    allow, response = await acl.process_request("gemini://test/", "203.0.113.50")
    assert not allow
    assert response is not None
    assert "53" in response

    # Other IPs should be allowed
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.1")
    assert allow


@pytest.mark.asyncio
async def test_access_control_single_ip():
    """Test access control with single IP (not CIDR)."""
    config = AccessControlConfig(allow_list=["192.168.1.100"], default_allow=False)
    acl = AccessControl(config)

    # Exact IP should be allowed
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.100")
    assert allow

    # Different IP should be denied
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.101")
    assert not allow


@pytest.mark.asyncio
async def test_access_control_default_allow():
    """Test access control with no lists uses default policy."""
    # Default allow
    config = AccessControlConfig(default_allow=True)
    acl = AccessControl(config)

    allow, _ = await acl.process_request("gemini://test/", "192.168.1.1")
    assert allow

    # Default deny
    config = AccessControlConfig(default_allow=False)
    acl = AccessControl(config)

    allow, _ = await acl.process_request("gemini://test/", "192.168.1.1")
    assert not allow


@pytest.mark.asyncio
async def test_access_control_deny_takes_precedence():
    """Test that deny list takes precedence over allow list."""
    config = AccessControlConfig(
        allow_list=["192.168.1.0/24"],
        deny_list=["192.168.1.100"],  # Block one specific IP in allowed range
        default_allow=False,
    )
    acl = AccessControl(config)

    # IP in allow range but also in deny list should be blocked
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.100")
    assert not allow

    # Other IPs in allow range should work
    allow, _ = await acl.process_request("gemini://test/", "192.168.1.50")
    assert allow


@pytest.mark.asyncio
async def test_access_control_invalid_ip():
    """Test access control handles invalid IP addresses."""
    config = AccessControlConfig(default_allow=True)
    acl = AccessControl(config)

    # Invalid IP should be denied
    allow, _ = await acl.process_request("gemini://test/", "not-an-ip")
    assert not allow


@pytest.mark.asyncio
async def test_middleware_chain_all_allow():
    """Test middleware chain when all middlewares allow."""
    # Create middlewares that all allow
    config1 = AccessControlConfig(default_allow=True)
    config2 = RateLimitConfig(capacity=10, refill_rate=1.0)

    acl = AccessControl(config1)
    limiter = RateLimiter(config2)

    chain = MiddlewareChain([acl, limiter])

    # Should allow when all middlewares allow
    allow, _ = await chain.process_request("gemini://test/", "192.168.1.1")
    assert allow


@pytest.mark.asyncio
async def test_middleware_chain_first_denies():
    """Test middleware chain stops at first denial."""
    # First middleware denies
    config1 = AccessControlConfig(deny_list=["192.168.1.0/24"], default_allow=True)
    config2 = RateLimitConfig(capacity=10, refill_rate=1.0)

    acl = AccessControl(config1)
    limiter = RateLimiter(config2)

    chain = MiddlewareChain([acl, limiter])

    # Should deny and return access control error (not rate limit)
    allow, response = await chain.process_request("gemini://test/", "192.168.1.100")
    assert not allow
    assert "53" in response  # Access control error, not 44 rate limit


@pytest.mark.asyncio
async def test_middleware_chain_second_denies():
    """Test middleware chain processes all until denial."""
    # First allows, second denies
    config1 = AccessControlConfig(default_allow=True)
    config2 = RateLimitConfig(capacity=0, refill_rate=1.0)  # No capacity = immediate deny

    acl = AccessControl(config1)
    limiter = RateLimiter(config2)

    chain = MiddlewareChain([acl, limiter])

    # Should deny with rate limit error
    allow, response = await chain.process_request("gemini://test/", "192.168.1.1")
    assert not allow
    assert "44" in response  # Rate limit error


@pytest.mark.asyncio
async def test_middleware_chain_empty():
    """Test middleware chain with no middlewares."""
    chain = MiddlewareChain([])

    # Should allow everything
    allow, _ = await chain.process_request("gemini://test/", "192.168.1.1")
    assert allow


@pytest.mark.asyncio
async def test_rate_limiter_refill_allows_more():
    """Test that rate limiter allows more requests after refill."""
    config = RateLimitConfig(capacity=1, refill_rate=5.0)  # 5 tokens per second
    limiter = RateLimiter(config)

    # First request succeeds
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert allow

    # Second request immediately fails
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert not allow

    # Wait for refill (0.3s should refill 1.5 tokens at 5/sec, so we get 1 token back)
    await asyncio.sleep(0.3)

    # Should succeed now
    allow, _ = await limiter.process_request("gemini://test/", "192.168.1.1")
    assert allow


# Certificate Authentication Tests


@pytest.mark.asyncio
async def test_certificate_auth_no_requirements():
    """Test certificate auth with no requirements allows all requests."""
    config = CertificateAuthConfig(require_cert=False, allowed_fingerprints=None)
    auth = CertificateAuth(config)

    # No cert provided - should allow
    allow, _ = await auth.process_request("gemini://test/", "192.168.1.1", None)
    assert allow

    # Cert provided - should also allow
    allow, _ = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:abc123"
    )
    assert allow


@pytest.mark.asyncio
async def test_certificate_auth_require_cert():
    """Test certificate auth when certificate is required."""
    config = CertificateAuthConfig(require_cert=True, allowed_fingerprints=None)
    auth = CertificateAuth(config)

    # No cert provided - should deny with status 60
    allow, response = await auth.process_request("gemini://test/", "192.168.1.1", None)
    assert not allow
    assert "60" in response

    # Cert provided - should allow (any cert is fine)
    allow, _ = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:abc123"
    )
    assert allow


@pytest.mark.asyncio
async def test_certificate_auth_fingerprint_whitelist():
    """Test certificate auth with fingerprint whitelist."""
    allowed = {"sha256:trusted1", "sha256:trusted2"}
    config = CertificateAuthConfig(require_cert=False, allowed_fingerprints=allowed)
    auth = CertificateAuth(config)

    # No cert - should deny (whitelist requires cert)
    allow, response = await auth.process_request("gemini://test/", "192.168.1.1", None)
    assert not allow
    assert "60" in response

    # Trusted cert - should allow
    allow, _ = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:trusted1"
    )
    assert allow

    # Untrusted cert - should deny with status 61
    allow, response = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:untrusted"
    )
    assert not allow
    assert "61" in response


@pytest.mark.asyncio
async def test_certificate_auth_combined_require_and_whitelist():
    """Test certificate auth with both require and whitelist."""
    allowed = {"sha256:authorized"}
    config = CertificateAuthConfig(require_cert=True, allowed_fingerprints=allowed)
    auth = CertificateAuth(config)

    # No cert - status 60
    allow, response = await auth.process_request("gemini://test/", "192.168.1.1", None)
    assert not allow
    assert "60" in response

    # Wrong cert - status 61
    allow, response = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:wrong"
    )
    assert not allow
    assert "61" in response

    # Correct cert - allowed
    allow, _ = await auth.process_request(
        "gemini://test/", "192.168.1.1", "sha256:authorized"
    )
    assert allow


@pytest.mark.asyncio
async def test_certificate_auth_in_middleware_chain():
    """Test certificate auth works in middleware chain."""
    cert_config = CertificateAuthConfig(require_cert=True)
    access_config = AccessControlConfig(default_allow=True)

    cert_auth = CertificateAuth(cert_config)
    access = AccessControl(access_config)

    chain = MiddlewareChain([cert_auth, access])

    # No cert - should fail at cert auth
    allow, response = await chain.process_request("gemini://test/", "192.168.1.1", None)
    assert not allow
    assert "60" in response

    # With cert - should pass both middlewares
    allow, _ = await chain.process_request("gemini://test/", "192.168.1.1", "sha256:any")
    assert allow
