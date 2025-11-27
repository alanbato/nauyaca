"""Tests for PyOpenSSL TLS integration."""

import pytest
from OpenSSL import SSL

from nauyaca.security.certificates import generate_self_signed_cert
from nauyaca.security.pyopenssl_tls import (
    create_pyopenssl_server_context,
    get_peer_certificate_from_connection,
    verify_callback,
    x509_to_cryptography,
)


class TestVerifyCallback:
    """Tests for the verify callback function."""

    def test_verify_callback_accepts_valid_cert(self):
        """Test that verify callback returns True for ok=True."""
        assert verify_callback(None, None, 0, 0, True) is True

    def test_verify_callback_accepts_invalid_cert(self):
        """Test that verify callback returns True even for ok=False."""
        # ok=False indicates OpenSSL rejected the cert, but we accept anyway
        assert verify_callback(None, None, 0, 0, False) is True

    def test_verify_callback_accepts_self_signed_error(self):
        """Test that verify callback accepts self-signed certs (error 18)."""
        # Error 18 is X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT
        assert verify_callback(None, None, 18, 0, False) is True

    def test_verify_callback_accepts_any_error_number(self):
        """Test that verify callback accepts any error number."""
        for errnum in [0, 10, 18, 19, 20, 21, 100]:
            assert verify_callback(None, None, errnum, 0, False) is True


class TestCreatePyOpenSSLServerContext:
    """Tests for PyOpenSSL server context creation."""

    def test_create_context_basic(self, tmp_path):
        """Test basic context creation."""
        cert_pem, key_pem = generate_self_signed_cert("localhost")
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        cert_file.write_bytes(cert_pem)
        key_file.write_bytes(key_pem)

        ctx = create_pyopenssl_server_context(
            str(cert_file),
            str(key_file),
            request_client_cert=False,
        )

        assert isinstance(ctx, SSL.Context)

    def test_create_context_with_client_cert_request(self, tmp_path):
        """Test context creation with client cert request enabled."""
        cert_pem, key_pem = generate_self_signed_cert("localhost")
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        cert_file.write_bytes(cert_pem)
        key_file.write_bytes(key_pem)

        ctx = create_pyopenssl_server_context(
            str(cert_file),
            str(key_file),
            request_client_cert=True,
        )

        assert isinstance(ctx, SSL.Context)

    def test_create_context_invalid_cert_file(self, tmp_path):
        """Test that invalid cert file raises error."""
        key_pem = generate_self_signed_cert("localhost")[1]
        key_file = tmp_path / "key.pem"
        key_file.write_bytes(key_pem)

        with pytest.raises(SSL.Error):
            create_pyopenssl_server_context(
                str(tmp_path / "nonexistent.pem"),
                str(key_file),
            )

    def test_create_context_invalid_key_file(self, tmp_path):
        """Test that invalid key file raises error."""
        cert_pem = generate_self_signed_cert("localhost")[0]
        cert_file = tmp_path / "cert.pem"
        cert_file.write_bytes(cert_pem)

        with pytest.raises(SSL.Error):
            create_pyopenssl_server_context(
                str(cert_file),
                str(tmp_path / "nonexistent.key"),
            )


class TestGetPeerCertificateFromConnection:
    """Tests for peer certificate extraction."""

    def test_get_peer_certificate_returns_none_on_error(self):
        """Test that get_peer_certificate_from_connection handles errors gracefully."""
        # Pass None which will cause an exception
        result = get_peer_certificate_from_connection(None)
        assert result is None


class TestX509ToCryptography:
    """Tests for X509 to cryptography conversion."""

    def test_convert_certificate(self, tmp_path):
        """Test converting a PyOpenSSL X509 to cryptography Certificate."""
        from cryptography import x509
        from OpenSSL import crypto

        # Generate a certificate
        cert_pem, _ = generate_self_signed_cert("localhost")

        # Load as PyOpenSSL X509
        pyopenssl_cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)

        # Convert to cryptography
        crypto_cert = x509_to_cryptography(pyopenssl_cert)

        # Verify it's a cryptography Certificate
        assert isinstance(crypto_cert, x509.Certificate)

        # Verify the subject matches
        subject_cn = crypto_cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME
        )[0].value
        assert subject_cn == "localhost"
