# Building a Gemini Client

This tutorial will guide you through building a Python application that fetches and interacts with Gemini resources using nauyaca as a library.

## What We'll Build

By the end of this tutorial, you'll have created a simple but functional Gemini browser that can:

- Fetch resources from Gemini servers
- Handle all response types (success, redirects, input, errors)
- Parse Gemtext content and extract links
- Follow links interactively
- Manage certificate trust using TOFU

## Prerequisites

- Python 3.10 or higher
- Basic understanding of async/await in Python
- nauyaca installed (`uv add nauyaca` or `pip install nauyaca`)

## Step 1: Your First Gemini Request

Let's start with the simplest possible Gemini client - fetching a single URL and displaying its content.

Create a new file called `gemini_fetch.py`:

```python
import asyncio
from nauyaca.client import GeminiClient


async def main():
    """Fetch and display a Gemini resource."""
    # Create a client using async context manager
    async with GeminiClient() as client:
        # Fetch a resource
        response = await client.get("gemini://geminiprotocol.net/")

        # Display the response
        if response.is_success():
            print(f"Content-Type: {response.meta}")
            print(response.body)
        else:
            print(f"Error: {response.status} - {response.meta}")


if __name__ == "__main__":
    asyncio.run(main())
```

Run this script:

```bash
python gemini_fetch.py
```

**What's happening here:**

- `GeminiClient()` creates a client with TOFU certificate validation enabled by default
- The async context manager (`async with`) ensures proper cleanup
- `client.get()` fetches the URL and automatically follows redirects
- `response.is_success()` checks if we got a success response (status 2x)
- For success responses, `response.meta` contains the MIME type and `response.body` contains the content

## Step 2: Handling All Response Types

Gemini has several response types. Let's handle them all properly:

```python
import asyncio
from nauyaca.client import GeminiClient


async def fetch_and_display(url: str):
    """Fetch a URL and display the appropriate information."""
    async with GeminiClient() as client:
        response = await client.get(url)

        # Success (2x) - show content
        if response.is_success():
            print(f"✓ Success ({response.status})")
            print(f"Content-Type: {response.meta}")
            print("\n" + "=" * 70)
            print(response.body)
            print("=" * 70)

        # Redirect (3x) - show where it's redirecting
        elif response.is_redirect():
            print(f"↻ Redirect ({response.status})")
            print(f"Location: {response.redirect_url}")
            # Note: client.get() automatically follows redirects by default
            # This code path only executes if you use follow_redirects=False

        # Input required (1x) - show prompt
        elif 10 <= response.status < 20:
            print(f"? Input Required ({response.status})")
            print(f"Prompt: {response.meta}")
            if response.status == 11:
                print("(This is sensitive input - like a password)")

        # Temporary failure (4x) - can retry later
        elif 40 <= response.status < 50:
            print(f"⚠ Temporary Failure ({response.status})")
            print(f"Message: {response.meta}")
            if response.status == 44:
                print("Rate limited - try again later")

        # Permanent failure (5x) - don't retry
        elif 50 <= response.status < 60:
            print(f"✗ Permanent Failure ({response.status})")
            print(f"Message: {response.meta}")

        # Client certificate required (6x) - needs authentication
        elif 60 <= response.status < 70:
            print(f"🔒 Certificate Required ({response.status})")
            print(f"Message: {response.meta}")
            print("You need a client certificate to access this resource")


async def main():
    """Test different URLs to see different response types."""
    urls = [
        "gemini://geminiprotocol.net/",  # Success
        "gemini://geminiprotocol.net/docs/",  # Another success
    ]

    for url in urls:
        print(f"\n{'='*70}")
        print(f"Fetching: {url}")
        print('='*70)
        await fetch_and_display(url)


if __name__ == "__main__":
    asyncio.run(main())
```

**Why this matters:**

- **Success (2x)**: Normal content delivery - display it
- **Redirect (3x)**: Resource moved - follow it (or inform the user)
- **Input (1x)**: Server needs more information - prompt the user
- **Temporary failures (4x)**: Transient errors - retry might work
- **Permanent failures (5x)**: Don't retry - resource doesn't exist
- **Certificate required (6x)**: Needs client authentication - special handling needed

## Step 3: Parsing Gemtext Content

