"""Pytest configuration and shared fixtures for nauyaca tests."""

import asyncio
import ssl
from collections.abc import AsyncGenerator

import pytest

from nauyaca.security.tls import create_client_context, create_server_context


@pytest.fixture
def client_ssl_context() -> ssl.SSLContext:
    """Create a test SSL context for client connections (no verification)."""
    return create_client_context(
        verify_mode=ssl.CERT_NONE,
        check_hostname=False,
    )


@pytest.fixture
async def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
