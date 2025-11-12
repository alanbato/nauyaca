# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nauyaca is a modern, production-ready implementation of the Gemini protocol in Python using asyncio's Protocol/Transport pattern. The project provides both server and client capabilities with full protocol feature support including TLS, client certificates, TOFU validation, and comprehensive error handling.

**Current Status**: Early development - prototype exists in `sample/` directory. The production implementation will be built in `src/nauyaca/` following the architecture and patterns demonstrated in the prototype.

## Development Setup

```bash
# Install project with dev dependencies
uv sync

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/nauyaca --cov-report=html

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/

# Run specific test file
pytest tests/test_protocol/test_request.py

# Run single test function
pytest tests/test_server/test_handler.py::test_static_file_serving

# Run tests by marker
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not slow"    # Exclude slow tests
```

## Architecture & Core Design

### Why Protocol/Transport Pattern?

The project uses Python's low-level `asyncio.Protocol` and `asyncio.Transport` pattern (not the higher-level Streams API) because:

1. **Efficient callback-based design**: Avoids async/await context switching overhead
2. **Fine-grained control**: Direct access to buffering, flow control, and connection lifecycle
3. **Protocol-oriented**: Natural fit for implementing network protocols
4. **Performance**: Better for high-throughput server applications

### Protocol/Transport Fundamentals

**Key Protocol Methods**:
```python
class MyProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        # Called once when connection established
        self.transport = transport

    def data_received(self, data):
        # Called one or more times as data arrives
        # CRITICAL: May be called multiple times for a single logical message
        self.buffer += data

    def eof_received(self):
        # Called when remote end closes their write side (graceful shutdown)
        return False  # Return False to close our write side too

    def connection_lost(self, exc):
        # Called when connection is fully closed
        # exc is None for clean close, otherwise contains exception
```

**Connection Lifecycle**:
```
connection_made(transport)
    ↓
data_received(data)      # Can be called multiple times
data_received(data)      # with partial data
data_received(data)
    ↓
eof_received()          # Optional - only for graceful shutdown
    ↓
connection_lost(exc)
```

### Gemini Protocol Specification

**Core Characteristics**:
- **Port**: TCP 1965 (default)
- **Security**: Mandatory TLS 1.2+ (non-negotiable, no plaintext fallback)
- **Connection Model**: One request per connection, non-persistent
- **Max Request Size**: 1024 bytes (URL including scheme and CRLF)
- **Encoding**: UTF-8 for all text

**Transaction Flow**:
```
Client                          Server
  |                                |
  |--- TLS Handshake ------------->|
  |<-- TLS Handshake --------------|
  |                                |
  |--- gemini://host/path\r\n --->|
  |                                |
  |<-- 20 text/gemini\r\n ---------|
  |<-- (response body) ------------|
  |                                |
  |<-- Connection Close -----------|
```

**Request Format**:
- Single line: `<URL><CRLF>`
- Must be absolute URL with scheme (e.g., `gemini://example.com/path`)
- Terminated by CRLF (`\r\n`)
- Maximum 1024 bytes total

**Response Format**:
- Header: `<STATUS><SPACE><META><CRLF>`
- STATUS: 2-digit code (10-69)
- META: Varies by status (MIME type for 2x, redirect URL for 3x, error message for failures)
- Body: Optional, only present for 2x success responses

**Status Code Ranges**:
- **1x (INPUT)**: Server needs additional input from client
  - 10: INPUT - Meta is prompt text
  - 11: SENSITIVE INPUT - Like 10 but don't echo (passwords)
- **2x (SUCCESS)**: Request successful, body follows
  - 20: SUCCESS - Meta is MIME type (e.g., `text/gemini`)
- **3x (REDIRECT)**: Resource moved
  - 30: REDIRECT TEMPORARY - Meta is new URL
  - 31: REDIRECT PERMANENT - Meta is new URL
- **4x (TEMPORARY FAILURE)**: Retry may succeed later
  - 40: TEMPORARY FAILURE - Generic
  - 41: SERVER UNAVAILABLE
  - 42: CGI ERROR
  - 43: PROXY ERROR
  - 44: SLOW DOWN - Rate limiting (meta may contain delay in seconds)
- **5x (PERMANENT FAILURE)**: Don't retry
  - 50: PERMANENT FAILURE - Generic
  - 51: NOT FOUND
  - 52: GONE - Previously existed, now removed
  - 53: PROXY REQUEST REFUSED
  - 59: BAD REQUEST
- **6x (CLIENT CERTIFICATE REQUIRED)**:
  - 60: CLIENT CERTIFICATE REQUIRED
  - 61: CERTIFICATE NOT AUTHORISED
  - 62: CERTIFICATE NOT VALID

### Critical Implementation Patterns

#### 1. Data Buffering (Essential)

`data_received()` can be called multiple times with partial data. **Always** accumulate in a buffer:

```python
def __init__(self):
    self.buffer = b""

def data_received(self, data):
    self.buffer += data

    # Only process when complete message received
    if b'\r\n' in self.buffer:
        message, remaining = self.buffer.split(b'\r\n', 1)
        self.process_message(message)
        self.buffer = remaining
```

