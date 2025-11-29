# Security Model

This document explains the security design philosophy and architecture of nauyaca, a Gemini protocol implementation. It focuses on **why** security features are designed the way they are, rather than **how** to configure them (see [SECURITY.md](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md) for configuration details).

## Security Philosophy

Nauyaca's security model is built on three core principles:

### 1. Defense in Depth

Multiple independent security layers protect against different attack vectors:

- **Network layer**: TLS encryption and certificate validation
- **Protocol layer**: Request size limits, timeout protection, validation
- **Application layer**: Rate limiting, access control, path traversal protection
- **Content layer**: MIME type validation, input sanitization

If one layer is bypassed, others remain to prevent compromise. For example, even if an attacker bypasses rate limiting, they still face path traversal protection and request validation.

### 2. Secure by Default

Security features are enabled by default with conservative settings:

- TLS 1.2+ is **mandatory** - there is no plaintext fallback
- Certificate validation is enabled in clients
- Request size and timeout limits are enforced automatically
- Path canonicalization prevents directory traversal

Users must explicitly opt out of security features, not opt in. This protects inexperienced operators from accidental misconfiguration.

### 3. Privacy-Preserving

Nauyaca minimizes data collection and exposure:

- Client IP addresses can be hashed in logs
- Minimal logging by default (errors only, not all requests)
- No tracking cookies or persistent identifiers
- TOFU model requires no third-party trust relationships

The Gemini protocol itself is privacy-focused (no cookies, no JavaScript, no third-party resources), and nauyaca maintains that philosophy in its implementation.

## TLS Requirements

### Why TLS 1.2+ Minimum?

The Gemini specification **requires** TLS for all connections. Nauyaca enforces TLS 1.2 as the minimum version because:

1. **TLS 1.0 and 1.1 are deprecated**: Both protocols have known vulnerabilities (BEAST, POODLE) and were officially deprecated by the IETF in March 2021.

2. **Modern cipher suites**: TLS 1.2 supports modern authenticated encryption modes (AES-GCM, ChaCha20-Poly1305) that provide both confidentiality and integrity.

3. **Widespread support**: TLS 1.2 was released in 2008 and is supported by all modern operating systems and libraries.

4. **Future-proofing**: While TLS 1.3 is preferred when available, requiring it would limit compatibility. TLS 1.2 provides a secure baseline.

### No Plaintext Fallback

Unlike HTTP (which can fall back to unencrypted connections), Gemini has **no plaintext mode**. This design decision provides several benefits:

- **No downgrade attacks**: Attackers cannot force connections to use weaker security
- **Simple implementation**: No protocol negotiation complexity
- **Clear security guarantees**: Users know all Gemini connections are encrypted

If TLS cannot be established, the connection simply fails. This is by design.

### Certificate Requirements

Server operators have two options:

1. **Self-signed certificates**: Most Gemini servers use self-signed certificates, relying on TOFU for trust
2. **CA-signed certificates**: Traditional certificates work but provide no additional benefit in the TOFU model

Client certificates are optional and used for authentication when servers require them (status codes 60-62).

## TOFU vs CA-based PKI

### What is TOFU?

**Trust On First Use (TOFU)** is an alternative to traditional Certificate Authority (CA) based Public Key Infrastructure. The algorithm is simple:

1. **First connection**: Accept the server's certificate and store its fingerprint (SHA-256 hash)
2. **Subsequent connections**: Verify the certificate matches the stored fingerprint
3. **Certificate change**: Prompt the user for confirmation

This is similar to how SSH handles host keys.

### Advantages Over the CA Model

The CA model has several fundamental problems that TOFU addresses:

**1. No Single Point of Failure**

In the CA model, compromise of any trusted CA allows an attacker to issue valid certificates for any domain. This has happened repeatedly:

- DigiNotar (2011): Issued fraudulent certificates for Google, CIA, Mossad
- Comodo (2011): Issued certificates for major web properties
- Let's Encrypt (multiple incidents): Certificate misissuance

With TOFU, there is **no trusted third party** to compromise. Each user maintains their own trust relationships.

**2. Simpler Trust Model**

The CA model requires:
- Trusting hundreds of CAs worldwide
- Certificate revocation lists (CRL) or OCSP for revocation checking
- Complex certificate chain validation
- Understanding of intermediate certificates, cross-signing, etc.

TOFU requires:
- Storing a single fingerprint per host
- Comparing the current certificate to the stored fingerprint

**3. No Costs or Barriers**

