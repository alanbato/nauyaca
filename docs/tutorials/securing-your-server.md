# Securing Your Gemini Server

Learn how to transform your basic Gemini capsule into a production-ready, secure server with rate limiting, access control, and certificate authentication.

**Level:** Intermediate
**Time:** ~30 minutes
**Prerequisites:** Basic server setup (see [Quick Start](../quickstart.md))

## What You'll Learn

By the end of this tutorial, you'll have configured:

- Proper TLS certificates with meaningful metadata
- Rate limiting to prevent denial-of-service attacks
- IP-based access control to block unwanted traffic
- Path-based client certificate requirements for authenticated areas
- Security-focused logging with privacy protection

## Why Security Matters

A basic Gemini server is easy to set up, but running it on the public internet exposes you to several threats:

- **Denial of Service (DoS)**: Attackers can overwhelm your server with requests
- **Unauthorized Access**: Without controls, anyone can access your content
- **Resource Exhaustion**: Unchecked traffic can consume bandwidth and CPU
- **Privacy Risks**: Poor logging practices can expose user information

Nauyaca provides multiple security layers to address these threats. Let's implement them step by step.

---

## Step 1: Use Proper TLS Certificates

### The Problem

The auto-generated certificates from `nauyaca serve` are convenient for testing, but they:

- Use generic hostnames (often "localhost")
- Have random serial numbers
- Don't include organization information
- Make TOFU validation less meaningful

### Generate a Production Certificate

Create a proper self-signed certificate with meaningful metadata:

```bash
# Generate certificate for your domain
nauyaca cert generate \
  --hostname gemini.example.com \
  --organization "My Capsule" \
  --days 365 \
  --output-cert cert.pem \
  --output-key key.pem
```

**Parameters explained:**

- `--hostname`: Your actual domain name (critical for TOFU validation)
- `--organization`: Helps identify the certificate owner
- `--days`: Certificate validity period (365 = 1 year)
- `--output-cert/--output-key`: Where to save the files

!!! tip "Certificate Renewal"
    Set a calendar reminder to renew certificates before expiration. Clients will be prompted to accept the new certificate fingerprint.

### Use an Existing Certificate

If you already have certificates from Let's Encrypt, another CA, or a previous setup:

```bash
# Just point to your existing files
nauyaca serve ./capsule \
  --certfile /path/to/your/cert.pem \
  --keyfile /path/to/your/key.pem
```

### Secure Your Certificate Files

Protect your private key with proper permissions:

```bash
# Set restrictive permissions
chmod 600 key.pem cert.pem

# Only the server user should read these files
chown your-server-user:your-server-user key.pem cert.pem
```

!!! warning "Security Critical"
    Never share your private key (`key.pem`). If compromised, generate a new certificate immediately.

**Verify your setup:**

```bash
# Check permissions
ls -l *.pem
# Should show: -rw------- (600)

# Test the certificate
nauyaca serve ./capsule --certfile cert.pem --keyfile key.pem
```

---

## Step 2: Configure Rate Limiting

### The Threat: Denial of Service

Without rate limiting, an attacker can:

- Send thousands of requests per second
- Exhaust your server's CPU and memory
- Make your capsule unavailable to legitimate users
- Consume all your bandwidth

### How Rate Limiting Works

Nauyaca uses the **token bucket algorithm**:

1. Each IP address gets a "bucket" with a certain capacity
2. Each request consumes one token from the bucket
3. Tokens refill at a constant rate
4. When the bucket is empty, requests are rejected with status `44 SLOW DOWN`

### Create a Configuration File

Let's move from command-line arguments to a configuration file:

```bash
# Create config.toml in your capsule directory
cat > config.toml << 'EOF'
[server]
host = "0.0.0.0"
port = 1965
document_root = "./capsule"
certfile = "cert.pem"
keyfile = "key.pem"

[rate_limit]
enabled = true
capacity = 10        # Allow 10-request burst
refill_rate = 1.0    # Refill at 1 request/second
retry_after = 30     # Tell clients to wait 30 seconds
EOF
```

**Parameters explained:**

- **`capacity`**: Maximum burst size (10 means 10 requests instantly available)
- **`refill_rate`**: Sustained request rate (1.0 = 1 request per second)
- **`retry_after`**: Seconds to wait when limited (sent in the `44` response)

### Start Server with Configuration

```bash
nauyaca serve --config config.toml
```

### Test Rate Limiting

Open another terminal and test the limits:

```bash
# Send rapid requests
for i in {1..15}; do
  echo "Request $i:"
  nauyaca get gemini://localhost/ --no-verify-cert
  sleep 0.1
done
```

