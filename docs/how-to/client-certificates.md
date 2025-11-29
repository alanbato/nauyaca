# Client Certificate Authentication

This guide shows you how to use client certificates for authentication in Gemini, both as a server administrator requiring certificates and as a client using certificates to authenticate.

## Overview

Client certificates in Gemini provide a lightweight authentication mechanism without passwords. Servers can require certificates for specific paths (like `/admin/` or `/app/`), and clients present certificates to prove their identity.

## Generate a Client Certificate

Use the `nauyaca cert generate` command to create a self-signed certificate for client authentication:

```bash
# Generate a certificate named 'myidentity'
nauyaca cert generate myidentity

# Generate with custom validity period
nauyaca cert generate myidentity --valid-days 730

# Generate in a specific directory
nauyaca cert generate myidentity --output-dir ./certs/

# Overwrite existing certificate
nauyaca cert generate myidentity --force
```

By default, certificates are created in `~/.nauyaca/certs/` with:

- Certificate file: `~/.nauyaca/certs/myidentity.pem`
- Private key: `~/.nauyaca/certs/myidentity.key` (with restrictive permissions)

The certificate name you provide becomes the Common Name (CN) in the certificate, which some Gemini servers may display as your identity.

### View Certificate Information

To view details about a certificate, including its fingerprint:

```bash
nauyaca cert info ~/.nauyaca/certs/myidentity.pem
```

This displays:

- Subject and issuer
- Serial number
- Validity period (not before/not after dates)
- SHA-256 fingerprint (used for authorization)

## Require Client Certificates (Server)

As a server administrator, you can require client certificates for specific paths using the `[[certificate_auth.paths]]` section in your configuration file.

### Require Any Certificate for a Path

To require that clients present any valid certificate for a specific path:

```toml
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true
```

This configuration:

- Applies to all URLs starting with `/app/`
- Returns status 60 (CLIENT CERTIFICATE REQUIRED) if no certificate is presented
- Accepts any valid client certificate

### Create Public Areas Within Authenticated Paths

Rules are checked in order, so you can create public areas within authenticated paths:

```toml
# Public area - no certificate needed
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false

# Rest of /app/ requires certificate
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true
```

With this configuration:

- `/app/public/` and its subdirectories are accessible to everyone
- All other `/app/` paths require a client certificate
- Order matters: the more specific rule must come first

## Restrict to Specific Certificates

For administrative areas or user-specific content, you can restrict access to specific certificates by their fingerprint.

### Extract Certificate Fingerprint

First, get the fingerprint of the client certificate you want to authorize:

```bash
nauyaca cert info ~/.nauyaca/certs/myidentity.pem
```

Look for the line starting with `Fingerprint (SHA-256):`. It will look like:

```
sha256:a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

### Configure Allowed Fingerprints

Add the fingerprint to your server configuration:

```toml
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
]
```

This configuration:

- Requires a client certificate for `/admin/`
- Only accepts the specific certificate(s) listed
- Returns status 61 (CERTIFICATE NOT AUTHORISED) if a different certificate is presented
- Returns status 60 (CLIENT CERTIFICATE REQUIRED) if no certificate is presented

### Multiple Users

To allow multiple users with different certificates:

```toml
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:admin1-fingerprint-here...",
  "sha256:admin2-fingerprint-here...",
  "sha256:admin3-fingerprint-here...",
]
```

## Send Client Certificate (Client)

As a client, use the `--client-cert` and `--client-key` options to authenticate:

```bash
nauyaca get gemini://secure.example.com/app/ \
  --client-cert ~/.nauyaca/certs/myidentity.pem \
  --client-key ~/.nauyaca/certs/myidentity.key
```

Both options must be provided together:

- `--client-cert`: Path to your certificate file (PEM format)
- `--client-key`: Path to your private key file (PEM format)

### Using the Library API

When using Nauyaca as a library in Python:

```python
import asyncio
from pathlib import Path
from nauyaca.client.session import GeminiClient

