# Manage TLS Certificates

This guide shows you how to manage TLS certificates for your Nauyaca Gemini server and client. You'll learn how to generate certificates, inspect them, use external certificates, renew them, and troubleshoot common issues.

## Generate a Self-Signed Certificate

Nauyaca can generate self-signed TLS certificates for your Gemini server. This is the quickest way to get started.

### For Server Use

Generate a certificate for your server's hostname:

```bash
nauyaca cert generate localhost
```

This creates two files in `~/.nauyaca/certs/`:

- `localhost.pem` - The certificate (public)
- `localhost.key` - The private key (secret, permissions set to 0600)

**Example output:**

```
Generating certificate for 'localhost'...

Certificate generated successfully!

Certificate   /home/user/.nauyaca/certs/localhost.pem
Private key   /home/user/.nauyaca/certs/localhost.key
Fingerprint   sha256:a1b2c3d4e5f6...
Valid until   2025-11-29

Use with:
  nauyaca get gemini://example.com/ \
    --client-cert /home/user/.nauyaca/certs/localhost.pem \
    --client-key /home/user/.nauyaca/certs/localhost.key
```

### Custom Options

Generate a certificate with custom validity period and key size:

```bash
nauyaca cert generate myserver --valid-days 730 --key-size 4096
```

Options:

- `--valid-days`: Certificate validity in days (default: 365)
- `--key-size`: RSA key size in bits (default: 2048, recommended: 2048 or 4096)
- `--output-dir`: Custom output directory (default: `~/.nauyaca/certs/`)
- `--force`: Overwrite existing certificate files

### For Client Authentication

Some Gemini servers require client certificates for authentication. Generate one with a meaningful name:

```bash
nauyaca cert generate myidentity
```

Use it when making requests:

```bash
nauyaca get gemini://secure.example.com/ \
  --client-cert ~/.nauyaca/certs/myidentity.pem \
  --client-key ~/.nauyaca/certs/myidentity.key
```

## View Certificate Details

Inspect a certificate file to see its properties:

```bash
nauyaca cert info ~/.nauyaca/certs/localhost.pem
```

**Example output:**

```
Subject         CN=localhost,O=Nauyaca Gemini Server
Issuer          CN=localhost,O=Nauyaca Gemini Server
Serial          123456789012345678901234567890
Not Before      2024-11-29T12:00:00+00:00
Not After       2025-11-29T12:00:00+00:00
Fingerprint     sha256:a1b2c3d4e5f6789012345678901234567890abcdef...
```

### Understanding the Output

- **Subject**: The identity the certificate represents (Common Name and Organization)
- **Issuer**: Who signed the certificate (same as Subject for self-signed certs)
- **Serial**: Unique identifier for this certificate
- **Not Before / Not After**: Validity period
- **Fingerprint**: SHA-256 hash used for TOFU validation

## Use Existing Certificates

You can use certificates from external sources like Let's Encrypt, your own CA, or commercial providers.

### Requirements

Certificates must be:

- In PEM format (text files with `-----BEGIN CERTIFICATE-----`)
- Valid for your server's hostname (CN or SAN must match)
- Accompanied by the private key (also in PEM format)

### Configure Server with External Certificates

Point Nauyaca to your certificate files:

```bash
nauyaca serve ./capsule \
  --cert /etc/letsencrypt/live/example.com/fullchain.pem \
  --key /etc/letsencrypt/live/example.com/privkey.pem
```

Or in your configuration file (`config.toml`):

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/letsencrypt/live/example.com/fullchain.pem"
keyfile = "/etc/letsencrypt/live/example.com/privkey.pem"
```

### Using Let's Encrypt Certificates

Let's Encrypt certificates work perfectly with Nauyaca. Generate them using certbot:

```bash
# Install certbot
sudo apt install certbot  # Debian/Ubuntu
sudo dnf install certbot  # Fedora/RHEL

# Generate certificate (HTTP challenge)
sudo certbot certonly --standalone -d gemini.example.com

# Certificates will be in:
# /etc/letsencrypt/live/gemini.example.com/fullchain.pem
# /etc/letsencrypt/live/gemini.example.com/privkey.pem
```

!!! tip "Certificate Renewal"
    Let's Encrypt certificates expire after 90 days. Set up automatic renewal with:

    ```bash
    sudo certbot renew --deploy-hook "systemctl restart nauyaca"
    ```

## Renew Certificates

Certificates have expiration dates. Here's how to handle renewal.

### Check When to Renew

View your certificate's expiration date:

```bash
nauyaca cert info ~/.nauyaca/certs/localhost.pem
```

Look for the "Not After" date. Renew before this date arrives.

!!! warning "Gemini TOFU Considerations"
    When you renew a certificate, the fingerprint changes. Clients using TOFU will see a certificate change warning. This is expected behavior - clients must manually accept the new certificate.

### Replace Certificates Without Downtime

For servers using systemd or process managers:

1. **Generate or obtain new certificate** with the same filename:

   ```bash
   nauyaca cert generate myserver --force
   # Or copy new Let's Encrypt cert
   sudo cp /etc/letsencrypt/live/example.com/fullchain.pem /path/to/cert.pem
   ```

2. **Reload server gracefully**:

   ```bash
   # Systemd
   sudo systemctl reload nauyaca

   # Or send HUP signal
   sudo kill -HUP $(pgrep -f "nauyaca serve")
   ```

3. **Verify new certificate is in use**:

   Connect as a client and check the fingerprint:

   ```bash
   nauyaca get gemini://localhost/ -v
   ```

### Self-Signed Certificate Renewal

Self-signed certificates don't auto-renew. Generate a new one before expiration:

```bash
# Check expiration first
nauyaca cert info ~/.nauyaca/certs/myserver.pem

