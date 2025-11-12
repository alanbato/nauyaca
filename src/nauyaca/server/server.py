"""Server startup and lifecycle management.

This module provides functions for starting and managing Gemini servers.
"""

import asyncio

from ..content.templates import error_404
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode
from ..security.tls import create_server_context
from .config import ServerConfig
from .handler import StaticFileHandler
from .protocol import GeminiServerProtocol
from .router import Router


async def start_server(config: ServerConfig) -> None:
    """Start a Gemini server with the given configuration.

    This function sets up a Gemini server with static file serving,
    routing, and TLS configuration. It runs until interrupted.

    Args:
        config: Server configuration.

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
    # Validate configuration
    config.validate()

    # Create router and static file handler
    router = Router()
    static_handler = StaticFileHandler(config.document_root)

    # Set up default 404 handler
    def default_404_handler(request):
        return GeminiResponse(
            status=StatusCode.NOT_FOUND.value,
            meta="text/gemini",
            body=error_404(request.path),
        )

    router.set_default_handler(default_404_handler)

    # Add route for all paths - static file handler
    # This catches everything not explicitly routed
    from .router import RouteType

    router.add_route("/", static_handler.handle, route_type=RouteType.PREFIX)

    # Create SSL context
    if config.certfile and config.keyfile:
        ssl_context = create_server_context(str(config.certfile), str(config.keyfile))
    else:
        # For testing: create self-signed certificate
        ssl_context = _create_self_signed_context()

    # Get event loop
    loop = asyncio.get_running_loop()

    # Create server using Protocol pattern
    server = await loop.create_server(
        lambda: GeminiServerProtocol(router.route),
        config.host,
        config.port,
        ssl=ssl_context,
    )

    print(f"[Server] Serving on {config.host}:{config.port}")
    print(f"[Server] Document root: {config.document_root}")

    async with server:
        await server.serve_forever()


def _create_self_signed_context():
    """Create a self-signed SSL context for testing.

    WARNING: This is for testing only! Do not use in production.

    Returns:
        An SSL context with a self-signed certificate.
    """
    import ssl
    import subprocess
    import tempfile

    # Create temporary certificate and key
    with (
        tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as certfile,
        tempfile.NamedTemporaryFile(suffix=".key", delete=False) as keyfile,
    ):
        # Generate self-signed certificate
        try:
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-keyout",
                    keyfile.name,
                    "-out",
                    certfile.name,
                    "-days",
                    "365",
                    "-nodes",
                    "-subj",
                    "/CN=localhost",
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to generate self-signed certificate: {e.stderr.decode()}"
            )

        print("[Server] WARNING: Using self-signed certificate (testing only!)")
        print(f"[Server] Certificate: {certfile.name}")
        print(f"[Server] Key: {keyfile.name}")

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile.name, keyfile.name)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        return ssl_context