Gemtext is Gemini's native markup format. It's line-oriented, making it easy to parse. Let's extract links from Gemtext content:

```python
import asyncio
import re
from nauyaca.client import GeminiClient


def parse_gemtext_links(body: str) -> list[tuple[str, str]]:
    """Parse links from Gemtext content.

    Returns:
        List of (url, description) tuples.
    """
    links = []

    for line in body.split('\n'):
        # Link lines start with "=>" followed by whitespace, URL, and optional description
        if line.startswith('=>'):
            # Remove the "=>" prefix and strip whitespace
            link_content = line[2:].strip()

            # Split on whitespace to separate URL from description
            parts = link_content.split(None, 1)  # Split on first whitespace

            if parts:
                url = parts[0]
                description = parts[1] if len(parts) > 1 else url
                links.append((url, description))

    return links


async def fetch_with_links(url: str):
    """Fetch a URL and display its content with extracted links."""
    async with GeminiClient() as client:
        response = await client.get(url)

        if response.is_success():
            print(f"Content from: {url}")
            print("=" * 70)

            # Display the content
            print(response.body)

            # Extract and display links
            links = parse_gemtext_links(response.body)

            if links:
                print("\n" + "=" * 70)
                print(f"Found {len(links)} links:")
                print("=" * 70)

                for i, (link_url, description) in enumerate(links, 1):
                    print(f"{i}. {description}")
                    print(f"   → {link_url}")

            return links
        else:
            print(f"Error {response.status}: {response.meta}")
            return []


async def main():
    """Fetch a page and display its links."""
    url = "gemini://geminiprotocol.net/"
    await fetch_with_links(url)


if __name__ == "__main__":
    asyncio.run(main())
```

**Understanding Gemtext links:**

- Links start with `=>` at the beginning of a line
- Format: `=> URL [optional description]`
- Examples:
  - `=> gemini://example.com/` (URL only, use URL as description)
  - `=> /about About this capsule` (relative URL with description)
  - `=> https://example.com External link` (can link to other protocols)

## Step 4: Building an Interactive Browser

Now let's combine everything into an interactive browser that lets you navigate between pages:

```python
import asyncio
from urllib.parse import urljoin
from nauyaca.client import GeminiClient


def parse_gemtext_links(body: str) -> list[tuple[str, str]]:
    """Parse links from Gemtext content."""
    links = []
    for line in body.split('\n'):
        if line.startswith('=>'):
            link_content = line[2:].strip()
            parts = link_content.split(None, 1)
            if parts:
                url = parts[0]
                description = parts[1] if len(parts) > 1 else url
                links.append((url, description))
    return links


async def browse_interactive():
    """Interactive Gemini browser."""
    # Start with a default URL
    current_url = "gemini://geminiprotocol.net/"

    async with GeminiClient() as client:
        while True:
            print("\n" + "=" * 70)
            print(f"Fetching: {current_url}")
            print("=" * 70 + "\n")

            try:
                response = await client.get(current_url)

                if response.is_success():
                    # Display content
                    print(response.body)
                    print("\n" + "-" * 70)

                    # Extract links
                    links = parse_gemtext_links(response.body)

                    if links:
                        print(f"\nFound {len(links)} links:")
                        for i, (url, description) in enumerate(links, 1):
                            print(f"{i}. {description}")

                        # Prompt user to select a link
                        print("\nCommands:")
                        print("  [number] - Follow that link")
                        print("  b - Go back")
                        print("  u [url] - Visit a URL")
                        print("  q - Quit")

                        choice = input("\n> ").strip().lower()

                        if choice == 'q':
                            print("Goodbye!")
                            break
                        elif choice == 'b':
                            print("(Back navigation not implemented in this example)")
                            continue
                        elif choice.startswith('u '):
                            # Visit custom URL
                            current_url = choice[2:].strip()
                        elif choice.isdigit():
                            link_num = int(choice)
                            if 1 <= link_num <= len(links):
                                new_url = links[link_num - 1][0]
                                # Handle relative URLs
                                current_url = urljoin(current_url, new_url)
                            else:
                                print(f"Invalid link number: {link_num}")
                                input("Press Enter to continue...")
                        else:
                            print(f"Unknown command: {choice}")
                            input("Press Enter to continue...")
                    else:
                        print("\nNo links found on this page.")
                        input("Press Enter to continue...")

                elif response.is_redirect():
                    # This shouldn't happen with default settings (auto-follow enabled)
                    print(f"Redirected to: {response.redirect_url}")
                    current_url = response.redirect_url

                elif 10 <= response.status < 20:
                    # Input required
                    user_input = input(f"{response.meta}: ")
                    # In a real implementation, you'd need to handle query strings
                    # For now, just notify the user
                    print("Input handling not fully implemented in this example")
                    input("Press Enter to continue...")

                else:
                    # Error
                    print(f"Error {response.status}: {response.meta}")
                    input("Press Enter to continue...")

            except TimeoutError:
                print("Request timed out")
                input("Press Enter to continue...")
            except ConnectionError as e:
                print(f"Connection failed: {e}")
                input("Press Enter to continue...")
            except Exception as e:
                print(f"Unexpected error: {e}")
                input("Press Enter to continue...")


async def main():
    """Run the interactive browser."""
    print("Welcome to the Gemini Browser!")
    print("=" * 70)
    await browse_interactive()


if __name__ == "__main__":
    asyncio.run(main())
```

