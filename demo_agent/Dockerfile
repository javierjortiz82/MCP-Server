# Demo Agent Dockerfile
# Build from project root: docker build -f demo_agent/Dockerfile -t demo-agent .
# Multi-stage build for minimal image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /tmp/build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY demo_agent/requirements.txt .
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

# Copy demo_agent application code
COPY demo_agent /app/demo_agent/

# Copy dependencies (agent, client_mcp, prompts, mcp_server)
# These are required for prompt_manager and related modules
COPY agent /app/agent
COPY client_mcp /app/client_mcp
COPY prompts /app/prompts
COPY mcp_server /app/mcp_server

# Set working directory and Python path
# NOTE: agent/src contains both gemini_agent and multi_agent modules
WORKDIR /app
ENV PYTHONPATH=/app:/app/agent/src:/app/client_mcp:/app/mcp_server

# Create logs directories and set permissions
RUN mkdir -p /app/demo_agent/logs /app/client_mcp/logs /app/agent/logs && \
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