**Expected behavior:**

- First 10 requests: Success (status `20`)
- Requests 11-15: Rate limited (status `44 Rate limit exceeded. Retry after 30 seconds`)

### Adjust for Your Use Case

Choose rate limits based on your capsule's purpose:

=== "Personal Capsule (Conservative)"

    ```toml
    [rate_limit]
    capacity = 5
    refill_rate = 0.5  # 1 request every 2 seconds
    retry_after = 60
    ```

=== "Public Server (Balanced)"

    ```toml
    [rate_limit]
    capacity = 10
    refill_rate = 1.0  # Default
    retry_after = 30
    ```

=== "High-Traffic Server (Generous)"

    ```toml
    [rate_limit]
    capacity = 50
    refill_rate = 5.0  # 5 requests/second sustained
    retry_after = 10
    ```

!!! note "Memory Management"
    Rate limit buckets are automatically cleaned up after 10 minutes of inactivity, preventing memory leaks.

---

## Step 3: Set Up Access Control

### The Threat: Unwanted Traffic

Sometimes you need to control who can access your capsule:

- **Private capsules**: Only accessible from your local network
- **Blocking bad actors**: IPs that have abused your server
- **Geographic restrictions**: Allow/deny specific IP ranges

### Understanding Access Control

Nauyaca processes IP addresses in this order:

1. **Check deny list** → Reject if match found
2. **Check allow list** → Accept if match found
3. **Apply default policy** → Use `default_allow` setting

### Private Capsule (Whitelist Mode)

Allow only your local network:

```toml
[access_control]
# Only allow local networks
allow_list = [
  "127.0.0.0/8",      # Localhost
  "192.168.1.0/24",   # Your home network
  "10.0.0.0/8"        # Your VPN
]
default_allow = false  # Deny everything else
```

### Public Server with Blocklist

Allow everyone except known bad actors:

```toml
[access_control]
# Block specific abusive IPs
deny_list = [
  "203.0.113.50",      # Individual IP
  "198.51.100.0/24",   # Entire subnet
]
default_allow = true   # Allow everyone else
```

### CIDR Notation Explained

CIDR lets you specify IP ranges efficiently:

| Notation | Meaning | Number of IPs |
|----------|---------|---------------|
| `192.168.1.100` | Single IP | 1 |
| `192.168.1.0/24` | 192.168.1.0 - 192.168.1.255 | 256 |
| `10.0.0.0/8` | 10.0.0.0 - 10.255.255.255 | 16,777,216 |
| `::1` | IPv6 localhost | 1 |
| `2001:db8::/32` | IPv6 subnet | 2^96 |

!!! tip "Finding Your Network Range"
    ```bash
    # On Linux/Mac, find your local network:
    ip addr show | grep inet
    # Or
    ifconfig | grep inet
    ```

### Test Access Control

```bash
# Edit config.toml
cat >> config.toml << 'EOF'

[access_control]
deny_list = ["127.0.0.1"]  # Block localhost for testing
default_allow = true
EOF

# Restart server
nauyaca serve --config config.toml

# In another terminal - this should be blocked
nauyaca get gemini://localhost/
```

**Expected output:**

```
Status: 53 Access denied
```

Remove the deny list entry to restore access.

---

## Step 4: Require Client Certificates

### What Are Client Certificates?

Client certificates enable mutual TLS (mTLS) - the server authenticates the client just as the client authenticates the server. This enables:

- User authentication without passwords
- Persistent identity across sessions
- Fine-grained access control
- Privacy-preserving authentication (no usernames/emails required)

### Use Cases

- **User registration**: Authenticate users by their certificate
- **Private areas**: Require certificates for `/admin/` or `/members/`
- **Mixed content**: Public content at `/`, authenticated at `/app/`

### Path-Based Certificate Requirements

Per Gemini best practices, certificates are typically required for specific paths, not globally:

```toml
# Example: Tiered access control
[[certificate_auth.paths]]
prefix = "/app/public/"
require_cert = false  # Public area - no cert needed

[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true  # Main app - any cert accepted

[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:a1b2c3d4...",  # Admin cert fingerprint
]
```

**Order matters!** Rules are checked from top to bottom, first match wins. Put more specific paths first.

### Generate a Client Certificate

```bash
# Generate a client certificate for testing
nauyaca cert generate-client \
  --name "My Admin Identity" \
  --output-cert client-cert.pem \
  --output-key client-key.pem
```

### Get the Certificate Fingerprint

```bash
# Calculate SHA-256 fingerprint
openssl x509 -in client-cert.pem -noout -fingerprint -sha256
```

