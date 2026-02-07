#!/usr/bin/env bash
# One-time GCP project setup: enable APIs, create Cloud Run service account.
# Usage: GCP_PROJECT=my-project [GCP_REGION=europe-west1] ./setup-project.sh
# Loads apps/backend/.env if present (same file as backend runtime).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-europe-west1}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runner}"

echo "Setting project to $GCP_PROJECT"
gcloud config set project "$GCP_PROJECT"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com

echo "Creating Artifact Registry repository (idempotent)..."
gcloud artifacts repositories describe agent-analysis --location="$GCP_REGION" 2>/dev/null ||
  gcloud artifacts repositories create agent-analysis \
    --repository-format=docker \
    --location="$GCP_REGION" \
    --description="Agent Analysis API images"

echo "Creating service account $SERVICE_ACCOUNT_NAME (idempotent)..."
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" 2>/dev/null; then
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name="Agent Analysis Cloud Run"
fi

echo "Granting Cloud SQL Client and Secret Manager Secret Accessor..."
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client" \
  --condition=None \
  --quiet 2>/dev/null || true
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  --quiet 2>/dev/null || true

echo "Done. SERVICE_ACCOUNT_EMAIL=${SA_EMAIL}"
echo "Use GCP_REGION=$GCP_REGION for subsequent scripts."
