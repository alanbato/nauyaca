# Gemini Protocol Server & Client

A modern, feature-complete implementation of the Gemini protocol in Python using asyncio, providing both server and client capabilities.

## 📋 Project Overview

This project implements the [Gemini protocol](https://geminiprotocol.net/) - a minimalist, privacy-focused alternative to HTTP. The implementation uses Python's asyncio Protocol/Transport pattern for efficient, non-blocking network I/O.

### Goals

- ✅ Implement a production-ready Gemini server
- ✅ Implement a full-featured Gemini client
- ✅ Support all Gemini protocol features (TLS, client certs, TOFU, etc.)
- ✅ Provide clean, maintainable, well-documented code
- ✅ Include comprehensive test coverage
- ✅ Offer both library and CLI interfaces

## 🛠 Technology Stack

- **asyncio** - Asynchronous I/O using Protocol/Transport pattern
- **ssl** - TLS 1.2+ encryption
- **pytest-asyncio** - Async test support
- **typer** - CLI interface
- **cryptography** - Certificate handling and TOFU implementation

## 🏗 Project Structure

```
gemini-protocol/
├── README.md
├── pyproject.toml           # Project metadata and dependencies
├── .gitignore
├── .env.example             # Environment variables template
│
├── src/
│   └── nauyaca/
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       │
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── constants.py      # Status codes, MIME types, etc.
│       │   ├── request.py        # Request parsing
│       │   ├── response.py       # Response building
│       │   └── status.py         # Status code utilities
│       │
│       ├── server/
│       │   ├── __init__.py
│       │   ├── protocol.py       # Server protocol implementation
│       │   ├── handler.py        # Request handler
│       │   ├── router.py         # URL routing
│       │   ├── config.py         # Server configuration
│       │   └── middleware.py     # Logging, rate limiting, etc.
│       │
│       ├── client/
│       │   ├── __init__.py
│       │   ├── protocol.py       # Client protocol implementation
│       │   ├── session.py        # High-level client API
│       │   ├── tofu.py           # Trust-On-First-Use cert validation
│       │   └── cache.py          # Response caching
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── tls.py            # TLS context creation
│       │   ├── certificates.py   # Cert generation and management
│       │   └── tofu.py           # TOFU database
│       │
│       ├── content/
│       │   ├── __init__.py
│       │   ├── gemtext.py        # Gemtext parser/renderer
│       │   ├── mime.py           # MIME type detection
│       │   └── templates.py      # Error page templates
│       │
│       └── utils/
│           ├── __init__.py
│           ├── url.py            # URL parsing/validation
│           ├── encoding.py       # Charset handling
│           └── logging.py        # Logging configuration
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_protocol/
│   ├── test_server/
│   ├── test_client/
│   ├── test_security/
│   └── test_integration/
│
├── examples/
│   ├── simple_server.py         # Minimal server example
│   ├── simple_client.py         # Minimal client example
│   ├── static_site.py           # Static file server
│   ├── dynamic_content.py       # CGI-like dynamic content
│   └── proxy.py                 # Gemini-to-HTTP proxy
│
├── docs/
│   ├── architecture.md          # Architecture decisions
│   ├── protocol_guide.md        # Gemini protocol overview
│   ├── api_reference.md         # API documentation
│   └── deployment.md            # Production deployment guide
│
└── capsule/                     # Example Gemini capsule content
    ├── index.gmi
    ├── about.gmi
    └── certs/                   # SSL certificates
        ├── .gitkeep
        └── README.md
```

## 🚀 Quick Start

### Installation

```bash
# Standalone CLI tool
uv tool install nauyaca

# Use it as a library in your project
uv add nauyaca
```

### Running the Server

```bash
# Minimal - serve current directory (uses auto-generated cert)
nauyaca serve ./capsule

# With custom host/port
nauyaca serve ./capsule --host 0.0.0.0 --port 1965

# With configuration file
nauyaca serve --config config.toml

# With TLS certificates
nauyaca serve ./capsule --cert cert.pem --key key.pem
```

### Generate SSL Certificates

```bash
# Generate self-signed certificate for testing
nauyaca cert generate --hostname localhost --output ./certs

# For production (with proper hostname)
nauyaca cert generate --hostname gemini.example.com --days 365
```

### Using the Client

```bash
# Fetch a resource
nauyaca fetch gemini://gemini.circumlunar.space/

# With TOFU certificate validation
nauyaca fetch gemini://example.com/ --tofu

# Manage TOFU database
nauyaca tofu list
nauyaca tofu export backup.json
nauyaca tofu import backup.json
nauyaca tofu revoke example.com
```

### As a Library

```python
import asyncio
from nauyaca.client.session import fetch_gemini

async def main():
    # Simple fetch with TOFU validation
    status, meta, body = await fetch_gemini("gemini://example.com/")

    if status == 20:
        print(f"Content-Type: {meta}")
        print(body)
    elif status == 30 or status == 31:
        print(f"Redirect to: {meta}")
    else:
        print(f"Error {status}: {meta}")

asyncio.run(main())
```


This project follows:
- **PEP 8** style guide
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking
- **isort** for import sorting

## 📖 Core Features

### Server Features

- [x] **Protocol Implementation**
  - TLS 1.2+ encryption (mandatory)
  - Complete status code support (1x-6x)
  - Request URL parsing and validation
  - Response header generation

- [x] **Content Serving**
  - Static file serving
  - Directory listings
  - MIME type detection
  - Gemtext rendering
  - CGI script support
  - Virtual hosting

- [x] **Security**
  - Client certificate support (status 6x)
  - Certificate-based authentication
  - Rate limiting
  - Access control lists
  - Path traversal protection

- [x] **Features**
  - URL rewriting and routing
  - Logging and monitoring
  - Graceful shutdown
  - Hot reload (development mode)
  - Custom error pages

### Client Features

- [x] **Protocol Implementation**
  - TLS connection handling
  - Request sending
  - Response parsing
  - Redirect following

- [x] **Security**
  - TOFU certificate validation
  - Certificate pinning
  - Client certificate support
  - Known hosts database

- [x] **Features**
  - Async/await API
  - Connection pooling
  - Response caching
  - Timeout handling
  - Retry logic
  - CLI interface

## 🔧 Configuration

### Server Configuration

The server supports TOML configuration files for persistent settings. Command-line arguments override config file values.

#### Minimal Configuration

Create a `config.toml` file with just the essentials:

```toml
[server]
# Required: Path to your gemini content
document_root = "./capsule"

# All other settings use sensible defaults:
# - host: localhost
# - port: 1965
# - TLS: auto-generated self-signed certificate (for testing only!)
# - Rate limiting: enabled with default limits
# - Access control: allow all
```

#### Full Configuration Example

For production deployments, use a complete configuration:

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "./capsule"
certfile = "./certs/cert.pem"
keyfile = "./certs/key.pem"

[rate_limit]
enabled = true
capacity = 10           # Max burst size (requests)
refill_rate = 1.0      # Requests per second
retry_after = 30       # Seconds to wait when limited

[access_control]
# IP-based access control (supports CIDR notation)
allow_list = ["192.168.1.0/24", "10.0.0.1"]
deny_list = ["203.0.113.0/24"]
default_allow = true   # Default policy when no lists match
```

#### Using Configuration Files

```bash
# Load configuration from file
nauyaca serve --config config.toml

# Override specific settings
nauyaca serve --config config.toml --host 0.0.0.0 --port 11965

# Without config file (all settings from CLI)
nauyaca serve ./capsule --host localhost --port 1965
```

### Client Configuration

The client uses TOFU (Trust-On-First-Use) certificate validation with a local database:

```bash
# TOFU database location
~/.nauyaca/known_hosts.db

# List known hosts
nauyaca tofu list

# Export known hosts for backup
nauyaca tofu export backup.json

# Import known hosts
nauyaca tofu import backup.json

# Revoke trust for a host
nauyaca tofu revoke example.com

# Manually trust a host
nauyaca tofu trust example.com --fingerprint <sha256>
```

## 🏛 Architecture

### Key Design Decisions

1. **asyncio Protocol Pattern**: Low-level control, high performance
2. **Plugin Architecture**: Extensible handler system
3. **TOFU by Default**: Privacy-focused certificate validation
4. **Stateless**: Each request is independent (no sessions)
5. **Type Hints**: Full typing for better IDE support and error catching

## 🧪 Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution (<1s total)

### Integration Tests
- Test component interactions
- Use real network connections (localhost)
- Test TLS handshakes

### End-to-End Tests
- Full server/client scenarios
- Test with real certificates
- Validate protocol compliance

### Performance Tests
- Load testing with multiple concurrent connections
- Memory profiling
- Response time benchmarks

## 📚 API Examples

### Server API

```python
from gemini.server import GeminiServer
from gemini.server.handler import StaticFileHandler

async def main():
    server = GeminiServer(
        host='localhost',
        port=1965,
        certfile='cert.pem',
        keyfile='key.pem'
    )

    # Add handler
    handler = StaticFileHandler(root='./capsule')
    server.add_handler('/*', handler)

    # Start server
    await server.start()
    await server.serve_forever()
```

### Client API

```python
from gemini.client import GeminiClient

async def main():
    async with GeminiClient() as client:
        # Simple fetch
        response = await client.fetch('gemini://example.com/')

        # Handle different status codes
        if response.status == 20:
            print(response.body)
        elif response.status == 30:
            print(f"Redirect to: {response.meta}")
        elif response.status == 10:
            user_input = input(response.meta + ": ")
            response = await client.fetch(
                response.url,
                query=user_input
            )
```

### Custom Handler Example

```python
from gemini.server import RequestHandler
from gemini.protocol import Response, StatusCode

class MyHandler(RequestHandler):
    async def handle(self, request):
        if request.path == '/time':
            from datetime import datetime
            body = f"# Current Time\n\n{datetime.now()}"
            return Response(
                status=StatusCode.SUCCESS,
                meta='text/gemini',
                body=body
            )
        return Response(
            status=StatusCode.NOT_FOUND,
            meta='Page not found'
        )
```

## 🔒 Security Features

Nauyaca implements multiple layers of security to protect both servers and clients. See [SECURITY.md](SECURITY.md) for complete security documentation.

### TLS Security

**Mandatory TLS 1.2+**
- All Gemini connections require TLS 1.2 or higher
- No plaintext fallback - non-TLS connections rejected
- Strong cipher suites enforced by default
- Self-signed certificates supported (TOFU model)

```python
# Automatic strong TLS configuration
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
```

### TOFU (Trust-On-First-Use) Certificate Validation

**How TOFU Works:**
1. **First Connection**: Accept certificate, store SHA-256 fingerprint
2. **Subsequent Connections**: Verify certificate matches stored fingerprint
3. **Certificate Change**: Prompt user for confirmation (may be renewal or MITM attack)

**TOFU Management:**
```bash
# List all known hosts with fingerprints
nauyaca tofu list

# Export for backup/sharing
nauyaca tofu export backup.json

# Import from backup
nauyaca tofu import backup.json

# Revoke trust for compromised host
nauyaca tofu revoke example.com

# Manually trust a specific certificate
nauyaca tofu trust example.com --fingerprint abc123...
```

**Storage**: Certificates stored in `~/.nauyaca/known_hosts.db` (SQLite database)

### Rate Limiting & DoS Protection

**Token Bucket Algorithm**
- Industry-standard rate limiting per client IP
- Configurable capacity (burst size) and refill rate
- Automatic cleanup of idle rate limiters (memory efficient)
- Returns status `44 SLOW DOWN` when limits exceeded

**Configuration:**
```toml
[rate_limit]
enabled = true
capacity = 10           # Max burst size
refill_rate = 1.0      # Requests per second
retry_after = 30       # Seconds to wait when limited
```

**Example Rate Limits:**
- **Personal capsule**: capacity=5, refill_rate=0.5 (restrictive)
- **Public server**: capacity=20, refill_rate=2.0 (generous)
- **High-traffic**: capacity=50, refill_rate=5.0 (very generous)

### IP-based Access Control

**Allow/Deny Lists with CIDR Support**
- Individual IPs: `10.0.0.1`
- IPv4 networks: `192.168.1.0/24`
- IPv6 networks: `2001:db8::/32`
- Configurable default policy (allow or deny)

**Configuration:**
```toml
[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.1"]  # Whitelist
deny_list = ["203.0.113.0/24"]               # Blacklist
default_allow = true                          # Default policy
```

**Processing Order:**
1. Check deny list → reject if match
2. Check allow list → accept if match
3. Apply default policy

**Use Cases:**
- **Private capsule**: Set `default_allow = false`, add trusted IPs to allow_list
- **Public server**: Set `default_allow = true`, add abusive IPs to deny_list

### Request Validation & Protection

**Size Limits:**
- Maximum request size: 1024 bytes (per Gemini spec)
- Oversized requests receive status `59 BAD REQUEST`

**Timeout Protection:**
- Default request timeout: 30 seconds
- Slow clients receive status `40 TIMEOUT`
- Prevents slow-loris attacks

**Path Traversal Protection:**
```python
# All file paths canonicalized and validated
safe_path = (root / requested_path).resolve()
if not safe_path.is_relative_to(root):
    return Response(status=51, meta='Not found')  # Never expose path info
```

### Client Certificate Support

**Mutual TLS (mTLS):**
- Server can request client certificates for authentication
- Status codes `60-62` for certificate-based access control
- Certificate fingerprint validation

**Generate Client Certificate:**
```bash
nauyaca cert generate-client --name "My Identity"
```

### Security Best Practices

**For Server Operators:**
- Use proper certificates (CA-signed or self-signed with TOFU)
- Keep private keys secure (file mode 0600)
- Enable rate limiting appropriate to your traffic
- Use whitelist mode for private capsules
- Monitor logs for suspicious activity
- Keep document root clean of sensitive files

**For Client Users:**
- Verify certificate fingerprints on first connection
- Be suspicious of unexpected certificate changes
- Keep TOFU database backed up
- Use separate certificates for different identities
- Check redirect destinations before following

**Important**: See [SECURITY.md](SECURITY.md) for:
- Complete security documentation
- Vulnerability reporting process
- Known limitations
- Deployment guidelines
- Compliance information

### Systemd Service Example

```ini
[Unit]
Description=Nauyaca Gemini Protocol Server
After=network.target

[Service]
Type=simple
User=nauyaca
WorkingDirectory=/opt/nauyaca
ExecStart=/opt/nauyaca/venv/bin/gemini-server --config /etc/nauyaca/config.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Ensure tests pass (`pytest`)
6. Format code (`ruff check src/ tests/`)
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add client certificate support
fix: Handle edge case in URL parsing
docs: Update API reference
test: Add integration tests for server
refactor: Simplify protocol parsing logic
```

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Resources

- [Gemini Protocol Specification](https://geminiprotocol.net/docs/specification.gmi)
- [Gemini Protocol FAQ](https://geminiprotocol.net/docs/faq.gmi)
- [Project Gemini](https://gemini.circumlunar.space/)
- [Awesome Gemini](https://github.com/kr1sp1n/awesome-gemini)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

## 💬 Support

- Documentation: See `docs/` directory
- Issues: GitHub Issues
- Discussions: GitHub Discussions

## 🙏 Acknowledgments

- Solderpunk for creating the Gemini protocol
- The Gemini community for feedback and testing

---

**Note**: This project is in active development. The API may change until version 1.0.0.

For more detailed documentation, see the `docs/` directory.
