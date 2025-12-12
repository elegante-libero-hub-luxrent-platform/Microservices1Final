# Dockerfile for User & Profile Service (MS1)
# Optimized for Google Cloud Run deployment
# Multi-stage build for minimal image size

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies to a local directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (minimal)
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies (no dev tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Create non-root user for security (required by Cloud Run)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set PATH to use local Python packages
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Expose port (Cloud Run uses PORT env var by default)
EXPOSE 8000

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
# Note: Cloud Run automatically sets PORT env var, use it if available
CMD exec uvicorn main_db:app --host 0.0.0.0 --port ${PORT:-8000}
