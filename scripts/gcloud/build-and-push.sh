#!/usr/bin/env bash
# Build Agent Analysis backend image and push to Artifact Registry.
# Requires Docker and GCP_PROJECT, GCP_REGION. Loads apps/backend/.env if present.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-europe-west1}"
ARTIFACT_REGISTRY_REPO="${ARTIFACT_REGISTRY_REPO:-agent-analysis}"
IMAGE_NAME="${IMAGE_NAME:-agent-analysis}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

FULL_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

echo "Building image from repo root (includes search/ for RAG)..."
docker build --platform linux/amd64 -t "$FULL_IMAGE" -f "$REPO_ROOT/apps/backend/Dockerfile" "$REPO_ROOT"

echo "Pushing $FULL_IMAGE..."
docker push "$FULL_IMAGE"

echo "Done. Use this image in deploy.sh:"
echo "  IMAGE=$FULL_IMAGE"
