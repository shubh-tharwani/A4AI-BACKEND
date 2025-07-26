# Use Python 3.13 for better performance and security
FROM python:3.13-slim

# Set environment variables optimized for Cloud Run
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080
ENV WORKERS=1
ENV HOST=0.0.0.0

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies optimized for Cloud Run
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create necessary directories with proper permissions
RUN mkdir -p /app/temp_audio /app/logs \
    && chown -R appuser:appuser /app

# Copy requirements first for better layer caching
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies with optimizations for production
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge \
    && find /usr/local -depth \( \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \) -exec rm -rf '{}' + \
    && find /usr/local -type f -name "*.so" -exec strip {} \;

# Copy application files
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check optimized for Cloud Run
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Start the server optimized for Cloud Run
CMD ["sh", "-c", "exec uvicorn main:app --host ${HOST} --port ${PORT} --workers ${WORKERS} --access-log --log-level info --timeout-keep-alive 0"]
