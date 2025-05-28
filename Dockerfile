# CPU-only Dockerfile for Reddit FinBERT Sentiment Collector
# Optimized for fast builds without CUDA dependencies

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY apps/collector/requirements.txt /app/requirements.txt

# Install Python dependencies with CPU-only PyTorch
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0+cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/ /app/apps/
COPY .env.example /app/.env.example

# Create data directory
RUN mkdir -p /data

# Expose metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Run the collector
CMD ["python", "apps/collector/collector.py"]
