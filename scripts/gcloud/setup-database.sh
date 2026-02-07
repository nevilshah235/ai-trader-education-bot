#!/usr/bin/env bash
# Create Cloud SQL PostgreSQL instance, database, and app user. Stores DB password in Secret Manager.
# Run after setup-project.sh. Requires GCP_PROJECT, GCP_REGION.
# Loads apps/backend/.env if present.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$REPO_ROOT/apps/backend/.env" ] && set -a && source "$REPO_ROOT/apps/backend/.env" && set +a

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-europe-west1}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-trader-edu-db}"
# Cheapest: ENTERPRISE + db-f1-micro. If project requires ENTERPRISE_PLUS, set CLOUD_SQL_EDITION=ENTERPRISE_PLUS and CLOUD_SQL_TIER=db-perf-optimized-2
CLOUD_SQL_EDITION="${CLOUD_SQL_EDITION:-ENTERPRISE}"
CLOUD_SQL_TIER="${CLOUD_SQL_TIER:-db-f1-micro}"
DB_NAME="${DB_NAME:-trader_edu}"
DB_USER="${DB_USER:-trader_edu_app}"
SECRET_NAME_DB_PASSWORD="${SECRET_NAME_DB_PASSWORD:-db-password}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runner}"

CONNECTION_NAME="${GCP_PROJECT}:${GCP_REGION}:${CLOUD_SQL_INSTANCE}"

echo "Creating Cloud SQL instance $CLOUD_SQL_INSTANCE in $GCP_REGION (this may take several minutes)..."
if gcloud sql instances describe "$CLOUD_SQL_INSTANCE" 2>/dev/null; then
  echo "Instance already exists."
else
  gcloud sql instances create "$CLOUD_SQL_INSTANCE" \
    --database-version=POSTGRES_16 \
    --edition="$CLOUD_SQL_EDITION" \
    --tier="$CLOUD_SQL_TIER" \
    --region="$GCP_REGION" \
    --root-password="$(openssl rand -base64 24)"
fi

echo "Creating database $DB_NAME..."
gcloud sql databases create "$DB_NAME" --instance="$CLOUD_SQL_INSTANCE" 2>/dev/null || echo "Database may already exist."

# Generate and set app user password; store in Secret Manager
DB_PASSWORD="$(openssl rand -base64 24)"
echo "Creating or updating user $DB_USER..."
if gcloud sql users list --instance="$CLOUD_SQL_INSTANCE" 2>/dev/null | grep -q "^$DB_USER"; then
  gcloud sql users set-password "$DB_USER" --instance="$CLOUD_SQL_INSTANCE" --password="$DB_PASSWORD"
else
  gcloud sql users create "$DB_USER" --instance="$CLOUD_SQL_INSTANCE" --password="$DB_PASSWORD"
fi

echo "Storing DB password in Secret Manager..."
if gcloud secrets describe "$SECRET_NAME_DB_PASSWORD" 2>/dev/null; then
  echo -n "$DB_PASSWORD" | gcloud secrets versions add "$SECRET_NAME_DB_PASSWORD" --data-file=-
else
  echo -n "$DB_PASSWORD" | gcloud secrets create "$SECRET_NAME_DB_PASSWORD" --data-file=- --replication-policy=automatic
fi

# Full DATABASE_URL for Cloud Run (password and socket path must be URL-encoded)
ENCODED_PASSWORD=$(printf '%s' "$DB_PASSWORD" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))")
SOCKET_PATH="/cloudsql/${CONNECTION_NAME}"
ENCODED_HOST=$(printf '%s' "$SOCKET_PATH" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))")
DATABASE_URL="postgresql+psycopg2://${DB_USER}:${ENCODED_PASSWORD}@/trader_edu?host=${ENCODED_HOST}"
SECRET_NAME_DATABASE_URL="${SECRET_NAME_DATABASE_URL:-database-url}"
echo "Storing DATABASE_URL in Secret Manager..."
if gcloud secrets describe "$SECRET_NAME_DATABASE_URL" 2>/dev/null; then
  echo -n "$DATABASE_URL" | gcloud secrets versions add "$SECRET_NAME_DATABASE_URL" --data-file=-
else
  echo -n "$DATABASE_URL" | gcloud secrets create "$SECRET_NAME_DATABASE_URL" --data-file=- --replication-policy=automatic
fi

echo "Granting service account access to $SECRET_NAME_DATABASE_URL..."
SA_EMAIL="${SERVICE_ACCOUNT_NAME:-backend-runner}@${GCP_PROJECT}.iam.gserviceaccount.com"
gcloud secrets add-iam-policy-binding "$SECRET_NAME_DATABASE_URL" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet 2>/dev/null || true

echo ""
echo "Done. Cloud SQL connection name (use in deploy.sh):"
echo "  CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME"
echo "  SECRET_NAME_DATABASE_URL=$SECRET_NAME_DATABASE_URL"
echo "  SECRET_NAME_DB_PASSWORD=$SECRET_NAME_DB_PASSWORD"
