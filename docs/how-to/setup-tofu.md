# TOFU Certificate Management

This guide shows you how to manage Trust-On-First-Use (TOFU) certificates when using Nauyaca's Gemini client.

TOFU is the recommended security model for Gemini. Instead of relying on Certificate Authorities, clients trust certificates on first use and verify them on subsequent connections.

## View Known Hosts

To see all hosts you've previously connected to:

```bash
nauyaca tofu list
```

This displays a table showing:

- **Hostname**: The domain name (e.g., `gemini.circumlunar.space`)
- **Port**: The port number (default: 1965)
- **Fingerprint**: SHA-256 hash of the certificate (truncated for display)
- **First Seen**: Date you first connected
- **Last Seen**: Date of your most recent connection

!!! tip "Empty List"
    If you see "No known hosts in TOFU database", you haven't connected to any Gemini servers yet, or you've cleared your database.

## Trust a New Host

When you connect to a Gemini server for the first time, Nauyaca automatically trusts its certificate and adds it to the database. No action is needed.

```bash
# First connection - certificate automatically trusted
nauyaca get gemini://example.com/
```

### Manually Trust a Host

To manually trust a host's current certificate (useful after certificate changes):

```bash
nauyaca tofu trust example.com
```

For servers on non-standard ports:

```bash
nauyaca tofu trust example.com --port 1965
```

This connects to the server, retrieves its certificate, and updates the database.

!!! warning "Security Consideration"
    Only manually trust a certificate if you've verified it's legitimate (e.g., the server admin announced a certificate renewal).

## Revoke Trust

To remove a host from your trusted database:

```bash
nauyaca tofu revoke example.com
```

For non-standard ports:

```bash
nauyaca tofu revoke example.com --port 1965
```

### When to Revoke

Revoke trust when:

- You no longer want to connect to the server
- You suspect the certificate has been compromised
- You want to re-verify the server's certificate on next connection
- You're troubleshooting connection issues

After revoking, the next connection will automatically trust the new certificate (first-use behavior).

## Handle Certificate Changes

When a server's certificate changes, you'll see an error like this:

```
Certificate Changed!
Host: example.com:1965
Old fingerprint: sha256:abc123...
New fingerprint: sha256:def456...

This could indicate:
  1. A man-in-the-middle attack
  2. Legitimate certificate renewal

To trust the new certificate, run:
  nauyaca tofu trust example.com --port 1965
```

### Deciding to Accept or Reject

**Accept the new certificate** if:

- The server admin announced a certificate renewal
- The certificate expired and was legitimately renewed
- You control the server and know the change is intentional

**Reject and investigate** if:

- You weren't expecting a certificate change
- The timing seems suspicious
- You're on an untrusted network (public WiFi, etc.)
- The server hasn't announced any changes

To accept, run the suggested command:

```bash
nauyaca tofu trust example.com --port 1965
```

!!! danger "Security Alert"
    Certificate changes can indicate man-in-the-middle attacks. Always verify through a separate channel (email, Matrix, etc.) before trusting a changed certificate.

## View Host Information

To see detailed information about a specific host:

```bash
nauyaca tofu info example.com
```

For non-standard ports:

```bash
nauyaca tofu info example.com --port 1965
```

This shows:

- Hostname
- Port
- Full SHA-256 fingerprint
- First seen timestamp
- Last seen timestamp

## Export TOFU Database

To create a backup or transfer your trusted hosts to another machine:

```bash
nauyaca tofu export backup.toml
```

This creates a human-readable TOML file containing all trusted hosts.

To overwrite an existing file:

```bash
nauyaca tofu export backup.toml --force
```

### What's in the Export

The exported TOML file contains:

```toml
[_metadata]
exported_at = "2025-11-29T12:00:00+00:00"
version = "1.0"

[hosts."example.com:1965"]
hostname = "example.com"
port = 1965
fingerprint = "sha256:abc123..."
first_seen = "2025-01-15T10:30:00+00:00"
last_seen = "2025-11-29T11:45:00+00:00"
```

You can edit this file manually if needed, but be careful with fingerprints.

## Import TOFU Database

To restore from a backup or transfer from another machine:

```bash
nauyaca tofu import backup.toml
```

