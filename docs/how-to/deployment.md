# Deploy Nauyaca

This guide covers deploying Nauyaca in production environments using Docker or systemd.

## Prerequisites

- Nauyaca installed (see [Installation](../installation.md))
- TLS certificate and private key for your domain
- A directory with your Gemini content (capsule)

## Environment Variables

Nauyaca supports configuration via environment variables, which is ideal for containerized deployments. Environment variables take highest priority, overriding both CLI arguments and config file settings.

### Supported Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NAUYACA_HOST` | Server bind address | `0.0.0.0` |
| `NAUYACA_PORT` | Server port | `1965` |
| `NAUYACA_DOCUMENT_ROOT` | Path to capsule content | `/var/gemini/capsule` |
| `NAUYACA_CERTFILE` | Path to TLS certificate | `/etc/nauyaca/cert.pem` |
| `NAUYACA_KEYFILE` | Path to TLS private key | `/etc/nauyaca/key.pem` |

### Priority Order

Configuration is resolved in this order (highest priority first):

1. **Environment variables** (`NAUYACA_*`)
2. **CLI arguments** (`--host`, `--port`, etc.)
3. **Config file** (`config.toml`)
4. **Defaults**

## Docker Deployment

### Quick Start

1. Create your capsule directory:

```bash
mkdir -p capsule
echo "# Welcome to my Gemini capsule!" > capsule/index.gmi
```

2. Build and run with Docker Compose:

```bash
docker compose up -d
```

Your server is now running at `gemini://localhost:1965/`.

### Build the Image

```bash
docker build -t nauyaca:latest .
```

### Run with Docker

**Minimal (auto-generated certificate for testing):**

```bash
docker run -d \
  --name nauyaca \
  -p 1965:1965 \
  -v ./capsule:/capsule:ro \
  nauyaca:latest /capsule
```

**Production (with TLS certificates):**

```bash
docker run -d \
  --name nauyaca \
  -p 1965:1965 \
  -v ./capsule:/capsule:ro \
  -v ./certs:/certs:ro \
  -e NAUYACA_CERTFILE=/certs/cert.pem \
  -e NAUYACA_KEYFILE=/certs/key.pem \
  nauyaca:latest /capsule
```

**With config file:**

```bash
docker run -d \
  --name nauyaca \
  -p 1965:1965 \
  -v ./capsule:/capsule:ro \
  -v ./certs:/certs:ro \
  -v ./config.toml:/config/config.toml:ro \
  nauyaca:latest
```

### Docker Compose

The included `docker-compose.yml` provides a production-ready configuration:

```yaml
services:
  nauyaca:
    build: .
    ports:
      - "1965:1965"
    volumes:
      - ./capsule:/capsule:ro
      - ./certs:/certs:ro
      - ./config.toml:/config/config.toml:ro
    environment:
      NAUYACA_HOST: "0.0.0.0"
      NAUYACA_PORT: "1965"
    restart: unless-stopped
```

### Security Recommendations

The Docker image includes several security features:

- **Non-root user**: Runs as `gemini` user (UID 1000)
- **Read-only filesystem**: Use `read_only: true` in compose
- **Resource limits**: Configure CPU and memory limits
- **No new privileges**: Prevents privilege escalation

Example with all security options:

```yaml
services:
  nauyaca:
    build: .
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 128M
    tmpfs:
      - /tmp:size=10M,mode=1777
```

## Systemd Deployment

### Installation

1. Install Nauyaca system-wide:

```bash
sudo pip install nauyaca
# or with uv:
sudo uv tool install nauyaca
```

2. Create the gemini user:

```bash
sudo useradd -r -s /bin/false gemini
```

3. Set up directories:

```bash
sudo mkdir -p /var/gemini/capsule /etc/nauyaca
sudo chown -R gemini:gemini /var/gemini
sudo chmod 750 /var/gemini /var/gemini/capsule
```

