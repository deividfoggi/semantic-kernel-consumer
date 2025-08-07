# Single-stage build for semantic-kernel-consumer
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SHUTDOWN_TIMEOUT=30

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security with explicit UID/GID to match K8s security context
RUN groupadd -g 1000 appuser && useradd -u 1000 -g 1000 -s /bin/bash appuser

# Create application directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy application code (excluding cache files)
COPY --chown=1000:1000 . .

# Remove any Python cache files that might have been copied and ensure clean state
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app -name "*.pyc" -delete 2>/dev/null || true && \
    find /app -name "*.pyo" -delete 2>/dev/null || true

# Create directories for temporary files and logs
RUN mkdir -p /app/logs /app/tmp && \
    chown -R 1000:1000 /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port (if needed for monitoring endpoints)
EXPOSE 8080

# Default command
CMD ["python", "main.py"]