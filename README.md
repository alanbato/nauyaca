# Nauyaca - Gemini Protocol Server & Client

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue.svg)](https://nauyaca.readthedocs.io)

A modern, high-performance implementation of the [Gemini protocol](https://geminiprotocol.net) in Python. Nauyaca (pronounced "now-YAH-kah", meaning "serpent" in Nahuatl) uses asyncio's low-level Protocol/Transport pattern for efficient, non-blocking network I/O with both server and client capabilities.

## Key Features

- **High Performance** - asyncio Protocol/Transport pattern for maximum efficiency
- **Security First** - Mandatory TLS 1.2+, TOFU certificate validation, rate limiting, and access control
- **Production Ready** - TOML configuration, middleware system, and systemd integration
- **Developer Friendly** - Full type hints, comprehensive tests, and modern tooling with `uv`

> **[Read the full documentation](https://nauyaca.readthedocs.io)**

## Quick Start

### Installation

```bash
# As a CLI tool (recommended)
uv tool install nauyaca

# As a library
uv add nauyaca

# From source (for development)
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca && uv sync
```

### Run a Server

```bash
# Serve content from a directory
nauyaca serve ./capsule

# With configuration file
nauyaca serve --config config.toml

# With hot-reload for development
nauyaca serve ./capsule --reload
```

### Fetch Content

```bash
# Get a Gemini resource
nauyaca get gemini://geminiprotocol.net/

# With verbose output
nauyaca get gemini://geminiprotocol.net/ --verbose
```

### Use as a Library

```python
import asyncio
from nauyaca.client import GeminiClient

async def main():
    async with GeminiClient() as client:
        response = await client.get("gemini://geminiprotocol.net/")

        if response.is_success():
            print(response.body)
        elif response.is_redirect():
            print(f"Redirect to: {response.redirect_url}")
        else:
            print(f"Error {response.status}: {response.meta}")

asyncio.run(main())
```

## Documentation

**[nauyaca.readthedocs.io](https://nauyaca.readthedocs.io)**

| Section | Description |
|---------|-------------|
| [Installation](https://nauyaca.readthedocs.io/installation/) | Setup and requirements |
| [Quick Start](https://nauyaca.readthedocs.io/quickstart/) | Get running in 5 minutes |
| [Tutorials](https://nauyaca.readthedocs.io/tutorials/) | Step-by-step guides |
| [How-to Guides](https://nauyaca.readthedocs.io/how-to/) | Task-oriented recipes |
| [Reference](https://nauyaca.readthedocs.io/reference/) | CLI, configuration, API |
| [Explanation](https://nauyaca.readthedocs.io/explanation/) | Architecture and concepts |

## Contributing

```bash
# Setup
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca && uv sync

# Test
uv run pytest

# Lint & Type Check
uv run ruff check src/ tests/
uv run mypy src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Resources

- [Gemini Protocol](https://geminiprotocol.net) - Official protocol website
- [SECURITY.md](SECURITY.md) - Security documentation and vulnerability reporting
- [GitHub Issues](https://github.com/alanbato/nauyaca/issues) - Bug reports
- [GitHub Discussions](https://github.com/alanbato/nauyaca/discussions) - Questions and ideas

## Acknowledgments

- **Solderpunk** for creating the Gemini protocol
- The **Gemini community** for feedback and inspiration

---

**Status**: Active development (pre-1.0). Core protocol and security features are stable.