**Output:**
```
SHA256 Fingerprint=A1:B2:C3:D4:E5:F6:...:78:9A
```

Convert to the format Nauyaca expects:

```bash
# Remove colons and add 'sha256:' prefix
sha256:a1b2c3d4e5f6...789a
```

### Configure Certificate Authentication

```toml
# Add to config.toml

# Require any client certificate for /members/ area
[[certificate_auth.paths]]
prefix = "/members/"
require_cert = true

# Require specific certificate for /admin/
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:a1b2c3d4e5f6...789a"  # Your fingerprint from above
]
```

### Create Protected Content

```bash
# Create members-only content
mkdir -p capsule/members
cat > capsule/members/index.gmi << 'EOF'
# Members Area

Welcome, authenticated member!

This content is only visible with a client certificate.

=> ../  Back to public area
EOF

# Create admin content
mkdir -p capsule/admin
cat > capsule/admin/index.gmi << 'EOF'
# Admin Panel

This area requires a specific certificate fingerprint.

Only authorized administrators can access this page.
EOF
```

### Test Certificate Authentication

```bash
# Without certificate - should be rejected
nauyaca get gemini://localhost/members/

# Expected output:
# Status: 60 Client certificate required

# With certificate - should succeed
nauyaca get gemini://localhost/members/ \
  --client-cert client-cert.pem \
  --client-key client-key.pem

# Expected output:
# Status: 20 text/gemini
# (page content)
```

!!! tip "Certificate Management"
    - Store client certificates securely (mode 600)
    - Use different certificates for different identities
    - Rotate certificates periodically (every 6-12 months)

---

## Step 5: Configure Privacy-Preserving Logging

### The Privacy Problem

Standard access logs contain IP addresses, which:

- Can identify users
- May violate privacy regulations (GDPR, etc.)
- Create a surveillance record

### IP Hashing Solution

Nauyaca can hash IP addresses in logs, providing:

- Abuse detection (same hash = same user)
- Privacy protection (hash is one-way, can't recover IP)
- Compliance with privacy best practices

### Enable IP Hashing

```toml
[logging]
# Hash IP addresses with SHA-256
hash_ips = true
```

**Before:**
```
[INFO] 192.168.1.100 requested gemini://example.com/
```

**After:**
```
[INFO] a1b2c3d4... requested gemini://example.com/
```

### Set Up Log Rotation

Prevent logs from growing indefinitely:

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/nauyaca << 'EOF'
/var/log/nauyaca/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nauyaca nauyaca
}
EOF
```

This will:

- Rotate logs daily
- Keep 7 days of logs
- Compress old logs
- Create new log files with proper permissions

---

## Step 6: Full Production Configuration

Let's combine all security features into a complete production configuration:

```toml
# Production Nauyaca Configuration
# /etc/nauyaca/config.toml

