"""TLS context creation for Gemini protocol.

This module provides functions for creating SSL/TLS contexts for both
client and server connections, following Gemini protocol requirements.
"""

import ssl


def create_client_context(
    verify_mode: ssl.VerifyMode = ssl.CERT_NONE,
    check_hostname: bool = False,
    certfile: str | None = None,
    keyfile: str | None = None,
) -> ssl.SSLContext:
    """Create an SSL context for Gemini client connections.

    The Gemini protocol requires TLS 1.2 or higher. This function creates
    an SSL context configured for client connections.

    Args:
        verify_mode: SSL certificate verification mode. Default is CERT_NONE
            for testing/development. Use CERT_REQUIRED with proper TOFU
            validation for production.
        check_hostname: Whether to check that the certificate hostname matches
            the server hostname. Default is False (for testing/development).
        certfile: Optional path to client certificate file (for client cert auth).
        keyfile: Optional path to client private key file (for client cert auth).

    Returns:
        An SSL context configured for Gemini client connections.

    Examples:
        >>> # Testing mode - accept all certificates
        >>> context = create_client_context()

        >>> # Production mode with TOFU (implement custom verification)
        >>> context = create_client_context(
        ...     verify_mode=ssl.CERT_REQUIRED,
        ...     check_hostname=True
        ... )

        >>> # With client certificate authentication
        >>> context = create_client_context(
        ...     certfile='client.pem',
        ...     keyfile='client-key.pem'
        ... )
    """
    # Create default SSL context
    context = ssl.create_default_context()

    # Set minimum TLS version (Gemini requires TLS 1.2+)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Configure certificate verification
    context.check_hostname = check_hostname
    context.verify_mode = verify_mode

    # Load client certificate if provided
    if certfile and keyfile:
        context.load_cert_chain(certfile, keyfile)

    return context


def create_server_context(
    certfile: str,
    keyfile: str,
    request_client_cert: bool = False,
    client_ca_certs: list[str] | None = None,
) -> ssl.SSLContext:
    """Create an SSL context for Gemini server connections.

    Args:
        certfile: Path to server certificate file.
        keyfile: Path to server private key file.
        request_client_cert: Whether to request client certificates.
            When True, the server will ask clients to send a certificate.
            With OpenSSL 3.x, client certificates must be signed by a CA
            in client_ca_certs or the TLS handshake will fail silently.
            Enforcement should be done via CertificateAuth middleware.
            Default is False.
        client_ca_certs: List of paths to CA certificates for verifying client
            certificates. For self-signed client certs, include each client's
            cert file here. Required when request_client_cert=True with
            OpenSSL 3.x. Default is None.

    Returns:
        An SSL context configured for Gemini server connections.

    Examples:
        >>> # Basic server context
        >>> context = create_server_context('cert.pem', 'key.pem')

        >>> # Server requesting client certificates (for middleware auth)
        >>> context = create_server_context(
        ...     'cert.pem',
        ...     'key.pem',
        ...     request_client_cert=True,
        ...     client_ca_certs=['trusted_client1.pem', 'trusted_client2.pem']
        ... )
    """
    # Create SSL context for server
    # NOTE: We use SSLContext directly instead of create_default_context because
    # create_default_context loads system CA certificates which we don't need.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Set minimum TLS version (Gemini requires TLS 1.2+)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Load server certificate and key
    context.load_cert_chain(certfile, keyfile)

    # Configure client certificate handling
    # Use CERT_OPTIONAL to request certs without requiring them
    # The CertificateAuth middleware handles actual enforcement
    if request_client_cert:
        context.verify_mode = ssl.CERT_OPTIONAL

        # Load client CA certificates if provided
        # NOTE: With OpenSSL 3.x, CERT_OPTIONAL requires CA certs to be loaded,
        # otherwise self-signed client certificates cause silent TLS failures.
        # For self-signed client certs, load each cert as a trusted CA.
        if client_ca_certs:
            for ca_cert in client_ca_certs:
                context.load_verify_locations(ca_cert)
    else:
        context.verify_mode = ssl.CERT_NONE

    return context
