# Client API Reference

The client module provides a high-level API for fetching Gemini resources with support for TOFU certificate validation, redirects, and timeouts.

## Overview

The Nauyaca client is built on Python's `asyncio.Protocol` and `asyncio.Transport` pattern for efficient, non-blocking I/O. It provides:

- **High-level async/await interface** via `GeminiClient`
- **TOFU (Trust On First Use) validation** for secure connections without CA infrastructure
- **Automatic redirect following** with loop detection
- **Client certificate authentication** for restricted resources
- **Configurable timeouts** and connection settings

## GeminiClient

::: nauyaca.client.session.GeminiClient

### Basic Usage

The simplest way to fetch a Gemini resource:

```python
import asyncio
from nauyaca.client.session import GeminiClient

async def main():
    async with GeminiClient() as client:
        response = await client.get('gemini://geminiprotocol.net/')

        if response.is_success():
            print(response.body)
        else:
            print(f"Error {response.status}: {response.meta}")

asyncio.run(main())
```

### Configuration Options

Create a client with custom settings:

```python
from pathlib import Path
from nauyaca.client.session import GeminiClient

async def main():
    # Client with custom timeout and redirect settings
    client = GeminiClient(
        timeout=60.0,              # 60 second timeout
        max_redirects=3,            # Follow up to 3 redirects
        trust_on_first_use=True,    # Enable TOFU (recommended)
        tofu_db_path=Path("~/.config/nauyaca/tofu.db").expanduser()
    )

    response = await client.get('gemini://example.com/path')
```

### Client Certificate Authentication

For servers that require client certificates (status 6x):

```python
from pathlib import Path
from nauyaca.client.session import GeminiClient

async def main():
    client = GeminiClient(
        client_cert=Path("/path/to/client-cert.pem"),
        client_key=Path("/path/to/client-key.pem")
    )

    # Now requests will include your client certificate
    response = await client.get('gemini://restricted.example.com/')
```

### Error Handling

Handle common error conditions:

```python
import asyncio
from nauyaca.client.session import GeminiClient
from nauyaca.security.tofu import CertificateChangedError

async def main():
    async with GeminiClient() as client:
        try:
            response = await client.get('gemini://example.com/')

            if response.is_success():
                print(f"Content-Type: {response.mime_type}")
                print(response.body)
            elif response.is_redirect():
                print(f"Redirects to: {response.redirect_url}")
            else:
                print(f"Error {response.status}: {response.meta}")

        except CertificateChangedError as e:
            # Certificate changed - potential security issue
            print(f"WARNING: Certificate changed for {e.hostname}:{e.port}")
            print(f"Old fingerprint: {e.old_fingerprint}")
            print(f"New fingerprint: {e.new_fingerprint}")
            # User should verify this is legitimate before trusting

        except asyncio.TimeoutError:
            print("Request timed out")

        except ConnectionError as e:
            print(f"Connection failed: {e}")

        except ValueError as e:
            print(f"Invalid URL or redirect: {e}")
```

### Uploading Content (Titan)

Upload content to a Gemini server using the Titan protocol:

```python
async def main():
    async with GeminiClient() as client:
        # Upload text content
        response = await client.upload(
            'gemini://example.com/wiki/page.gmi',
            '# My Page\n\nContent here...',
            mime_type='text/gemini',
            token='auth-token',
        )

        if response.is_success():
            print("Upload successful!")

        # Upload binary content
        with open('image.png', 'rb') as f:
            response = await client.upload(
                'gemini://example.com/images/photo.png',
                f.read(),
                mime_type='image/png',
                token='auth-token',
            )
```

### Deleting Content (Titan)

Delete a resource using a zero-byte Titan upload:

```python
async def main():
    async with GeminiClient() as client:
        response = await client.delete(
            'gemini://example.com/wiki/old-page.gmi',
            token='auth-token',
        )

        if response.is_success():
            print("Deleted!")
```

!!! note "Server Support Required"
    The server must have Titan enabled with `enable_delete = true` for delete operations to succeed.

### Disabling Redirects

Sometimes you want to handle redirects manually:

```python
async def main():
    async with GeminiClient() as client:
        # Don't follow redirects automatically
        response = await client.get(
            'gemini://example.com/',
            follow_redirects=False
        )

        if response.is_redirect():
            print(f"Got redirect to: {response.redirect_url}")
            # Decide whether to follow it yourself
```

## GeminiResponse

::: nauyaca.protocol.response.GeminiResponse

### Checking Response Types

The `GeminiResponse` class provides convenient methods for checking response status:

```python
response = await client.get('gemini://example.com/')

# Check if request succeeded
if response.is_success():
    # Status 20-29: response has body content
    print(f"MIME type: {response.mime_type}")
    print(f"Body: {response.body}")

# Check if it's a redirect
elif response.is_redirect():
    # Status 30-39: meta contains redirect URL
    print(f"Redirect to: {response.redirect_url}")

# Otherwise it's an error or input request
else:
    status_category = interpret_status(response.status)
    print(f"{status_category}: {response.meta}")
```

### Accessing Response Attributes

All response data is available as attributes:

