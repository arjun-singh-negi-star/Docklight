#!/usr/bin/env bash
# Builds both images and pushes them to a registry (Docker Hub or ECR).
# Usage: ./scripts/build_and_push.sh <registry>/<repo-prefix> [tag]
set -euo pipefail

REGISTRY=${1:?"Usage: build_and_push.sh <registry-prefix> [tag]"}
TAG=${2:-latest}

docker build -t "${REGISTRY}/rag-backend:${TAG}" ./backend
docker build -t "${REGISTRY}/rag-frontend:${TAG}" ./frontend

docker push "${REGISTRY}/rag-backend:${TAG}"
docker push "${REGISTRY}/rag-frontend:${TAG}"

echo "Pushed:"
echo "  ${REGISTRY}/rag-backend:${TAG}"
echo "  ${REGISTRY}/rag-frontend:${TAG}"
