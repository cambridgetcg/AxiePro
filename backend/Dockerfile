# Axie Ronin Explorer Backend
# Multi-stage build for smaller image size

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install AWS SDK for Secrets Manager
RUN pip install --no-cache-dir boto3

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (needed for cryptography, psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check (disabled - let App Runner handle it)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run application with startup logging
CMD ["sh", "-c", "echo '=== Starting AxiePro API ===' && echo 'Python version:' && python --version && echo 'Checking imports...' && python -c 'print(\"Testing basic import...\"); from src.main import app; print(\"App imported successfully!\")' && echo 'Starting uvicorn...' && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level warning --no-access-log"]