**Try it out:**

1. Run the script
2. Read the content
3. Enter a link number to follow it
4. Use `u gemini://example.com/` to visit a specific URL
5. Enter `q` to quit

## Step 5: Configuring Client Options

The `GeminiClient` accepts several configuration options:

```python
import asyncio
from pathlib import Path
from nauyaca.client import GeminiClient


async def main():
    """Demonstrate various client configuration options."""

    # Example 1: Custom timeout
    async with GeminiClient(timeout=60.0) as client:
        response = await client.get("gemini://slow-server.example/")

    # Example 2: Limit redirects
    async with GeminiClient(max_redirects=3) as client:
        response = await client.get("gemini://example.com/")

    # Example 3: Disable redirect following
    async with GeminiClient() as client:
        response = await client.get(
            "gemini://example.com/",
            follow_redirects=False
        )
        if response.is_redirect():
            print(f"Got redirect to: {response.redirect_url}")

    # Example 4: Use client certificate for authentication
    async with GeminiClient(
        client_cert=Path("./client_cert.pem"),
        client_key=Path("./client_key.pem")
    ) as client:
        response = await client.get("gemini://auth-required.example/")

    # Example 5: Custom TOFU database location
    async with GeminiClient(
        tofu_db_path=Path("./my_tofu.db")
    ) as client:
        response = await client.get("gemini://example.com/")

    # Example 6: Disable TOFU (not recommended for production!)
    async with GeminiClient(trust_on_first_use=False) as client:
        # This accepts any certificate without validation
        response = await client.get("gemini://example.com/")


if __name__ == "__main__":
    asyncio.run(main())
```

**Configuration options:**

- `timeout`: Request timeout in seconds (default: 30.0)
- `max_redirects`: Maximum redirects to follow (default: 5)
- `trust_on_first_use`: Enable TOFU validation (default: True, recommended)
- `tofu_db_path`: Path to TOFU database (default: `~/.nauyaca/tofu.db`)
- `client_cert` / `client_key`: Client certificate for authentication
- `verify_ssl`: Use CA validation instead of TOFU (default: False, not recommended for Gemini)

## Step 6: Handling TOFU Programmatically

The client automatically handles TOFU validation, but you may want to handle certificate changes yourself:

```python
import asyncio
from nauyaca.client import GeminiClient
from nauyaca.security.tofu import CertificateChangedError


async def fetch_with_tofu_handling(url: str):
    """Fetch a URL with manual TOFU certificate handling."""
    async with GeminiClient() as client:
        try:
            response = await client.get(url)
            print(f"Success: {response.status}")

        except CertificateChangedError as e:
            # Certificate changed - this could be legitimate or an attack
            print(f"⚠ Certificate changed for {e.hostname}:{e.port}")
            print(f"Old fingerprint: {e.old_fingerprint}")
            print(f"New fingerprint: {e.new_fingerprint}")

            # Ask user what to do
            print("\nThis could mean:")
            print("  1. The server renewed their certificate (legitimate)")
            print("  2. Man-in-the-middle attack (security threat)")

            choice = input("\nTrust new certificate? [y/N]: ").strip().lower()

            if choice == 'y':
                # Access the TOFU database and update trust
                from nauyaca.security.tofu import TOFUDatabase
                from nauyaca.security.certificates import load_certificate

                # In a real implementation, you'd need to get the new certificate
                # from the failed connection. For this example, we'll re-connect
                # with TOFU disabled to get it.

                # Create a new client with TOFU disabled
                async with GeminiClient(trust_on_first_use=False) as temp_client:
                    response = await temp_client.get(url)

                print("Certificate trusted for future connections")
            else:
                print("Certificate not trusted - connection aborted")


async def main():
    """Test TOFU handling."""
    # This example won't actually trigger CertificateChangedError unless
    # you've previously connected to a host that has changed certificates
    await fetch_with_tofu_handling("gemini://geminiprotocol.net/")


if __name__ == "__main__":
    asyncio.run(main())
```

