# Nauyaca

**A modern, high-performance implementation of the Gemini protocol in Python**

Nauyaca (pronounced "now-YAH-kah", meaning "serpent" in Nahuatl) brings modern Python async capabilities to the Gemini protocol, providing both server and client implementations with a focus on performance, security, and developer experience.

---

## Why Nauyaca?

<div class="grid cards" markdown>

-   :rocket: **High Performance**

    ---

    Built on asyncio's low-level Protocol/Transport pattern for maximum efficiency and fine-grained control over network I/O

-   :lock: **Security First**

    ---

    TOFU certificate validation, rate limiting, access control, and TLS 1.2+ enforcement built-in from the ground up

-   :gear: **Production Ready**

    ---

    Comprehensive TOML configuration, middleware system, systemd integration, and deployment-ready architecture

-   :hammer_and_wrench: **Developer Friendly**

    ---

    Full type hints, extensive test coverage, clean APIs, and powered by `uv` for fast dependency management

</div>

---

## Quick Example

Get started in seconds with both client and server:

=== "Client"

    ```python
    import asyncio
    from nauyaca.client import GeminiClient

    async def main():
        async with GeminiClient() as client:
            response = await client.get("gemini://geminiprotocol.net/")

            if response.is_success():
                print(f"Content-Type: {response.meta}")
                print(response.body)

    asyncio.run(main())
    ```

=== "Server"

    ```python
    import asyncio
    from nauyaca.server import GeminiServer
    from nauyaca.server.config import ServerConfig

    async def main():
        config = ServerConfig(
            host="localhost",
            port=1965,
            document_root="./capsule"
        )

        server = GeminiServer(config)
        await server.start()

    asyncio.run(main())
    ```

=== "CLI"

    ```bash
    # Start a server
    nauyaca serve ./capsule --host localhost --port 1965

    # Fetch a resource
    nauyaca get gemini://geminiprotocol.net/

    # Manage trusted certificates
    nauyaca tofu list
    nauyaca tofu trust example.com
    ```

---

## Installation

Choose the installation method that fits your use case:

!!! tip "Recommended: Install with uv"

    ```bash
    # As a standalone CLI tool
    uv tool install nauyaca

    # Or add to your project
    uv add nauyaca
    ```

!!! note "Alternative: Install with pip"

    ```bash
    pip install nauyaca
    ```

**Requirements:** Python 3.10 or higher

---

## Key Features

### Server Capabilities

- **Complete Protocol Support** - TLS 1.2+, all status codes (1x-6x), client certificates
- **Security Hardened** - Rate limiting, IP-based access control, path traversal protection
- **TOML Configuration** - Flexible configuration with sensible defaults and CLI overrides
- **Middleware Architecture** - Composable middleware for logging, rate limiting, and access control
- **Production Ready** - Systemd integration, graceful shutdown, comprehensive error handling

### Client Capabilities

- **TOFU Validation** - Trust-On-First-Use certificate validation with SQLite-backed database
- **Async/Await API** - Clean, modern Python API built on asyncio
- **Certificate Management** - Import/export known hosts, revoke trust, manual certificate trusting
- **CLI Interface** - Full-featured command-line client for browsing Geminispace
- **Redirect Handling** - Automatic redirect following with loop detection

---

## Documentation Sections

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Getting Started](installation.md)**

    ---

    Installation, quick start guide, and your first Gemini server

    [:octicons-arrow-right-24: Get started](installation.md)

-   :material-book-open-variant: **[Tutorials](tutorials/index.md)**

    ---

    Step-by-step lessons for building Gemini servers and clients

    [:octicons-arrow-right-24: Learn by doing](tutorials/index.md)

-   :material-compass: **[How-To Guides](how-to/index.md)**

    ---

    Practical guides for common tasks and deployment scenarios

    [:octicons-arrow-right-24: Solve problems](how-to/index.md)

-   :material-file-document: **[Reference](reference/index.md)**

    ---

    Complete API reference, CLI commands, and configuration options

    [:octicons-arrow-right-24: Look up details](reference/index.md)

-   :material-lightbulb-on: **[Explanation](explanation/index.md)**

    ---

    Understanding the Gemini protocol, TOFU, and architecture decisions

    [:octicons-arrow-right-24: Understand concepts](explanation/index.md)

-   :material-shield-lock: **[Security](explanation/security-model.md)**

    ---

    Security features, best practices, and vulnerability reporting

    [:octicons-arrow-right-24: Secure your capsule](explanation/security-model.md)

</div>

---

## What is Gemini?

The [Gemini protocol](https://geminiprotocol.net) is a modern, privacy-focused alternative to HTTP and the web. It aims to be:

- **Simple** - Easier to implement than HTTP, harder to extend (by design)
- **Privacy-focused** - No cookies, no tracking, no JavaScript
- **Secure** - TLS is mandatory, not optional
- **Lightweight** - Text-focused content with minimal formatting
- **User-centric** - Readers control how content is displayed

Think of it as a modern take on Gopher, sitting comfortably between the complexity of the web and the simplicity of plain text.

---

## Project Status

!!! success "Version 0.2.0 - Core Features Complete"

    Current phase: Security Hardening & Integration Testing

| Feature | Status |
|---------|--------|
| Core Protocol Implementation | :white_check_mark: Complete |
| TLS 1.2+ Support | :white_check_mark: Complete |
| Server Configuration (TOML) | :white_check_mark: Complete |
| TOFU Certificate Validation | :white_check_mark: Complete |
| Rate Limiting & DoS Protection | :white_check_mark: Complete |
| IP-based Access Control | :white_check_mark: Complete |
| Client Session Management | :white_check_mark: Complete |
| Security Documentation | :white_check_mark: Complete |
| Integration Testing | :construction: In Progress |
| CLI Interface | :construction: In Progress |
| Static File Serving | :calendar: Planned |
| Content Type Detection | :calendar: Planned |

---

## Community & Support

<div class="grid cards" markdown>

-   :material-github: **[GitHub Repository](https://github.com/alanbato/nauyaca)**

    ---

    Source code, issue tracker, and project development

-   :material-bug: **[Bug Reports](https://github.com/alanbato/nauyaca/issues)**

    ---

    Report bugs and request features

-   :material-forum: **[Discussions](https://github.com/alanbato/nauyaca/discussions)**

    ---

    Ask questions and share ideas with the community

-   :material-shield-alert: **[Security](https://github.com/alanbato/nauyaca/security/policy)**

    ---

    Responsible disclosure for security vulnerabilities

</div>

---

## License

Nauyaca is released under the **MIT License**. See the [LICENSE](https://github.com/alanbato/nauyaca/blob/main/LICENSE) file for details.

---

## Next Steps

Ready to get started? Here's what to do next:

1. **[Install Nauyaca](installation.md)** - Get up and running in minutes
2. **[Quick Start Guide](quickstart.md)** - Build your first Gemini server
3. **[Explore Tutorials](tutorials/index.md)** - Learn by building real projects
4. **[Read the Security Guide](explanation/security-model.md)** - Understand TOFU, rate limiting, and best practices

!!! info "Development Status"

    This project is in active development (pre-1.0). Core protocol and security features are stable, but the high-level API may change based on community feedback.
