"""Pytest configuration and shared fixtures for nauyaca tests."""

import socket
import ssl
from pathlib import Path

import pytest
from cryptography import x509

from nauyaca.security.certificates import generate_self_signed_cert
from nauyaca.security.tls import create_client_context
from nauyaca.security.tofu import TOFUDatabase


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


@pytest.fixture
def temp_tofu_db(tmp_path: Path) -> TOFUDatabase:
    """Create a temporary TOFU database for testing.

    Args:
        tmp_path: Pytest fixture providing temporary directory.

    Yields:
        TOFUDatabase instance using temporary database file.
    """
    db_path = tmp_path / "test_tofu.db"
    db = TOFUDatabase(db_path)

    yield db

    db.close()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_cert() -> x509.Certificate:
    """Generate a test certificate for testing.

    Returns:
        X.509 certificate for testing.
    """
    cert_pem, _ = generate_self_signed_cert("test.example.com")
    return x509.load_pem_x509_certificate(cert_pem)


@pytest.fixture
def test_cert_different() -> x509.Certificate:
    """Generate a different test certificate for testing certificate changes.

    Returns:
        X.509 certificate (different from test_cert).
    """
    cert_pem, _ = generate_self_signed_cert("test.example.com")
    return x509.load_pem_x509_certificate(cert_pem)
