# Security API Reference

This page documents the security-related modules in Nauyaca, including certificate management, TOFU (Trust On First Use) validation, and TLS context creation.

!!! note "Security Model"
    Nauyaca uses **Trust On First Use (TOFU)** for certificate validation instead of traditional Certificate Authority (CA) validation. This is the recommended approach for the Gemini protocol. See the [Security Explanation](../../explanation/security-model.md) for more details.

## Overview

The security modules provide:

- **Certificate Management** (`nauyaca.security.certificates`) - Generate, load, validate, and fingerprint TLS certificates
- **TOFU Database** (`nauyaca.security.tofu`) - Store and verify certificate fingerprints for known hosts
- **TLS Context Creation** (`nauyaca.security.tls`) - Create SSL contexts for client and server connections

## Certificate Management

::: nauyaca.security.certificates

### Common Certificate Operations

#### Generating a Self-Signed Certificate

```python
from pathlib import Path
from nauyaca.security.certificates import generate_self_signed_cert

# Generate certificate for localhost
cert_pem, key_pem = generate_self_signed_cert("localhost")

# Save to files
Path("cert.pem").write_bytes(cert_pem)
Path("key.pem").write_bytes(key_pem)
```

#### Loading and Fingerprinting Certificates

```python
from pathlib import Path
from nauyaca.security.certificates import (
    load_certificate,
    get_certificate_fingerprint,
    get_certificate_info
)

# Load certificate
cert = load_certificate(Path("cert.pem"))

# Get fingerprint
fingerprint = get_certificate_fingerprint(cert)
print(f"Certificate fingerprint: {fingerprint}")

# Get detailed information
info = get_certificate_info(cert)
for key, value in info.items():
    print(f"{key}: {value}")
```

#### Validating Certificates

```python
from pathlib import Path
from nauyaca.security.certificates import (
    load_certificate,
    is_certificate_expired,
    is_certificate_valid_for_hostname,
    validate_certificate_file
)

# Check if certificate is valid
is_valid, error_msg = validate_certificate_file(Path("cert.pem"))
if not is_valid:
    print(f"Certificate invalid: {error_msg}")

# Load and perform detailed checks
cert = load_certificate(Path("cert.pem"))

# Check expiration
if is_certificate_expired(cert):
    print("Certificate has expired!")

# Check hostname validity
if is_certificate_valid_for_hostname(cert, "example.com"):
    print("Certificate is valid for example.com")
```

## TOFU Database

::: nauyaca.security.tofu.TOFUDatabase

::: nauyaca.security.tofu.CertificateChangedError

### Common TOFU Operations

#### Basic TOFU Validation

```python
from pathlib import Path
from nauyaca.security.tofu import TOFUDatabase
from nauyaca.security.certificates import load_certificate

# Initialize TOFU database (uses ~/.nauyaca/tofu.db by default)
tofu = TOFUDatabase()

# Load certificate to verify
cert = load_certificate(Path("server.pem"))

# Verify certificate
is_valid, reason = tofu.verify("example.com", 1965, cert)

if reason == "first_use":
    print("First connection to this host - trusting certificate")
    tofu.trust("example.com", 1965, cert)
elif is_valid:
    print("Certificate verified successfully")
else:
    print(f"Certificate verification failed: {reason}")
```

#### Managing Known Hosts

```python
from nauyaca.security.tofu import TOFUDatabase

tofu = TOFUDatabase()

# List all known hosts
hosts = tofu.list_hosts()
for host in hosts:
    print(f"{host['hostname']}:{host['port']} - {host['fingerprint']}")

# Get info about specific host
info = tofu.get_host_info("example.com", 1965)
if info:
    print(f"First seen: {info['first_seen']}")
    print(f"Last seen: {info['last_seen']}")

# Revoke trust for a host
if tofu.revoke("example.com", 1965):
    print("Host removed from database")
```

#### Exporting and Importing TOFU Data

```python
from pathlib import Path
from nauyaca.security.tofu import TOFUDatabase

tofu = TOFUDatabase()

# Export to TOML file
count = tofu.export_toml(Path("tofu-backup.toml"))
print(f"Exported {count} hosts")

# Import from TOML file (merge with existing)
added, updated, skipped = tofu.import_toml(
    Path("tofu-backup.toml"),
    merge=True
)
print(f"Import: {added} added, {updated} updated, {skipped} skipped")

# Import with conflict resolution
def resolve_conflict(hostname, port, old_fp, new_fp):
    """Ask user whether to update the fingerprint."""
    print(f"\nConflict for {hostname}:{port}")
    print(f"Old: {old_fp}")
    print(f"New: {new_fp}")
    response = input("Update? [y/N]: ")
    return response.lower() == 'y'

added, updated, skipped = tofu.import_toml(
    Path("tofu-backup.toml"),
    merge=True,
    on_conflict=resolve_conflict
)
```

#### Custom TOFU Database Location

```python
from pathlib import Path
from nauyaca.security.tofu import TOFUDatabase

# Use custom database path
custom_db = Path("/var/lib/myapp/tofu.db")
tofu = TOFUDatabase(db_path=custom_db)
```