```python
response = await client.get('gemini://example.com/')

# Core attributes
print(f"Status: {response.status}")       # e.g., 20
print(f"Meta: {response.meta}")           # e.g., "text/gemini"
print(f"Body: {response.body}")           # Only present for 2x status
print(f"URL: {response.url}")             # The URL that was requested

# Convenience properties
print(f"MIME type: {response.mime_type}") # Extracted from meta (success only)
print(f"Charset: {response.charset}")     # Defaults to utf-8
print(f"Redirect: {response.redirect_url}") # Extracted from meta (redirect only)
```

## Status Code Utilities

Utility functions for interpreting status codes:

::: nauyaca.protocol.status.interpret_status

::: nauyaca.protocol.status.is_success

::: nauyaca.protocol.status.is_redirect

::: nauyaca.protocol.status.is_input_required

::: nauyaca.protocol.status.is_error

### Status Code Examples

```python
from nauyaca.protocol.status import (
    interpret_status,
    is_success,
    is_redirect,
    is_input_required,
    is_error
)

response = await client.get('gemini://example.com/')

# Get category name
category = interpret_status(response.status)  # "SUCCESS", "REDIRECT", etc.

# Check specific categories
if is_success(response.status):
    print("Success!")
elif is_redirect(response.status):
    print(f"Redirect to: {response.redirect_url}")
elif is_input_required(response.status):
    print(f"Server needs input: {response.meta}")
elif is_error(response.status):
    print(f"Error: {response.meta}")
```

## Common Patterns

### Following Redirects Manually

```python
async def fetch_with_manual_redirects(client, url, max_redirects=5):
    """Fetch a URL and manually handle redirects."""
    redirects_followed = 0
    current_url = url

    while redirects_followed < max_redirects:
        response = await client.get(current_url, follow_redirects=False)

        if not response.is_redirect():
            return response

        # Check if it's a gemini:// redirect
        redirect_url = response.redirect_url
        if not redirect_url.startswith('gemini://'):
            print(f"Warning: non-Gemini redirect to {redirect_url}")
            return response

        print(f"Following redirect to: {redirect_url}")
        current_url = redirect_url
        redirects_followed += 1

    raise ValueError(f"Too many redirects (>{max_redirects})")
```

### Handling Input Prompts

```python
from nauyaca.protocol.status import is_input_required, StatusCode

async def interactive_fetch(client, url):
    """Fetch a URL and handle input prompts interactively."""
    response = await client.get(url)

    # Check if server is requesting input
    if is_input_required(response.status):
        # Display the prompt to the user
        print(f"Server prompt: {response.meta}")

        # Get user input
        if response.status == StatusCode.SENSITIVE_INPUT:
            # Don't echo for sensitive input (like passwords)
            import getpass
            user_input = getpass.getpass("Input (hidden): ")
        else:
            user_input = input("Input: ")

        # Build URL with query string
        # Gemini uses '?' to separate path from query
        query_url = f"{url}?{user_input}"

        # Make request with user's input
        response = await client.get(query_url)

    return response
```

### Client Certificate Authentication

```python
async def fetch_with_cert(url, cert_path, key_path):
    """Fetch a resource using client certificate authentication."""
    from pathlib import Path

    client = GeminiClient(
        client_cert=Path(cert_path),
        client_key=Path(key_path)
    )

    try:
        response = await client.get(url)

        # Check for certificate-related errors
        if response.status == 60:
            print("Server requires a client certificate")
        elif response.status == 61:
            print("Certificate not authorized for this resource")
        elif response.status == 62:
            print("Certificate not valid")
        else:
            return response

    finally:
        # Client will be cleaned up automatically
        pass
```

### TOFU Certificate Management

```python
from nauyaca.security.tofu import TOFUDatabase, CertificateChangedError
from pathlib import Path

async def safe_fetch_with_tofu(url):
    """Fetch with TOFU validation and user confirmation on changes."""
    client = GeminiClient(trust_on_first_use=True)

    try:
        response = await client.get(url)
        return response

    except CertificateChangedError as e:
        # Certificate changed - ask user to verify
        print(f"\nWARNING: Certificate changed for {e.hostname}:{e.port}")
        print(f"Old fingerprint: {e.old_fingerprint}")
        print(f"New fingerprint: {e.new_fingerprint}")
        print("\nThis could be a legitimate certificate renewal,")
        print("or it could indicate a man-in-the-middle attack.")

        answer = input("\nDo you want to trust the new certificate? (yes/no): ")

        if answer.lower() == 'yes':
            # Trust the new certificate
            tofu_db = TOFUDatabase()
            # Need to fetch again to get the certificate
            # This time we'll trust it
            # (In practice, you'd want to extract and trust the cert directly)
            print("Please verify the fingerprint through a separate channel!")
        else:
            print("Certificate not trusted. Aborting.")
            raise
```

### Batch Requests

```python
async def fetch_multiple(urls):
    """Fetch multiple URLs concurrently."""
    async with GeminiClient() as client:
        # Create tasks for all URLs
        tasks = [client.get(url) for url in urls]

        # Run them concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for url, response in zip(urls, responses):
            if isinstance(response, Exception):
                print(f"{url}: Error - {response}")
            elif response.is_success():
                print(f"{url}: Success - {len(response.body)} bytes")
            else:
                print(f"{url}: Status {response.status}")
```

## See Also

- [Protocol Reference](../../explanation/gemini-protocol.md) - Low-level protocol details
- [Security Guide](../../explanation/security-model.md) - TOFU and certificate management
- [How-to: Client Usage](../../how-to/setup-tofu.md) - Practical client recipes
