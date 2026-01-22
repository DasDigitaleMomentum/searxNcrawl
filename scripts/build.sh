#!/usr/bin/env sh
set -eu

IMAGE_NAME="${IMAGE_NAME:-searxncrawl}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "Building Docker image ${IMAGE_NAME}:${IMAGE_TAG}..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo "Build complete."