CA certificates require:
- Payment (for most CAs) or proof of domain ownership (Let's Encrypt)
- Regular renewal processes
- Dealing with certificate expiration
- Understanding complex certificate request formats

Self-signed certificates with TOFU require:
- One command to generate a certificate
- No external dependencies or services
- No expiration concerns (can use long-lived certificates)

**4. Privacy Benefits**

The CA model requires:
- Contacting OCSP responders to check revocation (leaks browsing patterns)
- Trusting CAs not to log certificate issuance/validation

TOFU requires:
- No external communication (all validation is local)
- No third parties involved in trust decisions

### Trade-offs and Limitations

TOFU is not perfect. It has important limitations:

**1. No Protection on First Use**

On the **first connection** to a server, TOFU provides no security. An attacker with a man-in-the-middle position can present their own certificate, which the client will trust.

Mitigation strategies:
- Verify fingerprints through a secondary channel (phone, email, in person)
- Use first connections only on trusted networks
- Share known_hosts databases from trusted sources

**2. No Revocation Mechanism**

If a server's private key is compromised, there's no way to notify clients. The server operator must:
- Generate a new certificate
- Announce the change through out-of-band channels
- Wait for users to accept the new certificate

This is less automated than CRL/OCSP but arguably more secure (no reliance on third parties).

**3. Certificate Change Ambiguity**

When a certificate changes, the client cannot distinguish between:
- Legitimate certificate renewal
- Server migration or upgrade
- Man-in-the-middle attack

Users must make trust decisions with limited information. This requires:
- Server operators to announce certificate changes
- Users to be vigilant about unexpected changes
- Trust relationships with server operators

### TOFU Workflow in Nauyaca

Nauyaca implements TOFU with a SQLite database (`~/.nauyaca/known_hosts.db`):

```
First connection to gemini://example.com:
1. Receive certificate
2. Display fingerprint to user
3. Prompt: "Trust this certificate?"
4. If yes: Store (hostname, port, fingerprint, timestamp)
5. Connect

Subsequent connections:
1. Receive certificate
2. Compute SHA-256 fingerprint
3. Query database for (hostname, port)
4. If fingerprint matches: Connect
5. If fingerprint differs: Prompt user

Certificate change prompt:
"Certificate for example.com has changed!
Old fingerprint: abc123...
New fingerprint: def456...
Last seen: 2025-01-15

This could be a legitimate renewal or a MITM attack.
Verify with server operator before proceeding.

Accept new certificate? [y/N]"
```

Users can manage trust manually:

```bash
# List all trusted hosts
nauyaca tofu list

# Manually trust a host (after verifying fingerprint)
nauyaca tofu trust example.com --fingerprint <sha256>

# Revoke trust (after learning of compromise)
nauyaca tofu revoke example.com

# Export for backup
nauyaca tofu export backup.json

# Import on new device
nauyaca tofu import backup.json
```

## Rate Limiting Design

### Token Bucket Algorithm

Nauyaca uses the **token bucket** algorithm for rate limiting, which provides:

1. **Burst tolerance**: Clients can make several quick requests (up to capacity)
2. **Sustained rate control**: Tokens refill at a steady rate
3. **Simplicity**: Easy to understand and implement correctly

How it works:

```
Each client IP has a bucket with:
- capacity: Maximum number of tokens (e.g., 10)
- tokens: Current number of tokens (starts at capacity)
- refill_rate: Tokens added per second (e.g., 1.0)

On each request:
1. Refill bucket: tokens += (time_since_last * refill_rate)
2. tokens = min(tokens, capacity)
3. If tokens >= 1:
   - tokens -= 1
   - Allow request
4. Else:
   - Reject with status 44 SLOW DOWN
   - Include retry_after in response
```

This allows a client to make 10 quick requests in a row, then at most 1 request per second thereafter.

### Per-IP Tracking

Rate limits are tracked **per client IP address**. This provides:

- **Fair resource allocation**: Heavy users don't slow down others
- **DoS mitigation**: Attackers cannot exhaust server capacity
- **Simple implementation**: No authentication required

Limitations:
- **NAT/proxy issues**: Multiple users behind the same IP share limits
- **IP rotation**: Attackers with multiple IPs can bypass limits
- **Memory usage**: Each unique IP requires state

To mitigate memory concerns, nauyaca automatically cleans up rate limiters for IPs that haven't connected in 5 minutes.

### DoS Mitigation Strategy

Rate limiting is one layer of DoS protection. Nauyaca combines multiple strategies:

1. **Rate limiting**: Limits request volume per IP
2. **Request size limits**: Maximum 1024 bytes prevents large payloads
3. **Timeout protection**: 30-second limit prevents slow-loris attacks
4. **Connection limits**: Operating system limits concurrent connections
5. **Access control**: IP allow/deny lists block known attackers

For serious DoS attacks, operators should also:
- Use a reverse proxy (like nginx) for additional buffering
- Implement OS-level connection limits (iptables, nftables)
- Consider CDN or DDoS mitigation services
- Monitor for attack patterns and update deny lists

## Access Control Layers

Nauyaca implements multiple access control mechanisms:

### 1. IP-based Filtering

The most basic layer, processed **before** any request handling:

```toml
[access_control]
allow_list = ["192.168.1.0/24"]  # Local network only
deny_list = ["203.0.113.0/24"]   # Known bad actors
default_allow = false             # Whitelist mode
```

Processing order:
1. Check deny list → reject if match
2. Check allow list → accept if match
3. Apply default policy

This runs before TLS handshake completes, minimizing resource usage for blocked IPs.

### 2. Certificate-based Authentication

The server can request client certificates for specific paths:

```python
# Require client certificate for /private/*
if request.path.startswith('/private'):
    if not client_cert:
        return Response(60, "Certificate required")
    if not verify_cert(client_cert):
        return Response(61, "Certificate not authorized")
```

This provides **identity-based** access control. Users present certificates to prove who they are.

### 3. Path-based Authorization

Even authenticated users may not access all resources:

```python
# Admin users only
if request.path.startswith('/admin'):
    if not is_admin(client_cert):
        return Response(61, "Admin privileges required")

# Owner-only access
if request.path.startswith('/user/alice'):
    if cert_owner(client_cert) != 'alice':
        return Response(61, "Not authorized")
```

This provides **fine-grained** access control based on resource paths.

### Defense in Depth Example

All three layers work together:

```
Request: gemini://example.com/admin/users

1. IP-based: Is IP in allow list? → Yes, continue
2. Rate limiting: Has IP exceeded limits? → No, continue
3. Certificate check: Does user have valid cert? → Yes, continue
4. Path authorization: Is user an admin? → No, reject with 61
```

An attacker must bypass **all layers** to access protected resources.

## Privacy Features

### IP Address Hashing

Logs can contain hashed IPs instead of raw addresses:

```python
# Configuration
log_ip_addresses = "hash"  # Options: full, hash, none

# Result
[2025-01-29] a8f7e2... requested /index.gmi
# Instead of:
[2025-01-29] 203.0.113.42 requested /index.gmi
```

Benefits:
- Audit trails for abuse detection
- Cannot identify individuals from logs
- Compliant with privacy regulations (GDPR, etc.)

### Minimal Logging

Default logging level is **ERROR** (not INFO):

- No logs of successful requests
- Only errors and security events are logged
- Reduces disk usage and information leakage

Operators can enable verbose logging if needed, but must opt in.

### No Tracking

The Gemini protocol itself has no:
- Cookies
- Sessions
- JavaScript
- Third-party resources
- Referrer headers

Nauyaca maintains this philosophy:
- No session identifiers
- No persistent tracking across requests
- No analytics or telemetry

## Known Limitations

Nauyaca's security model has important limitations users should understand:

### What Nauyaca DOES Protect Against

✅ **Path traversal attacks**: File access outside document root
✅ **Request smuggling**: Strict protocol validation
✅ **Slowloris attacks**: Request timeout protection
✅ **Basic DoS**: Rate limiting per IP
✅ **MITM attacks on known hosts**: TOFU validation
✅ **Unauthorized access**: Certificate and IP-based access control

### What Nauyaca DOES NOT Protect Against

❌ **MITM on first connection**: TOFU trusts first certificate
❌ **Distributed DoS (DDoS)**: IP-based rate limiting easily bypassed
❌ **Network-level attacks**: SYN floods, amplification attacks
❌ **Physical access attacks**: If attacker has server access, game over
❌ **Compromised client certificates**: No revocation mechanism
❌ **Social engineering**: Tricking users into accepting bad certificates

### Network-level Attacks

Nauyaca operates at the **application layer**. It cannot protect against:

- **SYN flood**: TCP handshake exhaustion → use iptables/nftables
- **UDP amplification**: Reflection attacks → firewall configuration
- **BGP hijacking**: Network routing attacks → provider-level mitigation
- **Bandwidth exhaustion**: Overwhelming network capacity → DDoS mitigation service

### Recommendations for Production

For production deployments, supplement nauyaca with:

1. **Reverse proxy**: nginx or HAProxy for connection buffering
2. **Firewall**: iptables/nftables for SYN flood protection
3. **DDoS mitigation**: Cloudflare, Fastly, or similar service
4. **Monitoring**: Prometheus, Grafana for attack detection
5. **Backup**: Regular TOFU database and config backups
6. **Updates**: Keep nauyaca and dependencies current

Consider your threat model:
- **Personal capsule**: Built-in security is usually sufficient
- **Public server**: Add reverse proxy and monitoring
- **High-profile target**: Use professional DDoS mitigation

## See Also

- [SECURITY.md](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md) - Complete security documentation with configuration examples
- [Server Configuration How-to](../how-to/configure-server.md) - Practical configuration guide
- [Rate Limiting How-to](../how-to/rate-limiting.md) - Rate limiting setup and tuning
- [TOFU Management How-to](../how-to/setup-tofu.md) - Client trust management

---

*For security vulnerability reports, see [SECURITY.md](https://github.com/alanbato/nauyaca/blob/main/SECURITY.md#reporting-security-vulnerabilities).*
