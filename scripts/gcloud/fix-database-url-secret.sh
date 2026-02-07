#!/usr/bin/env bash
# One-off: update database-url secret with URL-encoded host (fixes Cloud Run DB connection).
# Run after setup-database. Loads apps/backend/.env. Requires gcloud and Secret Manager access.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-europe-west1}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-trader-edu-db}"
DB_USER="${DB_USER:-trader_edu_app}"
SECRET_NAME_DB_PASSWORD="${SECRET_NAME_DB_PASSWORD:-db-password}"
SECRET_NAME_DATABASE_URL="${SECRET_NAME_DATABASE_URL:-database-url}"

CONNECTION_NAME="${GCP_PROJECT}:${GCP_REGION}:${CLOUD_SQL_INSTANCE}"

echo "Reading current DB password from Secret Manager..."
DB_PASSWORD=$(gcloud secrets versions access latest --secret="$SECRET_NAME_DB_PASSWORD" --project="$GCP_PROJECT")

ENCODED_PASSWORD=$(printf '%s' "$DB_PASSWORD" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))")
SOCKET_PATH="/cloudsql/${CONNECTION_NAME}"
ENCODED_HOST=$(printf '%s' "$SOCKET_PATH" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))")
DATABASE_URL="postgresql+psycopg2://${DB_USER}:${ENCODED_PASSWORD}@/trader_edu?host=${ENCODED_HOST}"

echo "Adding new version to secret $SECRET_NAME_DATABASE_URL..."
echo -n "$DATABASE_URL" | gcloud secrets versions add "$SECRET_NAME_DATABASE_URL" --data-file=- --project="$GCP_PROJECT"

echo "Done. Redeploy Cloud Run to pick up the new secret version: ./deploy.sh"
