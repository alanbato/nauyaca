# Logging and Monitoring

This guide shows you how to configure logging and monitoring for your Nauyaca Gemini server.

## Set Log Level

Control the verbosity of server logs by setting the log level. Available levels:

- **DEBUG**: Detailed diagnostic information for troubleshooting
- **INFO**: General informational messages about server operation (default)
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for problems that need attention

### Using CLI

```bash
# Set to DEBUG for troubleshooting
nauyaca serve ./capsule --log-level DEBUG

# Set to WARNING to reduce noise in production
nauyaca serve ./capsule --log-level WARNING
```

### Using Configuration File

```toml
[logging]
level = "INFO"
```

Then start the server with the config file:

```bash
nauyaca serve --config config.toml
```

!!! tip
    Use **DEBUG** during development and troubleshooting, **INFO** for normal operation, and **WARNING** or **ERROR** for production environments where you only want important messages.

## Write Logs to File

By default, logs are written to stdout (console). For production deployments, you should write logs to a file.

### Using CLI

```bash
# Write logs to a file
nauyaca serve ./capsule --log-file /var/log/nauyaca/server.log
```

### Using Configuration File

```toml
[logging]
file = "/var/log/nauyaca/server.log"
```

!!! note "File Permissions"
    Ensure the user running the server has write permissions to the log file directory. Create the log directory first:

    ```bash
    sudo mkdir -p /var/log/nauyaca
    sudo chown $(whoami):$(whoami) /var/log/nauyaca
    ```

