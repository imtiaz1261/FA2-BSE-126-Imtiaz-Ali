#!/bin/bash

# Docker build script for Code Alpha services
# Builds all Docker images with proper tagging and caching

set -e

REGISTRY="${DOCKER_REGISTRY:-codealpha}"
TAG="${DOCKER_TAG:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building Code Alpha Docker images..."
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Build Date: $BUILD_DATE"
echo "VCS Ref: $VCS_REF"
echo ""

# Build API Gateway
echo "Building API Gateway..."
docker build \
  -f docker/Dockerfile.api-gateway \
  -t "$REGISTRY/api:$TAG" \
  -t "$REGISTRY/api:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --cache-from "$REGISTRY/api:latest" \
  .

# Build Orchestrator
echo "Building Orchestrator..."
docker build \
  -f docker/Dockerfile.orchestrator \
  -t "$REGISTRY/orchestrator:$TAG" \
  -t "$REGISTRY/orchestrator:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --cache-from "$REGISTRY/orchestrator:latest" \
  .

# Build Sandbox Worker
echo "Building Sandbox Worker..."
docker build \
  -f docker/Dockerfile.sandbox-worker \
  -t "$REGISTRY/sandbox-worker:$TAG" \
  -t "$REGISTRY/sandbox-worker:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --cache-from "$REGISTRY/sandbox-worker:latest" \
  .

# Build Indexing Worker
echo "Building Indexing Worker..."
docker build \
  -f docker/Dockerfile.indexing-worker \
  -t "$REGISTRY/indexing-worker:$TAG" \
  -t "$REGISTRY/indexing-worker:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --cache-from "$REGISTRY/indexing-worker:latest" \
  .

echo ""
echo "✓ All images built successfully!"
echo ""
echo "Built images:"
docker images | grep "$REGISTRY" | head -n 8

echo ""
echo "Next steps:"
echo "  Development:  docker-compose -f docker/docker-compose.dev.yml up"
echo "  Production:   docker-compose -f docker/docker-compose.prod.yml up -d"
echo "  Testing:      docker-compose -f docker/docker-compose.test.yml up"
echo ""
echo "Push to registry (if configured):"
echo "  docker push $REGISTRY/api:$TAG"
echo "  docker push $REGISTRY/orchestrator:$TAG"
echo "  docker push $REGISTRY/sandbox-worker:$TAG"
echo "  docker push $REGISTRY/indexing-worker:$TAG"