4. Create configuration file:

```bash
sudo cp config.example.toml /etc/nauyaca/config.toml
sudo chown gemini:gemini /etc/nauyaca/config.toml
sudo chmod 640 /etc/nauyaca/config.toml
```

5. Edit `/etc/nauyaca/config.toml`:

```toml
[server]
host = "0.0.0.0"
port = 1965
document_root = "/var/gemini/capsule"
certfile = "/etc/nauyaca/cert.pem"
keyfile = "/etc/nauyaca/key.pem"
```

6. Install the service file:

```bash
sudo cp contrib/nauyaca.service /etc/systemd/system/
sudo systemctl daemon-reload
```

7. Enable and start:

```bash
sudo systemctl enable --now nauyaca
```

### Managing the Service

```bash
# Check status
sudo systemctl status nauyaca

# View logs
sudo journalctl -u nauyaca -f

# Restart after config changes
sudo systemctl restart nauyaca

# Stop the server
sudo systemctl stop nauyaca
```

### Using Environment Variables

Edit the service file to add environment variables:

```bash
sudo systemctl edit nauyaca
```

Add overrides:

```ini
[Service]
Environment=NAUYACA_HOST=0.0.0.0
Environment=NAUYACA_PORT=1965
```

### Security Hardening

The provided service file includes comprehensive security hardening:

- **NoNewPrivileges**: Prevents privilege escalation
- **ProtectSystem=strict**: Read-only system directories
- **PrivateTmp**: Isolated /tmp directory
- **RestrictAddressFamilies**: Only IPv4/IPv6 allowed
- **MemoryDenyWriteExecute**: Prevents code injection

## Generate TLS Certificates

### Using Nauyaca

Generate a self-signed certificate for testing:

```bash
nauyaca cert generate myserver --output-dir ./certs
```

### Using OpenSSL

For production, generate a proper certificate:

```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem -out cert.pem \
  -days 365 -nodes \
  -subj "/CN=example.com"
```

### Using Let's Encrypt (via Certbot)

For publicly accessible servers:

```bash
# Install certbot
sudo apt install certbot

# Get certificate (HTTP challenge)
sudo certbot certonly --standalone -d gemini.example.com

# Link certificates
sudo ln -s /etc/letsencrypt/live/gemini.example.com/fullchain.pem /etc/nauyaca/cert.pem
sudo ln -s /etc/letsencrypt/live/gemini.example.com/privkey.pem /etc/nauyaca/key.pem
```

## Troubleshooting

### Container Won't Start

**Symptoms**: Container exits immediately.

**Check logs:**

```bash
docker logs nauyaca
```

**Common causes:**

1. Missing document root directory
2. Invalid certificate paths
3. Port already in use

### Permission Denied Errors

**Symptoms**: "Permission denied" when accessing files.

**Solution**: Ensure volume permissions match container user (UID 1000):

```bash
sudo chown -R 1000:1000 ./capsule ./certs
```

### Certificate Errors

**Symptoms**: TLS handshake failures.

**Check:**

1. Certificate and key files exist and are readable
2. Certificate matches your domain
3. Key file permissions (should be 600)

```bash
# Verify certificate
openssl x509 -in cert.pem -text -noout

# Check key matches certificate
openssl x509 -in cert.pem -noout -modulus | openssl md5
openssl rsa -in key.pem -noout -modulus | openssl md5
# (Both should output the same hash)
```

### Port Already in Use

**Symptoms**: "Address already in use" error.

**Solution**: Check what's using port 1965:

```bash
sudo lsof -i :1965
# or
sudo ss -tlnp | grep 1965
```

## See Also

- [Configure Server](configure-server.md) - Configuration file options
- [Manage Certificates](manage-certificates.md) - Certificate management
- [Rate Limiting](rate-limiting.md) - DoS protection
- [Security Best Practices](../explanation/security-model.md) - Security guide
