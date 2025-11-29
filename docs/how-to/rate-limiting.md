# Configure Rate Limiting

This guide shows you how to configure Nauyaca's rate limiting feature to protect your Gemini server from denial-of-service (DoS) attacks and abusive clients.

## Prerequisites

- Nauyaca installed (see [Installation](../installation.md))
- A TOML configuration file (or ready to create one)
- Basic understanding of request rates and burst traffic

## Understanding Rate Limiting

Nauyaca uses the **token bucket algorithm** for rate limiting:

- **Capacity**: Maximum burst size (number of requests allowed in rapid succession)
- **Refill Rate**: Sustained request rate (tokens added per second)
- **Retry-After**: How long clients should wait when rate limited

When a client exceeds the rate limit, Nauyaca responds with status **44 SLOW DOWN** and includes the retry-after duration in the response.

## Enable Rate Limiting

Add the `[rate_limit]` section to your configuration file:

```toml
[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.0
retry_after = 30
```

This enables basic protection with default values:
- Allows bursts of up to 10 requests
- Permits 1 sustained request per second
- Asks rate-limited clients to wait 30 seconds

## Configure Token Bucket Parameters

### Capacity (Burst Size)

The **capacity** controls how many requests can be made in rapid succession:

```toml
[rate_limit]
capacity = 20  # Allow bursts of 20 requests
```

**When to increase:**
- Users frequently navigate multiple pages quickly
- Your server handles media-rich content with many subresources
- Legitimate client tools make rapid sequential requests

**When to decrease:**
- You have limited server resources
- You're experiencing abuse from scrapers
- Your content is primarily text-based with infrequent navigation

### Refill Rate (Sustained Request Rate)

The **refill_rate** determines the sustained request rate in tokens per second:

```toml
[rate_limit]
refill_rate = 2.0  # 2 requests per second sustained
```

Common settings:
- `0.5` = 1 request every 2 seconds (very strict)
- `1.0` = 1 request per second (default, reasonable)
- `2.0` = 2 requests per second (generous)
- `5.0` = 5 requests per second (very permissive)

**Formula:** After exhausting burst capacity, clients can make **refill_rate × seconds** additional requests.

### Retry-After (Client Wait Time)

The **retry_after** value tells rate-limited clients how long to wait:

```toml
[rate_limit]
retry_after = 60  # Wait 60 seconds
```

This appears in the response: `44 Rate limit exceeded. Retry after 60 seconds`

**Guidelines:**
- **15-30 seconds**: For suspected legitimate traffic spikes
- **30-60 seconds**: Default/balanced approach
- **60-300 seconds**: For detected abuse or scraping

## Choose Settings for Your Use Case

### Personal Capsule (Generous Limits)

For a personal capsule with trusted visitors:

```toml
[rate_limit]
enabled = true
capacity = 20        # Allow navigation bursts
refill_rate = 2.0    # 2 requests/second sustained
retry_after = 15     # Short wait time
```

### Public Server (Balanced Protection)

For a public server with moderate traffic:

```toml
[rate_limit]
enabled = true
capacity = 10        # Standard burst allowance
refill_rate = 1.0    # 1 request/second sustained
retry_after = 30     # Standard wait time
```

### High-Traffic Server (Strict Protection)

For high-traffic servers or those under attack:

```toml
[rate_limit]
enabled = true
capacity = 5         # Small bursts only
refill_rate = 0.5    # 1 request every 2 seconds
retry_after = 60     # Longer penalty
```

### Development/Testing (Disabled)

For local development where rate limiting would be annoying:

```toml
[rate_limit]
enabled = false
```

## Test Rate Limiting

### Verify Rate Limiting is Active

Make rapid requests to your server to trigger the rate limit:

```bash
# Make 15 rapid requests (exceeds default capacity of 10)
for i in {1..15}; do
    echo "Request $i:"
    echo "gemini://localhost/" | openssl s_client -connect localhost:1965 \
        -quiet -crlf 2>/dev/null | head -1
    echo ""
done
```

**Expected output:**
```
Request 1:
20 text/gemini

Request 2:
20 text/gemini

...

Request 11:
44 Rate limit exceeded. Retry after 30 seconds

Request 12:
44 Rate limit exceeded. Retry after 30 seconds
```

### Test Retry-After Behavior

Verify that waiting allows requests to succeed again:

```bash
# Trigger rate limit
for i in {1..15}; do
    echo "gemini://localhost/" | openssl s_client -connect localhost:1965 \
        -quiet -crlf 2>/dev/null | head -1
done

# Wait for retry period
echo "Waiting 30 seconds..."
sleep 30

# Try again - should succeed
echo "After waiting:"
echo "gemini://localhost/" | openssl s_client -connect localhost:1965 \
    -quiet -crlf 2>/dev/null | head -1
```