# Generate new certificate (overwrites old one)
nauyaca cert generate myserver --valid-days 365 --force
```

## Set Correct File Permissions

TLS private keys must be protected from unauthorized access.

### Secure Private Key Permissions

Nauyaca automatically sets secure permissions (0600) when generating certificates, but verify them:

```bash
ls -l ~/.nauyaca/certs/
```

You should see:

```
-rw------- 1 user user 1234 Nov 29 12:00 localhost.key  # 0600 - correct
-rw-r--r-- 1 user user 5678 Nov 29 12:00 localhost.pem  # 0644 - correct
```

### Fix Permission Issues

If permissions are too open, fix them:

```bash
# Fix private key permissions
chmod 600 ~/.nauyaca/certs/*.key

# Fix certificate permissions
chmod 644 ~/.nauyaca/certs/*.pem
```

### Server Deployment Permissions

For production servers, use a dedicated user:

```bash
# Create nauyaca user
sudo useradd -r -s /bin/false nauyaca

# Set ownership
sudo chown nauyaca:nauyaca /etc/nauyaca/certs/*

# Set permissions
sudo chmod 600 /etc/nauyaca/certs/*.key
sudo chmod 644 /etc/nauyaca/certs/*.pem
```

### Common Permission Errors

**Error: "Permission denied: key file"**

```bash
# Your user doesn't have read access to the key
# Fix ownership or permissions:
sudo chown $USER /path/to/key.pem
chmod 600 /path/to/key.pem
```

**Error: "Private key is world-readable"**

```bash
# Security warning - key has overly permissive permissions
# Fix:
chmod 600 /path/to/key.pem
```

## Extract Certificate Fingerprint

Certificate fingerprints are used for TOFU (Trust-On-First-Use) validation.

### Get Fingerprint from Certificate File

Use the `cert info` command:

```bash
nauyaca cert info /path/to/certificate.pem
```

The fingerprint is shown in the output:

```
Fingerprint (SHA-256)  sha256:a1b2c3d4e5f6789012345678901234567890abcdef...
```

### Why Fingerprints Matter

In Gemini's TOFU security model:

1. **First connection**: Client stores the server's certificate fingerprint
2. **Subsequent connections**: Client compares current fingerprint with stored value
3. **Mismatch**: Client warns about potential security issue

When you renew certificates, the fingerprint changes. Clients must manually accept the new certificate:

```bash
nauyaca tofu trust example.com
```

### Manual Fingerprint Extraction

You can also use OpenSSL to extract fingerprints:

```bash
# SHA-256 fingerprint
openssl x509 -in cert.pem -noout -fingerprint -sha256

# SHA-1 fingerprint (legacy)
openssl x509 -in cert.pem -noout -fingerprint -sha1
```

### Compare Two Certificates

Check if two certificate files have the same fingerprint:

```bash
nauyaca cert info cert1.pem | grep Fingerprint
nauyaca cert info cert2.pem | grep Fingerprint
```

If the fingerprints match, they're the same certificate.

## Troubleshooting

### Certificate Not Valid for Hostname

**Problem:** Server hostname doesn't match certificate CN/SAN.

```
ERROR: Certificate not valid for hostname 'example.com'
```

**Solution:** Generate a certificate with the correct hostname:

```bash
nauyaca cert generate example.com
```

Or get a certificate that includes your hostname in the Subject Alternative Name (SAN).

### Certificate Expired

**Problem:** Certificate has passed its expiration date.

```
ERROR: Certificate has expired
```

**Solution:** Generate a new certificate:

```bash
nauyaca cert generate myserver --valid-days 365 --force
```

### Private Key Doesn't Match Certificate

**Problem:** Certificate and private key are from different pairs.

```
ERROR: Private key does not match certificate
```

**Solution:** Ensure you're using the matching certificate and key pair. When generating certificates, Nauyaca creates matching pairs with the same base name:

- `name.pem` - certificate
- `name.key` - matching private key

### Missing Certificate Files

**Problem:** Server can't find certificate files.

```
ERROR: Certificate file not found: /path/to/cert.pem
```

**Solution:** Check the file path and permissions:

```bash
# Verify file exists
ls -l /path/to/cert.pem

# Check absolute path
realpath /path/to/cert.pem

# Use absolute path in configuration
nauyaca serve ./capsule --cert $(realpath cert.pem) --key $(realpath key.pem)
```

## See Also

- [Server Configuration](../reference/configuration.md) - Configure TLS settings in TOML
- [Security Guide](../reference/api/security.md) - Understanding Gemini security model
- [TOFU Management](setup-tofu.md) - Manage trusted certificates as a client
