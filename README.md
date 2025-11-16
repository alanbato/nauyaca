# Nauyaca - Gemini Protocol Server & Client

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

A modern, high-performance implementation of the Gemini protocol in Python using asyncio, providing both server and client capabilities.

## ✨ Why Nauyaca?

**Nauyaca** (pronounced "now-YAH-kah", meaning "serpent" in Nahuatl) brings modern Python async capabilities to the Gemini protocol:

- **🚀 High Performance**: Uses asyncio's low-level Protocol/Transport pattern for maximum efficiency
- **🔒 Security First**: TOFU certificate validation, rate limiting, and access control built-in
- **⚙️ Production Ready**: Comprehensive configuration, middleware system, and systemd integration
- **🛠️ Developer Friendly**: Full type hints, extensive tests, and powered by `uv` for fast dependency management
- **📚 Well Documented**: Clear architecture docs, security guidelines, and API examples

## 📋 Table of Contents

- [Why Nauyaca?](#-why-nauyaca)
- [Project Overview](#-project-overview)
  - [What is Gemini?](#what-is-gemini)
  - [About Nauyaca](#about-nauyaca)
  - [Goals](#goals)
  - [Project Status](#project-status)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Server](#running-the-server)
  - [Using the Client](#using-the-client)
  - [As a Library](#as-a-library)
- [Core Features](#-core-features)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [Testing](#-testing)
- [API Examples](#-api-examples)
- [Security Features](#-security-features)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [Resources](#-resources)
- [Roadmap](#-roadmap)

## 📖 Project Overview

### What is Gemini?

The [Gemini protocol](https://geminiprotocol.net) is a modern, privacy-focused alternative to HTTP and the web. It aims to be:

- **Simple**: Easier to implement than HTTP, harder to extend (by design)
- **Privacy-focused**: No cookies, no tracking, no JavaScript
- **Secure**: TLS is mandatory, not optional
- **Lightweight**: Text-focused content with minimal formatting
- **User-centric**: Readers control how content is displayed

Think of it as a modern take on Gopher, sitting comfortably between the complexity of the web and the simplicity of plain text.

### About Nauyaca

This project implements the Gemini protocol with a focus on **performance** and **security**. Unlike typical implementations, Nauyaca uses Python's low-level asyncio Protocol/Transport pattern for efficient, non-blocking network I/O with fine-grained control over connection handling.

### Goals

- ✅ Implement a production-ready Gemini server
- ✅ Implement a full-featured Gemini client
- ✅ Support all Gemini protocol features (TLS, client certs, TOFU, etc.)
- ✅ Provide clean, maintainable, well-documented code
- ✅ Include comprehensive test coverage
- ✅ Offer both library and CLI interfaces

### Project Status

**Current Phase**: Security Hardening & Integration Testing

| Feature | Status |
|---------|--------|
| Core Protocol Implementation | ✅ Complete |
| TLS 1.2+ Support | ✅ Complete |
| Server Configuration (TOML) | ✅ Complete |
| TOFU Certificate Validation | ✅ Complete |
| Rate Limiting & DoS Protection | ✅ Complete |
| IP-based Access Control | ✅ Complete |
| Client Session Management | ✅ Complete |
| Security Documentation | ✅ Complete |
| Integration Testing | 🚧 In Progress |
| CLI Interface | 🚧 In Progress |
| Static File Serving | 📋 Planned |
| Content Type Detection | 📋 Planned |

The core protocol and security features are production-ready. CLI and content serving features are being actively developed.

## 🛠 Technology Stack

- **Python 3.11+** - Modern Python features and performance
- **asyncio** - Asynchronous I/O using Protocol/Transport pattern
- **ssl** - TLS 1.2+ encryption with custom certificate validation
- **uv** - Fast, modern Python package manager for development
- **pytest-asyncio** - Async test support and fixtures
- **typer** - CLI interface with rich terminal output
- **cryptography** - Certificate handling and TOFU implementation
- **tomllib** - TOML configuration file parsing

## 🏗 Project Structure

```
nauyaca/
├── README.md
├── SECURITY.md              # Security documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── CODE_OF_CONDUCT.md       # Code of conduct
├── pyproject.toml           # Project metadata and dependencies (managed by uv)
├── uv.lock                  # Dependency lock file
├── config.example.toml      # Full configuration example
├── config.minimal.toml      # Minimal configuration example
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
│       │   └── middleware.py     # Rate limiting, access control
│       │
│       ├── client/
│       │   ├── __init__.py
│       │   ├── protocol.py       # Client protocol implementation
│       │   └── session.py        # High-level client API
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── tls.py            # TLS context creation
│       │   ├── certificates.py   # Cert generation and management
│       │   └── tofu.py           # TOFU database
│       │
│       └── utils/
│           ├── __init__.py
│           └── url.py            # URL parsing/validation
│
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_protocol/
│   ├── test_server/
│   ├── test_client/
│   ├── test_security/
│   └── test_integration/
│
├── docs/
│   └── gemini_protocol/         # Gemini protocol reference docs
│       └── gemtext.txt
│
└── capsule/                     # Example Gemini capsule content directory
```

## 🚀 Quick Start

### Prerequisites

- Python 3.14 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager (recommended)
  ```bash
  # Install uv if you haven't already
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Installation

**Option 1: Standalone CLI tool** (recommended for general use)
```bash
uv tool install nauyaca
```

**Option 2: As a library** (for development or embedding in your project)
```bash
# Add to existing project
uv add nauyaca

# Or start a new project
uv init my-gemini-project
cd my-gemini-project
uv add nauyaca
```

**Option 3: From source** (for development)
```bash
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca
uv sync
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
# Get a resource
nauyaca get gemini://geminiprotocol.net/

# Get with verbose output showing response headers
nauyaca get gemini://geminiprotocol.net/ --verbose

# Manage TOFU database
nauyaca tofu list
nauyaca tofu trust geminiprotocol.net
nauyaca tofu export backup.toml
nauyaca tofu import backup.toml
nauyaca tofu revoke example.com
```

### As a Library

```python
import asyncio
from nauyaca.client import GeminiClient

async def main():
    # Simple fetch with TOFU validation
    async with GeminiClient() as client:
        response = await client.get("gemini://geminiprotocol.net/")

        if response.is_success():
            print(f"Content-Type: {response.meta}")
            print(response.body)
        elif response.is_redirect():
            print(f"Redirect to: {response.redirect_url}")
        else:
            print(f"Error {response.status}: {response.meta}")

asyncio.run(main())
```

### Development Standards

This project follows modern Python best practices:
- **PEP 8** style guide compliance
- **Ruff** for linting and code formatting (replaces Black, isort, flake8)
- **mypy** for strict type checking
- **pytest** for comprehensive testing with async support
- **uv** for fast, reliable dependency management

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src/nauyaca --cov-report=html

# Run specific test file
uv run pytest tests/test_protocol/test_request.py

# Run specific test function
uv run pytest tests/test_server/test_handler.py::test_static_file_serving

# Run with verbose output
uv run pytest -v

# Run only unit tests (fast)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Watch mode (requires pytest-watch)
uv run ptw
```

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
nauyaca tofu export backup.toml

# Import known hosts
nauyaca tofu import backup.toml

# Revoke trust for a host
nauyaca tofu revoke example.com

# Manually trust a host (connects and retrieves certificate)
nauyaca tofu trust example.com
```

## 🏛 Architecture

### Key Design Decisions

1. **asyncio Protocol Pattern**: Low-level control, high performance
2. **Plugin Architecture**: Extensible handler system
3. **TOFU by Default**: Privacy-focused certificate validation
4. **Stateless**: Each request is independent (no sessions)
5. **Type Hints**: Full typing for better IDE support and error catching

## 🧪 Testing

Nauyaca has comprehensive test coverage across multiple layers:

### Test Organization

- **Unit Tests** (`@pytest.mark.unit`)
  - Test individual components in isolation
  - Mock external dependencies
  - Fast execution for rapid development feedback

- **Integration Tests** (`@pytest.mark.integration`)
  - Test component interactions
  - Real network connections (localhost only)
  - TLS handshake validation

- **Security Tests**
  - TOFU certificate validation
  - Rate limiting behavior
  - Access control enforcement
  - Path traversal protection

### Test Coverage

Current test coverage focuses on:
- ✅ Protocol parsing and validation
- ✅ TLS configuration and certificate handling
- ✅ TOFU database operations (store, verify, export, import)
- ✅ Server middleware (rate limiting, access control)
- ✅ Configuration loading and validation
- 🚧 End-to-end client/server integration (in progress)

Run `uv run pytest --cov=src/nauyaca --cov-report=html` to generate a detailed coverage report.

## 📚 API Examples

### Using Nauyaca as a Library

```python
import asyncio
from nauyaca.client import GeminiClient

async def main():
    # Create client with TOFU validation enabled (default)
    async with GeminiClient() as client:
        # Simple GET request
        response = await client.get("gemini://geminiprotocol.net/")

        # Check response status
        if response.is_success():
            print(f"Content-Type: {response.meta}")
            print(response.body)
        elif response.is_redirect():
            print(f"Redirect to: {response.redirect_url}")
        elif 10 <= response.status < 20:
            # Input required (status 1x)
            print(f"Input requested: {response.meta}")
        else:
            print(f"Error {response.status}: {response.meta}")

asyncio.run(main())
```

### Advanced Configuration

```python
from nauyaca.client import GeminiClient

# Custom timeout and redirect settings
async with GeminiClient(timeout=60, max_redirects=3) as client:
    response = await client.get("gemini://geminiprotocol.net/")

# Disable redirect following
async with GeminiClient() as client:
    response = await client.get(
        "gemini://geminiprotocol.net/",
        follow_redirects=False
    )
```

For more advanced usage, see the [integration tests](tests/test_integration/) which demonstrate server and client usage patterns.

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
nauyaca tofu export backup.toml

# Import from backup
nauyaca tofu import backup.toml

# Revoke trust for compromised host
nauyaca tofu revoke example.com

# Manually trust a certificate (connects and retrieves it)
nauyaca tofu trust example.com
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

## 🚀 Deployment

### Systemd Service Example

For production deployments on Linux systems with systemd:

```ini
[Unit]
Description=Nauyaca Gemini Protocol Server
After=network.target

[Service]
Type=simple
User=nauyaca
Group=nauyaca
WorkingDirectory=/opt/nauyaca
ExecStart=/usr/local/bin/nauyaca serve --config /etc/nauyaca/config.toml
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/nauyaca/capsule

[Install]
WantedBy=multi-user.target
```

Save this as `/etc/systemd/system/nauyaca.service`, then:

```bash
# Enable and start the service
sudo systemctl enable nauyaca
sudo systemctl start nauyaca

# Check status
sudo systemctl status nauyaca

# View logs
sudo journalctl -u nauyaca -f
```

## 🤝 Contributing

We welcome contributions! Follow these steps to get started.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca

# Install dependencies with uv
uv sync

# Run tests to verify setup
uv run pytest

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/
```

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Ensure tests pass: `uv run pytest`
6. Run linting: `uv run ruff check src/ tests/`
7. Run type checking: `uv run mypy src/`
8. Commit changes (`git commit -m 'Add amazing feature'`)
9. Push to branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

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

### Gemini Protocol
- [Gemini Protocol Homepage](https://geminiprotocol.net) - Official Gemini protocol website
- [Awesome Gemini](https://github.com/kr1sp1n/awesome-gemini) - Curated list of Gemini resources

### Python & Asyncio
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html) - Official asyncio docs
- [asyncio Protocol/Transport](https://docs.python.org/3/library/asyncio-protocol.html) - Low-level networking
- [Real Python - Async IO](https://realpython.com/async-io-python/) - Comprehensive tutorial

### Nauyaca Documentation
- [SECURITY.md](SECURITY.md) - Security features and best practices
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Code of conduct

## 💬 Support & Community

- **📖 Documentation**: See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and project docs
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/alanbato/nauyaca/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/alanbato/nauyaca/discussions)
- **🤝 Contributing**: See [Contributing](#-contributing) section above
- **📧 Security Issues**: See [SECURITY.md](SECURITY.md) for responsible disclosure

### Getting Help

1. Check the documentation ([SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md))
2. Search existing [GitHub Issues](https://github.com/alanbato/nauyaca/issues)
3. Ask questions in [GitHub Discussions](https://github.com/alanbato/nauyaca/discussions)
4. Review the [integration tests](tests/test_integration/) for usage examples

## 🗺️ Roadmap

### Version 0.2.0 (Current)
- ✅ Core protocol implementation
- ✅ Security features (TOFU, rate limiting, access control)
- ✅ Configuration system
- 🚧 Integration testing
- 🚧 CLI interface completion

### Version 0.3.0 (Next)
- Static file serving
- Content type detection
- Directory listings
- Error page templates
- Performance optimization

### Version 1.0.0 (Stable)
- Production-ready release
- Stable API
- Complete documentation
- Performance benchmarks
- Migration guides

## 🙏 Acknowledgments

- **Solderpunk** for creating the Gemini protocol
- The **Gemini community** for feedback and inspiration
- Contributors and testers who help improve Nauyaca

---

**Development Status**: This project is in active development (pre-1.0). Core protocol and security features are stable, but the high-level API may change based on community feedback.