**Understanding TOFU:**

- **First connection**: Certificate is automatically trusted and stored
- **Subsequent connections**: Certificate must match the stored fingerprint
- **Certificate change**: Raises `CertificateChangedError` - you decide whether to trust it

**Managing the TOFU database:**

```python
from pathlib import Path
from nauyaca.security.tofu import TOFUDatabase

# Open the database
tofu = TOFUDatabase()  # Uses default path ~/.nauyaca/tofu.db

# List all known hosts
hosts = tofu.list_hosts()
for host in hosts:
    print(f"{host['hostname']}:{host['port']} - {host['fingerprint']}")

# Revoke trust for a host
tofu.revoke("suspicious.example", 1965)

# Export to TOML for backup
export_data = tofu.export_to_toml()
Path("backup.toml").write_text(export_data)

# Import from TOML
toml_data = Path("backup.toml").read_text()
tofu.import_from_toml(toml_data)
```

## Step 7: Complete Example - Gemini Fetch Tool

Here's a complete, production-ready script that combines everything we've learned:

```python
#!/usr/bin/env python3
"""
gemfetch - A simple Gemini protocol fetcher

Usage:
    python gemfetch.py <url>
    python gemfetch.py --verbose <url>
    python gemfetch.py --timeout 60 <url>
"""

import argparse
import asyncio
import sys
from nauyaca.client import GeminiClient
from nauyaca.security.tofu import CertificateChangedError


def parse_gemtext_links(body: str) -> list[tuple[str, str]]:
    """Parse links from Gemtext content."""
    links = []
    for line in body.split('\n'):
        if line.startswith('=>'):
            link_content = line[2:].strip()
            parts = link_content.split(None, 1)
            if parts:
                url = parts[0]
                description = parts[1] if len(parts) > 1 else url
                links.append((url, description))
    return links


async def fetch(url: str, verbose: bool = False, timeout: float = 30.0):
    """Fetch a Gemini URL and display results."""
    async with GeminiClient(timeout=timeout) as client:
        if verbose:
            print(f"Connecting to: {url}", file=sys.stderr)

        try:
            response = await client.get(url)

            # Show headers in verbose mode
            if verbose:
                print(f"\nStatus: {response.status}", file=sys.stderr)
                print(f"Meta: {response.meta}", file=sys.stderr)
                print(f"Type: {response.mime_type}\n", file=sys.stderr)

            # Handle different response types
            if response.is_success():
                # Success - display body
                print(response.body)

                # Show links in verbose mode
                if verbose:
                    links = parse_gemtext_links(response.body)
                    if links:
                        print(f"\n--- Found {len(links)} links ---", file=sys.stderr)
                        for i, (link_url, desc) in enumerate(links, 1):
                            print(f"{i}. {desc} -> {link_url}", file=sys.stderr)

                return 0  # Success exit code

            elif response.is_redirect():
                print(f"Redirected to: {response.redirect_url}", file=sys.stderr)
                return 0

            elif 10 <= response.status < 20:
                # Input required
                print(f"Input required: {response.meta}", file=sys.stderr)
                sensitive = " (sensitive)" if response.status == 11 else ""
                print(f"The server is asking for input{sensitive}", file=sys.stderr)
                return 1

            elif 40 <= response.status < 50:
                # Temporary failure
                print(f"Temporary failure ({response.status}): {response.meta}",
                      file=sys.stderr)
                if response.status == 44:
                    print("Rate limited - try again later", file=sys.stderr)
                return 2

            elif 50 <= response.status < 60:
                # Permanent failure
                print(f"Permanent failure ({response.status}): {response.meta}",
                      file=sys.stderr)
                return 3

            elif 60 <= response.status < 70:
                # Certificate required
                print(f"Client certificate required ({response.status}): {response.meta}",
                      file=sys.stderr)
                print("Use --cert and --key options to provide a client certificate",
                      file=sys.stderr)
                return 4

        except CertificateChangedError as e:
            print(f"Certificate changed for {e.hostname}:{e.port}", file=sys.stderr)
            print(f"Old: {e.old_fingerprint}", file=sys.stderr)
            print(f"New: {e.new_fingerprint}", file=sys.stderr)
            print("\nThis could be a security threat!", file=sys.stderr)
            print("Use 'nauyaca tofu revoke' then 'nauyaca tofu trust' if you trust the new certificate",
                  file=sys.stderr)
            return 5

        except TimeoutError:
            print(f"Connection timed out after {timeout} seconds", file=sys.stderr)
            return 6

        except ConnectionError as e:
            print(f"Connection failed: {e}", file=sys.stderr)
            return 7

        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            if verbose:
                import traceback
                traceback.print_exc()
            return 8


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch and display Gemini protocol resources"
    )
    parser.add_argument("url", help="Gemini URL to fetch")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including headers and links"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith("gemini://"):
        print("Error: URL must start with gemini://", file=sys.stderr)
        sys.exit(1)

    # Run the async fetch
    exit_code = asyncio.run(fetch(args.url, args.verbose, args.timeout))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

**Using the complete example:**

```bash
# Basic usage
python gemfetch.py gemini://geminiprotocol.net/

