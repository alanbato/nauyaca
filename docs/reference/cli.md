# CLI Reference

This page provides a complete reference for all `nauyaca` command-line interface commands and options.

## Global Commands

### nauyaca --help

Display help information for the CLI or any subcommand.

```bash
nauyaca --help
nauyaca get --help
nauyaca tofu --help
```

### nauyaca version

Show version information.

```bash
nauyaca version
```

**Output:**

```
Nauyaca Gemini Protocol Client & Server
Version: 0.1.0 (MVP)
Protocol: Gemini (gemini://)
```

---

## Client Commands

### nauyaca get

Fetch and display a Gemini resource.

**Syntax:**

```bash
nauyaca get [OPTIONS] URL
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `URL` | Gemini URL to fetch (e.g., `gemini://example.com/`) | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--max-redirects` | `-r` | Integer | 5 | Maximum number of redirects to follow |
| `--no-redirects` | | Flag | False | Disable automatic redirect following |
| `--timeout` | `-t` | Float | 30.0 | Request timeout in seconds |
| `--verbose` | `-v` | Flag | False | Show verbose output with response headers |
| `--trust/--no-trust` | | Flag | True | Enable/disable TOFU certificate validation (recommended: enabled) |
| `--verify-ssl/--no-verify-ssl` | | Flag | False | Use CA-based SSL verification instead of TOFU (not recommended for Gemini) |
| `--client-cert` | | Path | None | Path to client certificate file (PEM format) for authentication |
| `--client-key` | | Path | None | Path to client private key file (PEM format) for authentication |

!!! note "Client Certificate Requirements"
    Both `--client-cert` and `--client-key` must be provided together. Providing only one will result in an error.

**Examples:**

```bash
# Fetch a URL
nauyaca get gemini://gemini.circumlunar.space/

# Fetch with verbose output showing headers
nauyaca get -v gemini://example.com/

# Don't follow redirects
nauyaca get --no-redirects gemini://example.com/

# Custom timeout (10 seconds)
nauyaca get -t 10 gemini://example.com/

# Limit redirects to 2
nauyaca get --max-redirects 2 gemini://example.com/

# Authenticate with client certificate
nauyaca get gemini://secure.example.com/ \
    --client-cert ~/.nauyaca/certs/myidentity.pem \
    --client-key ~/.nauyaca/certs/myidentity.key

# Disable TOFU (not recommended)
nauyaca get --no-trust gemini://example.com/
```

**Exit Codes:**

- `0`: Success (status 2x response)
- `1`: Error (status 4x/5x/6x response, network error, or certificate error)

---

## Server Commands

### nauyaca serve

Start a Gemini server to serve files from a directory.

**Syntax:**

```bash
nauyaca serve [OPTIONS] [ROOT]
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `ROOT` | Document root directory to serve files from | Optional if `--config` is provided |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | None | Path to TOML configuration file (overrides other options) |
| `--host` | `-h` | String | localhost | Server host address (overrides config file) |
| `--port` | `-p` | Integer | 1965 | Server port (overrides config file) |
| `--cert` | | Path | None | Path to TLS certificate file (generates self-signed if omitted) |
| `--key` | | Path | None | Path to TLS private key file |
| `--enable-directory-listing` | `-d` | Flag | False | Enable automatic directory listings for directories without index files |
| `--log-level` | `-l` | String | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `--log-file` | | Path | None | Path to log file (default: stdout) |
| `--json-logs` | | Flag | False | Output logs in JSON format (useful for log aggregation) |
| `--hash-ips/--no-hash-ips` | | Flag | True | Hash client IP addresses in logs for privacy |
| `--max-file-size` | | Integer | 104857600 | Maximum file size to serve in bytes (default: 100 MiB) |
| `--require-client-cert` | | Flag | False | Require client certificates for all connections (status 60 if missing) |
| `--reload` | | Flag | False | Enable auto-reload: restart server when files change (development only) |
| `--reload-dir` | | Path | None | Directory to watch for changes (repeatable). Defaults to document_root and src/nauyaca |
| `--reload-ext` | | String | None | File extension to watch (repeatable). Defaults to .py and .gmi |

!!! tip "Configuration File vs CLI Arguments"
    When using `--config`, CLI arguments override values from the configuration file. This allows you to use a base configuration file and selectively override specific settings.

!!! warning "Hot-Reload is for Development Only"
    The `--reload` flag should never be used in production. It's designed for development workflows where you want the server to automatically restart when source files or content changes.

**Examples:**

```bash
# Serve current directory on default port (1965)
nauyaca serve .