[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/www/gemini"
certfile = "/etc/nauyaca/certs/cert.pem"
keyfile = "/etc/nauyaca/certs/key.pem"
max_file_size = 104857600  # 100 MiB

[rate_limit]
enabled = true
capacity = 20              # Generous burst for public server
refill_rate = 2.0          # 2 requests/second sustained
retry_after = 30

[access_control]
# Block known bad actors (example)
deny_list = [
  "203.0.113.0/24",        # Example abusive network
]
# Allow everyone else
default_allow = true

# Public content - no certificate needed
[[certificate_auth.paths]]
prefix = "/public/"
require_cert = false

# Application area - any certificate accepted
[[certificate_auth.paths]]
prefix = "/app/"
require_cert = true

# Admin area - specific certificates only
[[certificate_auth.paths]]
prefix = "/admin/"
require_cert = true
allowed_fingerprints = [
  "sha256:replace-with-your-admin-cert-fingerprint",
]

[logging]
# Privacy-preserving logging
hash_ips = true
```

### File Permissions Best Practices

```bash
# Configuration file - sensitive (contains cert paths)
chmod 600 /etc/nauyaca/config.toml
chown nauyaca:nauyaca /etc/nauyaca/config.toml

# Certificates - highly sensitive
chmod 600 /etc/nauyaca/certs/key.pem
chmod 644 /etc/nauyaca/certs/cert.pem
chown nauyaca:nauyaca /etc/nauyaca/certs/*

# Document root - publicly readable
chmod 755 /var/www/gemini
find /var/www/gemini -type f -exec chmod 644 {} \;
find /var/www/gemini -type d -exec chmod 755 {} \;
```

### Systemd Service for Production

Run Nauyaca as a system service:

```bash
# Create service file
sudo tee /etc/systemd/system/nauyaca.service << 'EOF'
[Unit]
Description=Nauyaca Gemini Server
After=network.target

[Service]
Type=simple
User=nauyaca
Group=nauyaca
WorkingDirectory=/var/www/gemini
ExecStart=/usr/local/bin/nauyaca serve --config /etc/nauyaca/config.toml
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/nauyaca

[Install]
WantedBy=multi-user.target
EOF

# Create nauyaca user (if not exists)
sudo useradd -r -s /bin/false nauyaca

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nauyaca
sudo systemctl start nauyaca

# Check status
sudo systemctl status nauyaca
```

---

## What to Monitor

Keep an eye on these security indicators:

### Rate Limiting Events

```bash
# Check logs for rate limit hits
sudo journalctl -u nauyaca | grep "Rate limit"
```

High rate limit violations may indicate:

- DoS attack in progress
- Legitimate crawler (adjust limits)
- Misconfigured client

### Access Control Denials

```bash
# Check for blocked IPs
sudo journalctl -u nauyaca | grep "Access denied"
```

### Failed Certificate Authentication

```bash
# Check certificate rejections
sudo journalctl -u nauyaca | grep "Certificate"
```

### Set Up Alerts (Optional)

```bash
# Simple email alert for repeated rate limiting
# Add to /etc/cron.hourly/nauyaca-alerts

#!/bin/bash
COUNT=$(journalctl -u nauyaca --since "1 hour ago" | grep -c "Rate limit")
if [ $COUNT -gt 100 ]; then
  echo "High rate limiting: $COUNT events in last hour" | \
    mail -s "Nauyaca Alert" admin@example.com
fi
```

---

## Testing Your Security Setup

### Security Checklist

Use this checklist to verify your configuration:

- [ ] TLS certificates have proper hostname and metadata
- [ ] Certificate files have mode 600 (private key) and 644 (certificate)
- [ ] Rate limiting blocks rapid requests (test with loop)
- [ ] Access control denies blocked IPs (test with deny list)
- [ ] Certificate authentication requires certs for protected paths
- [ ] Specific certificate fingerprints are enforced for admin areas
- [ ] IP addresses are hashed in logs (check log output)
- [ ] Server runs as non-root user (check systemd service)
- [ ] Configuration file has restrictive permissions (600)

### Penetration Testing

Test your server's resilience:

```bash
# 1. DoS test (should trigger rate limiting)
for i in {1..100}; do
  nauyaca get gemini://your-server.com/ &
done
wait

# 2. Access control test (should be denied)
# From an IP in your deny list

# 3. Certificate bypass test (should require cert)
nauyaca get gemini://your-server.com/admin/

# 4. Wrong certificate test (should reject)
nauyaca get gemini://your-server.com/admin/ \
  --client-cert wrong-cert.pem \
  --client-key wrong-key.pem
```

---

## Next Steps

Congratulations! You've secured your Gemini server with production-ready security features.

### Further Learning

- **[SECURITY.md](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md)** - Complete security documentation including threat model, limitations, and best practices
- **[Configuration Reference](../reference/configuration.md)** - All available configuration options
- **[Logging Guide](../how-to/logging.md)** - Set up comprehensive logging and monitoring

### Security Considerations

Remember that security is layers:

1. **Network layer**: Firewall, fail2ban, DDoS protection
2. **Application layer**: Rate limiting, access control (this tutorial)
3. **Authentication layer**: Client certificates
4. **Transport layer**: TLS 1.2+
5. **System layer**: User isolation, file permissions, SELinux/AppArmor

Nauyaca handles layers 2-4. You're responsible for layers 1 and 5.

### Known Limitations

Be aware of these security limitations:

- **No certificate revocation**: Gemini/TOFU has no CRL or OCSP
- **IP-based rate limiting**: Can be bypassed with multiple IPs or shared by NAT
- **In-memory state**: Rate limits reset on server restart
- **No geo-blocking**: Use external firewall for geographic restrictions

See [SECURITY.md](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md) for complete details.

---

## Summary

You've learned how to:

- Generate and use proper TLS certificates with meaningful metadata
- Configure token bucket rate limiting to prevent DoS attacks
- Set up IP-based access control with allow/deny lists
- Require client certificates for specific paths
- Implement privacy-preserving logging with IP hashing
- Deploy a production-ready configuration with systemd
- Monitor security events and set up alerts

Your Gemini server is now protected against common threats and ready for public deployment!

---

**Questions or Issues?**

- Review the [Security Documentation](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md)
- Ask in [GitHub Discussions](https://github.com/alanbato/nauyaca/discussions)
- Report security vulnerabilities privately (see SECURITY.md)
