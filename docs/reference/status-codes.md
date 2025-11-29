# Status Code Reference

This reference provides complete documentation for all Gemini protocol status codes. Status codes are two-digit integers where the first digit indicates the general category of the response.

## Status Code Format

Every Gemini response starts with a status line:

```
<STATUS><SPACE><META><CRLF>
```

- **STATUS**: Two-digit code (10-69)
- **META**: Status-dependent metadata (MIME type, URL, error message, or prompt)
- **CRLF**: Carriage return + line feed (`\r\n`)

## Quick Reference Table

| Code | Name | META Contains | Body Present |
|------|------|---------------|--------------|
| 10 | INPUT | Prompt text | No |
| 11 | SENSITIVE INPUT | Prompt text | No |
| 20 | SUCCESS | MIME type | Yes |
| 30 | REDIRECT TEMPORARY | New URL | No |
| 31 | REDIRECT PERMANENT | New URL | No |
| 40 | TEMPORARY FAILURE | Error message | No |
| 41 | SERVER UNAVAILABLE | Error message | No |
| 42 | CGI ERROR | Error message | No |
| 43 | PROXY ERROR | Error message | No |
| 44 | SLOW DOWN | Retry-after time | No |
| 50 | PERMANENT FAILURE | Error message | No |
| 51 | NOT FOUND | Error message | No |
| 52 | GONE | Error message | No |
| 53 | PROXY REQUEST REFUSED | Error message | No |
| 59 | BAD REQUEST | Error message | No |
| 60 | CLIENT CERTIFICATE REQUIRED | Certificate info | No |
| 61 | CERTIFICATE NOT AUTHORISED | Error message | No |
| 62 | CERTIFICATE NOT VALID | Error message | No |

## Status Code Categories

### 1x - Input Required

The server needs additional input from the client to complete the request.

#### 10 - INPUT

**When returned**: The server needs additional input (like a search query, form data, etc.) to fulfill the request.

**META contains**: A prompt to display to the user explaining what input is needed.

**Client handling**:
- Display the prompt to the user
- Accept user input
- Re-request the same URL with the input appended as a query string

**Nauyaca server example**:
```python
from nauyaca.protocol.response import GeminiResponse
from nauyaca.protocol.status import StatusCode

response = GeminiResponse(
    status=StatusCode.INPUT.value,
    meta="Enter your search query:"
)
# Client re-requests: gemini://example.com/search?user+input+here
```

**Real-world uses**:
- Search forms
- Interactive tools (calculators, converters)
- Comment submission
- Any dynamic content requiring user input

---

#### 11 - SENSITIVE INPUT

**When returned**: Like status 10, but the input should be treated as sensitive and not echoed to the screen.

**META contains**: A prompt explaining what sensitive input is needed.

**Client handling**:
- Display the prompt
- Accept input WITHOUT echoing characters (like password entry)
- Re-request with input as query string
- Do NOT store this input in history or logs

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.SENSITIVE_INPUT.value,
    meta="Enter your password:"
)
```

**Real-world uses**:
- Password authentication
- API keys or tokens
- Personal identification numbers
- Any sensitive data that shouldn't appear in logs or history

---

### 2x - Success

The request was successful and content follows.

#### 20 - SUCCESS

**When returned**: The request was successful and the response body contains the requested resource.

**META contains**: The MIME type of the response body, optionally with charset parameter.

**Client handling**:
- Parse the MIME type from META
- Read and process the response body according to the MIME type
- If no charset is specified, assume UTF-8

**Nauyaca server example**:
```python
from nauyaca.protocol.constants import MIME_TYPE_GEMTEXT

# Gemtext response
response = GeminiResponse(
    status=StatusCode.SUCCESS.value,
    meta=MIME_TYPE_GEMTEXT,  # "text/gemini"
    body="# Welcome\n\nThis is gemtext content."
)

# Plain text with charset
response = GeminiResponse(
    status=StatusCode.SUCCESS.value,
    meta="text/plain; charset=utf-8",
    body="Plain text content"
)

# Binary content
response = GeminiResponse(
    status=StatusCode.SUCCESS.value,
    meta="image/png",
    body=png_image_bytes
)
```

**Common MIME types**:
- `text/gemini` - Gemtext (native markup)
- `text/plain` - Plain text
- `text/html` - HTML (some clients may not render)
- `image/png`, `image/jpeg`, `image/gif` - Images
- `application/pdf` - PDF documents
- `audio/mpeg`, `video/mp4` - Media files

**Real-world uses**:
- Serving any successful content
- Static files (documents, images, media)
- Dynamically generated content
- Directory listings

!!! note "Only 2x responses have bodies"
    Status 20 (and other 2x codes if defined) are the ONLY status codes where a response body is present. All other status codes have only a header line.

---

### 3x - Redirect

The requested resource is available at a different URL.

#### 30 - REDIRECT TEMPORARY

**When returned**: The resource is temporarily available at a different URL. This redirect may not be permanent.

**META contains**: The full URL where the resource can be found.

**Client handling**:
- Do NOT update bookmarks or permanent links
- Follow the redirect to the new URL
- Implement redirect loop detection (max 5 redirects recommended)
- Display the new URL to the user

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.REDIRECT_TEMPORARY.value,
    meta="gemini://example.com/new-location"
)
```

