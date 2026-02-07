#!/usr/bin/env bash
# Deploy Agent Analysis backend to Cloud Run with Cloud SQL and secrets.
# Run after build-and-push.sh. Requires IMAGE, CLOUD_SQL_CONNECTION_NAME. Loads apps/backend/.env if present.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-europe-west1}"
IMAGE="${IMAGE:?Set IMAGE (e.g. europe-west1-docker.pkg.dev/PROJECT/agent-analysis/agent-analysis:latest)}"
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:?Set CLOUD_SQL_CONNECTION_NAME (PROJECT:REGION:INSTANCE)}"
SERVICE_NAME="${SERVICE_NAME:-agent-analysis}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runner}"
SECRET_NAME_GEMINI="${SECRET_NAME_GEMINI:-gemini-api-key}"
SECRET_NAME_DATABASE_URL="${SECRET_NAME_DATABASE_URL:-database-url}"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "Deploying $SERVICE_NAME to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$GCP_REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA_EMAIL" \
  --add-cloudsql-instances="$CLOUD_SQL_CONNECTION_NAME" \
  --set-secrets="GEMINI_API_KEY=${SECRET_NAME_GEMINI}:latest,DATABASE_URL=${SECRET_NAME_DATABASE_URL}:latest" \
  --port=8000 \
  --no-cpu-throttling \
  --timeout=300

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$GCP_REGION" --format='value(status.url)')
echo ""
echo "Deployed. Set AGENT_ANALYSIS_API_URL in your frontend (e.g. Cloudflare Pages):"
echo "  $SERVICE_URL"
