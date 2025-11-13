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
from ..security.tls import create_server_context
from ..utils.logging import configure_logging, get_logger
from .config import ServerConfig
from .handler import StaticFileHandler
from .middleware import (
    AccessControl,
    AccessControlConfig,
    MiddlewareChain,
    RateLimitConfig,
    RateLimiter,
)
from .protocol import GeminiServerProtocol
from .router import Router


async def start_server(
    config: ServerConfig,
    enable_directory_listing: bool = False,
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
    enable_rate_limiting: bool = True,
    rate_limit_config: RateLimitConfig | None = None,
    access_control_config: AccessControlConfig | None = None,
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
    # Configure logging first
    configure_logging(log_level=log_level, log_file=log_file, json_logs=json_logs)
    logger = get_logger(__name__)

    # Validate configuration
    config.validate()

    # Create router and static file handler
    router = Router()
    static_handler = StaticFileHandler(
        config.document_root, enable_directory_listing=enable_directory_listing
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

    router.set_default_handler(default_404_handler)

    # Add route for all paths - static file handler
    # This catches everything not explicitly routed
    from .router import RouteType

    router.add_route("/", static_handler.handle, route_type=RouteType.PREFIX)

    # Create SSL context
    if config.certfile and config.keyfile:
        ssl_context = create_server_context(str(config.certfile), str(config.keyfile))
        logger.info(
            "tls_configured",
            certfile=str(config.certfile),
            keyfile=str(config.keyfile),
        )
    else:
        # For testing: create self-signed certificate
        ssl_context = _create_self_signed_context()
        logger.warning("using_self_signed_certificate", mode="testing_only")

    # Set up middleware chain
    middlewares: list[Any] = []

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


def _create_self_signed_context() -> ssl.SSLContext:
    """Create a self-signed SSL context for testing.

    WARNING: This is for testing only! Do not use in production.

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

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile.name, keyfile.name)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        return ssl_context
