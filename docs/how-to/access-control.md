# Configure IP-based Access Control

This guide shows you how to restrict access to your Gemini capsule based on client IP addresses using allow lists (whitelists) and deny lists (blacklists).

## Prerequisites

- A working Nauyaca server installation
- Basic understanding of IP addresses and CIDR notation (explained below)
- Server configuration file (`config.toml`)

## Enable Access Control

Add the `[access_control]` section to your `config.toml`:

```toml
[access_control]
# Default policy when IP is not in any list
default_allow = true
```

The `default_allow` setting determines what happens when a client IP doesn't match any rules:

- `default_allow = true` (default): Allow all connections except those in deny_list
- `default_allow = false`: Deny all connections except those in allow_list

## Create an Allow List (Whitelist)

An allow list restricts access to specific IP addresses or ranges. This is useful for internal-only capsules or private servers.

### Allow specific IPs

```toml
[access_control]
allow_list = ["192.168.1.100", "10.0.0.50"]
default_allow = false
```

This allows only the two specified IP addresses to connect.

### Allow IP ranges with CIDR notation

```toml
[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.0/16"]
default_allow = false
```

This allows:
- Any IP from `192.168.1.0` to `192.168.1.255` (256 addresses)
- Any IP from `10.0.0.0` to `10.0.255.255` (65,536 addresses)

### Use case: Internal-only capsule

For a capsule accessible only from your local network:

```toml
[access_control]
allow_list = ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8"]
default_allow = false
```

This allows:
- Localhost (`127.0.0.1`)
- All private IPv4 addresses in `192.168.x.x` and `10.x.x.x` ranges

## Create a Deny List (Blacklist)

A deny list blocks specific IP addresses while allowing all others. This is useful for blocking known bad actors while keeping your capsule publicly accessible.

### Block specific IPs

```toml
[access_control]
deny_list = ["198.51.100.10", "203.0.113.50"]
default_allow = true
```

### Block IP ranges

```toml
[access_control]
deny_list = ["198.51.100.0/24"]
default_allow = true
```

This blocks all IPs from `198.51.100.0` to `198.51.100.255`.

### Use case: Block scrapers or abusive clients

```toml
[access_control]
deny_list = [
    "198.51.100.0/24",    # Known scraper network
    "203.0.113.45",        # Abusive individual IP
    "192.0.2.0/24"         # Another problematic range
]
default_allow = true
```

## Understand Processing Order

Access control checks IPs in this order:

1. **Deny list first**: If IP matches deny_list, block immediately (returns status 53)
2. **Allow list second**: If allow_list exists and IP matches, allow
3. **Default policy**: If no lists match, use default_allow setting

This means:
- Deny list always takes precedence
- Allow list is only checked if IP is not denied
- Default policy only applies if no rules match

**Example with both lists:**

```toml
[access_control]
allow_list = ["192.168.1.0/24"]
deny_list = ["192.168.1.50"]
default_allow = false
```

Result:
- `192.168.1.50`: Denied (in deny_list, even though in allow_list range)
- `192.168.1.100`: Allowed (in allow_list)
- `10.0.0.1`: Denied (not in allow_list, default_allow = false)

## Use CIDR Notation

CIDR (Classless Inter-Domain Routing) notation specifies IP address ranges using the format `IP/prefix-length`.

### Understanding CIDR

The number after the `/` indicates how many bits are fixed. The remaining bits can vary:

- `/32`: Single IPv4 address (32 bits fixed, 0 bits vary = 1 address)
- `/24`: Class C network (24 bits fixed, 8 bits vary = 256 addresses)
- `/16`: Class B network (16 bits fixed, 16 bits vary = 65,536 addresses)
- `/8`: Class A network (8 bits fixed, 24 bits vary = 16,777,216 addresses)

### Common IPv4 examples

```toml
# Single IP address
"192.168.1.50/32"    # or just "192.168.1.50"

# /24 network (256 addresses)
"192.168.1.0/24"     # 192.168.1.0 - 192.168.1.255

# /16 network (65,536 addresses)
"10.0.0.0/16"        # 10.0.0.0 - 10.0.255.255

# /8 network (16,777,216 addresses)
"10.0.0.0/8"         # 10.0.0.0 - 10.255.255.255

# Localhost range
"127.0.0.0/8"        # 127.0.0.0 - 127.255.255.255
```

### IPv6 support

Nauyaca supports IPv6 addresses and CIDR notation:

```toml
[access_control]
allow_list = [
    "2001:db8::/32",           # IPv6 network
    "::1",                      # IPv6 localhost
    "fe80::/10"                 # IPv6 link-local
]
```

## Test Access Control

After configuring access control, test that it works as expected.

### Test from an allowed IP

1. Start your server:
   ```bash
   nauyaca-server --config config.toml
   ```

2. Connect from an allowed IP:
   ```bash
   nauyaca-client gemini://localhost/
   ```

   Expected result: Normal response (status 20)

### Test from a denied IP

If testing from the same machine, you can temporarily add your own IP to the deny list:

1. Add your IP to deny_list in `config.toml`
2. Restart the server
3. Try to connect:
   ```bash
   nauyaca-client gemini://localhost/
   ```

   Expected result: Status 53 response with "Access denied"

### Verify in logs

Check server logs to see access control decisions:

```
INFO: Connection from 192.168.1.50
INFO: Access denied by access control middleware
```

## Common Patterns

### Localhost only

For development or a personal capsule:

```toml
[access_control]
allow_list = ["127.0.0.1", "::1"]
default_allow = false
```

### LAN only

For a capsule accessible on your local network:

```toml
[access_control]
allow_list = [
    "127.0.0.0/8",      # Localhost
    "192.168.0.0/16",   # Private class C
    "10.0.0.0/8",       # Private class A
    "172.16.0.0/12",    # Private class B
    "::1",              # IPv6 localhost
    "fe80::/10"         # IPv6 link-local
]
default_allow = false
```

### Public with exceptions

Allow everyone except known problem IPs:

```toml
[access_control]
deny_list = [
    "198.51.100.0/24",  # Known scraper
    "203.0.113.45"       # Abusive client
]
default_allow = true
```

### Allowlist with temporary exceptions

Allow a specific network but block one problematic host within it:

```toml
[access_control]
allow_list = ["192.168.1.0/24"]
deny_list = ["192.168.1.100"]    # Deny takes precedence
default_allow = false
```

## See Also

- [Rate Limiting Guide](rate-limiting.md) - Protect against DoS attacks
- [Security Reference](../reference/api/security.md) - Complete security features overview
- [Configuration Reference](../reference/configuration.md) - All configuration options