# Verbose output
python gemfetch.py --verbose gemini://geminiprotocol.net/

# Custom timeout
python gemfetch.py --timeout 60 gemini://slow-server.example/
```

## Next Steps

Congratulations! You've built a functional Gemini client. Here are some ways to extend it:

**Additional features to explore:**

1. **History and bookmarks** - Save visited URLs and favorites
2. **Link following with history** - Implement back/forward navigation
3. **Download non-text content** - Handle images, audio, etc.
4. **Search integration** - Add support for input queries (status 1x)
5. **Client certificates** - Generate and use client certs for authentication
6. **Caching** - Store responses to reduce redundant requests
7. **Multiple protocols** - Handle http/https links found in gemtext

**Further reading:**

- [Client API Reference](../reference/api/client.md) - Complete API documentation
- [TOFU How-To Guide](../how-to/setup-tofu.md) - Advanced TOFU management
- [Security API Reference](../reference/api/security.md) - Security considerations
- [Gemini Protocol Specification](https://geminiprotocol.net/docs/specification.gmi) - Official spec

## Common Issues and Solutions

### Certificate Validation Errors

**Problem**: `CertificateChangedError` on every connection

**Solution**: The TOFU database might be corrupted. Clear it and start fresh:

```bash
rm ~/.nauyaca/tofu.db
```

### Timeout Errors

**Problem**: Frequent timeout errors

**Solution**: Increase the timeout or check your network connection:

```python
async with GeminiClient(timeout=60.0) as client:
    response = await client.get(url)
```

### Relative URL Handling

**Problem**: Relative links don't work

**Solution**: Use `urllib.parse.urljoin()` to resolve relative URLs:

```python
from urllib.parse import urljoin

base_url = "gemini://example.com/page"
relative_url = "/other"
absolute_url = urljoin(base_url, relative_url)
# Result: "gemini://example.com/other"
```

### Unicode Content Issues

**Problem**: Garbled text or encoding errors

**Solution**: The client automatically uses UTF-8 (Gemini's default). If you encounter issues, check the `charset` parameter in the response:

```python
if response.is_success():
    charset = response.charset  # Default: utf-8
    print(f"Using charset: {charset}")
```

## Summary

In this tutorial, you learned how to:

- ✅ Create a `GeminiClient` and fetch resources
- ✅ Handle all Gemini response types (success, redirect, input, errors)
- ✅ Parse Gemtext content and extract links
- ✅ Build an interactive browser with link following
- ✅ Configure client options (timeouts, redirects, certificates)
- ✅ Handle TOFU certificate validation programmatically
- ✅ Build a complete command-line fetch tool

You now have the foundation to build more sophisticated Gemini applications using nauyaca!
