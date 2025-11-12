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
    require_client_cert: bool = False,
) -> ssl.SSLContext:
    """Create an SSL context for Gemini server connections.

    Args:
        certfile: Path to server certificate file.
        keyfile: Path to server private key file.
        require_client_cert: Whether to require client certificates for
            authentication. Default is False.

    Returns:
        An SSL context configured for Gemini server connections.

    Examples:
        >>> # Basic server context
        >>> context = create_server_context('cert.pem', 'key.pem')

        >>> # Server requiring client certificates
        >>> context = create_server_context(
        ...     'cert.pem',
        ...     'key.pem',
        ...     require_client_cert=True
        ... )
    """
    # Create SSL context for server
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    # Set minimum TLS version (Gemini requires TLS 1.2+)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Load server certificate and key
    context.load_cert_chain(certfile, keyfile)

    # Configure client certificate verification
    if require_client_cert:
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_NONE

    return context
