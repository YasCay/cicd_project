#!/bin/bash

# Build script for Reddit Sentiment Collector Docker image
# Handles platform-specific builds and PyTorch compatibility

set -e

IMAGE_NAME="reddit-collector"
TAG=${1:-latest}
PLATFORM=${2:-linux/amd64}

echo "Building Docker image: ${IMAGE_NAME}:${TAG}"
echo "Platform: ${PLATFORM}"

# Check if buildx is available and configured
if docker buildx version >/dev/null 2>&1; then
    echo "Using Docker buildx for multi-platform support..."
    
    # Build for specific platform to avoid QEMU issues
    docker buildx build \
        --platform ${PLATFORM} \
        --tag ${IMAGE_NAME}:${TAG} \
        --load \
        .
else
    echo "Using standard docker build..."
    docker build -t ${IMAGE_NAME}:${TAG} .
fi

echo "Build completed successfully!"
echo "Image: ${IMAGE_NAME}:${TAG}"

# Test the image
echo "Testing the built image..."
docker run --rm --env-file .env.example ${IMAGE_NAME}:${TAG} python -c "
import torch
import transformers
import pandas as pd
print('✅ All dependencies imported successfully')
print(f'PyTorch version: {torch.__version__}')
print(f'Transformers version: {transformers.__version__}')
print(f'Pandas version: {pd.__version__}')
"

echo "✅ Docker image built and tested successfully!"
