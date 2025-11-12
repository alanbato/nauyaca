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
uv tool install gemini --from nauyaca

# Use it as a library in your project
uv add nauyaca
```

### Generate SSL Certificates (for development)

```bash
# Generate self-signed certificate
python -m nauyaca.utils.certificates generate \
    --hostname localhost \
    --output capsule/certs/
```

### Running the Server

```bash
# Start server with default settings
gemini-server --root ./capsule --host localhost --port 1965

# Or use Python module
python -m nauyaca server --root ./capsule
```

### Using the Client

```bash
# Fetch a resource
gemini-client gemini://localhost:1965/

# Interactive mode
gemini-client --interactive

# Or as a library
python -c "
import asyncio
from gemini.client import GeminiClient

async def main():
    async with GeminiClient() as client:
        response = await client.fetch('gemini://gemini.circumlunar.space/')
        print(response.body)

asyncio.run(main())
"
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

Create a `config.toml` file:

```toml
[server]
host = "0.0.0.0"
port = 1965
root = "./capsule"
index = "index.gmi"

[tls]
certfile = "./certs/cert.pem"
keyfile = "./certs/key.pem"
min_version = "TLS1_2"

[security]
require_client_cert = false
rate_limit = 100  # requests per minute
max_request_size = 1024  # bytes

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file = "./logs/server.log"

[virtual_hosts]
"example.com" = "./capsules/example"
"another.com" = "./capsules/another"
```

### Client Configuration

Create `~/.config/nauyaca/config.toml`:

```toml
[client]
timeout = 30
follow_redirects = true
max_redirects = 5
verify_mode = "tofu"  # tofu, strict, or none

[tofu]
database = "~/.config/gemini/known_hosts.db"
prompt_on_change = true

[certificates]
directory = "~/.config/gemini/certs"

[cache]
enabled = true
directory = "~/.cache/gemini"
max_age = 3600  # seconds
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

## 🔒 Security Considerations

### TLS Requirements
- Minimum TLS 1.2
- Self-signed certificates acceptable (TOFU model)
- Client certificates supported for authentication

### TOFU Implementation
- First connection: Accept and store certificate fingerprint
- Subsequent connections: Verify against stored fingerprint
- Certificate change: Prompt user for confirmation

### Rate Limiting
- Configurable requests per minute per IP
- Token bucket algorithm
- Graceful degradation

### Path Traversal Protection
```python
# Bad: ../../../etc/passwd
# Good: Canonicalize and validate paths
from pathlib import Path

safe_path = (root / requested_path).resolve()
if not safe_path.is_relative_to(root):
    return Response(status=51, meta='Invalid path')
```

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