async def fetch_with_cert():
    cert_path = Path.home() / ".nauyaca" / "certs" / "myidentity.pem"
    key_path = Path.home() / ".nauyaca" / "certs" / "myidentity.key"

    async with GeminiClient(
        client_cert=cert_path,
        client_key=key_path,
    ) as client:
        response = await client.get("gemini://secure.example.com/app/")
        print(response.body)

asyncio.run(fetch_with_cert())
```

## Handle Certificate Errors

When accessing certificate-protected resources, you may encounter these status codes:

### Status 60: CLIENT CERTIFICATE REQUIRED

The server requires a client certificate, but you didn't provide one.

**Solution**: Provide a client certificate:

```bash
nauyaca get gemini://example.com/app/ \
  --client-cert ~/.nauyaca/certs/myidentity.pem \
  --client-key ~/.nauyaca/certs/myidentity.key
```

### Status 61: CERTIFICATE NOT AUTHORISED

You provided a client certificate, but it's not authorized for this resource.

**Possible causes**:

- The server requires a specific certificate, and yours isn't on the list
- Your certificate has expired
- You're using the wrong certificate for this resource

**Solution**: Verify you're using the correct certificate, or contact the server administrator to have your certificate authorized.

### Status 62: CERTIFICATE NOT VALID

Your client certificate is invalid or malformed.

**Possible causes**:

- Certificate file is corrupted
- Certificate has expired
- Certificate format is incorrect

**Solution**: Generate a new certificate or verify the certificate file is valid:

```bash
# Check certificate validity
nauyaca cert info ~/.nauyaca/certs/myidentity.pem
```

## Common Patterns

### Admin Area with Specific Certificate

Require a specific administrator certificate for the admin area:

```toml
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:admin-cert-fingerprint...",
]
```

### Multi-User Application with Tiered Access

Create different access levels with different certificate requirements:

```toml
# Public area - no auth
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false

# User area - any certificate
[[certificate_auth.paths]]
prefix = "/app/users/"
require_cert = true

# Admin area - specific certificates only
[[certificate_auth.paths]]
prefix = "/app/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:admin1-fingerprint...",
  "sha256:admin2-fingerprint...",
]

# Default for /app/ - require any certificate
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true
```

### Personal Capsule with Private Section

Serve public content by default, but require your personal certificate for private content:

```toml
[[certificate_auth.paths]]
prefix = "/private/"
require_cert = true
allowed_fingerprints = [
  "sha256:my-personal-cert-fingerprint...",
]
```

### Testing with Self-Signed Certificates

During development, require any certificate for testing authentication flows:

```toml
[[certificate_auth.paths]]
prefix = "/test-auth/"
require_cert = true
# No allowed_fingerprints = accept any valid certificate
```

## Security Considerations

### Certificate Storage

- Store private keys securely with restrictive permissions (0600)
- Nauyaca automatically sets correct permissions when generating certificates
- Never share your private key files
- Back up your certificates if they represent persistent identities

### Certificate Rotation

Certificates have expiration dates. Plan for certificate rotation:

1. Generate a new certificate before the old one expires
2. Add both fingerprints to the server configuration temporarily
3. Switch to using the new certificate on the client
4. Remove the old fingerprint from the server after transition

Example transition configuration:

```toml
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:old-cert-fingerprint...",  # Remove after transition
  "sha256:new-cert-fingerprint...",  # Keep this one
]
```

### Fingerprint Verification

Always verify fingerprints through a secure out-of-band channel:

- Don't accept fingerprints sent over email or instant messaging
- Use HTTPS, SSH, or in-person verification to exchange fingerprints
- Document which certificate fingerprints belong to which users

## See Also

- [Server Configuration](configure-server.md) - Full server configuration options
- [Security Best Practices](../reference/api/security.md) - Security considerations
- [API Reference: Certificates](../reference/api/security.md) - Certificate management API
