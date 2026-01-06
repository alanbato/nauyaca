# Titan Uploads

This guide covers how to configure and use Titan, Gemini's companion protocol for uploading content to servers.

## What is Titan?

Titan is an upload protocol designed specifically for Gemini. While Gemini only supports fetching content, Titan enables clients to send content to servers. Key characteristics:

- Uses the `titan://` URL scheme
- Shares port 1965 with Gemini
- Requires TLS (same security model as Gemini)
- Supports authentication via tokens
- Zero-byte uploads indicate deletion

## Server Configuration

### Enabling Titan Support

Add a `[titan]` section to your configuration file:

```toml
[titan]
enabled = true
upload_dir = "./uploads"
```

!!! warning "Security First"
    Titan is disabled by default for security. Only enable it if you need upload functionality.

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable Titan upload support |
| `upload_dir` | string | (required) | Directory for storing uploads |
| `max_upload_size` | integer | `10485760` | Maximum upload size in bytes (10 MiB) |
| `allowed_mime_types` | array | `null` | Allowed MIME types (`null` = all allowed) |
| `auth_tokens` | array | `null` | Authentication tokens (`null` = no auth required) |
| `enable_delete` | boolean | `false` | Allow delete operations via zero-byte uploads |

### Example Configurations

**Basic Wiki Setup**:
```toml
[titan]
enabled = true
upload_dir = "./wiki-content"
max_upload_size = 1048576  # 1 MiB for text content
allowed_mime_types = ["text/gemini", "text/plain"]
auth_tokens = ["wiki-editor-token"]
enable_delete = true
```

**Image Upload Server**:
```toml
[titan]
enabled = true
upload_dir = "./images"
max_upload_size = 5242880  # 5 MiB for images
allowed_mime_types = ["image/png", "image/jpeg", "image/gif"]
auth_tokens = ["image-upload-token"]
enable_delete = false
```

**Public Upload (Not Recommended)**:
```toml
[titan]
enabled = true
upload_dir = "./public-uploads"
max_upload_size = 102400  # 100 KB limit
# No auth_tokens = anyone can upload
# No allowed_mime_types = any type accepted
```

!!! danger "Public Uploads"
    Allowing unauthenticated uploads is risky. Always use authentication tokens on public servers.

## Client Usage

### Uploading Content

Use the `GeminiClient.upload()` method to upload content:

```python
import asyncio
from nauyaca.client.session import GeminiClient

async def main():
    async with GeminiClient() as client:
        # Upload text content
        response = await client.upload(
            'gemini://example.com/wiki/my-page.gmi',
            '# My Page\n\nHello, Geminispace!',
            mime_type='text/gemini',
            token='wiki-editor-token',
        )

        if response.is_success():
            print("Upload successful!")
        else:
            print(f"Upload failed: {response.status} {response.meta}")

asyncio.run(main())
```

### Uploading Binary Content

```python
async def upload_image():
    async with GeminiClient() as client:
        with open('photo.png', 'rb') as f:
            image_data = f.read()

        response = await client.upload(
            'gemini://example.com/images/photo.png',
            image_data,
            mime_type='image/png',
            token='image-upload-token',
        )

        return response
```

### URL Scheme Handling

The `upload()` method accepts both `gemini://` and `titan://` URLs:

```python
# Both work identically:
await client.upload('gemini://example.com/file.gmi', content)
await client.upload('titan://example.com/file.gmi', content)
```

The client automatically converts `gemini://` to `titan://` and adds the required parameters.

### Deleting Content

Delete resources using zero-byte uploads with the `delete()` method:

```python
async def delete_page():
    async with GeminiClient() as client:
        response = await client.delete(
            'gemini://example.com/wiki/old-page.gmi',
            token='wiki-editor-token',
        )

        if response.is_success():
            print("Deleted successfully!")
        else:
            print(f"Delete failed: {response.status} {response.meta}")
```

!!! note "Server Support Required"
    Delete operations require `enable_delete = true` on the server. If disabled, the server returns status 50 (PERMANENT FAILURE).

## Security Considerations

### Authentication Tokens

Always use authentication tokens for upload endpoints:

```toml
[titan]
auth_tokens = ["token1", "token2", "token3"]
```

- Tokens are passed in the URL parameters: `titan://host/path;size=N;token=TOKEN`
- Without valid tokens, uploads are rejected with status 60 (CLIENT CERTIFICATE REQUIRED)
- Use long, random tokens (e.g., generated with `openssl rand -hex 32`)

### Path Traversal Protection

Nauyaca protects against path traversal attacks:

- Paths like `../secret.txt` are rejected
- All uploads are confined to the `upload_dir`
- Symlinks are not followed outside the upload directory

### Size Limits

Configure appropriate size limits to prevent abuse:

```toml
[titan]
max_upload_size = 1048576  # 1 MiB
```

Uploads exceeding this limit are rejected with status 50 (PERMANENT FAILURE).

### MIME Type Filtering

Restrict allowed file types:

```toml
[titan]
allowed_mime_types = ["text/gemini", "text/plain", "text/markdown"]
```

Uploads with disallowed MIME types are rejected with status 59 (BAD REQUEST).

## Error Handling

Common error responses when uploading:

| Status | Meaning | Cause |
|--------|---------|-------|
| 20 | Success | Upload completed |
| 50 | Permanent Failure | Size exceeded, delete disabled |
| 59 | Bad Request | Invalid path, disallowed MIME type |
| 60 | Client Cert Required | Missing or invalid auth token |

Handle these in your client code:

```python
async def safe_upload(client, url, content, token):
    try:
        response = await client.upload(url, content, token=token)

        if response.status == 20:
            return True, "Upload successful"
        elif response.status == 50:
            return False, f"Server rejected: {response.meta}"
        elif response.status == 59:
            return False, f"Bad request: {response.meta}"
        elif response.status == 60:
            return False, "Authentication required"
        else:
            return False, f"Unexpected status {response.status}: {response.meta}"

    except asyncio.TimeoutError:
        return False, "Upload timed out"
    except ConnectionError as e:
        return False, f"Connection failed: {e}"
```

## Titan URL Format

The Titan URL format is:

```
titan://hostname[:port]/path;size=BYTES;mime=TYPE[;token=TOKEN]
```

- `size`: Content size in bytes (mandatory)
- `mime`: MIME type (default: `text/gemini`)
- `token`: Authentication token (optional)

The client builds this URL automatically from the parameters you provide.

## See Also

- [Configuration Reference](../reference/configuration.md#titan-section) - Complete Titan configuration options
- [Client API Reference](../reference/api/client.md) - `upload()` and `delete()` method documentation
- [Gemini Protocol](../explanation/gemini-protocol.md) - Understanding the Gemini ecosystem
