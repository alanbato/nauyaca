# Server API

The server API provides tools for running Gemini servers programmatically. Use these APIs to create custom server implementations, add middleware, and configure server behavior.

## Overview

The server API consists of:

- **`ServerConfig`** - Configuration management and TOML loading
- **`start_server()`** - Server startup and lifecycle management
- **Middleware** - Request processing and security (rate limiting, access control, certificate auth)
- **Handlers** - Request handling and response generation

## Quick Start

### Minimal Server

Start a basic Gemini server with default settings:

```python
import asyncio
from pathlib import Path
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server

async def main():
    config = ServerConfig(
        host="localhost",
        port=1965,
        document_root=Path("./capsule"),
        certfile=Path("cert.pem"),
        keyfile=Path("key.pem")
    )

    await start_server(config)

if __name__ == "__main__":
    asyncio.run(main())
```

### Server with Configuration File

Load configuration from a TOML file:

```python
import asyncio
from pathlib import Path
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server

async def main():
    # Load from TOML
    config = ServerConfig.from_toml(Path("config.toml"))

    # Start server with configuration
    await start_server(
        config,
        enable_directory_listing=True,
        log_level="INFO"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Server with Custom Middleware

Add custom middleware to the server:

```python
import asyncio
from pathlib import Path
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server
from nauyaca.server.middleware import RateLimitConfig, AccessControlConfig