**Real-world uses**:
- Temporary maintenance pages
- A/B testing
- Load balancing
- Short-term URL changes

---

#### 31 - REDIRECT PERMANENT

**When returned**: The resource has permanently moved to a new URL.

**META contains**: The full URL of the new permanent location.

**Client handling**:
- Update bookmarks and permanent links to the new URL
- Follow the redirect
- Implement redirect loop detection
- Cache this redirect for future requests

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.REDIRECT_PERMANENT.value,
    meta="gemini://newdomain.com/resource"
)
```

**Real-world uses**:
- Domain migrations
- Permanent URL restructuring
- Canonical URL enforcement (e.g., redirecting www to non-www)

!!! warning "Redirect Security"
    Clients should validate that redirect URLs use the `gemini://` scheme to prevent protocol downgrade attacks. Cross-protocol redirects (e.g., to `http://`) should be rejected or require explicit user confirmation.

---

### 4x - Temporary Failure

The request failed, but retrying later may succeed.

#### 40 - TEMPORARY FAILURE

**When returned**: A generic temporary failure occurred. The request might succeed if retried later.

**META contains**: A human-readable error message explaining the failure.

**Client handling**:
- Display the error message to the user
- Allow manual retry
- Do NOT automatically retry immediately

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.TEMPORARY_FAILURE.value,
    meta="Database temporarily unavailable"
)
```

**Real-world uses**:
- Database connection failures
- Temporary file system issues
- External service timeouts
- Resource temporarily locked

---

#### 41 - SERVER UNAVAILABLE

**When returned**: The server is unavailable due to overload or maintenance.

**META contains**: A message explaining why the server is unavailable, possibly with retry information.

**Client handling**:
- Display the message to the user
- Wait before retrying (respect any retry-after timing in the message)
- Consider exponential backoff for automatic retries

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.SERVER_UNAVAILABLE.value,
    meta="Server maintenance in progress. Retry in 30 minutes."
)
```

**Real-world uses**:
- Scheduled maintenance
- Server overload (too many connections)
- Graceful shutdown in progress
- Resource exhaustion

---

#### 42 - CGI ERROR

**When returned**: A CGI script or dynamic handler encountered an error.

**META contains**: Error message describing the CGI failure.

**Client handling**:
- Display the error to the user
- The error is temporary - script issues may be fixed

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.CGI_ERROR.value,
    meta="CGI script execution failed"
)
```

**Real-world uses**:
- CGI script crashes
- Script timeout
- Script permission errors
- Script dependency failures

---

#### 43 - PROXY ERROR

**When returned**: A proxy encountered an error when attempting to reach the upstream server.

**META contains**: Error message describing the proxy failure.

**Client handling**:
- Display the error to the user
- The upstream server may be temporarily down
- Retry may succeed if upstream recovers

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.PROXY_ERROR.value,
    meta="Upstream server connection timeout"
)
```

**Real-world uses**:
- Upstream server unreachable
- Upstream connection timeout
- Upstream returned invalid response
- Proxy configuration error

---

#### 44 - SLOW DOWN

**When returned**: The client is making requests too quickly and has been rate-limited.

**META contains**: A message indicating rate limiting, often including a retry-after time in seconds.

**Client handling**:
- Display the rate limit message
- Parse retry-after time if present
- Wait before retrying
- Reduce request frequency
- DO NOT implement aggressive automatic retries

**Nauyaca server example**:
```python
from nauyaca.server.middleware import RateLimitMiddleware, RateLimitConfig

# Configuration
config = RateLimitConfig(
    capacity=10,        # 10 requests
    refill_rate=1.0,    # 1 token per second
    retry_after=30      # Suggest 30 second retry delay
)

# Middleware returns:
# "44 Rate limit exceeded. Retry after 30 seconds\r\n"
```

**Real-world uses**:
- Preventing DoS attacks
- Protecting server resources
- Enforcing fair usage policies
- Preventing scraping/hammering

