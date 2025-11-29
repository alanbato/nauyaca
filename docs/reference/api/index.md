# API Reference

Nauyaca can be used as a Python library to build Gemini clients, servers, or custom protocol implementations. This section provides comprehensive API documentation for all public modules.

## Overview

The Nauyaca API is organized into three main areas:

<div class="grid cards" markdown>

-   :material-download: **Client API**

    ---

    Use `GeminiClient` to fetch Gemini resources, manage TOFU validation, and handle responses programmatically.

    [:octicons-arrow-right-24: Client API Reference](client.md)

-   :material-server: **Server API**

    ---

    Configure and run Gemini servers with `ServerConfig`, implement custom handlers, and add middleware.

    [:octicons-arrow-right-24: Server API Reference](server.md)

-   :material-shield-check: **Security API**

    ---

    Manage TLS certificates, implement TOFU validation, and handle cryptographic operations.

    [:octicons-arrow-right-24: Security API Reference](security.md)

</div>

## Quick Start

### Client Usage

```python
from nauyaca.client.session import GeminiClient
from nauyaca.security.tofu import TofuDatabase

# Initialize client with TOFU validation
tofu_db = TofuDatabase("~/.config/nauyaca/tofu.db")
client = GeminiClient(tofu_db=tofu_db)

# Fetch a resource
response = await client.fetch("gemini://example.com/")
```

### Server Usage

```python
from nauyaca.server.config import ServerConfig
from nauyaca.server.protocol import start_gemini_server

# Load configuration
config = ServerConfig.from_toml("config.toml")

# Start server
await start_gemini_server(config)
```

### Security Usage

```python
from nauyaca.security.certificates import generate_certificate, fingerprint
from nauyaca.security.tofu import TofuDatabase

# Generate a self-signed certificate
generate_certificate(
    hostname="localhost",
    certfile="cert.pem",
    keyfile="key.pem"
)

# Calculate certificate fingerprint
fp = fingerprint("cert.pem")
print(f"Certificate fingerprint: {fp}")
```

## Documentation Notes

!!! info "Auto-Generated Documentation"
    API documentation is automatically generated from docstrings in the source code. All type hints, parameters, return values, and exceptions are documented inline.

!!! tip "Type Hints"
    All public APIs include comprehensive type hints. Use a type checker like `mypy` for the best development experience:

    ```bash
    pip install mypy
    mypy your_script.py
    ```

## Module Organization

The Nauyaca library is structured as follows:

```
nauyaca/
├── client/          # Client session and protocol
├── server/          # Server configuration and handlers
├── security/        # TLS certificates and TOFU validation
├── protocol/        # Core protocol types and constants
├── content/         # Content handling and MIME types
└── utils/           # Utility functions
```

## See Also

- [CLI Reference](../cli.md) - Command-line interface documentation
- [How-to Guides](../../how-to/index.md) - Task-oriented guides
- [Tutorials](../../tutorials/index.md) - Learning-oriented lessons
