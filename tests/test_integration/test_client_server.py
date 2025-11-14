"""Integration tests for client-server communication.

These tests use the production Nauyaca server and client to test end-to-end
functionality with real network connections and TLS.
"""

import asyncio
import ssl
from pathlib import Path

import pytest

from nauyaca.client.session import GeminiClient
from nauyaca.security.certificates import generate_self_signed_cert
from nauyaca.server.config import ServerConfig
from nauyaca.server.handler import StaticFileHandler
from nauyaca.server.protocol import GeminiServerProtocol
from nauyaca.server.router import Router, RouteType
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
async def lightweight_server(unused_tcp_port, tmp_path):
    """Start a lightweight test Gemini server using GeminiServerProtocol directly.

    This fixture provides fast startup/teardown for basic integration tests.
    Uses minimal setup without middleware for performance.

    Yields:
        int: The port number the server is listening on
    """
    # Create test capsule
    capsule = tmp_path / "capsule"
    create_test_capsule(capsule)

    # Setup router with static file handler
    router = Router()
    handler = StaticFileHandler(capsule)
    router.add_route("/", handler.handle, RouteType.PREFIX)

    # Generate self-signed certificate for testing
    cert_pem, key_pem = generate_self_signed_cert("localhost")

    # Create temporary cert files
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    # Create SSL context
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(str(cert_file), str(key_file))
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Start server
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: GeminiServerProtocol(router.route),
        "127.0.0.1",
        unused_tcp_port,
        ssl=ssl_context,
    )

    # Wait for server to be ready
    await asyncio.sleep(0.1)

    yield unused_tcp_port

    # Cleanup
    server.close()
    await server.wait_closed()


@pytest.fixture
async def full_server(unused_tcp_port, tmp_path):
    """Start full production Gemini server with all capabilities.

    This fixture uses the production start_server() function with ServerConfig.
    Suitable for testing middleware integration and full production behavior.
    Currently configured with middleware disabled for basic tests.

    Yields:
        int: The port number the server is listening on
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

    # Create server configuration
    config = ServerConfig(
        host="127.0.0.1",
        port=unused_tcp_port,
        document_root=capsule,
        certfile=cert_file,
        keyfile=key_file,
        enable_rate_limiting=False,  # Disable for basic tests
        enable_access_control=False,  # Disable for basic tests
    )

    # Start server in background task
    server_task = asyncio.create_task(start_server(config))

    # Wait for server to start
    await asyncio.sleep(0.5)

    yield unused_tcp_port

    # Cleanup: cancel server task
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.mark.integration
@pytest.mark.network
async def test_get_index_page(lightweight_server):
    """Test getting the index page from test server."""
    port = lightweight_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/")

        assert response.status == 20
        assert response.mime_type == "text/gemini"
        assert "Welcome to Gemini" in response.body
        assert response.is_success()


@pytest.mark.integration
@pytest.mark.network
async def test_get_about_page(lightweight_server):
    """Test getting the about page from test server."""
    port = lightweight_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.get(f"gemini://127.0.0.1:{port}/about.gmi")

        assert response.status == 20
        assert response.mime_type == "text/gemini"
        assert "About" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_get_not_found(lightweight_server):
    """Test getting a non-existent page returns 51."""
    port = lightweight_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.get(
            f"gemini://127.0.0.1:{port}/notfound.gmi",
            follow_redirects=False,
        )

        assert response.status == 51
        assert response.meta == "Not found"
        assert response.body is None


@pytest.mark.integration
@pytest.mark.network
async def test_connection_refused(unused_tcp_port):
    """Test that connection failure is handled correctly."""
    # Don't start a server, so connection will be refused

    async with GeminiClient(timeout=0.5, verify_ssl=False) as client:
        with pytest.raises(ConnectionError, match="Connection failed"):
            await client.get(f"gemini://127.0.0.1:{unused_tcp_port}/")


@pytest.mark.integration
@pytest.mark.network
async def test_multiple_requests(lightweight_server):
    """Test making multiple sequential requests."""
    port = lightweight_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Get index
        response1 = await client.get(f"gemini://127.0.0.1:{port}/")
        assert response1.status == 20

        # Get about
        response2 = await client.get(f"gemini://127.0.0.1:{port}/about.gmi")
        assert response2.status == 20

        # Get not found
        response3 = await client.get(
            f"gemini://127.0.0.1:{port}/missing",
            follow_redirects=False,
        )
        assert response3.status == 51
