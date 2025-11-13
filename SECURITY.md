# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

**Note**: Nauyaca is currently in early development. Security updates will be provided for the latest release only.

## Reporting Security Vulnerabilities

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security issues by:

1. **Email**: Send details to the project maintainers (contact info in README.md)
2. **GitHub Security Advisories**: Use the "Security" tab on GitHub to privately report vulnerabilities

### What to Include

Please provide:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if available)
- Your contact information for follow-up

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies by severity (critical issues prioritized)

## Security Features

Nauyaca implements multiple layers of security to protect both servers and clients.

### 1. TLS Security

**Mandatory TLS 1.2+**
- All Gemini connections require TLS 1.2 or higher
- No plaintext fallback - connections without proper TLS are rejected
- Strong cipher suites enforced by default

**Server TLS Configuration**:
```python
# Automatic strong TLS settings
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
```

**Client TLS Configuration**:
- Certificate verification enabled by default
- TOFU (Trust-On-First-Use) validation for first-time connections
- Certificate pinning for known hosts

### 2. TOFU (Trust-On-First-Use)

Nauyaca implements TOFU certificate validation instead of relying on Certificate Authorities.

**How TOFU Works**:
1. **First Connection**: Accept certificate, store SHA-256 fingerprint
2. **Subsequent Connections**: Verify certificate matches stored fingerprint
3. **Certificate Change**: Prompt user for confirmation (may indicate renewal or MITM attack)

**TOFU Storage**:
- Certificates stored in `~/.nauyaca/known_hosts.db` (SQLite database)
- Export/import functionality for backup and sharing
- Manual trust management via CLI commands

**TOFU CLI Commands**:
```bash
# List known hosts
nauyaca tofu list

# Trust a specific host
nauyaca tofu trust example.com --fingerprint <sha256>

# Revoke trust for a host
nauyaca tofu revoke example.com

# Export known hosts
nauyaca tofu export known_hosts_backup.json

# Import known hosts
nauyaca tofu import known_hosts_backup.json
```

### 3. Rate Limiting & DoS Protection

**Token Bucket Algorithm**:
- Configurable capacity and refill rate per client IP
- Default: 10 requests, refill at 1 req/second
- Automatic cleanup of idle rate limiters (memory management)

**Configuration**:
```toml
[rate_limit]
enabled = true
capacity = 10           # Max burst size
refill_rate = 1.0      # Requests per second
retry_after = 30       # Seconds to wait when limited
```

**Response**: Status `44 SLOW DOWN` with retry-after time

### 4. Access Control

**IP-based Allow/Deny Lists**:
- Support for individual IPs and CIDR notation
- IPv4 and IPv6 support
- Configurable default policy (allow or deny)

**Configuration**:
```toml
[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.1"]
deny_list = ["203.0.113.0/24"]
default_allow = false    # Whitelist mode
```

**Processing Order**:
1. Check deny list (reject if match)
2. Check allow list (accept if match)
3. Apply default policy

### 5. Request Validation

**Size Limits**:
- Maximum request size: 1024 bytes (per Gemini specification)
- Requests exceeding limit receive status `59 BAD REQUEST`

**Timeout Protection**:
- Default request timeout: 30 seconds
- Slow clients receive status `40 TIMEOUT`
- Prevents resource exhaustion from slow-loris attacks

**Path Traversal Protection**:
- All file paths canonicalized with `Path.resolve()`
- Validation against document root with `is_relative_to()`
- Attempts to access files outside document root return `51 NOT FOUND`

### 6. Client Certificate Support

**Mutual TLS (mTLS)**:
- Server can request client certificates for authentication
- Status codes `60-62` for certificate-based access control
- Certificate fingerprint validation

**Client Certificate Generation**:
```bash
nauyaca cert generate-client --name "My Identity"
```

## Best Practices for Server Operators

### Certificate Management

**Use Proper Certificates**:
- **Production**: Use certificates from a trusted CA or self-signed certs with TOFU
- **Testing**: Auto-generated self-signed certificates are acceptable
- **Renewal**: Update certificates before expiration; clients will be prompted to accept new fingerprints

**Generate Production Certificates**:
```bash
# Generate self-signed certificate for your domain
nauyaca cert generate --hostname gemini.example.com --days 365
```

**Certificate Security**:
- Keep private keys secure (mode 0600)
- Use strong key sizes (2048-bit RSA minimum, 4096-bit recommended)
- Rotate certificates periodically (annually recommended)

### Rate Limiting Configuration

**Adjust Based on Use Case**:
```toml
# Personal capsule (conservative)
[rate_limit]
capacity = 5
refill_rate = 0.5

# Public server (generous)
[rate_limit]
capacity = 20
refill_rate = 2.0

# High-traffic server (very generous)
[rate_limit]
capacity = 50
refill_rate = 5.0
```

