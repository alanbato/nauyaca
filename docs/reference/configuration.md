# Configuration Reference

This page documents all configuration options for the Nauyaca Gemini server. Configuration can be provided via TOML files using the `--config` flag, with CLI arguments overriding file-based settings.

## Configuration File Format

Nauyaca uses [TOML](https://toml.io/) (Tom's Obvious Minimal Language) for configuration files. TOML is a minimal, easy-to-read configuration format with clear semantics.

```bash
# Start server with configuration file
nauyaca serve --config config.toml

# Override specific settings via CLI
nauyaca serve --config config.toml --port 8080 --host 0.0.0.0
```

!!! tip "Configuration Examples"
    See [`config.minimal.toml`](https://github.com/alanbato/nauyaca/blob/main/config.minimal.toml) for the simplest working configuration, or [`config.example.toml`](https://github.com/alanbato/nauyaca/blob/main/config.example.toml) for a complete configuration with all available options.

---

## [server] Section

Core server settings including network binding, TLS configuration, and content serving.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | `"localhost"` | Host address to bind to. Use `"0.0.0.0"` to bind to all interfaces, `"localhost"` for local-only access. |
| `port` | integer | `1965` | TCP port to listen on. Standard Gemini port is 1965. Valid range: 1-65535. |
| `document_root` | string | (required) | Path to directory containing files to serve. Can be relative or absolute. Must exist and be a directory. |
| `certfile` | string | `null` | Path to TLS certificate file (PEM format). If omitted, a self-signed certificate will be auto-generated for testing. |
| `keyfile` | string | `null` | Path to TLS private key file (PEM format). Must be provided together with `certfile`. |
| `max_file_size` | integer | `104857600` | Maximum file size to serve in bytes. Default is 100 MiB (104857600 bytes). Gemini is not designed for large file transfers. |
| `require_client_cert` | boolean | `false` | Request client certificates using PyOpenSSL. When `true`, the server can accept any self-signed client certificate. Use with `[[certificate_auth.paths]]` rules to enforce authorization. |

!!! warning "Production TLS Certificates"
    Auto-generated self-signed certificates are only suitable for testing. For production deployments, generate proper certificates using tools like [agate-cert](https://github.com/mbrubeck/agate) or OpenSSL.

!!! note "Certificate and Key Pairing"
    Both `certfile` and `keyfile` must be provided together, or both must be omitted (for auto-generation).

### Example

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"
max_file_size = 52428800  # 50 MiB
```

### CLI Overrides

| TOML Option | CLI Flag | Example |
|-------------|----------|---------|
| `host` | `--host`, `-h` | `--host 0.0.0.0` |
| `port` | `--port`, `-p` | `--port 8080` |
| `document_root` | First positional argument | `nauyaca serve ./capsule` |
| `certfile` | `--cert` | `--cert cert.pem` |
| `keyfile` | `--key` | `--key key.pem` |
| `max_file_size` | `--max-file-size` | `--max-file-size 52428800` |

---

## [rate_limit] Section

Token bucket rate limiting to protect against DoS attacks. Limits the number of requests per IP address.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable or disable rate limiting. Set to `false` to completely disable rate limiting. |
| `capacity` | integer | `10` | Maximum number of tokens (requests) allowed in a burst. This is the initial bucket size. |
| `refill_rate` | float | `1.0` | Rate at which tokens are added to the bucket per second. This controls the sustained request rate. For example, `1.0` = 1 request/second, `2.0` = 2 requests/second. |
| `retry_after` | integer | `30` | Number of seconds the client should wait when rate limited. Sent in the status 44 (SLOW DOWN) response meta field. |

!!! info "Token Bucket Algorithm"
    Each IP address gets a token bucket. Requests consume one token. When the bucket is empty, requests are rejected with status 44 (SLOW DOWN). Tokens refill at the configured rate up to the maximum capacity.

### Rate Limiting Behavior

- **Initial burst**: Clients can make up to `capacity` requests immediately
- **Sustained rate**: After the initial burst, clients are limited to `refill_rate` requests per second
- **Rate limit response**: Status `44 SLOW DOWN` with `retry_after` seconds in the meta field
- **Automatic cleanup**: Rate limit state for inactive IPs is cleaned up automatically

### Example

```toml
[rate_limit]
enabled = true
capacity = 20
refill_rate = 2.0   # Allow 2 requests per second sustained
retry_after = 60    # Tell clients to wait 60 seconds when rate limited
```

### CLI Overrides

Rate limiting cannot be fully configured via CLI. Use a configuration file for fine-grained control. The `--config` flag allows loading these settings from TOML.

---

## [access_control] Section

IP-based access control with support for CIDR notation. Allows creating allowlists (whitelists) and denylists (blacklists).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable or disable access control. Set to `false` to completely disable IP-based access control even if lists are configured. |
| `allow_list` | array of strings | `null` | List of allowed IP addresses/networks in CIDR notation. If set, **only** these IPs can connect (whitelist mode). |
| `deny_list` | array of strings | `null` | List of denied IP addresses/networks in CIDR notation. These IPs are blocked from connecting (blacklist mode). |
| `default_allow` | boolean | `true` | Default policy when an IP is not in any list. `true` = allow all unlisted IPs, `false` = deny all unlisted IPs. |

!!! tip "CIDR Notation"
    Both lists support CIDR notation for network ranges:

    - `192.168.1.0/24` - entire subnet (192.168.1.0 - 192.168.1.255)
    - `10.0.0.5` - single IP address (equivalent to `10.0.0.5/32`)
    - `127.0.0.0/8` - localhost range

### Access Control Modes

**Whitelist Mode** (allow only specific IPs):
```toml
[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.5"]
default_allow = false
```

**Blacklist Mode** (block specific IPs):
```toml
[access_control]
deny_list = ["203.0.113.0/24", "198.51.100.10"]
default_allow = true
```

**Localhost Only**:
```toml
[access_control]
allow_list = ["127.0.0.1", "::1"]
default_allow = false
```

**Local Network Only**:
```toml
[access_control]
allow_list = ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8"]
default_allow = false
```

### Decision Logic

1. If IP is in `deny_list` → **Reject** (status 53 PROXY REQUEST REFUSED)
2. If IP is in `allow_list` → **Allow**
3. Otherwise → Use `default_allow` setting

### Example

```toml
[access_control]
# Block known abusive networks
deny_list = [
    "198.51.100.0/24",
    "203.0.113.0/24"
]
# Allow everyone else
default_allow = true
```

### CLI Overrides

Access control cannot be configured via CLI arguments. Use a configuration file to set up IP-based access control.

---

## [[certificate_auth.paths]] Section

Path-based client certificate authentication following Gemini best practices. Certificates are activated for specific URL prefixes rather than globally, allowing public and authenticated content to coexist on the same server.

!!! info "Array of Tables"
    `[[certificate_auth.paths]]` is a TOML "array of tables". Each `[[certificate_auth.paths]]` entry defines one path rule. Rules are checked in order - the first matching rule applies.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prefix` | string | (required) | URL path prefix to match (e.g., `"/app/"`, `"/admin/"`). Must start with `/`. |
| `require_cert` | boolean | `false` | Whether a client certificate is required for this path. If `true` and no cert is provided, returns status 60 (CLIENT CERTIFICATE REQUIRED). |
| `allowed_fingerprints` | array of strings | `null` | List of allowed certificate fingerprints (SHA-256, format: `"sha256:..."`). If set, only certificates matching these fingerprints are accepted. If `null`, any valid certificate is accepted. |

### Certificate Fingerprints

Certificate fingerprints are SHA-256 hashes in the format:
```
sha256:a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

To get a certificate's fingerprint:
```bash
openssl x509 -in client-cert.pem -noout -fingerprint -sha256
```

### Matching Rules

- Rules are evaluated in the order they appear in the configuration file
- The **first matching prefix** applies to the request
- If no rule matches, the request is allowed without certificate requirements
- Longer prefixes should generally come before shorter ones for proper precedence

### Response Codes

- **60 CLIENT CERTIFICATE REQUIRED**: No certificate provided but `require_cert = true`
- **61 CERTIFICATE NOT AUTHORISED**: Certificate provided but not in `allowed_fingerprints` list
- **62 CERTIFICATE NOT VALID**: Certificate is present but invalid (expired, malformed, etc.)

### Examples

**Require any certificate for /app/ paths**:
```toml
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true
```

**Require specific certificates for /admin/ paths**:
```toml
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
    "sha256:a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
]
```

**Mixed public and authenticated content**:
```toml
# Public area - no cert needed (must come before /app/ rule!)
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false

# Main app - any cert accepted
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true

# Admin area - specific certs only
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = ["sha256:admin-cert-fingerprint-here"]
```

!!! warning "Rule Order Matters"
    In the example above, `/app/public/` must come **before** `/app/` because rules are evaluated in order. If `/app/` came first, it would match `/app/public/` requests and require a certificate.

### CLI Overrides

| TOML Option | CLI Flag | Example |
|-------------|----------|---------|
| Basic cert requirement | `--require-client-cert` | Requires client cert for **all** paths |

!!! note "CLI Limitation"
    The `--require-client-cert` flag applies globally to all paths and does not support fingerprint restrictions. For fine-grained path-based authentication, use a TOML configuration file.

---

## [logging] Section

Privacy-preserving logging configuration.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `hash_ips` | boolean | `true` | Hash client IP addresses in logs using SHA-256. When enabled, IP addresses are replaced with hashes like `ip:abc123...`. This allows abuse detection while protecting user privacy. |

!!! tip "Privacy by Default"
    IP hashing is enabled by default to protect user privacy. Hashed IPs can still be used to detect patterns of abuse (same hash = same IP) without storing raw IP addresses.

### Example

```toml
[logging]
hash_ips = true
```

### CLI Overrides

| TOML Option | CLI Flag | Example |
|-------------|----------|---------|
| `hash_ips` | `--hash-ips` / `--no-hash-ips` | `--no-hash-ips` to disable hashing |

### Additional Logging Options (CLI Only)

The following logging options are **only available via CLI flags**, not in TOML configuration:

| CLI Flag | Default | Description |
|----------|---------|-------------|
| `--log-level`, `-l` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--log-file` | stdout | Path to log file. If not specified, logs to stdout |
| `--json-logs` | `false` | Output logs in JSON format (useful for log aggregation systems) |

---

## Complete Configuration Example

This example shows all available configuration options:

```toml
# Nauyaca Gemini Server Configuration

[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"
max_file_size = 104857600  # 100 MiB

[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.0
retry_after = 30

[access_control]
enabled = true
# Allow local network and specific remote IPs
allow_list = [
    "127.0.0.0/8",
    "192.168.0.0/16",
    "203.0.113.42"
]
# Block known bad actors
deny_list = ["198.51.100.0/24"]
default_allow = false

# Path-based certificate authentication
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false

[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true

[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
    "sha256:a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
]

[logging]
hash_ips = true
```

---

## Minimal Configuration Example

The simplest working configuration requires only the document root:

```toml
[server]
document_root = "./capsule"
```

This uses defaults for everything else:

- Host: `localhost` (local access only)
- Port: `1965` (standard Gemini port)
- TLS: Auto-generated self-signed certificate
- Rate limiting: Enabled with default settings
- Access control: Allow all
- Logging: IP hashing enabled

---

## Configuration Validation

When loading a configuration file, Nauyaca validates:

1. **File existence**: Config file and referenced paths (document_root, certfile, keyfile) must exist
2. **Port range**: Port must be between 1 and 65535
3. **Directory checks**: `document_root` must be a directory, not a file
4. **Certificate pairing**: Both `certfile` and `keyfile` must be provided together
5. **TOML syntax**: File must be valid TOML format

Validation errors are reported clearly with helpful error messages indicating what went wrong.

---

## See Also

- [How-to: Server Configuration](../how-to/configure-server.md) - Step-by-step configuration guide
- [Security Features](../explanation/security-model.md) - Understanding security features
- [CLI Reference](cli.md) - Complete CLI command reference
