"""Server startup and lifecycle management.

This module provides functions for starting and managing Gemini servers.
"""

import asyncio
import ssl
import tempfile
from pathlib import Path
from typing import Any

from ..content.templates import error_404
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode
from ..security.certificates import generate_self_signed_cert
from ..security.pyopenssl_tls import create_pyopenssl_server_context
from ..security.tls import create_server_context
from ..utils.logging import configure_logging, get_logger
from .config import ServerConfig
from .handler import StaticFileHandler
from .middleware import (
    AccessControl,
    AccessControlConfig,
    CertificateAuth,
    CertificateAuthConfig,
    MiddlewareChain,
    RateLimitConfig,
    RateLimiter,
)
from .protocol import GeminiServerProtocol
from .router import Router
from .tls_protocol import TLSServerProtocol


async def start_server(
    config: ServerConfig,
    enable_directory_listing: bool = False,
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
    enable_rate_limiting: bool = True,
    rate_limit_config: RateLimitConfig | None = None,
    access_control_config: AccessControlConfig | None = None,
    certificate_auth_config: CertificateAuthConfig | None = None,
    hash_ips: bool | None = None,
    max_file_size: int | None = None,
) -> None:
    """Start a Gemini server with the given configuration.

    This function sets up a Gemini server with static file serving,
    routing, TLS configuration, and middleware. It runs until interrupted.

    Args:
        config: Server configuration.
        enable_directory_listing: Enable automatic directory listings.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file. If None, logs to stdout.
        json_logs: If True, output logs in JSON format.
        enable_rate_limiting: Enable rate limiting middleware.
        rate_limit_config: Rate limiting configuration. Uses defaults if None.
        access_control_config: Access control configuration. None to disable.
        certificate_auth_config: Certificate auth configuration. None to disable.
        hash_ips: Hash client IPs in logs. If None, uses config.hash_client_ips.
        max_file_size: Maximum file size to serve. If None, uses config.max_file_size.

    Raises:
        ValueError: If configuration is invalid.
        OSError: If unable to bind to the specified host/port.

    Examples:
        >>> import asyncio
        >>> from pathlib import Path
        >>> config = ServerConfig(
        ...     host="localhost",
        ...     port=1965,
        ...     document_root=Path("./capsule"),
        ...     certfile=Path("cert.pem"),
        ...     keyfile=Path("key.pem")
        ... )
        >>> asyncio.run(start_server(config))
    """
    # Resolve hash_ips from config if not explicitly set
    effective_hash_ips = hash_ips if hash_ips is not None else config.hash_client_ips

    # Configure logging first
    configure_logging(
        log_level=log_level,
        log_file=log_file,
        json_logs=json_logs,
        hash_ips=effective_hash_ips,
    )
    logger = get_logger(__name__)

    # Validate configuration
    config.validate()

    # Resolve max_file_size from config if not explicitly set
    effective_max_file_size = (
        max_file_size if max_file_size is not None else config.max_file_size
    )

    # Set up default 404 handler
    def default_404_handler(request: object) -> GeminiResponse:
        from ..protocol.request import GeminiRequest

        if isinstance(request, GeminiRequest):
            path = request.path
        else:
            path = "/"
        return GeminiResponse(
            status=StatusCode.NOT_FOUND.value,
            meta="text/gemini",
            body=error_404(path),
        )

    # Create router - use location-based routing if configured, else simple static
    location_router = config.get_location_router(enable_directory_listing)

    if location_router:
        # Location-based routing configured
        router = location_router
        router.set_default_handler(default_404_handler)
        # locations is guaranteed non-empty when location_router exists
        assert config.locations is not None
        logger.info(
            "location_routing_enabled",
            location_count=len(config.locations),
            prefixes=[loc.prefix for loc in config.locations],
        )
    else:
        # Fallback: simple static file handler for document_root
        from .router import RouteType

        router = Router()
        static_handler = StaticFileHandler(
            config.document_root,
            enable_directory_listing=enable_directory_listing,
            max_file_size=effective_max_file_size,
        )
        router.set_default_handler(default_404_handler)
        router.add_route("/", static_handler.handle, route_type=RouteType.PREFIX)

    # Determine if we need to request client certificates
    # PyOpenSSL is used if:
    # 1. config.require_client_cert is explicitly True, OR
    # 2. ANY certificate auth path rule requires certificates or has fingerprint whitelist
    request_client_cert = config.require_client_cert or (
        certificate_auth_config is not None
        and any(
            rule.require_cert or rule.allowed_fingerprints is not None
            for rule in certificate_auth_config.path_rules
        )
    )

    # Determine if we need PyOpenSSL for client certificate support
    # PyOpenSSL is required because Python's ssl module with OpenSSL 3.x
    # silently rejects self-signed client certificates
    use_pyopenssl = request_client_cert

    # Create SSL context (only used when NOT using PyOpenSSL)
    ssl_context: ssl.SSLContext | None = None
    pyopenssl_ctx = None

    if use_pyopenssl:
        # Use PyOpenSSL for proper self-signed client cert support
        if config.certfile and config.keyfile:
            pyopenssl_ctx = create_pyopenssl_server_context(
                str(config.certfile),
                str(config.keyfile),
                request_client_cert=True,
            )
            logger.info(
                "tls_configured",
                certfile=str(config.certfile),
                keyfile=str(config.keyfile),
                request_client_cert=True,
                tls_backend="pyopenssl",
            )
        else:
            # For testing: create self-signed certificate with PyOpenSSL
            pyopenssl_ctx = _create_self_signed_pyopenssl_context()
            logger.warning(
                "using_self_signed_certificate",
                mode="testing_only",
                tls_backend="pyopenssl",
            )
    else:
        # Standard ssl module is fine when not requesting client certs
        if config.certfile and config.keyfile:
            ssl_context = create_server_context(
                str(config.certfile),
                str(config.keyfile),
                request_client_cert=False,
            )
            logger.info(
                "tls_configured",
                certfile=str(config.certfile),
                keyfile=str(config.keyfile),
                request_client_cert=False,
                tls_backend="stdlib",
            )
        else:
            # For testing: create self-signed certificate
            ssl_context = _create_self_signed_context(request_client_cert=False)
            logger.warning(
                "using_self_signed_certificate",
                mode="testing_only",
                tls_backend="stdlib",
            )

    # Set up middleware chain
    middlewares: list[Any] = []

    # Add certificate auth if configured (check this first - before IP-based checks)
    if certificate_auth_config:
        cert_auth = CertificateAuth(certificate_auth_config)
        middlewares.append(cert_auth)
        logger.info(
            "certificate_auth_enabled",
            path_rules_count=len(certificate_auth_config.path_rules),
            paths_requiring_cert=[
                rule.prefix
                for rule in certificate_auth_config.path_rules
                if rule.require_cert or rule.allowed_fingerprints is not None
            ],
        )

    # Add access control if configured
    if access_control_config:
        access_control = AccessControl(access_control_config)
        middlewares.append(access_control)
        logger.info(
            "access_control_enabled",
            allow_list=access_control_config.allow_list,
            deny_list=access_control_config.deny_list,
            default_allow=access_control_config.default_allow,
        )

    # Add rate limiting if enabled
    if enable_rate_limiting:
        rate_limiter = RateLimiter(rate_limit_config)
        rate_limiter.start()  # Start cleanup task
        middlewares.append(rate_limiter)
        logger.info(
            "rate_limiting_enabled",
            capacity=rate_limiter.config.capacity,
            refill_rate=rate_limiter.config.refill_rate,
            retry_after=rate_limiter.config.retry_after,
        )

    # Create middleware chain if any middlewares configured
    middleware_chain = MiddlewareChain(middlewares) if middlewares else None

    # Get event loop
    loop = asyncio.get_running_loop()

    # Create server using Protocol pattern
    if use_pyopenssl and pyopenssl_ctx is not None:
        # Use PyOpenSSL TLS wrapper - NO ssl= parameter since TLS is handled manually
        server = await loop.create_server(
            lambda: TLSServerProtocol(
                lambda: GeminiServerProtocol(router.route, middleware_chain),
                pyopenssl_ctx,
            ),
            config.host,
            config.port,
            # NO ssl= parameter - TLS handled by TLSServerProtocol
        )
    else:
        # Standard ssl module
        server = await loop.create_server(
            lambda: GeminiServerProtocol(router.route, middleware_chain),
            config.host,
            config.port,
            ssl=ssl_context,
        )

    logger.info(
        "server_started",
        host=config.host,
        port=config.port,
        document_root=str(config.document_root),
        directory_listing_enabled=enable_directory_listing,
    )

    async with server:
        await server.serve_forever()