!!! warning "Log Rotation"
    Nauyaca does not automatically rotate logs. See [Configure Log Rotation](#configure-log-rotation) below for best practices.

## Enable JSON Logging

JSON-formatted logs are ideal for log aggregation systems like ELK Stack, Splunk, or Grafana Loki.

### Using CLI

```bash
# Enable JSON logging
nauyaca serve ./capsule --log-file server.log --json-logs
```

### Using Configuration File

```toml
[logging]
file = "/var/log/nauyaca/server.log"
json_format = true
```

### JSON Log Format

With JSON logging enabled, each log entry is a single JSON object:

```json
{
  "event": "request_handled",
  "timestamp": "2025-11-29T14:23:45.123456Z",
  "level": "info",
  "client_ip_hash": "a1b2c3d4e5f6",
  "path": "/index.gmi",
  "status": 20,
  "response_time_ms": 12.3
}
```

This structured format makes it easy to:

- Parse and query logs programmatically
- Filter by specific fields (IP, status code, path)
- Aggregate metrics and generate dashboards
- Set up alerts on specific conditions

## Enable IP Hashing

For privacy protection (recommended by Gemini application best practices), hash client IP addresses in logs instead of storing them in plaintext.

### Using CLI

```bash
# IP hashing is enabled by default
nauyaca serve ./capsule

# Disable IP hashing (not recommended)
nauyaca serve ./capsule --no-hash-ips
```

### Using Configuration File

```toml
[logging]
# Hash client IPs (default: true)
hash_ips = true
```

### Why Hash IPs?

**Privacy Compliance**: Hashing IP addresses helps comply with privacy regulations like GDPR while still allowing abuse detection.

With IP hashing:

- Each IP address is converted to a SHA-256 hash (truncated to 12 characters)
- The same IP always produces the same hash
- You can still detect abusive patterns (repeated requests from the same hash)
- You cannot reverse the hash to get the original IP address

**Example log entries:**

```
# With IP hashing (default)
client_ip_hash=a1b2c3d4e5f6 path=/index.gmi status=20

# Without IP hashing (--no-hash-ips)
client_ip=203.0.113.42 path=/index.gmi status=20
```

!!! tip "GDPR Considerations"
    If you operate in jurisdictions with strict privacy laws, keep IP hashing enabled. Hashed IPs are generally not considered personally identifiable information (PII) since they cannot be reversed.

## Configure Log Rotation

Nauyaca does not include built-in log rotation. Use your system's log rotation tool to prevent log files from consuming excessive disk space.

### Using logrotate (Linux)

Create a logrotate configuration file at `/etc/logrotate.d/nauyaca`:

```
/var/log/nauyaca/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nauyaca nauyaca
    sharedscripts
    postrotate
        # No need to send signals - structlog opens files per write
    endscript
}
```

This configuration:

- Rotates logs daily
- Keeps 14 days of logs
- Compresses old logs to save space
- Creates new log files with appropriate permissions
- Doesn't fail if log files are missing
- Skips rotation for empty files

Test the configuration:

```bash
sudo logrotate -d /etc/logrotate.d/nauyaca  # Dry run
sudo logrotate -f /etc/logrotate.d/nauyaca  # Force rotation
```

### Size-based Rotation

To rotate based on file size instead of time:

```
/var/log/nauyaca/*.log {
    size 100M
    rotate 5
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nauyaca nauyaca
}
```

This rotates logs when they reach 100 MB and keeps 5 old log files.

## Monitor for Security Events

Here are important events to monitor in your Nauyaca logs:

### Rate Limit Triggers

Watch for clients hitting rate limits, which may indicate abuse or misconfigured clients:

```bash
# Search for rate limit events
grep "rate_limited" server.log

# JSON logs - use jq for filtering
jq 'select(.event == "rate_limited")' server.log
```

Example log entry:

```json
{
  "event": "rate_limited",
  "client_ip_hash": "a1b2c3d4e5f6",
  "timestamp": "2025-11-29T14:23:45.123456Z",
  "level": "warning"
}
```

### Access Control Denials

Monitor blocked connection attempts:

```bash
# Search for access denials
grep "access_denied" server.log

# JSON logs
jq 'select(.event == "access_denied")' server.log
```

### Certificate Authentication Failures

Track failed client certificate authentication attempts:

```bash
# Search for certificate failures
grep "certificate" server.log | grep -E "(required|invalid|not_authorized)"

# JSON logs
jq 'select(.event | contains("certificate")) | select(.level == "warning" or .level == "error")' server.log
```

### Unusual Request Patterns

Monitor for suspicious activity:

```bash
# Find requests to unusual paths
grep "path=" server.log | grep -E "(\.\./|\.\.\\|/etc/|/proc/)"

# Frequent 59 (BAD REQUEST) responses
jq 'select(.status == 59)' server.log
```

### Error Rates

Track server errors that may indicate problems:

```bash
# Count errors by hour (requires JSON logs)
jq -r '.timestamp[:13] + " " + .level' server.log | \
    grep ERROR | uniq -c

# Find all 5x status codes (permanent failures)
jq 'select(.status >= 50 and .status < 60)' server.log
```

!!! tip "Set Up Alerts"
    Configure your monitoring system to alert on:

    - High rate limit trigger frequency
    - Sudden increase in access denials
    - Multiple certificate failures from the same IP hash
    - High error rates (5x status codes)
    - Unusual request patterns

## Integrate with Log Aggregation

For production deployments, integrate Nauyaca with a log aggregation system.

### Example: Forwarding to Loki/Grafana

1. **Enable JSON logging**:

```toml
[logging]
file = "/var/log/nauyaca/server.log"
json_format = true
```

2. **Install Promtail** (Loki's log shipper):

```bash
# Download and configure Promtail
wget https://github.com/grafana/loki/releases/download/v2.9.0/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
```

3. **Configure Promtail** (`promtail-config.yml`):

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: nauyaca
    static_configs:
      - targets:
          - localhost
        labels:
          job: nauyaca
          __path__: /var/log/nauyaca/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            event: event
            client_ip_hash: client_ip_hash
            status: status
      - labels:
          level:
          event:
```

4. **Run Promtail**:

```bash
./promtail-linux-amd64 -config.file=promtail-config.yml
```

### Example: Forwarding to ELK Stack

1. **Enable JSON logging** (as above)

2. **Install Filebeat**:

```bash
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.11.0-amd64.deb
sudo dpkg -i filebeat-8.11.0-amd64.deb
```

3. **Configure Filebeat** (`/etc/filebeat/filebeat.yml`):

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/nauyaca/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "nauyaca-%{+yyyy.MM.dd}"

setup.template.name: "nauyaca"
setup.template.pattern: "nauyaca-*"
```

4. **Start Filebeat**:

```bash
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

### Benefits of Structured Logging

With JSON logs and aggregation, you can:

- **Create dashboards**: Visualize request rates, status code distribution, response times
- **Set up alerts**: Get notified when error rates spike or rate limits trigger frequently
- **Debug issues**: Quickly filter logs by IP hash, path, status code, or time range
- **Analyze trends**: Identify popular content, peak traffic times, abuse patterns

## Complete Logging Example

Here's a production-ready logging configuration:

### Configuration File (`config.toml`)

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"

[logging]
# Write JSON logs to file for aggregation
file = "/var/log/nauyaca/server.log"
json_format = true

# Hash IPs for privacy compliance
hash_ips = true

# Use INFO level for normal operation
level = "INFO"

[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.0
retry_after = 30
```

### Systemd Service (`/etc/systemd/system/nauyaca.service`)

```ini
[Unit]
Description=Nauyaca Gemini Server
After=network.target

[Service]
Type=simple
User=nauyaca
Group=nauyaca
WorkingDirectory=/var/gemini
ExecStart=/usr/local/bin/nauyaca serve --config /etc/nauyaca/config.toml
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/nauyaca

[Install]
WantedBy=multi-user.target
```

### Log Rotation (`/etc/logrotate.d/nauyaca`)

```
/var/log/nauyaca/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nauyaca nauyaca
}
```

### Start the Service

```bash
# Create log directory
sudo mkdir -p /var/log/nauyaca
sudo chown nauyaca:nauyaca /var/log/nauyaca

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nauyaca
sudo systemctl start nauyaca

# Check logs
sudo journalctl -u nauyaca -f
tail -f /var/log/nauyaca/server.log
```

## See Also

- [Configure Server](configure-server.md) - Server configuration options
- [Security Reference](../reference/api/security.md) - Security features and best practices
- [CLI Reference](../reference/cli.md) - Complete CLI command reference