By default, this **merges** with your existing database:

- New hosts are added
- Existing hosts with matching fingerprints are skipped
- Conflicts trigger a prompt

### Handle Conflicts

When a host exists in both databases with different fingerprints, you'll see:

```
Fingerprint conflict for example.com:1965

Source                  Fingerprint
Current (database)      sha256:abc123...
New (TOML file)         sha256:def456...

Accept new fingerprint? [y/N]
```

Answer `y` to update to the new fingerprint, or `n` to keep your current one.

### Replace Mode

To **replace** your entire database with the import:

```bash
nauyaca tofu import backup.toml --replace
```

This clears all existing entries first. You'll be prompted to confirm unless you use `--force`.

!!! warning "Destructive Operation"
    Replace mode deletes all current entries. Make sure you have a backup first.

### Auto-Accept Conflicts

To skip all prompts and automatically accept new fingerprints:

```bash
nauyaca tofu import backup.toml --force
```

Use this when:

- You're restoring from a known-good backup
- You trust the source of the TOML file completely
- You're migrating to a new machine

## Clear All Trust

To remove all hosts from the database:

```bash
nauyaca tofu clear
```

You'll be prompted to confirm. To skip confirmation:

```bash
nauyaca tofu clear --force
```

### When to Clear

Clear the database to:

- Start fresh after security concerns
- Test TOFU behavior
- Remove all trust before switching to a different client

!!! danger "Permanent Deletion"
    This removes all trusted certificates. You'll need to re-trust hosts on next connection. Consider exporting first.

## TOFU Database Location

### Default Location

Nauyaca stores the TOFU database at:

```
~/.nauyaca/tofu.db
```

On different platforms:

- **Linux/macOS**: `/home/username/.nauyaca/tofu.db`
- **Windows**: `C:\Users\username\.nauyaca\tofu.db`

### Database Format

The database is SQLite 3. You can inspect it with standard SQLite tools:

```bash
sqlite3 ~/.nauyaca/tofu.db "SELECT * FROM known_hosts;"
```

However, the `nauyaca tofu` commands provide a safer interface.

### Custom Database Path

Currently, Nauyaca uses the default path. For programmatic use via the Python API:

```python
from pathlib import Path
from nauyaca.security.tofu import TOFUDatabase

# Use custom path
db = TOFUDatabase(Path("/custom/path/tofu.db"))
```

### Backup Recommendations

Regularly backup your TOFU database:

```bash
# Create backup
nauyaca tofu export ~/backups/tofu-$(date +%Y%m%d).toml

# Or copy the database file
cp ~/.nauyaca/tofu.db ~/backups/tofu-$(date +%Y%m%d).db
```

Set up automatic backups if you connect to many servers.

## Advanced Usage

### Disable TOFU

To connect without TOFU validation (testing only):

```bash
nauyaca get gemini://example.com/ --no-trust
```

!!! danger "Security Risk"
    Disabling TOFU removes certificate validation. Only use for testing with known self-signed certificates.

### Combine with Client Certificates

TOFU works alongside client certificate authentication:

```bash
nauyaca get gemini://secure.example.com/ \
  --client-cert ~/.nauyaca/certs/myidentity.pem \
  --client-key ~/.nauyaca/certs/myidentity.key
```

The server's certificate is still validated via TOFU.

### Programmatic Access

For Python scripts:

```python
import asyncio
from nauyaca.client.session import GeminiClient
from nauyaca.security.tofu import CertificateChangedError

async def main():
    try:
        async with GeminiClient(trust_on_first_use=True) as client:
            response = await client.get("gemini://example.com/")
            print(response.body)
    except CertificateChangedError as e:
        print(f"Certificate changed for {e.hostname}")
        print(f"Old: {e.old_fingerprint}")
        print(f"New: {e.new_fingerprint}")
        # Handle appropriately

asyncio.run(main())
```

## See Also

- [Quickstart Guide](../quickstart.md) - Getting started with Nauyaca
- [Security Documentation](../reference/api/security.md) - Detailed security information
- [CLI Reference](../reference/cli.md) - Complete CLI command reference
- [Client API Reference](../reference/api/client.md) - Python API documentation