**Common mistake**: Processing data immediately without buffering leads to parsing errors with fragmented messages.

#### 2. Bridging Callbacks to async/await

Protocol methods use callbacks, but higher-level APIs need async/await. Use `asyncio.Future`:

```python
# In high-level async function:
loop = asyncio.get_running_loop()
result_future = loop.create_future()

# Create protocol with future
transport, protocol = await loop.create_connection(
    lambda: MyProtocol(result_future),
    host, port
)

# Protocol sets result in connection_lost():
def connection_lost(self, exc):
    if not self.result_future.done():
        self.result_future.set_result(self.data)

# Back in async function:
result = await result_future  # Can now await the result
```

#### 3. TLS Configuration

Gemini **requires** TLS 1.2+ minimum:

```python
# Server-side:
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

# Client-side (production with TOFU):
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED  # Or custom TOFU verification
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

# Client-side (testing with self-signed certs):
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
```

#### 4. Connection Management

Gemini connections are **non-persistent**:
- Server: **Always** close connection after sending response
- Client: Expect connection to close after receiving response
- No keep-alive, no pipelining, no connection reuse

```python
# Server after sending response:
self.transport.write(response.encode('utf-8'))
self.transport.close()  # Required by Gemini spec

# Client: Handle in connection_lost()
def connection_lost(self, exc):
    # This is normal - extract final data here
    self.result_future.set_result(self.buffer)
```

#### 5. Flow Control

For handling backpressure when writing large responses:

```python
def pause_writing(self):
    # Called when write buffer is full
    self.paused = True

def resume_writing(self):
    # Called when buffer drained
    self.paused = False
    self.continue_sending_data()
```

### Planned Module Structure

```
src/nauyaca/
├── __init__.py
├── __main__.py           # CLI entry point
│
├── protocol/
│   ├── __init__.py
│   ├── constants.py      # Status codes, MIME types, limits (1024 bytes, etc.)
│   ├── request.py        # GeminiRequest class, URL parsing/validation
│   ├── response.py       # GeminiResponse class, response building
│   └── status.py         # StatusCode enum, status interpretation utilities
│
├── server/
│   ├── __init__.py
│   ├── protocol.py       # GeminiServerProtocol (asyncio.Protocol subclass)
│   ├── handler.py        # RequestHandler base class, StaticFileHandler, CGIHandler
│   ├── router.py         # URL pattern matching, route registration
│   ├── config.py         # ServerConfig dataclass, TOML loading
│   └── middleware.py     # Logging, rate limiting, access control
│
├── client/
│   ├── __init__.py
│   ├── protocol.py       # GeminiClientProtocol (asyncio.Protocol subclass)
│   ├── session.py        # GeminiClient high-level async API, connection pooling
│   ├── tofu.py           # Trust-On-First-Use certificate validation
│   └── cache.py          # Response caching with expiry
│
├── security/
│   ├── __init__.py
│   ├── tls.py            # SSL context creation, TLS config helpers
│   ├── certificates.py   # Cert generation, loading, fingerprinting
│   └── tofu.py           # TOFU database (SQLite), cert storage/comparison
│
├── content/
│   ├── __init__.py
│   ├── gemtext.py        # Gemtext parser/renderer, line type detection
│   ├── mime.py           # MIME type detection from file extension/content
│   └── templates.py      # Error page templates, directory listing templates
│
└── utils/
    ├── __init__.py
    ├── url.py            # URL parsing, validation, normalization
    ├── encoding.py       # Charset detection, UTF-8 handling
    └── logging.py        # Logging configuration, formatters
```

### Testing Strategy

**Test Organization**:
```
tests/
├── conftest.py              # Shared fixtures (SSL contexts, temp dirs, etc.)
├── test_protocol/
│   ├── test_constants.py
│   ├── test_request.py      # URL parsing, validation
│   └── test_response.py     # Response building, header formatting
├── test_server/
│   ├── test_protocol.py     # Server protocol behavior
│   ├── test_handler.py      # Request handlers
│   └── test_router.py       # Route matching
├── test_client/
│   ├── test_protocol.py     # Client protocol behavior
│   ├── test_session.py      # High-level client API
│   └── test_tofu.py         # TOFU validation
├── test_security/
│   └── test_certificates.py
└── test_integration/
    ├── test_server_client.py  # Full request/response cycle
    └── test_tls.py            # TLS handshake, client certs
```

**Test Markers**:
- `@pytest.mark.unit`: Fast, isolated unit tests
- `@pytest.mark.integration`: Tests with real network connections
- `@pytest.mark.slow`: Long-running tests (load testing, timeouts)
- `@pytest.mark.network`: Tests requiring network access

**Testing Protocols Without Network**:
```python
from unittest.mock import Mock

def test_request_handling():
    protocol = GeminiServerProtocol()
    transport = Mock()

    protocol.connection_made(transport)
    protocol.data_received(b'gemini://test/path\r\n')

    # Verify response
    transport.write.assert_called_once()
    transport.close.assert_called_once()
    response = transport.write.call_args[0][0].decode('utf-8')
    assert response.startswith('20 ')
```