## TLS Context Creation

::: nauyaca.security.tls

### Common TLS Operations

#### Creating Client Contexts

```python
import ssl
from nauyaca.security.tls import create_client_context

# Testing/development - accept all certificates
context = create_client_context()

# Production - with certificate verification
# (Combine with TOFU for full validation)
context = create_client_context(
    verify_mode=ssl.CERT_REQUIRED,
    check_hostname=True
)

# With client certificate authentication
context = create_client_context(
    verify_mode=ssl.CERT_REQUIRED,
    check_hostname=True,
    certfile="client.pem",
    keyfile="client-key.pem"
)
```

#### Creating Server Contexts

```python
from nauyaca.security.tls import create_server_context

# Basic server
context = create_server_context(
    certfile="server.pem",
    keyfile="server-key.pem"
)

# Server requesting client certificates
# (Used with CertificateAuth middleware)
context = create_server_context(
    certfile="server.pem",
    keyfile="server-key.pem",
    request_client_cert=True,
    client_ca_certs=["trusted_client1.pem", "trusted_client2.pem"]
)
```

!!! warning "Client Certificate Authentication"
    When using `request_client_cert=True` with OpenSSL 3.x, you **must** provide `client_ca_certs` or the TLS handshake will fail silently for self-signed client certificates. For self-signed client certs, include each client's certificate file in the `client_ca_certs` list.

## Integration Examples

### Custom Client with TOFU Validation

```python
import asyncio
import ssl
from pathlib import Path
from nauyaca.security.tls import create_client_context
from nauyaca.security.tofu import TOFUDatabase, CertificateChangedError

async def fetch_with_tofu(url: str):
    """Fetch a Gemini URL with TOFU validation."""
    # Parse URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname or "localhost"
    port = parsed.port or 1965

    # Initialize TOFU database
    tofu = TOFUDatabase()

    # Create SSL context
    ssl_context = create_client_context(
        verify_mode=ssl.CERT_NONE,  # We do our own TOFU validation
        check_hostname=False
    )

    # Connect and get certificate
    reader, writer = await asyncio.open_connection(
        hostname, port, ssl=ssl_context
    )

    # Get peer certificate
    ssl_object = writer.get_extra_info('ssl_object')
    cert_der = ssl_object.getpeercert(binary_form=True)

    # Parse certificate
    from cryptography import x509
    cert = x509.load_der_x509_certificate(cert_der)

    # Verify with TOFU
    is_valid, reason = tofu.verify(hostname, port, cert)

    if reason == "first_use":
        # Prompt user to trust
        from nauyaca.security.certificates import get_certificate_info
        info = get_certificate_info(cert)
        print("First connection to this host!")
        print(f"Fingerprint: {info['fingerprint_sha256']}")
        response = input("Trust this certificate? [y/N]: ")

        if response.lower() == 'y':
            tofu.trust(hostname, port, cert)
        else:
            writer.close()
            await writer.wait_closed()
            raise ValueError("Certificate not trusted")

    elif not is_valid:
        # Certificate changed - potential security issue
        writer.close()
        await writer.wait_closed()
        raise CertificateChangedError(
            hostname, port,
            tofu.get_host_info(hostname, port)['fingerprint'],
            cert.fingerprint(ssl.create_default_context().check_hostname)
        )

    # Send request
    writer.write(f"{url}\r\n".encode())
    await writer.drain()

    # Read response
    response = await reader.read()

    # Close connection
    writer.close()
    await writer.wait_closed()

    return response.decode('utf-8')

# Use the function
asyncio.run(fetch_with_tofu("gemini://example.com/"))
```

### Programmatic Certificate Generation

```python
from pathlib import Path
from nauyaca.security.certificates import (
    generate_self_signed_cert,
    get_certificate_fingerprint,
    load_certificate
)

def setup_server_certificate(hostname: str, cert_dir: Path):
    """Generate and save server certificate."""
    cert_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    # Generate certificate
    print(f"Generating certificate for {hostname}...")
    cert_pem, key_pem = generate_self_signed_cert(
        hostname=hostname,
        key_size=2048,
        valid_days=365
    )

    # Save to files
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    # Display fingerprint
    cert = load_certificate(cert_path)
    fingerprint = get_certificate_fingerprint(cert)

    print(f"Certificate saved to {cert_path}")
    print(f"Private key saved to {key_path}")
    print(f"Fingerprint: {fingerprint}")

    return cert_path, key_path

# Example usage
cert_path, key_path = setup_server_certificate(
    "localhost",
    Path("/etc/nauyaca/certs")
)
```

## See Also

- [Security Model Explanation](../../explanation/security-model.md) - Understand TOFU and why it's used
- [Server Configuration Reference](../configuration.md) - Configure TLS for servers
- [CLI Reference](../cli.md) - Use the `tofu` command for certificate management
- [How to Set Up TOFU](../../how-to/setup-tofu.md) - Step-by-step TOFU setup guide
