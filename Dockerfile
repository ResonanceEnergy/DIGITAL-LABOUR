# ── DIGITAL LABOUR — Railway Deployment ──
# Multi-stage build for FastAPI app

# Stage 1: Install dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create data directory for SQLite databases
RUN mkdir -p /app/data

# Copy project files
COPY . .

# Ensure data directory exists and is writable
RUN chmod -R 755 /app/data

# Default port (Railway overrides via $PORT)
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Railway injects $PORT at runtime
CMD uvicorn api.intake:app --host 0.0.0.0 --port ${PORT}
