"""Tests for TOFU client integration."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from nauyaca.client.protocol import GeminiClientProtocol
from nauyaca.client.session import GeminiClient
from nauyaca.security.tofu import CertificateChangedError, TOFUDatabase


class TestGeminiClientTOFU:
    """Test GeminiClient TOFU integration."""

    def test_client_initialization_with_tofu_enabled(self, tmp_path: Path):
        """Test client initialization with TOFU enabled."""
        client = GeminiClient(
            verify_ssl=True,
            trust_on_first_use=True,
            tofu_db_path=tmp_path / "tofu.db",
        )

        assert client.verify_ssl is True
        assert client.trust_on_first_use is True
        assert client.tofu_db is not None
        assert isinstance(client.tofu_db, TOFUDatabase)

        # Clean up
        client.tofu_db.close()

    def test_client_initialization_with_tofu_disabled(self):
        """Test client initialization with TOFU disabled."""
        client = GeminiClient(
            verify_ssl=False,
            trust_on_first_use=False,
        )

        assert client.verify_ssl is False
        assert client.trust_on_first_use is False
        assert client.tofu_db is None

    def test_client_initialization_verify_without_tofu(self):
        """Test client initialization with SSL verify but no TOFU."""
        client = GeminiClient(
            verify_ssl=True,
            trust_on_first_use=False,
        )

        assert client.verify_ssl is True
        assert client.trust_on_first_use is False
        assert client.tofu_db is None

    async def test_client_context_manager_closes_tofu_db(self, tmp_path: Path):
        """Test that context manager properly closes TOFU database."""
        db_path = tmp_path / "tofu.db"

        async with GeminiClient(
            verify_ssl=True,
            trust_on_first_use=True,
            tofu_db_path=db_path,
        ) as client:
            assert client.tofu_db is not None

        # After exiting context, database file should exist
        assert db_path.exists()


class TestTOFUDatabaseOperations:
    """Test TOFU database operations through the client."""

    def test_tofu_db_stores_certificate_on_trust(
        self, temp_tofu_db: TOFUDatabase, test_cert: x509.Certificate
    ):
        """Test that TOFU database stores certificate on trust."""
        temp_tofu_db.trust("example.com", 1965, test_cert)

        hosts = temp_tofu_db.list_hosts()
        assert len(hosts) == 1
        assert hosts[0]["hostname"] == "example.com"
        assert hosts[0]["port"] == 1965

    def test_tofu_db_validates_same_certificate(
        self, temp_tofu_db: TOFUDatabase, test_cert: x509.Certificate
    ):
        """Test that TOFU database validates same certificate."""
        # Trust first
        temp_tofu_db.trust("example.com", 1965, test_cert)

        # Verify same cert
        is_valid, message = temp_tofu_db.verify("example.com", 1965, test_cert)

        assert is_valid is True
        assert message == ""  # No message for valid cert

    def test_tofu_db_detects_certificate_change(
        self,
        temp_tofu_db: TOFUDatabase,
        test_cert: x509.Certificate,
        test_cert_different: x509.Certificate,
    ):
        """Test that TOFU database detects certificate change."""
        # Trust first cert
        temp_tofu_db.trust("example.com", 1965, test_cert)

        # Verify different cert
        is_valid, message = temp_tofu_db.verify(
            "example.com", 1965, test_cert_different
        )

        assert is_valid is False
        assert message == "changed"

    def test_tofu_db_recognizes_first_use(
        self, temp_tofu_db: TOFUDatabase, test_cert: x509.Certificate
    ):
        """Test that TOFU database recognizes first use."""
        is_valid, message = temp_tofu_db.verify("example.com", 1965, test_cert)

        assert is_valid is True
        assert message == "first_use"


class TestGeminiClientProtocolCertificateExtraction:
    """Test certificate extraction from client protocol."""

    async def test_get_peer_certificate_with_valid_cert(
        self, test_cert: x509.Certificate
    ):
        """Test getting peer certificate from transport."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://test.example.com/", future)

        # Mock transport with certificate
        mock_transport = Mock()
        cert_der = test_cert.public_bytes(encoding=serialization.Encoding.DER)
        mock_transport.get_extra_info.return_value = cert_der

        protocol.transport = mock_transport

        cert = protocol.get_peer_certificate()

        assert cert is not None
        assert isinstance(cert, x509.Certificate)
        mock_transport.get_extra_info.assert_called_once_with("peercert", True)

    async def test_get_peer_certificate_no_transport(self):
        """Test getting peer certificate when transport is None."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://test.example.com/", future)
        protocol.transport = None

        cert = protocol.get_peer_certificate()

        assert cert is None

    async def test_get_peer_certificate_no_cert_data(self):
        """Test getting peer certificate when no certificate data available."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://test.example.com/", future)

        # Mock transport returning None (no certificate)
        mock_transport = Mock()
        mock_transport.get_extra_info.return_value = None

        protocol.transport = mock_transport

        cert = protocol.get_peer_certificate()

        assert cert is None

    async def test_get_peer_certificate_invalid_cert_data(self):
        """Test getting peer certificate with invalid certificate data."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://test.example.com/", future)

        # Mock transport returning invalid certificate data
        mock_transport = Mock()
        mock_transport.get_extra_info.return_value = b"invalid certificate data"

        protocol.transport = mock_transport

        cert = protocol.get_peer_certificate()

        # Should return None for invalid certificate
        assert cert is None


class TestCertificateChangedError:
    """Test CertificateChangedError exception."""

    def test_certificate_changed_error_attributes(self):
        """Test CertificateChangedError has correct attributes."""
        error = CertificateChangedError(
            "example.com", 1965, "old_fingerprint", "new_fingerprint"
        )

        assert error.hostname == "example.com"
        assert error.port == 1965
        assert error.old_fingerprint == "old_fingerprint"
        assert error.new_fingerprint == "new_fingerprint"

    def test_certificate_changed_error_message(self):
        """Test CertificateChangedError message format."""
        error = CertificateChangedError("example.com", 1965, "abc123", "def456")

        error_msg = str(error)
        assert "example.com:1965" in error_msg
        assert "abc123" in error_msg
        assert "def456" in error_msg
