"""PyOpenSSL-based TLS for accepting self-signed client certificates.

This module provides TLS context creation using PyOpenSSL instead of Python's
standard ssl module. The key advantage is the ability to use a custom verification
callback that accepts ANY client certificate (including self-signed), allowing
actual validation to happen at the application layer via fingerprint checking.

Background:
- Python's ssl module with OpenSSL 3.x and CERT_OPTIONAL silently rejects
  self-signed client certificates when no CA certificates are loaded
- This prevents arbitrary Gemini clients (with their own self-signed certs)
  from connecting to servers
- PyOpenSSL allows custom verification callbacks that can accept any certificate
"""

from cryptography import x509
from OpenSSL import SSL, crypto


def verify_callback(
    conn: SSL.Connection,
    cert: crypto.X509,
    errnum: int,
    depth: int,
    ok: int,
) -> bool:
    """Custom verification callback that accepts any certificate.

    This allows self-signed client certificates. Actual validation
    (fingerprint checking) happens at the application layer via
    CertificateAuth middleware.

    Args:
        conn: The SSL connection object.
        cert: The certificate being verified.
        errnum: The error number (e.g., 18 for self-signed).
        depth: Certificate chain depth.
        ok: Whether OpenSSL considers the cert valid (ignored).

    Returns:
        Always True - we validate via fingerprint in middleware.
    """
    return True


def create_pyopenssl_server_context(
    certfile: str,
    keyfile: str,
    request_client_cert: bool = False,
) -> SSL.Context:
    """Create a PyOpenSSL context for server connections.

    Unlike Python's ssl module, this accepts ANY client certificate
    (including self-signed) when request_client_cert=True.

    Args:
        certfile: Path to server certificate file (PEM format).
        keyfile: Path to server private key file (PEM format).
        request_client_cert: Whether to request client certificates.

    Returns:
        A PyOpenSSL SSL.Context configured for server connections.

    Example:
        >>> ctx = create_pyopenssl_server_context(
        ...     "server.pem",
        ...     "server-key.pem",
        ...     request_client_cert=True,
        ... )
    """
    ctx = SSL.Context(SSL.TLS_SERVER_METHOD)

    # Set minimum TLS version (Gemini requires TLS 1.2+)
    ctx.set_min_proto_version(SSL.TLS1_2_VERSION)

    # Load server certificate and key
    ctx.use_certificate_file(certfile, crypto.FILETYPE_PEM)
    ctx.use_privatekey_file(keyfile, crypto.FILETYPE_PEM)

    if request_client_cert:
        # Request client cert with custom callback that accepts all
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
    else:
        ctx.set_verify(SSL.VERIFY_NONE, lambda *args: True)

    return ctx


def get_peer_certificate_from_connection(conn: SSL.Connection) -> crypto.X509 | None:
    """Extract peer certificate from PyOpenSSL connection.

    Args:
        conn: The PyOpenSSL SSL connection.

    Returns:
        The peer's X509 certificate, or None if not available.
    """
    try:
        return conn.get_peer_certificate()
    except Exception:
        return None


def x509_to_cryptography(cert: crypto.X509) -> x509.Certificate:
    """Convert PyOpenSSL X509 to cryptography Certificate.

    This allows using the existing certificate utilities (fingerprinting, etc.)
    which are built on the cryptography library.

    Args:
        cert: PyOpenSSL X509 certificate.

    Returns:
        Cryptography library Certificate object.

    Example:
        >>> pyopenssl_cert = conn.get_peer_certificate()
        >>> crypto_cert = x509_to_cryptography(pyopenssl_cert)
        >>> fingerprint = get_certificate_fingerprint(crypto_cert)
    """
    der_bytes = crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
    return x509.load_der_x509_certificate(der_bytes)
