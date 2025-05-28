# Complete Dockerfile for Reddit FinBERT Sentiment Collector
# Optimized for fast builds with all dependencies

FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"
ENV HF_HOME="/app/.cache/huggingface"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r collector && useradd -r -g collector collector

# Create application directory and set ownership
WORKDIR /app
RUN mkdir -p /data /app/.cache/huggingface && \
    chown -R collector:collector /app /data

# Install Python dependencies in optimized order
# 1. Install CPU-only PyTorch first
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0+cpu

# 2. Install all other dependencies
RUN pip install --no-cache-dir \
    pandas==2.1.4 \
    transformers==4.36.2 \
    praw==7.7.1 \
    python-dotenv==1.0.0 \
    prometheus-client==0.19.0 \
    psutil>=5.9.0 \
    pybloom-live \
    numpy==1.26.3

# Copy application code
COPY apps/ /app/apps/
COPY .env.example /app/.env.example

# Set correct ownership
RUN chown -R collector:collector /app

# Switch to non-root user
USER collector

# Expose metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Run the collector
CMD ["python", "-m", "apps.collector.collector"]
