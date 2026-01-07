# Nauyaca Gemini Server Dockerfile
# Multi-stage build for smaller image size

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Copy project files (include lock file for reproducibility if present)
COPY pyproject.toml uv.lock* ./
COPY src/ src/

# Build wheel
RUN uv build --wheel

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# Create non-root user for security
RUN groupadd -r gemini && useradd -r -g gemini gemini

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for package installation (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /usr/local/bin/uv

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install nauyaca
RUN uv pip install --system /tmp/*.whl && rm /tmp/*.whl

# Create directories for volumes
RUN mkdir -p /capsule /certs /config && \
    chown -R gemini:gemini /capsule /certs /config

# Switch to non-root user
USER gemini

# Set working directory
WORKDIR /capsule

# Default environment variables
ENV NAUYACA_HOST=0.0.0.0 \
    NAUYACA_PORT=1965 \
    NAUYACA_DOCUMENT_ROOT=/capsule

# Expose Gemini port
EXPOSE 1965

# Health check - verify TLS handshake succeeds
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import socket,ssl; ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; s=ctx.wrap_socket(socket.socket(),server_hostname='localhost'); s.settimeout(5); s.connect(('localhost',1965)); s.close()" || exit 1

# Default command
ENTRYPOINT ["nauyaca", "serve"]
CMD ["--config", "/config/config.toml"]