### Common Pitfalls & How to Avoid

1. **Forgetting to buffer data**:
   - ❌ `message = data.decode()` in `data_received()`
   - ✅ `self.buffer += data; if b'\r\n' in self.buffer: ...`

2. **Wrong line endings**:
   - ❌ Splitting on `\n` or using `readline()`
   - ✅ Always check for `\r\n` (CRLF)

3. **Keeping connections alive**:
   - ❌ Not calling `transport.close()` after response
   - ✅ Always close after each transaction (Gemini requirement)

4. **Encoding issues**:
   - ❌ Implicit encoding, mixing bytes and strings
   - ✅ Explicit `.encode('utf-8')` and `.decode('utf-8')`

5. **TLS version**:
   - ❌ Using default TLS version
   - ✅ `ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2`

6. **Request size limits**:
   - ❌ Not limiting request size
   - ✅ Enforce 1024 byte limit for requests

7. **Path traversal**:
   - ❌ Directly joining user paths: `root + requested_path`
   - ✅ Use `Path.resolve()` and validate with `is_relative_to()`
   ```python
   safe_path = (root / requested_path).resolve()
   if not safe_path.is_relative_to(root):
       return error_response(51, "Invalid path")
   ```

### TOFU (Trust On First Use) Implementation

Gemini uses TOFU instead of traditional CA-based PKI:

**Algorithm**:
1. First connection to host: Accept certificate, store fingerprint (SHA-256 hash)
2. Subsequent connections: Compare certificate fingerprint with stored value
3. Certificate change: Prompt user for confirmation (may be legitimate renewal or MITM attack)

**Storage**: Use SQLite database with schema:
```sql
CREATE TABLE known_hosts (
    hostname TEXT PRIMARY KEY,
    port INTEGER,
    fingerprint TEXT NOT NULL,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
)
```

### Security Considerations

**Server Security**:
- Rate limiting: Token bucket algorithm, configurable per-IP limits
- Path traversal protection: Canonicalize paths, validate within document root
- Request size limits: 1024 bytes maximum
- Client certificate validation: For 6x status codes
- Access control lists: IP-based allow/deny lists

**Client Security**:
- TOFU certificate validation
- Certificate pinning for known hosts
- Prompt on certificate change
- Respect rate limit headers (44 SLOW DOWN)
- Redirect loop detection (max 5 redirects)

### Code Style & Quality Standards

**Linting & Formatting**:
- Use **Ruff** for both linting and formatting (replaces Black + isort + flake8)
- Configuration in `pyproject.toml` with `select = ["E", "W", "F", "I", "C", "B", "UP"]`
- Run `ruff check src/ tests/` before committing

**Type Checking**:
- Use **mypy** with strict settings enabled
- All functions must have type hints
- No `Any` types without explicit comment justification
- Configuration: `disallow_untyped_defs = true`

**Testing**:
- Minimum 80% code coverage
- All public APIs must have tests
- Integration tests for server/client interaction
- Mock external dependencies in unit tests

**Documentation**:
- All public classes/functions have docstrings
- Docstrings follow Google style format
- Include usage examples for complex APIs

### Reference Materials

The `sample/` directory contains the prototype implementation:

- **`sample/GEMINI_ASYNCIO_GUIDE.md`**: Comprehensive 400+ line guide explaining:
  - Protocol/Transport pattern fundamentals
  - Step-by-step server implementation
  - Step-by-step client implementation
  - TLS configuration
  - Buffering strategies
  - Future-based async/await bridging
  - Testing approaches
  - Common pitfalls

- **`sample/gemini_protocol.py`**: Working 350+ line reference implementation with:
  - `GeminiServerProtocol`: Complete server with request parsing, routing, error handling
  - `GeminiClientProtocol`: Complete client with response parsing, future-based async interface
  - `start_gemini_server()`: Server startup with TLS
  - `fetch_gemini()`: High-level async client function
  - Demo code showing concurrent server/client operation

**When implementing features**: Always refer to these samples first to understand the proven patterns before writing production code in `src/`.

### Development Workflow Conventions

1. **Implement incrementally**: Start with protocol layer, then server, then client
2. **Test as you go**: Write tests alongside implementation (TDD encouraged)
3. **Reference samples**: Check `sample/` for patterns before implementing
4. **Type everything**: No untyped code - use `mypy --strict`
5. **Document thoroughly**: Complex protocol logic needs clear comments
6. **Security first**: Validate all inputs, sanitize all paths, enforce limits

### CLI Commands (Future)

Once implemented, the project will provide:

```bash
# Start server
gemini-server --root ./capsule --host localhost --port 1965

# Fetch resource
gemini-client gemini://example.com/

# Interactive client
gemini-client --interactive

# Generate self-signed certificate
python -m nauyaca.security.certificates generate --hostname localhost
```

### Commit Conventions

Follow Conventional Commits format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
