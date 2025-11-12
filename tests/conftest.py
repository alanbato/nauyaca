"""Pytest configuration and shared fixtures for nauyaca tests."""

import asyncio
import socket
import ssl

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
def unused_tcp_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
