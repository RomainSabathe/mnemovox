# ABOUTME: Docker image for MnemoVox audio recording manager
# ABOUTME: Includes Python runtime, FFmpeg, and application dependencies

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install uv

# Create app user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/data/audio /app/incoming && \
    chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start application
CMD ["python", "main.py"]
