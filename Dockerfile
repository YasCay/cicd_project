# Complete Dockerfile for Reddit FinBERT Sentiment Collector
# Optimized for fast builds with all dependencies

FROM python:3.13.7-slim

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
# 1. Update pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 2. Install CPU-only PyTorch (stable version)
RUN pip install --no-cache-dir \
    torch==2.3.1+cpu torchvision==0.18.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# 3. Install all other dependencies
RUN pip install --no-cache-dir \
    pandas==2.2.0 \
    transformers==4.42.0 \
    praw==7.7.1 \
    python-dotenv==1.0.0 \
    prometheus-client==0.20.0 \
    psutil>=5.9.0 \
    pybloom-live \
    numpy==1.26.4

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
