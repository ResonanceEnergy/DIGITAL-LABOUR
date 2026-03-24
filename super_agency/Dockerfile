FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Final stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Resonance Energy <dev@resonanceenergy.com>"
LABEL description="Bit Rage Systems runtime — Digital Labour agents, orchestrator, dashboards"

WORKDIR /app

# System deps (git for repo operations, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

# Copy application
COPY . .

# Create non-root user
RUN groupadd -r agency && useradd -r -g agency -d /app agency

# Create runtime directories and set ownership
RUN mkdir -p logs reports/daily state/matrix_maximizer \
    knowledge/secondbrain council_meetings/proposals memory_backups memory \
    && chown -R agency:agency /app

USER agency

# Expose service ports
EXPOSE 8080 8081 5001

# Health check — probe the OpsAPI
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:5001/health || exit 1

# Default entrypoint
ENTRYPOINT ["python", "start.py"]
