# Quick Start

Get up and running with Nauyaca in 5 minutes. This guide covers the most common use cases to help you start serving and browsing Gemini content immediately.

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

**Install uv** (if you don't have it):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

Choose the installation method that fits your needs:

=== "Standalone Tool (Recommended)"

    Perfect for running Nauyaca as a CLI tool:

    ```bash
    uv tool install nauyaca
    ```

=== "Library in Your Project"

    For using Nauyaca as a library in your Python project:

    ```bash
    # Add to existing project
    uv add nauyaca

    # Or start a new project
    uv init my-gemini-project
    cd my-gemini-project
    uv add nauyaca
    ```

=== "From Source"

    For development or contributing:

    ```bash
    git clone https://github.com/alanbato/nauyaca.git
    cd nauyaca
    uv sync
    ```

## Use Case 1: Serve Your First Capsule

Host Gemini content from your local machine in three simple steps.

### 1. Create Your Capsule Content

Create a directory with a simple Gemini text file:

```bash
mkdir my-capsule
cat > my-capsule/index.gmi << 'EOF'
# Welcome to My Gemini Capsule!

This is my first Gemini page.

## What is Gemini?

Gemini is a modern, privacy-focused protocol that sits between Gopher and the web.

=> gemini://geminiprotocol.net/ Learn more about Gemini

## Links

=> about.gmi About me
=> /blog Blog posts

Thanks for visiting!
EOF
```

### 2. Start the Server

```bash
nauyaca serve ./my-capsule
```

You'll see output like:

```
[INFO] Auto-generating self-signed certificate for localhost...
[INFO] Server starting on localhost:1965
[INFO] Serving files from: /home/user/my-capsule
[INFO] Press Ctrl+C to stop
```

!!! note "Auto-Generated Certificates"
    By default, Nauyaca generates a self-signed certificate for testing. This is perfect for local development. For production, see the [Certificate Management Guide](how-to/manage-certificates.md).

### 3. Test Your Server

Open another terminal and fetch your page:

```bash
nauyaca get gemini://localhost/
```

You should see your page content displayed!

**Next Steps:**

- See [Server Configuration](reference/configuration.md) for advanced options
- Learn about [TLS certificate generation](how-to/manage-certificates.md) for production
- Read the [Server Security Tutorial](tutorials/securing-your-server.md)

---

## Use Case 2: Browse Gemini Content

Fetch and view content from Gemini servers around the world.

### Fetch a Public Gemini Page

Try fetching the official Gemini protocol homepage:

```bash
nauyaca get gemini://geminiprotocol.net/
```

**Expected Output:**

```
# Project Gemini

## Overview

Gemini is a new internet protocol which:

* Is heavier than gopher
* Is lighter than the web
* Will not replace either
* Strives for maximum power to weight ratio
...
```

### Trust-On-First-Use (TOFU)

The first time you connect to a server, Nauyaca will automatically trust and remember its certificate:

```
[INFO] First connection to geminiprotocol.net:1965
[INFO] Certificate fingerprint: sha256:a1b2c3d4...
[INFO] Storing certificate in TOFU database
```

If the certificate changes later (which could indicate a renewal or a security issue), you'll be prompted:

```
[ERROR] Certificate Changed!
Host: geminiprotocol.net:1965
Old fingerprint: sha256:a1b2c3d4...
New fingerprint: sha256:e5f6g7h8...

This could indicate:
  1. A man-in-the-middle attack
  2. Legitimate certificate renewal

To trust the new certificate, run:
  nauyaca tofu trust geminiprotocol.net
```

### View Response Details

Use the `--verbose` flag to see response headers:

```bash
nauyaca get --verbose gemini://geminiprotocol.net/
```

**Output:**

```
Status  20 (SUCCESS)
Meta    text/gemini; charset=utf-8
URL     gemini://geminiprotocol.net/

# Project Gemini
...
```

### Manage Trusted Certificates

```bash
# List all known hosts
nauyaca tofu list

# Manually trust a host
nauyaca tofu trust example.com

# Revoke trust (force re-trust on next connection)
nauyaca tofu revoke old-server.com

# Export TOFU database for backup
nauyaca tofu export ~/tofu-backup.toml

# Import TOFU database
nauyaca tofu import ~/tofu-backup.toml
```

**Next Steps:**

- Learn about [TOFU security model](explanation/security-model.md)
- See [Client API Reference](reference/api/client.md)
- Explore [Gemini servers to visit](https://geminiprotocol.net/community/)

---

## Use Case 3: Use Nauyaca as a Library

Integrate Gemini capabilities into your Python applications.

### Simple Client Example

Fetch and process Gemini content programmatically:

```python
import asyncio
from nauyaca.client import GeminiClient

async def main():
    # Create client with TOFU validation (recommended)
    async with GeminiClient() as client:
        response = await client.get("gemini://geminiprotocol.net/")

        # Check response status
        if response.is_success():
            print(f"Content-Type: {response.meta}")
            print(f"Body length: {len(response.body)} bytes")
            print("\nContent:")
            print(response.body)
        elif response.is_redirect():
            print(f"Redirected to: {response.meta}")
        else:
            print(f"Error {response.status}: {response.meta}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**

```bash
python my_client.py
```

**Output:**

```
Content-Type: text/gemini; charset=utf-8
Body length: 2847 bytes

Content:
# Project Gemini
...
```

### Simple Server Example

Create a basic Gemini server programmatically:

```python
import asyncio
from pathlib import Path
from nauyaca.server.config import ServerConfig
from nauyaca.server.server import start_server

async def main():
    # Configure server
    config = ServerConfig(
        host="localhost",
        port=1965,
        document_root=Path("./my-capsule"),
        # Optional: specify certificate files
        # certfile=Path("./certs/cert.pem"),
        # keyfile=Path("./certs/key.pem"),
    )

    # Start server (runs until interrupted)
    print(f"Starting server on {config.host}:{config.port}")
    print(f"Serving files from: {config.document_root}")
    print("Press Ctrl+C to stop")

    await start_server(config)

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**

```bash
python my_server.py
```

The server will auto-generate a certificate and start serving content from `./my-capsule`.

### Advanced Client Usage

Handle different response types and errors:

```python
import asyncio
from nauyaca.client import GeminiClient
from nauyaca.security.tofu import CertificateChangedError

async def fetch_with_error_handling(url: str):
    try:
        async with GeminiClient(timeout=30, max_redirects=5) as client:
            response = await client.get(url)

            # Success (2x status codes)
            if response.is_success():
                return response.body

            # Redirect (3x status codes)
            elif response.is_redirect():
                print(f"Redirected to: {response.meta}")
                return await fetch_with_error_handling(response.meta)

            # Input required (1x status codes)
            elif 10 <= response.status < 20:
                print(f"Input requested: {response.meta}")
                user_input = input("Enter input: ")
                # Re-request with query parameter
                return await fetch_with_error_handling(f"{url}?{user_input}")

            # Temporary failure (4x status codes)
            elif 40 <= response.status < 50:
                print(f"Temporary error: {response.meta}")
                return None

            # Permanent failure (5x status codes)
            elif 50 <= response.status < 60:
                print(f"Permanent error: {response.meta}")
                return None

            # Certificate required (6x status codes)
            elif 60 <= response.status < 70:
                print(f"Client certificate required: {response.meta}")
                return None

    except CertificateChangedError as e:
        print(f"Certificate changed for {e.hostname}:{e.port}")
        print(f"Old: {e.old_fingerprint}")
        print(f"New: {e.new_fingerprint}")
        return None
    except TimeoutError:
        print(f"Request timed out")
        return None
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        return None

# Use the function
asyncio.run(fetch_with_error_handling("gemini://geminiprotocol.net/"))
```

**Next Steps:**

- Read the [API Reference](reference/api/index.md)
- See [Server Configuration](reference/configuration.md) for advanced options
- Learn about [Rate Limiting](how-to/rate-limiting.md) and [Access Control](how-to/access-control.md)
- Explore [Client Certificate Authentication](how-to/client-certificates.md)

---

## Common Next Steps

Now that you've tried the basics, here are suggested learning paths:

### For Server Operators

1. **[Generate Production Certificates](how-to/manage-certificates.md)** - Create proper TLS certificates
2. **[Configure Your Server](reference/configuration.md)** - Set up TOML configuration
3. **[Enable Security Features](tutorials/securing-your-server.md)** - Rate limiting, access control
4. **[Server Configuration](how-to/configure-server.md)** - Production server setup

### For Client Users

1. **[Understand TOFU](explanation/security-model.md)** - Learn the trust model
2. **[Explore Geminispace](https://geminiprotocol.net/community/)** - Find interesting capsules
3. **[Use Client Certificates](how-to/client-certificates.md)** - Authenticate to servers
4. **[Build Your Own Client](tutorials/building-a-client.md)** - Custom Gemini browsers

### For Developers

1. **[API Reference](reference/api/index.md)** - Complete API documentation
2. **[Protocol Details](explanation/gemini-protocol.md)** - Understand the Gemini protocol
3. **[Rate Limiting Guide](how-to/rate-limiting.md)** - Configure rate limiting
4. **[Contributing Guide](https://github.com/alanbato/nauyaca/blob/main/CONTRIBUTING.md)** - Join the project

---

## Getting Help

- **Documentation**: Browse this site for detailed guides and references
- **Examples**: Check the [examples/](https://github.com/alanbato/nauyaca/tree/main/examples) directory
- **Issues**: Report bugs at [GitHub Issues](https://github.com/alanbato/nauyaca/issues)
- **Discussions**: Ask questions at [GitHub Discussions](https://github.com/alanbato/nauyaca/discussions)

## What's Next?

You've successfully:

- Served your first Gemini capsule
- Browsed Gemini content with TOFU validation
- Used Nauyaca as a Python library

Ready to dive deeper? Check out the [Tutorials](tutorials/index.md) section for comprehensive guides, or jump to the [How-To Guides](how-to/index.md) for specific tasks.

Happy exploring Geminispace!
