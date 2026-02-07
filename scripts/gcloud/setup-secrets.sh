#!/usr/bin/env bash
# Create GEMINI_API_KEY in Secret Manager and grant Cloud Run service account access to secrets.
# Run after setup-project.sh (and optionally after setup-database.sh for DB_PASSWORD secret).
# Loads apps/backend/.env if present (GEMINI_API_KEY can be set there).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GEMINI_API_KEY="${GEMINI_API_KEY:?Set GEMINI_API_KEY}"
SECRET_NAME_GEMINI="${SECRET_NAME_GEMINI:-gemini-api-key}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runner}"
SECRET_NAME_DB_PASSWORD="${SECRET_NAME_DB_PASSWORD:-db-password}"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "Creating or updating secret $SECRET_NAME_GEMINI..."
if gcloud secrets describe "$SECRET_NAME_GEMINI" 2>/dev/null; then
  echo -n "$GEMINI_API_KEY" | gcloud secrets versions add "$SECRET_NAME_GEMINI" --data-file=-
else
  echo -n "$GEMINI_API_KEY" | gcloud secrets create "$SECRET_NAME_GEMINI" --data-file=- --replication-policy=automatic
fi

echo "Granting $SA_EMAIL access to secrets..."
for SECRET in "$SECRET_NAME_GEMINI" "$SECRET_NAME_DB_PASSWORD"; do
  if gcloud secrets describe "$SECRET" 2>/dev/null; then
    gcloud secrets add-iam-policy-binding "$SECRET" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="roles/secretmanager.secretAccessor" \
      --quiet 2>/dev/null || true
  fi
done

echo "Done. Use SECRET_NAME_GEMINI=$SECRET_NAME_GEMINI in deploy.sh"
