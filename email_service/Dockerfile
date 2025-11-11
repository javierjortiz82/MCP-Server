# ============================================================================
# Email Service Dockerfile - Production-ready email worker
# ============================================================================
# Lightweight Python 3.11 Alpine image for email queue processor
#
# Features:
#   - Multi-stage build for smaller image size
#   - Non-root user for security
#   - Health check endpoint
#   - Optimized layer caching
#
# Usage:
#   docker build -t lab01-email-service:latest .
#   docker run --env-file .env lab01-email-service:latest
#
# Author: Lab01-MCP Team
# Version: 1.0.0
# ============================================================================

FROM python:3.11-slim AS base

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r emailworker && \
    useradd -r -g emailworker -u 1001 emailworker

# Set working directory
WORKDIR /app

# ============================================================================
# Dependencies stage - Install Python packages
# ============================================================================
FROM base AS dependencies

# Copy requirements first (better caching)
COPY requirements.txt ./

# Install dependencies (only external packages, not the email_service package itself)
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Production stage - Copy application code
# ============================================================================
FROM base AS production

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code - the parent directory becomes the Python path
# This ensures that 'email_service' package is importable
COPY --chown=emailworker:emailworker . /app/email_service/

# Create logs directory and set permissions
RUN mkdir -p /app/logs && \
    chown -R emailworker:emailworker /app

# Set PYTHONPATH so email_service module can be found
ENV PYTHONPATH=/app

# Switch to non-root user
USER emailworker

# Health check - verify the email_service package can be imported
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from email_service.config.settings import EmailConfig; print('healthy')" || exit 1

# Expose port (optional - for future metrics endpoint)
EXPOSE 8080

# Run email worker
CMD ["python", "-m", "email_service.worker"]
