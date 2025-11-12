"""Integration tests for client-server communication.

These tests use a real Gemini server (from sample code) and the Nauyaca client
to test end-to-end functionality.
"""

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from nauyaca.client.session import GeminiClient

# Import server from sample code
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sample"))
from gemini_protocol import (  # type: ignore
    GeminiServerProtocol,
    create_self_signed_context,
)


@pytest.fixture
async def test_server(unused_tcp_port):
    """Start a test Gemini server on an unused port."""
    loop = asyncio.get_running_loop()

    # Create SSL context
    ssl_context = create_self_signed_context()

    # Start server
    server = await loop.create_server(
        lambda: GeminiServerProtocol(),
        "127.0.0.1",
        unused_tcp_port,
        ssl=ssl_context,
    )

    # Let server start
    await asyncio.sleep(0.1)

    yield unused_tcp_port

    # Cleanup
    server.close()
    await server.wait_closed()


@pytest.mark.integration
@pytest.mark.network
async def test_fetch_index_page(test_server):
    """Test fetching the index page from test server."""
    port = test_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.fetch(f"gemini://127.0.0.1:{port}/")

        assert response.status == 20
        assert response.mime_type == "text/gemini"
        assert "Welcome to Gemini" in response.body
        assert response.is_success()


@pytest.mark.integration
@pytest.mark.network
async def test_fetch_about_page(test_server):
    """Test fetching the about page from test server."""
    port = test_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.fetch(f"gemini://127.0.0.1:{port}/about.gmi")

        assert response.status == 20
        assert response.mime_type == "text/gemini"
        assert "About" in response.body


@pytest.mark.integration
@pytest.mark.network
async def test_fetch_not_found(test_server):
    """Test fetching a non-existent page returns 51."""
    port = test_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        response = await client.fetch(
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
            await client.fetch(f"gemini://127.0.0.1:{unused_tcp_port}/")


@pytest.mark.integration
@pytest.mark.network
async def test_multiple_requests(test_server):
    """Test making multiple sequential requests."""
    port = test_server

    async with GeminiClient(timeout=5.0, verify_ssl=False) as client:
        # Fetch index
        response1 = await client.fetch(f"gemini://127.0.0.1:{port}/")
        assert response1.status == 20

        # Fetch about
        response2 = await client.fetch(f"gemini://127.0.0.1:{port}/about.gmi")
        assert response2.status == 20

        # Fetch not found
        response3 = await client.fetch(
            f"gemini://127.0.0.1:{port}/missing",
            follow_redirects=False,
        )
        assert response3.status == 51
