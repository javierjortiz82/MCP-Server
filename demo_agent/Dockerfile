
# Demo Agent Dockerfile
# Multi-stage build for minimal image size

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /tmp/build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (PostgreSQL client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder (system site-packages)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code into demo_agent subdirectory
COPY . /app/demo_agent/

# Set working directory and Python path
WORKDIR /app
ENV PYTHONPATH=/app:/app/agent/src:$PYTHONPATH

# Create logs directories and set permissions
RUN mkdir -p /app/demo_agent/logs /app/client_mcp/logs && \
    chmod -R 755 /app

# Non-root user for security
RUN useradd -m -u 1000 demouser && \
    chown -R demouser:demouser /app
USER demouser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8082/health || exit 1

# Expose port
EXPOSE 8082

# Run application using Python module
CMD ["python", "-m", "demo_agent"]
