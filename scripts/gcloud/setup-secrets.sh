#!/usr/bin/env bash
# Create secrets in Secret Manager from apps/backend/.env and grant Cloud Run service account access.
# Run after setup-project.sh (and optionally after setup-database.sh for DB_PASSWORD secret).
# Loads apps/backend/.env — syncs GEMINI_API_KEY, API_KEY (NVIDIA for RAG), etc.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GEMINI_API_KEY="${GEMINI_API_KEY:?Set GEMINI_API_KEY}"
SECRET_NAME_GEMINI="${SECRET_NAME_GEMINI:-gemini-api-key}"
SECRET_NAME_NVIDIA_API_KEY="${SECRET_NAME_NVIDIA_API_KEY:-nvidia-api-key}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runner}"
SECRET_NAME_DB_PASSWORD="${SECRET_NAME_DB_PASSWORD:-db-password}"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "Creating or updating secret $SECRET_NAME_GEMINI..."
if gcloud secrets describe "$SECRET_NAME_GEMINI" 2>/dev/null; then
  echo -n "$GEMINI_API_KEY" | gcloud secrets versions add "$SECRET_NAME_GEMINI" --data-file=-
else
  echo -n "$GEMINI_API_KEY" | gcloud secrets create "$SECRET_NAME_GEMINI" --data-file=- --replication-policy=automatic
fi

if [[ -n "${API_KEY:-}" ]]; then
  echo "Creating or updating secret $SECRET_NAME_NVIDIA_API_KEY (RAG)..."
  if gcloud secrets describe "$SECRET_NAME_NVIDIA_API_KEY" 2>/dev/null; then
    echo -n "$API_KEY" | gcloud secrets versions add "$SECRET_NAME_NVIDIA_API_KEY" --data-file=-
  else
    echo -n "$API_KEY" | gcloud secrets create "$SECRET_NAME_NVIDIA_API_KEY" --data-file=- --replication-policy=automatic
  fi
else
  echo "API_KEY not set in .env — skipping nvidia-api-key (RAG will fail without it)"
fi

echo "Granting $SA_EMAIL access to secrets..."
for SECRET in "$SECRET_NAME_GEMINI" "$SECRET_NAME_NVIDIA_API_KEY" "$SECRET_NAME_DB_PASSWORD"; do
  if gcloud secrets describe "$SECRET" 2>/dev/null; then
    gcloud secrets add-iam-policy-binding "$SECRET" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="roles/secretmanager.secretAccessor" \
      --quiet 2>/dev/null || true
  fi
done

echo "Done. deploy.sh uses: GEMINI_API_KEY, DATABASE_URL, API_KEY (nvidia-api-key)"