!!! tip "Rate Limiting Best Practices"
    When implementing clients:

    - Honor retry-after suggestions
    - Implement exponential backoff
    - Consider caching responses to reduce requests
    - Add delays between automated requests

    When implementing servers:

    - Use token bucket or similar algorithm
    - Track per-IP or per-certificate
    - Provide helpful retry-after times
    - Log rate limit violations for monitoring

---

### 5x - Permanent Failure

The request failed and should not be retried without modification.

#### 50 - PERMANENT FAILURE

**When returned**: A generic permanent failure occurred. Retrying without changes will not succeed.

**META contains**: A human-readable error message.

**Client handling**:
- Display the error message
- Do NOT automatically retry
- The user may need to modify their request or take other action

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.PERMANENT_FAILURE.value,
    meta="Access denied: insufficient permissions"
)
```

**Real-world uses**:
- Permission errors (when not using client certs)
- Invalid request parameters
- Unsupported operations
- System limitations

---

#### 51 - NOT FOUND

**When returned**: The requested resource does not exist at this URL.

**META contains**: Error message indicating the resource was not found.

**Client handling**:
- Display error to user
- Do NOT retry the same URL
- The URL may be incorrect or the resource may have been removed

**Nauyaca server example**:
```python
from nauyaca.server.handler import StaticFileHandler

# StaticFileHandler returns 51 when file doesn't exist:
response = GeminiResponse(
    status=StatusCode.NOT_FOUND.value,
    meta="Not found"
)
```

**Real-world uses**:
- File doesn't exist
- Page deleted
- Mistyped URL
- Path doesn't match any routes

---

#### 52 - GONE

**When returned**: The resource previously existed but has been permanently removed.

**META contains**: Message indicating the resource is gone, possibly with information about why or where to find alternatives.

**Client handling**:
- Display message to user
- Remove bookmarks/links to this resource
- Do NOT retry
- This is stronger than 51 - it confirms the resource DID exist

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.GONE.value,
    meta="This page has been permanently removed"
)
```

**Real-world uses**:
- Explicitly deleted content
- Expired time-limited resources
- Deprecated endpoints
- Removed after legal request

!!! note "51 vs 52"
    - **51 (NOT FOUND)**: Resource doesn't exist (may never have existed)
    - **52 (GONE)**: Resource DID exist but has been permanently removed

    Use 52 when you want to explicitly signal that removal was intentional.

---

#### 53 - PROXY REQUEST REFUSED

**When returned**: The request was for a proxied resource, but the server refuses to proxy it.

**META contains**: Message explaining why the proxy request was refused.

**Client handling**:
- Display error to user
- The request may be invalid or the proxy policy prohibits this request
- Do NOT retry the same request

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.PROXY_REQUEST_REFUSED.value,
    meta="Proxy access denied for this domain"
)
```

**Real-world uses**:
- Proxy whitelist/blacklist enforcement
- Blocked destination domains
- Proxy disabled for security reasons
- Invalid proxy request format

---

#### 59 - BAD REQUEST

**When returned**: The request was malformed or invalid according to Gemini protocol rules.

**META contains**: Message explaining what was wrong with the request.

**Client handling**:
- Display error to user
- The client has a bug or sent invalid data
- Do NOT retry without fixing the request
- Log the error for debugging

**Nauyaca server example**:
```python
from nauyaca.server.protocol import GeminiServerProtocol

# Protocol returns 59 for various violations:

# Request too large (>1024 bytes)
response = "59 Request exceeds maximum size (1024 bytes)\r\n"

# Invalid UTF-8
response = "59 Invalid UTF-8 encoding\r\n"

# Malformed URL
response = "59 Invalid request format\r\n"
```

**Real-world uses**:
- Request exceeds 1024 byte limit
- Missing CRLF terminator
- Invalid UTF-8 encoding
- Malformed URL
- Wrong protocol scheme

!!! tip "Request Validation"
    Nauyaca automatically validates requests and returns 59 for:

    - Requests over 1024 bytes
    - Invalid UTF-8 encoding
    - Missing or malformed URLs
    - Protocol violations

---

### 6x - Client Certificate Required

Authentication via client certificate is required or failed.

#### 60 - CLIENT CERTIFICATE REQUIRED

**When returned**: The requested resource requires a client certificate for access.

**META contains**: Message requesting a client certificate, possibly with information about what certificate is needed.

**Client handling**:
- Check if a client certificate is configured
- If available, retry the request with the certificate
- If not available, prompt the user to obtain/configure a certificate
- Display the META message explaining certificate requirements

**Nauyaca server example**:
```python
from nauyaca.server.middleware import ClientCertificateMiddleware