# Serve specific directory
nauyaca serve /var/gemini/capsule

# Serve using TOML configuration file
nauyaca serve --config config.toml

# Serve with config file and CLI overrides
nauyaca serve --config config.toml --port 8080

# Serve with directory listings enabled
nauyaca serve ./capsule --enable-directory-listing

# Serve with custom logging
nauyaca serve ./capsule --log-level DEBUG

# Serve with JSON logs to file
nauyaca serve ./capsule --log-file server.log --json-logs

# Serve with custom TLS certificate
nauyaca serve ./capsule --cert cert.pem --key key.pem

# Serve on all interfaces
nauyaca serve ./capsule --host 0.0.0.0

# Serve requiring client certificates
nauyaca serve ./capsule --require-client-cert

# Serve with privacy-preserving IP hashing disabled
nauyaca serve ./capsule --no-hash-ips

# Serve with hot-reload for development
nauyaca serve ./capsule --reload

# Hot-reload watching custom directories
nauyaca serve ./capsule --reload --reload-dir ./my-handlers

# Hot-reload watching additional file types
nauyaca serve ./capsule --reload --reload-ext .toml --reload-ext .txt
```

**Environment Variables:**

Currently, nauyaca does not use environment variables for server configuration. Use a TOML configuration file or CLI arguments instead.

**Exit Codes:**

- `0`: Server shut down gracefully (Ctrl+C)
- `1`: Configuration error, server error, or unexpected error

---

## Certificate Commands

### nauyaca cert generate

Generate a client certificate for Gemini authentication.

**Syntax:**

```bash
nauyaca cert generate [OPTIONS] NAME
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `NAME` | Name for the certificate (used in filename and as Common Name) | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output-dir` | `-o` | Path | `~/.nauyaca/certs/` | Output directory for certificate and key files |
| `--valid-days` | | Integer | 365 | Certificate validity in days |
| `--key-size` | | Integer | 2048 | RSA key size in bits |
| `--force` | `-f` | Flag | False | Overwrite existing certificate files |

**Output Files:**

- `{NAME}.pem`: Certificate file (PEM format)
- `{NAME}.key`: Private key file (PEM format, permissions set to 0600)

**Examples:**

```bash
# Generate a certificate named 'myidentity'
nauyaca cert generate myidentity

# Generate with custom validity period (2 years)
nauyaca cert generate myidentity --valid-days 730

# Generate with custom output location
nauyaca cert generate myidentity -o ./certs/

# Generate with 4096-bit key
nauyaca cert generate myidentity --key-size 4096

# Overwrite existing certificate
nauyaca cert generate myidentity --force
```

**Exit Codes:**

- `0`: Certificate generated successfully
- `1`: Error (file already exists, generation failed)

---

### nauyaca cert info

Display information about a certificate file.

**Syntax:**

```bash
nauyaca cert info CERT_FILE
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `CERT_FILE` | Path to certificate file (PEM format) | Yes |

**Examples:**

```bash
# Show certificate info
nauyaca cert info ~/.nauyaca/certs/myidentity.pem

# Show info for server certificate
nauyaca cert info /etc/nauyaca/server.pem
```

**Output:**

The command displays a table with:

- **Subject**: Certificate subject (Common Name)
- **Issuer**: Certificate issuer
- **Serial**: Serial number
- **Not Before**: Certificate validity start date
- **Not After**: Certificate expiration date
- **Fingerprint (SHA-256)**: SHA-256 fingerprint of the certificate

**Exit Codes:**

- `0`: Certificate information displayed successfully
- `1`: Error reading certificate

---

## TOFU Commands

The `tofu` subcommand manages the Trust-On-First-Use certificate database.

### nauyaca tofu list

List all known hosts in the TOFU database.

**Syntax:**

```bash
nauyaca tofu list
```

**Examples:**

```bash
nauyaca tofu list
```

**Output:**

Displays a table with:

- **Hostname**: Host domain name
- **Port**: Port number
- **Fingerprint**: SHA-256 fingerprint (truncated for display)
- **First Seen**: Date first encountered
- **Last Seen**: Date last accessed

**Exit Codes:**

- `0`: Success

---

### nauyaca tofu trust

Manually trust a certificate for a host.

This command connects to the host, retrieves its certificate, and adds it to (or updates it in) the TOFU database. This is useful after a certificate change that you've verified is legitimate.

**Syntax:**

```bash
nauyaca tofu trust [OPTIONS] HOSTNAME
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `HOSTNAME` | Hostname to trust | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | Integer | 1965 | Port number |

**Examples:**

```bash
# Trust a host on default port
nauyaca tofu trust example.com

