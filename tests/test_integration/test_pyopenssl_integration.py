"""Integration tests for PyOpenSSL-based client certificate support.

These tests verify that the PyOpenSSL TLS layer correctly accepts arbitrary
self-signed client certificates - the key feature that Python's standard ssl
module with OpenSSL 3.x fails to provide.

The key difference from test_middleware_integration.py is that these tests
do NOT pre-load the client certificate as a CA on the server. This proves
that PyOpenSSL's custom verification callback is working correctly.
"""

import asyncio
from pathlib import Path

import pytest

from nauyaca.client.session import GeminiClient
from nauyaca.security.certificates import (
    generate_self_signed_cert,
    get_certificate_fingerprint,
    load_certificate,
)
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server


def create_test_capsule(path: Path) -> None:
    """Create a standard test capsule directory with content."""
    path.mkdir(parents=True, exist_ok=True)

    (path / "index.gmi").write_text(
        "# Welcome to Gemini\n\n"
        "This is a test Gemini capsule.\n\n"
        "=> /about.gmi About this server\n"
    )

    (path / "about.gmi").write_text("# About\n\nThis is the about page.\n")

    (path / "protected.gmi").write_text(
        "# Protected Page\n\nThis page requires a client certificate.\n"
    )


@pytest.fixture
async def server_with_pyopenssl_cert_auth(unused_tcp_port, tmp_path):
    """Start server with certificate auth using PyOpenSSL.

    This fixture demonstrates the key advantage of PyOpenSSL:
    - Server does NOT pre-load client certificate as CA
    - Server accepts ANY self-signed client certificate
    - Validation happens via fingerprint at application layer

    Yields:
        dict: Contains 'port', and paths to cert files
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate server certificate
    server_cert_pem, server_key_pem = generate_self_signed_cert("localhost")
    server_cert_file = tmp_path / "server.pem"
    server_key_file = tmp_path / "server.key"
    server_cert_file.write_bytes(server_cert_pem)
    server_key_file.write_bytes(server_key_pem)

    # Generate client certificate for testing
    # NOTE: Server does NOT know about this cert beforehand!
    client_cert_pem, client_key_pem = generate_self_signed_cert("client")
    client_cert_file = tmp_path / "client.pem"
    client_key_file = tmp_path / "client.key"
    client_cert_file.write_bytes(client_cert_pem)
    client_key_file.write_bytes(client_key_pem)

    # Get client cert fingerprint
    client_cert = load_certificate(client_cert_file)
    client_fingerprint = get_certificate_fingerprint(client_cert)

    # Create certificate auth config that requires a certificate for all paths
    from nauyaca.server.middleware import CertificateAuthConfig, CertificateAuthPathRule

    cert_auth_config = CertificateAuthConfig(
        path_rules=[
            CertificateAuthPathRule(
                prefix="/",  # All paths
                require_cert=True,  # Require client certificate
            )
        ]
    )

    # Create server configuration
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=server_cert_file,
        keyfile=server_key_file,
        enable_rate_limiting=False,
    )

    # Start server - uses PyOpenSSL because certificate_auth_config requires certs
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=False,
            certificate_auth_config=cert_auth_config,
        )
    )

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield {
        "port": unused_tcp_port,
        "client_cert": client_cert_file,
        "client_key": client_key_file,
        "client_fingerprint": client_fingerprint,
        "tmp_path": tmp_path,
    }

    # Cleanup
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def server_with_optional_client_cert(unused_tcp_port, tmp_path):
    """Start server that requests but doesn't require client certificates.

    This tests the case where client certs are optional for TOFU-style
    authentication.

    Yields:
        dict: Contains 'port' and paths to cert files
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Generate server certificate
    server_cert_pem, server_key_pem = generate_self_signed_cert("localhost")
    server_cert_file = tmp_path / "server.pem"
    server_key_file = tmp_path / "server.key"
    server_cert_file.write_bytes(server_cert_pem)
    server_key_file.write_bytes(server_key_pem)

    # Generate client certificate for testing
    client_cert_pem, client_key_pem = generate_self_signed_cert("client")
    client_cert_file = tmp_path / "client.pem"
    client_key_file = tmp_path / "client.key"
    client_cert_file.write_bytes(client_cert_pem)
    client_key_file.write_bytes(client_key_pem)

    # Create server configuration with require_client_cert=True to trigger PyOpenSSL
    # This allows the server to accept ANY self-signed client certificate
    # without needing to pre-load it as a CA
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=server_cert_file,
        keyfile=server_key_file,
        enable_rate_limiting=False,
        require_client_cert=True,  # Triggers PyOpenSSL for self-signed cert support
    )

    # No certificate_auth_config means no middleware enforcement -
    # certs are requested but not required, and any cert is accepted
    server_task = asyncio.create_task(
        start_server(
            config,
            enable_rate_limiting=False,
        )
    )

    await asyncio.sleep(0.5)

    yield {
        "port": unused_tcp_port,
        "client_cert": client_cert_file,
        "client_key": client_key_file,
        "tmp_path": tmp_path,
    }

    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