async def main():
    config = ServerConfig(
        host="0.0.0.0",  # Listen on all interfaces
        port=1965,
        document_root=Path("/var/gemini/capsule"),
        certfile=Path("/etc/gemini/cert.pem"),
        keyfile=Path("/etc/gemini/key.pem")
    )

    # Configure rate limiting
    rate_limit_config = RateLimitConfig(
        capacity=20,        # Allow burst of 20 requests
        refill_rate=2.0,    # Refill 2 tokens per second
        retry_after=60      # Ask clients to wait 60s if limited
    )

    # Configure access control
    access_control_config = AccessControlConfig(
        allow_list=["192.168.1.0/24", "10.0.0.0/8"],
        deny_list=["192.168.1.100"],
        default_allow=False  # Deny by default
    )

    await start_server(
        config,
        enable_rate_limiting=True,
        rate_limit_config=rate_limit_config,
        access_control_config=access_control_config,
        log_level="DEBUG"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## ServerConfig

::: nauyaca.server.config.ServerConfig

### Loading from TOML

The `ServerConfig.from_toml()` method loads configuration from a TOML file:

```python
from pathlib import Path
from nauyaca.server.config import ServerConfig

# Load from file
config = ServerConfig.from_toml(Path("config.toml"))

# Access configuration values
print(f"Server will run on {config.host}:{config.port}")
print(f"Serving files from {config.document_root}")
```

Example TOML configuration:

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/gemini/cert.pem"
keyfile = "/etc/gemini/key.pem"
max_file_size = 104857600  # 100 MiB

[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.0
retry_after = 30

[access_control]
allow_list = ["192.168.1.0/24"]
default_allow = false

[logging]
hash_ips = true
```

### Programmatic Configuration

Create configuration entirely in code:

```python
from pathlib import Path
from nauyaca.server.config import ServerConfig

config = ServerConfig(
    host="localhost",
    port=1965,
    document_root=Path("/var/gemini/capsule"),
    certfile=Path("/etc/gemini/cert.pem"),
    keyfile=Path("/etc/gemini/key.pem"),

    # Rate limiting
    enable_rate_limiting=True,
    rate_limit_capacity=10,
    rate_limit_refill_rate=1.0,
    rate_limit_retry_after=30,

    # Access control
    access_control_allow_list=["192.168.1.0/24"],
    access_control_default_allow=False,

    # Security
    hash_client_ips=True,
    max_file_size=100 * 1024 * 1024  # 100 MiB
)

# Validate configuration
config.validate()

# Get middleware configurations
rate_limit_config = config.get_rate_limit_config()
access_control_config = config.get_access_control_config()
```

## Server Functions

::: nauyaca.server.server.start_server

### Server Lifecycle

The `start_server()` function runs indefinitely until interrupted:

```python
import asyncio
import signal
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server

async def main():
    config = ServerConfig.from_toml(Path("config.toml"))

    # This runs until Ctrl+C or SIGTERM
    await start_server(config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
```

### Graceful Shutdown

Handle graceful shutdown with signal handlers:

```python
import asyncio
import signal
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server

shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    shutdown_event.set()

async def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    config = ServerConfig.from_toml(Path("config.toml"))

    # Run server with shutdown handling
    server_task = asyncio.create_task(start_server(config))
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    # Wait for either server to finish or shutdown signal
    done, pending = await asyncio.wait(
        [server_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel remaining tasks
    for task in pending:
        task.cancel()

    print("Server shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
```

## Middleware

Middleware components process requests before they reach handlers. They can:

- Block requests (rate limiting, access control)
- Require authentication (client certificates)
- Log requests
- Modify request context

### Middleware Protocol

All middleware must implement the `Middleware` protocol:

::: nauyaca.server.middleware.Middleware
    options:
      members:
        - process_request

### Rate Limiting

::: nauyaca.server.middleware.RateLimitConfig

::: nauyaca.server.middleware.RateLimiter
    options:
      members:
        - __init__
        - start
        - stop
        - process_request

Example usage:

```python
from nauyaca.server.middleware import RateLimiter, RateLimitConfig

# Create rate limiter
config = RateLimitConfig(
    capacity=10,        # Allow 10 requests in burst
    refill_rate=1.0,    # Add 1 token per second
    retry_after=30      # Tell clients to wait 30s
)

rate_limiter = RateLimiter(config)
rate_limiter.start()  # Start background cleanup

# Use with server
await start_server(
    server_config,
    enable_rate_limiting=True,
    rate_limit_config=config
)
```

### Access Control

::: nauyaca.server.middleware.AccessControlConfig

::: nauyaca.server.middleware.AccessControl
    options:
      members:
        - __init__
        - process_request

Example usage:

```python
from nauyaca.server.middleware import AccessControl, AccessControlConfig

# Allow specific networks, deny specific IPs
config = AccessControlConfig(
    allow_list=["192.168.1.0/24", "10.0.0.0/8"],
    deny_list=["192.168.1.100", "10.0.0.50"],
    default_allow=False  # Deny everything not in allow list
)

access_control = AccessControl(config)

# Use with server
await start_server(
    server_config,
    access_control_config=config
)
```

!!! tip "CIDR Notation"
    Access control lists support CIDR notation for network ranges:

    - `192.168.1.0/24` matches 192.168.1.0-192.168.1.255
    - `10.0.0.0/8` matches 10.0.0.0-10.255.255.255
    - `192.168.1.100` matches a single IP (equivalent to /32)

### Certificate Authentication

::: nauyaca.server.middleware.CertificateAuthPathRule

::: nauyaca.server.middleware.CertificateAuthConfig

::: nauyaca.server.middleware.CertificateAuth
    options:
      members:
        - __init__
        - process_request

Example usage:

```python
from nauyaca.server.middleware import (
    CertificateAuth,
    CertificateAuthConfig,
    CertificateAuthPathRule
)

# Require certificates for specific paths
config = CertificateAuthConfig(
    path_rules=[
        # Public path - no cert required
        CertificateAuthPathRule(
            prefix="/public/",
            require_cert=False
        ),
        # Admin area - cert required
        CertificateAuthPathRule(
            prefix="/admin/",
            require_cert=True
        ),
        # App area - specific certs only
        CertificateAuthPathRule(
            prefix="/app/",
            require_cert=True,
            allowed_fingerprints={
                "a1b2c3...",  # SHA-256 fingerprints
                "d4e5f6..."
            }
        )
    ]
)

# Use with server
await start_server(
    server_config,
    certificate_auth_config=config
)
```

!!! info "Certificate Fingerprints"
    Certificate fingerprints are SHA-256 hashes of the DER-encoded certificate. Use the `nauyaca cert fingerprint` command to calculate fingerprints for client certificates.

!!! warning "PyOpenSSL Required"
    When using certificate authentication, Nauyaca automatically uses PyOpenSSL instead of the standard library's ssl module. This is required because OpenSSL 3.x silently rejects self-signed client certificates, which are common in Geminispace.

### Middleware Chain

::: nauyaca.server.middleware.MiddlewareChain
    options:
      members:
        - __init__
        - process_request

Middleware are executed in order:

1. **CertificateAuth** - Check client certificates first
2. **AccessControl** - Then check IP-based access
3. **RateLimiter** - Finally check rate limits

The first middleware that rejects a request stops the chain.

## Handlers

Handlers generate responses for requests. Nauyaca provides built-in handlers for common use cases.

### RequestHandler Base Class

::: nauyaca.server.handler.RequestHandler
    options:
      members:
        - handle

### StaticFileHandler

::: nauyaca.server.handler.StaticFileHandler

Example usage:

```python
from pathlib import Path
from nauyaca.server.handler import StaticFileHandler
from nauyaca.protocol.request import GeminiRequest

# Create handler
handler = StaticFileHandler(
    document_root=Path("/var/gemini/capsule"),
    default_indices=["index.gmi", "index.gemini"],
    enable_directory_listing=True,
    max_file_size=100 * 1024 * 1024  # 100 MiB
)

# Handle a request
request = GeminiRequest.from_line("gemini://example.com/page.gmi\r\n")
response = handler.handle(request)

print(f"Status: {response.status}")
print(f"Meta: {response.meta}")
print(f"Body: {response.body[:100]}...")
```

!!! info "Default Handler"
    The `start_server()` function automatically configures a `StaticFileHandler` for the document root. You don't need to create one manually unless you need custom behavior.

### ErrorHandler

::: nauyaca.server.handler.ErrorHandler

Example usage:

```python
from nauyaca.server.handler import ErrorHandler
from nauyaca.protocol.status import StatusCode

# Create 404 handler
not_found_handler = ErrorHandler(
    status=StatusCode.NOT_FOUND,
    message="Page not found"
)

# Create maintenance handler
maintenance_handler = ErrorHandler(
    status=StatusCode.TEMPORARY_FAILURE,
    message="Server maintenance - try again later"
)
```

### Custom Handlers

Create custom handlers by subclassing `RequestHandler`:

```python
from nauyaca.server.handler import RequestHandler
from nauyaca.protocol.request import GeminiRequest
from nauyaca.protocol.response import GeminiResponse
from nauyaca.protocol.status import StatusCode

class EchoHandler(RequestHandler):
    """Handler that echoes the request URL."""

    def handle(self, request: GeminiRequest) -> GeminiResponse:
        body = f"# Echo\n\nYou requested: {request.url}\n"

        return GeminiResponse(
            status=StatusCode.SUCCESS.value,
            meta="text/gemini",
            body=body
        )

# Use with router
from nauyaca.server.router import Router

router = Router()
router.add_route("/echo", EchoHandler().handle)
```

## See Also

- [Configuration Reference](../configuration.md) - Complete TOML configuration guide
- [CLI Reference](../cli.md) - Command-line server management
- [How-to: Configure Server](../../how-to/configure-server.md) - Server configuration guide
- [How-to: Rate Limiting](../../how-to/rate-limiting.md) - Rate limiting setup
- [How-to: Client Certificates](../../how-to/client-certificates.md) - Certificate authentication
- [Tutorial: Securing Your Server](../../tutorials/securing-your-server.md) - Security best practices