def _create_self_signed_context(request_client_cert: bool = False) -> ssl.SSLContext:
    """Create a self-signed SSL context for testing.

    WARNING: This is for testing only! Do not use in production.

    Args:
        request_client_cert: Whether to request client certificates.

    Returns:
        An SSL context with a self-signed certificate.
    """
    # Generate self-signed certificate using cryptography library
    try:
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="localhost",
            key_size=2048,
            valid_days=365,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate self-signed certificate: {e}") from e

    # Write to temporary files
    with (
        tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as certfile,
        tempfile.NamedTemporaryFile(suffix=".key", delete=False, mode="wb") as keyfile,
    ):
        certfile.write(cert_pem)
        keyfile.write(key_pem)
        certfile.flush()
        keyfile.flush()

        print("[Server] WARNING: Using self-signed certificate (testing only!)")
        print(f"[Server] Certificate: {certfile.name}")
        print(f"[Server] Key: {keyfile.name}")

        # Use SSLContext directly to avoid loading system CA certs
        # This allows self-signed client certificates to be accepted
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile.name, keyfile.name)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Configure client certificate handling
        if request_client_cert:
            ssl_context.verify_mode = ssl.CERT_OPTIONAL
        else:
            ssl_context.verify_mode = ssl.CERT_NONE

        return ssl_context


def _create_self_signed_pyopenssl_context() -> Any:
    """Create a self-signed PyOpenSSL context for testing with client certs.

    WARNING: This is for testing only! Do not use in production.

    This function creates a PyOpenSSL SSL.Context with a self-signed certificate,
    configured to accept any client certificate (including self-signed).

    Returns:
        A PyOpenSSL SSL.Context with a self-signed certificate.
    """
    # Generate self-signed certificate using cryptography library
    try:
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="localhost",
            key_size=2048,
            valid_days=365,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate self-signed certificate: {e}") from e

    # Write to temporary files (PyOpenSSL requires file paths)
    with (
        tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as certfile,
        tempfile.NamedTemporaryFile(suffix=".key", delete=False, mode="wb") as keyfile,
    ):
        certfile.write(cert_pem)
        keyfile.write(key_pem)
        certfile.flush()
        keyfile.flush()

        print("[Server] WARNING: Using self-signed certificate (testing only!)")
        print(f"[Server] Certificate: {certfile.name}")
        print(f"[Server] Key: {keyfile.name}")
        print("[Server] Using PyOpenSSL for client certificate support")

        # Create PyOpenSSL context that accepts any client certificate
        return create_pyopenssl_server_context(
            certfile.name,
            keyfile.name,
            request_client_cert=True,
        )