### Test with Nauyaca Client

Using the Nauyaca command-line client:

```bash
# Make rapid requests
for i in {1..15}; do
    nauyaca get gemini://localhost/
done
```

## Handle Rate Limited Responses (Client-Side)

If you're building a Gemini client or automated tool, properly handle status 44 responses:

### Detect Status 44

Check for the SLOW DOWN status code:

```python
from nauyaca.client import GeminiClient

async with GeminiClient() as client:
    response = await client.get('gemini://example.com/')

    if response.status == 44:
        print(f"Rate limited: {response.meta}")
        # Handle rate limit...
```

### Parse Retry-After

Extract the retry duration from the response:

```python
import re

def parse_retry_after(meta: str) -> int:
    """Extract retry-after seconds from status 44 meta.

    Returns:
        Seconds to wait, or 30 as default.
    """
    # Meta format: "Rate limit exceeded. Retry after 30 seconds"
    match = re.search(r'Retry after (\d+) seconds', meta)
    if match:
        return int(match.group(1))
    return 30  # Default fallback
```

### Implement Exponential Backoff

For robust clients, implement exponential backoff:

```python
import asyncio
from nauyaca.client import GeminiClient

async def fetch_with_backoff(url: str, max_retries: int = 3):
    """Fetch URL with exponential backoff on rate limits."""
    client = GeminiClient()

    for attempt in range(max_retries):
        response = await client.get(url)

        if response.status == 44:
            # Parse retry-after or use exponential backoff
            wait_time = parse_retry_after(response.meta)
            # Add exponential component
            wait_time *= (2 ** attempt)

            print(f"Rate limited, waiting {wait_time}s...")
            await asyncio.sleep(wait_time)
            continue

        return response

    raise Exception(f"Failed after {max_retries} retries")
```

### Respect Server Limits

**Good client practices:**

- Always parse and respect `retry_after` values
- Don't immediately retry after receiving status 44
- Implement delays between requests (e.g., 1 second minimum)
- Log rate limit events for debugging
- Consider caching responses to reduce requests

**Bad practices to avoid:**

- Ignoring status 44 and immediately retrying
- Using aggressive retry loops without backoff
- Making parallel requests that bypass per-IP limits
- Treating 44 as a transient error without delays

## Monitor Rate Limiting

### Enable Logging

Configure logging to track rate limit events:

```toml
[logging]
hash_ips = true  # Privacy-preserving IP logging
```

Run your server with verbose logging:

```bash
nauyaca serve --config config.toml --verbose
```

### Check Server Logs

Rate limit events appear in logs:

```
INFO: Client 192.168.1.100 rate limited (bucket exhausted)
INFO: Rate limit: capacity=10, refill=1.0, retry_after=30s
```

### Identify Abusive Clients

Look for patterns in rate-limited IPs:

```bash
# Count rate limit events by IP
grep "rate limited" server.log | cut -d' ' -f3 | sort | uniq -c | sort -nr
```

If you identify persistent abusers, use [access control](access-control.md) to block them:

```toml
[access_control]
deny_list = ["203.0.113.42"]  # Block abusive IP
```

## Troubleshooting

### Legitimate Users Getting Rate Limited

**Symptoms:** Regular users report seeing status 44 errors.

**Solutions:**
1. Increase `capacity` to allow larger bursts
2. Increase `refill_rate` for higher sustained rates
3. Reduce `retry_after` for shorter penalties
4. Check for misconfigured client tools making excessive requests

### Rate Limiting Not Working

**Symptoms:** Abusive clients continue making unlimited requests.

**Check:**
1. Verify `enabled = true` in configuration
2. Confirm server restarted after config changes
3. Check logs for rate limiter initialization messages
4. Test with rapid requests from known IP

### Server Performance Issues

**Symptoms:** High CPU/memory usage even with rate limiting.

**Considerations:**
- Rate limiting is per-IP; distributed attacks bypass it
- Consider using [access control](access-control.md) to block networks
- For advanced protection, consider:
  - Reverse proxy with additional rate limiting
  - Firewall-level rate limiting (iptables, nftables)
  - Connection-level limits in the OS

## See Also

- [Access Control](access-control.md) - Block abusive IPs completely
- [Server Configuration Reference](../reference/configuration.md) - All configuration options
- [Security Best Practices](../reference/api/security.md) - Comprehensive security guide
- [Server API Reference](../reference/api/server.md) - RateLimiter class documentation