**Monitoring**:
- Watch for clients hitting rate limits frequently
- Adjust limits based on legitimate traffic patterns
- Log rate limit violations for abuse detection

### Access Control

**Whitelist Mode** (recommended for private capsules):
```toml
[access_control]
allow_list = ["192.168.1.0/24", "trusted-proxy-ip"]
default_allow = false
```

**Blacklist Mode** (public servers with known bad actors):
```toml
[access_control]
deny_list = ["abusive-ip", "spam-network/24"]
default_allow = true
```

### Secure Deployment

**File Permissions**:
```bash
# Configuration files
chmod 600 config.toml

# Certificate files
chmod 600 cert.pem key.pem

# Document root (publicly readable)
chmod 755 capsule/
```

**User Isolation**:
- Run server as dedicated non-root user
- Use systemd or similar for process management
- Implement OS-level resource limits

**Logging**:
- Enable access logging for audit trails
- Monitor for suspicious patterns (port scans, path traversal attempts)
- Rotate logs regularly

### Content Security

**Input Validation**:
- Sanitize user input in CGI scripts
- Validate file uploads (if supporting dynamic content)
- Escape special characters in dynamic responses

**Path Security**:
- Keep sensitive files outside document root
- Use `.gemini-access` files for directory protection (if implementing)
- Audit document root for unintended file exposure

## Best Practices for Client Users

### TOFU Verification

**On First Connection**:
- Verify the certificate fingerprint via a trusted secondary channel
- Check hostname matches expected domain
- Note the certificate expiration date

**On Certificate Change**:
- Be suspicious of unexpected certificate changes
- Verify with server operator via independent channel
- Check for announcement of certificate renewal
- If suspicious, **do not accept** the new certificate

### Connection Security

**Verify TLS Settings**:
```python
# Client code should enforce TLS 1.2+
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
```

**Certificate Pinning**:
- Keep your known_hosts database backed up
- Export before system migrations
- Import on new devices for consistent trust

### Client Certificate Privacy

**Identity Management**:
- Use separate certificates for different identities
- Rotate certificates periodically
- Revoke compromised certificates immediately

**Certificate Storage**:
- Protect private keys (file mode 0600)
- Consider encrypted storage for sensitive identities
- Never share private keys

### Redirect Safety

**Follow Redirects Carefully**:
- Nauyaca limits redirects to 5 to prevent loops
- Verify redirect destination before following
- Be cautious of cross-domain redirects

### Content Validation

**Verify Content Integrity**:
- Check response MIME types match expectations
- Validate gemtext parsing for well-formed documents
- Be cautious of unexpected input prompts (status 10/11)

## Known Limitations

### Protocol Limitations

1. **No Certificate Revocation**:
   - Gemini/TOFU has no CRL or OCSP equivalent
   - Compromised certificates must be manually revoked by users
   - Server operators should announce certificate changes

2. **IP-based Rate Limiting**:
   - Can be bypassed with multiple IP addresses
   - NAT/proxy may cause legitimate users to share limits
   - Consider supplementing with application-level limits

3. **No Authentication Beyond Client Certs**:
   - No password or OAuth support in protocol
   - Client certificates are the only authentication mechanism
   - Application-level auth must be implemented in CGI scripts

### Implementation Limitations

1. **In-Memory Rate Limiting**:
   - Rate limit state not persisted across restarts
   - Distributed deployments need separate rate limiting solution
   - Future: Consider Redis-backed rate limiting

2. **Basic Access Control**:
   - IP-based only (no geographic or ASN filtering)
   - No dynamic rule updates (requires server restart)
   - No user-level permissions

3. **TOFU Database**:
   - SQLite database per-user (not system-wide)
   - No automatic certificate expiration warnings
   - Manual export/import required for backups

## Security Audit Status

**Last Audit**: Not yet performed (project in early development)

**Future Plans**:
- Engage security researchers for independent audit
- Implement fuzzing for protocol parser
- Add security-focused integration tests
- Consider formal verification for critical components

## Security Compliance

### Standards Followed

- **Gemini Protocol Specification**: Full compliance
- **TLS Best Practices**: Modern cipher suites, TLS 1.2+ minimum
- **OWASP Guidelines**: Path traversal prevention, input validation

### Cryptographic Dependencies

- Python `ssl` module (OpenSSL backend)
- SHA-256 for certificate fingerprinting
- No custom cryptography implementations

## Additional Resources

- [Gemini Protocol Specification](https://gemini.circumlunar.space/docs/specification.html)
- [TOFU Explained](https://gemini.circumlunar.space/docs/companion/specification.gmi)
- [TLS Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)

## License

Security features are provided as-is under the same license as the project (see LICENSE file).

## Changelog

### Version 0.1.0 (Current)
- Initial security features
- TOFU certificate validation
- Rate limiting with token bucket algorithm
- IP-based access control
- TLS 1.2+ enforcement
- Path traversal protection
- Request timeout protection