# Middleware can require certificates for specific paths:
response = GeminiResponse(
    status=StatusCode.CLIENT_CERT_REQUIRED.value,
    meta="Client certificate required to access this resource"
)
```

**Real-world uses**:
- Private/members-only sections
- Authentication without passwords
- Identity verification
- Access control

---

#### 61 - CERTIFICATE NOT AUTHORISED

**When returned**: A client certificate was provided, but it's not authorized to access this resource.

**META contains**: Message explaining why the certificate is not authorized.

**Client handling**:
- Display the error message
- The certificate is valid but doesn't have permission
- User may need a different certificate or permission needs to be granted
- Do NOT retry with the same certificate

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.CERT_NOT_AUTHORIZED.value,
    meta="This certificate is not authorized for this resource"
)
```

**Real-world uses**:
- Certificate not in allowlist
- Wrong user/identity for this resource
- Insufficient privileges
- Certificate revoked

---

#### 62 - CERTIFICATE NOT VALID

**When returned**: The provided client certificate is not valid.

**META contains**: Message explaining why the certificate is invalid.

**Client handling**:
- Display the error message
- The certificate has technical problems
- User needs to obtain a new valid certificate
- Do NOT retry with the same certificate

**Nauyaca server example**:
```python
response = GeminiResponse(
    status=StatusCode.CERT_NOT_VALID.value,
    meta="Client certificate has expired"
)
```

**Real-world uses**:
- Expired certificate
- Certificate signature verification failed
- Certificate from untrusted issuer
- Malformed certificate

!!! note "Certificate Status Codes"
    The distinction between 60, 61, and 62:

    - **60 (REQUIRED)**: No certificate provided, but one is needed
    - **61 (NOT AUTHORISED)**: Certificate is valid but lacks permission
    - **62 (NOT VALID)**: Certificate has technical problems (expired, invalid, etc.)

---

## Implementation Examples

### Server-Side Status Code Usage

```python
from nauyaca.protocol.response import GeminiResponse
from nauyaca.protocol.status import StatusCode
from nauyaca.server.handler import RequestHandler

class MyHandler(RequestHandler):
    async def handle_request(self, request):
        # Success with content
        if request.path == "/":
            return GeminiResponse(
                status=StatusCode.SUCCESS.value,
                meta="text/gemini",
                body="# Welcome\n\nContent here."
            )

        # Not found
        elif request.path == "/missing":
            return GeminiResponse(
                status=StatusCode.NOT_FOUND.value,
                meta="Page not found"
            )

        # Redirect
        elif request.path == "/old":
            return GeminiResponse(
                status=StatusCode.REDIRECT_PERMANENT.value,
                meta="gemini://example.com/new"
            )

        # Input required
        elif request.path == "/search" and not request.query:
            return GeminiResponse(
                status=StatusCode.INPUT.value,
                meta="Enter search query:"
            )
```

### Client-Side Status Code Handling

```python
from nauyaca.client.session import GeminiClient
from nauyaca.protocol.status import interpret_status

async def fetch_with_handling(url: str):
    client = GeminiClient()
    response = await client.fetch(url)

    category = interpret_status(response.status)

    if category == "SUCCESS":
        # Process the body content
        print(f"Content type: {response.mime_type}")
        print(response.body)

    elif category == "REDIRECT":
        # Follow redirect
        new_url = response.redirect_url
        print(f"Redirecting to: {new_url}")
        return await fetch_with_handling(new_url)

    elif category == "INPUT":
        # Prompt for input
        user_input = input(f"{response.meta} ")
        new_url = f"{url}?{user_input}"
        return await fetch_with_handling(new_url)

    elif category == "TEMPORARY FAILURE":
        if response.status == 44:  # SLOW DOWN
            print(f"Rate limited: {response.meta}")
            # Wait and retry
        else:
            print(f"Temporary error: {response.meta}")

    elif category == "PERMANENT FAILURE":
        print(f"Permanent error: {response.meta}")

    elif category == "CLIENT CERTIFICATE REQUIRED":
        print(f"Certificate needed: {response.meta}")
```

## Status Code Utilities

Nauyaca provides helper functions for working with status codes:

```python
from nauyaca.protocol.status import (
    interpret_status,
    is_success,
    is_redirect,
    is_input_required,
    is_error
)

# Categorize status codes
category = interpret_status(20)  # Returns "SUCCESS"
category = interpret_status(51)  # Returns "PERMANENT FAILURE"

# Check status categories
is_success(20)          # True
is_redirect(30)         # True
is_input_required(10)   # True
is_error(51)            # True (covers 4x, 5x, 6x)
```

## See Also

- [Gemini Protocol Specification](https://geminiprotocol.net/docs/specification.gmi) - Official specification
- [Configuration Reference](configuration.md) - Configure rate limiting and certificate requirements
- [API Reference](api/index.md) - Using status codes in Python code
- [Security Documentation](/SECURITY.md) - Certificate and authentication features