# Trust with custom port
nauyaca tofu trust example.com --port 1965

# Trust after certificate change warning
nauyaca tofu trust gemini.example.com
```

**Exit Codes:**

- `0`: Certificate trusted successfully
- `1`: Error retrieving or trusting certificate

---

### nauyaca tofu revoke

Remove a host from the TOFU database.

**Syntax:**

```bash
nauyaca tofu revoke [OPTIONS] HOSTNAME
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `HOSTNAME` | Hostname to revoke | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | Integer | 1965 | Port number |

**Examples:**

```bash
# Revoke a host on default port
nauyaca tofu revoke example.com

# Revoke with custom port
nauyaca tofu revoke example.com --port 1965
```

**Exit Codes:**

- `0`: Host revoked successfully (or not in database)

---

### nauyaca tofu info

Show detailed information about a known host.

**Syntax:**

```bash
nauyaca tofu info [OPTIONS] HOSTNAME
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `HOSTNAME` | Hostname to inspect | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | Integer | 1965 | Port number |

**Examples:**

```bash
# Show info for a host
nauyaca tofu info example.com

# Show info with custom port
nauyaca tofu info example.com --port 1965
```

**Output:**

Displays a table with:

- **Hostname**: Host domain name
- **Port**: Port number
- **Fingerprint (SHA-256)**: Full SHA-256 fingerprint
- **First Seen**: Timestamp of first encounter
- **Last Seen**: Timestamp of last access

**Exit Codes:**

- `0`: Information displayed successfully
- `1`: Host not found in database

---

### nauyaca tofu export

Export the TOFU database to a TOML file.

This creates a human-readable backup of your trusted hosts that can be edited, shared, or imported on another machine.

**Syntax:**

```bash
nauyaca tofu export [OPTIONS] FILE
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `FILE` | Output TOML file path | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--force` | `-f` | Flag | False | Overwrite existing file |

**Examples:**

```bash
# Export to a file
nauyaca tofu export backup.toml

# Overwrite existing file
nauyaca tofu export backup.toml --force

# Export to specific location
nauyaca tofu export ~/.nauyaca/tofu-backup-$(date +%Y%m%d).toml
```

**Exit Codes:**

- `0`: Export successful
- `1`: Error (file exists and `--force` not used, or export failed)

---

### nauyaca tofu import

Import TOFU database from a TOML file.

By default, entries are merged with the existing database. Use `--replace` to clear the database first. When fingerprint conflicts occur, you'll be prompted unless `--force` is used.

**Syntax:**

```bash
nauyaca tofu import [OPTIONS] FILE
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `FILE` | Input TOML file path | Yes |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--replace` | | Flag | False | Replace all existing entries (default: merge) |
| `--force` | `-f` | Flag | False | Skip all confirmations and auto-accept conflicts |

**Behavior:**

1. **Merge mode** (default): New entries are added, existing entries are kept unless a conflict occurs
2. **Replace mode** (`--replace`): Database is cleared before importing
3. **Conflict handling**: When a hostname exists with a different fingerprint:
   - Without `--force`: User is prompted to accept or reject
   - With `--force`: New fingerprint is automatically accepted

**Examples:**

```bash
# Import and merge with existing database
nauyaca tofu import backup.toml

# Replace entire database
nauyaca tofu import backup.toml --replace

# Auto-accept all conflicts
nauyaca tofu import backup.toml --force

# Replace database without confirmation prompts
nauyaca tofu import backup.toml --replace --force
```

**Output:**

Displays a summary table with:

- **Added**: Number of new entries added
- **Updated**: Number of entries updated (conflicts accepted)
- **Skipped**: Number of entries skipped (conflicts rejected)

**Exit Codes:**

- `0`: Import successful
- `1`: Error (file not found, invalid TOML, or import failed)

---

### nauyaca tofu clear

Clear all entries from the TOFU database.

**Syntax:**

```bash
nauyaca tofu clear [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--force` | `-f` | Flag | False | Skip confirmation prompt |

**Examples:**

```bash
# Clear with confirmation prompt
nauyaca tofu clear

# Clear without confirmation
nauyaca tofu clear --force
```

**Exit Codes:**

- `0`: Database cleared successfully (or operation cancelled)

---

## See Also

- [Server Configuration](../how-to/configure-server.md) - Detailed guide on server configuration
- [TOFU Management](../how-to/setup-tofu.md) - Guide to managing TOFU certificates
- [Server Configuration Reference](configuration.md) - TOML configuration file reference
