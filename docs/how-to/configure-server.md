# Configure a Gemini Server

This guide shows you how to configure a Nauyaca Gemini server using TOML configuration files and command-line overrides.

## Create a Configuration File

### Minimal Configuration

The simplest working configuration requires only a document root:

```toml
[server]
document_root = "./capsule"
```

Save this as `config.toml` in your project directory.

This configuration uses defaults for all other settings:

- **Host**: `localhost`
- **Port**: `1965`
- **TLS**: Auto-generated self-signed certificate (testing only)
- **Rate limiting**: Enabled with sensible defaults
- **Access control**: Allow all connections

!!! warning "Self-Signed Certificates"
    Auto-generated certificates are only suitable for testing. For production, you must provide your own certificates (see [Configure TLS](#configure-tls)).

### Full Configuration Template

For a complete configuration with all available options, copy `/home/alanbato/Code/nauyaca/config.example.toml` to your project:

```bash
cp config.example.toml config.toml
```

Then edit `config.toml` to match your needs.

### Where to Place Configuration Files

You can place configuration files anywhere, but common locations are:

- **Development**: `./config.toml` (project directory)
- **Production**: `/etc/nauyaca/config.toml` or `/etc/gemini/config.toml`
- **User-specific**: `~/.config/nauyaca/config.toml`

Use the `--config` flag to specify the location:

```bash
nauyaca serve --config /etc/nauyaca/config.toml
```

## Configure Network Settings

### Host and Port Binding

Set the host and port in the `[server]` section:

```toml
[server]
host = "0.0.0.0"  # Bind to all network interfaces
port = 1965       # Default Gemini port
```

**Common host values**:

- `"localhost"` or `"127.0.0.1"`: Local connections only (default)
- `"0.0.0.0"`: Accept connections from any network interface
- Specific IP: Bind to a specific network interface

**Test your configuration**:

```bash
# Start server with your config
nauyaca serve --config config.toml

# In another terminal, test connection
nauyaca get gemini://localhost/
```

### Document Root

Specify the directory containing your Gemini content:

```toml
[server]
document_root = "./capsule"  # Relative path
```

Or use an absolute path:

```toml
[server]
document_root = "/var/gemini/capsule"  # Absolute path
```

!!! tip "Path Resolution"
    Relative paths are resolved from the current working directory when you start the server, not from the config file location.

**Verify document root**:

```bash
# Check that the directory exists and contains content
ls -la ./capsule

# Test serving a file
nauyaca serve --config config.toml
# Then visit gemini://localhost/ in a Gemini client
```

## Configure TLS

### Certificate and Key Paths

Specify paths to your TLS certificate and private key:

```toml
[server]
certfile = "cert.pem"
keyfile = "key.pem"
```

For production systems, use absolute paths:

```toml
[server]
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"
```

!!! note "Certificate Requirements"
    - Both `certfile` and `keyfile` must be provided together
    - Files must exist and be readable
    - The certificate must be valid for your server's hostname

### Auto-Generation Behavior

If you omit `certfile` and `keyfile`, Nauyaca automatically generates a self-signed certificate:

```toml
[server]
document_root = "./capsule"
# No certfile/keyfile = auto-generated certificate
```

**When the certificate is generated**:

- On first server startup
- Saved as `cert.pem` and `key.pem` in the current directory
- Valid for the configured hostname

!!! warning "Production Use"
    Auto-generated certificates are **not suitable for production**. Clients will need to manually trust your certificate on first connection (TOFU).

**Test TLS configuration**:

```bash
# Start server
nauyaca serve --config config.toml

# Verify certificate is loaded
# Check server logs for "Using certificate: ..." message
```

## Configure Rate Limiting

Protect your server from abuse with rate limiting:

```toml
[rate_limit]
enabled = true          # Enable rate limiting
capacity = 10           # Allow 10 requests in a burst
refill_rate = 1.0       # Sustained rate: 1 request per second
retry_after = 30        # Tell clients to wait 30 seconds when limited
```

**Understanding the token bucket algorithm**:

- **Capacity**: Maximum burst size (requests that can happen rapidly)
- **Refill rate**: Sustained request rate (tokens per second)
- **Retry-after**: Delay clients should wait when rate-limited (status 44)

**Common configurations**:

```toml
# Lenient (high-traffic site)
[rate_limit]
capacity = 20
refill_rate = 2.0

# Strict (prevent abuse)
[rate_limit]
capacity = 5
refill_rate = 0.5

# Disable rate limiting (not recommended)
[rate_limit]
enabled = false
```

**Test rate limiting**:

```bash
# Make rapid requests to trigger rate limiting
for i in {1..15}; do nauyaca get gemini://localhost/; done

# You should see "44 SLOW DOWN" responses after the capacity is exceeded
```

## Configure Access Control

### IP-Based Allow/Deny Lists

Control which IP addresses can access your server using CIDR notation:

```toml
[access_control]
# Allow only local network
allow_list = ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8"]
default_allow = false

# Or block specific IPs/networks
deny_list = ["198.51.100.0/24", "203.0.113.5"]
default_allow = true
```

**Access control modes**:

1. **Whitelist mode** (explicit allow):
   ```toml
   allow_list = ["192.168.1.0/24"]
   default_allow = false  # Deny everything not in allow_list
   ```

2. **Blacklist mode** (explicit deny):
   ```toml
   deny_list = ["198.51.100.0/24"]
   default_allow = true  # Allow everything not in deny_list
   ```

3. **Combined** (allow takes precedence):
   ```toml
   allow_list = ["10.0.0.5"]
   deny_list = ["10.0.0.0/24"]
   default_allow = false
   # Result: Only 10.0.0.5 is allowed (allow_list takes precedence)
   ```

**Test access control**:

```bash
# From an allowed IP
nauyaca get gemini://localhost/
# Should succeed

# From a blocked IP (if testing locally, modify config temporarily)
# Should receive "53 PROXY REQUEST REFUSED" or connection refused
```

### Path-Based Certificate Authentication

Require client certificates for specific paths:

```toml
# Require any certificate for /app/ paths
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true

# Require specific certificates for admin area
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:a1b2c3d4e5f6...",
  "sha256:1234567890ab...",
]

# Public area (put before /app/ to override)
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false
```

!!! tip "Rule Order Matters"
    Path rules are checked in order. The first matching rule applies. Place more specific paths before general ones.

## Use CLI Overrides

Command-line arguments override configuration file values:

```bash
# Override port
nauyaca serve --config config.toml --port 8080

# Override host and document root
nauyaca serve --config config.toml --host 0.0.0.0 --root /var/gemini

# Override TLS certificates
nauyaca serve --config config.toml --cert /etc/ssl/cert.pem --key /etc/ssl/key.pem
```

### Precedence Rules

Configuration values are applied in this order (later values override earlier):

1. **Default values** (hardcoded in Nauyaca)
2. **Configuration file** (`--config config.toml`)
3. **Command-line arguments** (`--host`, `--port`, etc.)

**Example**:

```toml
# config.toml
[server]
host = "localhost"
port = 1965
```

```bash
# Starts on 0.0.0.0:8080 (CLI overrides config file)
nauyaca serve --config config.toml --host 0.0.0.0 --port 8080
```

### Available CLI Overrides

Not all configuration options can be overridden via CLI. These are supported:

- `--host`: Server host address
- `--port`: Server port
- `--root`: Document root directory
- `--cert`: TLS certificate file
- `--key`: TLS private key file
- `--log-level`: Logging level
- `--log-file`: Log file path
- `--hash-ips` / `--no-hash-ips`: IP address hashing

For other options (rate limiting, access control, certificate auth), use a configuration file.

## Validate Configuration

### Check Configuration Loads Correctly

Test that your configuration file is valid:

```bash
# Try loading the config
nauyaca serve --config config.toml

# Check for error messages like:
# - "Config file not found"
# - "Failed to parse TOML file"
# - "Document root does not exist"
```

If the server starts without errors, your configuration is valid.

### Common Validation Errors

**Document root does not exist**:
```
ValueError: Document root does not exist: /nonexistent/path
```
**Solution**: Create the directory or fix the path in your config.

**Certificate file not found**:
```
ValueError: Certificate file does not exist: cert.pem
```
**Solution**: Generate certificates or fix the path.

**Invalid port number**:
```
ValueError: Invalid port number: 99999 (must be 1-65535)
```
**Solution**: Use a valid port (1-65535).

**Mismatched cert/key**:
```
ValueError: Both certfile and keyfile must be provided together
```
**Solution**: Provide both `certfile` and `keyfile`, or omit both.

**Invalid TOML syntax**:
```
ValueError: Failed to parse TOML file: ...
```
**Solution**: Check TOML syntax. Common issues:
- Missing quotes around strings
- Mismatched brackets
- Invalid keys

**Test with validation**:

```bash
# The server validates config on startup
nauyaca serve --config config.toml

# If validation passes, you'll see:
# INFO     Starting Gemini server...
# INFO     Server listening on localhost:1965
```

## Environment-Specific Configs

### Development vs Production

Maintain separate configurations for different environments:

**Development** (`config.dev.toml`):
```toml
[server]
host = "localhost"
port = 1965
document_root = "./capsule"
# Auto-generated certificate is fine for dev

[logging]
hash_ips = false  # Show real IPs in dev logs

[rate_limit]
enabled = false  # Disable for easier testing
```

**Production** (`config.prod.toml`):
```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"

[logging]
hash_ips = true  # Privacy-preserving logs

[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.0

[access_control]
# Stricter access control in production
deny_list = ["198.51.100.0/24"]
```

**Use environment-specific configs**:

```bash
# Development
nauyaca serve --config config.dev.toml

# Production
nauyaca serve --config config.prod.toml
```

### Multiple Configuration Files

You can maintain multiple configs for different use cases:

```
configs/
├── minimal.toml          # Bare minimum
├── development.toml      # Local development
├── staging.toml          # Staging environment
├── production.toml       # Production deployment
└── testing.toml          # Integration testing
```

Select the appropriate config when starting the server:

```bash
nauyaca serve --config configs/production.toml
```

!!! tip "Environment Variables"
    For sensitive values like file paths, consider using environment variables in your deployment scripts:
    ```bash
    # deployment.sh
    CERT_PATH=/etc/ssl/certs/gemini.pem
    nauyaca serve --config config.toml --cert $CERT_PATH
    ```

## See Also

- [Configuration Reference](/home/alanbato/Code/nauyaca/docs/reference/configuration.md) - Complete list of all configuration options
- [Security Best Practices](/home/alanbato/Code/nauyaca/SECURITY.md) - Security considerations for production deployments
- [Getting Started Tutorial](/home/alanbato/Code/nauyaca/docs/tutorials/getting-started.md) - Step-by-step guide to running your first server
- [CLI Reference](/home/alanbato/Code/nauyaca/docs/reference/cli.md) - All available command-line options
