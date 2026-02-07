# Backend hosting on Google Cloud (gcloud scripts)

End-to-end scripts to host the Agent Analysis Python backend on **Cloud Run** with **Cloud SQL (PostgreSQL)** and **Secret Manager**.

## Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and logged in:
  - `gcloud auth login`
  - `gcloud auth application-default login` (for Docker/APIs)
- **Docker** installed (for `build-and-push.sh`), or use Cloud Build (see below).
- A **GCP project** and **GEMINI_API_KEY** for the agents.

## Order of execution

Run from this directory (`scripts/gcloud/`) or from repo root. **Env:** use **one** file, `apps/backend/.env`. Copy `apps/backend/.env.example` to `apps/backend/.env`, add `GCP_PROJECT`, `GCP_REGION`, and `GEMINI_API_KEY`. The gcloud scripts automatically source `apps/backend/.env` when present.

1. **setup-project.sh** – Enable APIs, create Artifact Registry repo, create service account `backend-runner` with Cloud SQL Client and Secret Manager access.
2. **setup-database.sh** – Create Cloud SQL PostgreSQL instance, database `trader_edu`, user, and store password + full `DATABASE_URL` in Secret Manager.
3. **setup-secrets.sh** – Create `GEMINI_API_KEY` secret and grant the service account access to all secrets.
4. **build-and-push.sh** – Build the backend Docker image and push to Artifact Registry (requires Docker).
5. **deploy.sh** – Deploy to Cloud Run with Cloud SQL connection and secrets. Set `IMAGE` and `CLOUD_SQL_CONNECTION_NAME` (output from previous steps).

## Required environment variables

| Variable | When | Description |
|----------|------|-------------|
| `GCP_PROJECT` | All | Your GCP project ID. |
| `GCP_REGION` | All | Region (default: `europe-west1`). |
| `GEMINI_API_KEY` | setup-secrets | API key for Gemini (agents). |
| `IMAGE` | deploy | Full image URL (e.g. from build-and-push.sh output). |
| `CLOUD_SQL_CONNECTION_NAME` | deploy | `PROJECT:REGION:INSTANCE` (e.g. from setup-database.sh output). |

Optional overrides are listed in `apps/backend/.env.example` (GCloud deployment section).

## Example (first-time)

```bash
# One .env for backend and gcloud (copy once, add your values)
cp apps/backend/.env.example apps/backend/.env
# Edit apps/backend/.env: set GCP_PROJECT, GCP_REGION, GEMINI_API_KEY

cd scripts/gcloud
./setup-project.sh
./setup-database.sh    # Takes several minutes for Cloud SQL
./setup-secrets.sh
./build-and-push.sh

# Add to apps/backend/.env after the steps above (or export here):
# IMAGE=europe-west1-docker.pkg.dev/YOUR_PROJECT/agent-analysis/agent-analysis:latest
# CLOUD_SQL_CONNECTION_NAME=YOUR_PROJECT:europe-west1:trader-edu-db
./deploy.sh
```

Then set **AGENT_ANALYSIS_API_URL** in your frontend (e.g. Cloudflare Pages env) to the Cloud Run service URL printed by `deploy.sh`.

## Cloud Build (no local Docker)

To build the image in GCP instead of locally, use the backend’s `cloudbuild.yaml`:

```bash
gcloud builds submit --config=apps/backend/cloudbuild.yaml apps/backend
```

Then set `IMAGE` to the image URL produced by the build and run `deploy.sh`.

## Security notes

- **CORS**: The backend allows all origins; for production, restrict to your frontend origin in `apps/backend/src/main.py`.
- **Cloud Run**: Deploy uses `--allow-unauthenticated` so the frontend can call the API. To lock down, remove it and use IAM invoker or an API key in headers.