# Tests for required client certificates


@pytest.mark.integration
@pytest.mark.network
async def test_pyopenssl_rejects_without_cert(server_with_pyopenssl_cert_auth):
    """Test that server returns 60 when client cert is required but not provided."""
    port = server_with_pyopenssl_cert_auth["port"]

    async with GeminiClient(
        timeout=5.0, verify_ssl=False, trust_on_first_use=False
    ) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/", follow_redirects=False)
        assert response.status == 60
        assert "certificate" in response.meta.lower()


@pytest.mark.integration
@pytest.mark.network
async def test_pyopenssl_accepts_arbitrary_self_signed_cert(
    server_with_pyopenssl_cert_auth,
):
    """Test that PyOpenSSL accepts arbitrary self-signed client certificates.

    This is the KEY test proving the PyOpenSSL integration works.
    The server has NOT pre-loaded this client certificate - it should
    accept ANY certificate and validate via fingerprint in middleware.
    """
    port = server_with_pyopenssl_cert_auth["port"]
    client_cert = server_with_pyopenssl_cert_auth["client_cert"]
    client_key = server_with_pyopenssl_cert_auth["client_key"]

    async with GeminiClient(
        timeout=5.0,
        verify_ssl=False,
        trust_on_first_use=False,
        client_cert=client_cert,
        client_key=client_key,
    ) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        # Should succeed - the server accepts any cert via PyOpenSSL
        assert response.status == 20
        assert "Welcome to Gemini" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_pyopenssl_accepts_new_unknown_cert(server_with_pyopenssl_cert_auth):
    """Test that PyOpenSSL accepts a completely new certificate.

    Generate a NEW certificate that the server has never seen and verify
    it still works. This proves PyOpenSSL's custom verification callback
    accepts any certificate.
    """
    port = server_with_pyopenssl_cert_auth["port"]
    tmp_path = server_with_pyopenssl_cert_auth["tmp_path"]

    # Generate a brand new certificate
    new_cert_pem, new_key_pem = generate_self_signed_cert("brand-new-client")
    new_cert_file = tmp_path / "new_client.pem"
    new_key_file = tmp_path / "new_client.key"
    new_cert_file.write_bytes(new_cert_pem)
    new_key_file.write_bytes(new_key_pem)

    async with GeminiClient(
        timeout=5.0,
        verify_ssl=False,
        trust_on_first_use=False,
        client_cert=new_cert_file,
        client_key=new_key_file,
    ) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        # Should succeed - PyOpenSSL accepts any cert
        assert response.status == 20
        assert "Welcome to Gemini" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_pyopenssl_multiple_different_clients(server_with_pyopenssl_cert_auth):
    """Test that multiple different clients with different certs can connect."""
    port = server_with_pyopenssl_cert_auth["port"]
    tmp_path = server_with_pyopenssl_cert_auth["tmp_path"]

    # Generate multiple client certificates
    clients = []
    for i in range(3):
        cert_pem, key_pem = generate_self_signed_cert(f"client-{i}")
        cert_file = tmp_path / f"client{i}.pem"
        key_file = tmp_path / f"client{i}.key"
        cert_file.write_bytes(cert_pem)
        key_file.write_bytes(key_pem)
        clients.append((cert_file, key_file))

    # Each client should be able to connect
    for i, (cert_file, key_file) in enumerate(clients):
        async with GeminiClient(
            timeout=5.0,
            verify_ssl=False,
            trust_on_first_use=False,
            client_cert=cert_file,
            client_key=key_file,
        ) as client:
            response = await client.get(f"gemini://127.0.0.1:{port}/")
            assert response.status == 20, f"Client {i} should succeed"


# Tests for optional client certificates


@pytest.mark.integration
@pytest.mark.network
async def test_optional_cert_allows_without_cert(server_with_optional_client_cert):
    """Test that server allows connection without cert when certs are optional."""
    port = server_with_optional_client_cert["port"]

    async with GeminiClient(
        timeout=5.0, verify_ssl=False, trust_on_first_use=False
    ) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        # Should succeed without a certificate
        assert response.status == 20
        assert "Welcome to Gemini" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_optional_cert_accepts_with_cert(server_with_optional_client_cert):
    """Test that server accepts connections with optional cert."""
    port = server_with_optional_client_cert["port"]
    client_cert = server_with_optional_client_cert["client_cert"]
    client_key = server_with_optional_client_cert["client_key"]

    async with GeminiClient(
        timeout=5.0,
        verify_ssl=False,
        trust_on_first_use=False,
        client_cert=client_cert,
        client_key=client_key,
    ) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/")
        # Should succeed with a certificate
        assert response.status == 20
        assert "Welcome to Gemini" in response.body
