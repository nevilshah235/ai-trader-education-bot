# InsightX

> AI-powered trader education: build strategies visually, run bots, and learn from every trade with Analyst and Tutor agents.

![Node](https://img.shields.io/badge/node-20.x-blue.svg)
![npm](https://img.shields.io/badge/npm-9.x-blue.svg)
![Build](https://img.shields.io/badge/build-RSBuild-green.svg)
![React](https://img.shields.io/badge/framework-React%2018-blue.svg)

## Table of Contents

- [Core problem](#core-problem)
- [Features](#features)
- [Design](#design)
- [Project guidelines](#project-guidelines)
- [Setup](#setup)
- [Vercel (frontend)](#vercel-frontend)
- [Google Cloud (backend)](#google-cloud-backend)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Core problem

Traders need to **automate strategies and learn from outcomes** without writing code. Existing tools either assume programming skills or offer no structured way to understand why a trade won or lost. The result:

- **Barrier to automation** – Strategy logic is locked in code; non-developers can’t build or tweak bots.
- **Shallow feedback** – P&L and logs don’t explain context, risk, or decision quality.
- **No personalised education** – Generic tutorials don’t tie lessons to the user’s own trades and strategy intent.

**InsightX** addresses this by combining a **visual bot builder** (Blockly + Deriv API) with an **agent-based education backend**: an **Analyst** agent analyses each trade objectively for learning, and a **Tutor** agent turns that into personalised explanations and follow-up. Traders build strategies in a drag-and-drop workspace, run them against live markets, and get AI-powered analysis and education grounded in their actual trade data and charts.

---

## Features

- **Visual bot builder** – Drag-and-drop Blockly blocks to define strategies; no code required. Integrates with Deriv’s API for real-time data and execution.
- **Real-time dashboard** – Monitor active bots, performance, and account stats in one place.
- **Charts and analysis** – SmartCharts/TradingView-style charts for market context and strategy review.
- **Interactive tutorials** – Step-by-step guides for bot building and trading concepts.
- **Analyst agent** – Deep, objective analysis of individual trades (what happened, key factors, win/loss drivers) using contract data, strategy intent, and optional chart images. Outputs structured insights for learning.
- **Tutor agent** – Personalised explanations and follow-up based on Analyst output; reinforces learning from the trader’s own results.
- **Persistence and RAG** – Backend stores analyses and supports RAG (LangChain/FAISS) for richer, context-aware answers.
- **Responsive UI** – Usable on desktop and mobile.
- **Analytics** – RudderStack and GTM for product and usage insights.
- **Real-time updates** – WebSockets for live market data and bot status.

---

## Design

### Architecture

- **Frontend** – React 18, TypeScript, MobX (RootStore), RSBuild. Blockly for the bot builder; Deriv API for trading. Main app lives in `apps/frontend` and deploys to Vercel (or Cloudflare Pages).
- **Backend** – FastAPI (Python 3.10+). Analyst and Tutor agents use Google Gemini; PostgreSQL (Cloud SQL in production) for persistence; LangChain + FAISS for RAG. Deploys to Google Cloud Run. See [apps/backend](apps/backend).
- **Shared** – `packages/shared` holds shared TypeScript (e.g. education API types) used by the frontend.

### Monorepo layout

| Path | Role |
|------|------|
| **apps/frontend** | React app: components, pages (Dashboard, Bot Builder, Chart, Tutorials), stores, Blockly/bot-skeleton, RSBuild config. |
| **apps/backend** | FastAPI app: agents (Analyst, Tutor), db (SQLAlchemy/PostgreSQL), routes, RAG services. |
| **packages/shared** | Shared TypeScript (education API, strategy intent, etc.). |
| **scripts/gcloud** | GCP scripts: Cloud Run + Cloud SQL + Secret Manager. See [scripts/gcloud/README.md](scripts/gcloud/README.md). |

### Tech stack

**Frontend:** React 18, TypeScript, MobX, React Router, RSBuild, Sass, Blockly, SmartCharts, @deriv-com/ui, @deriv/deriv-api. Jest, React Testing Library, ESLint, Prettier, Husky.

**Backend:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, PostgreSQL (psycopg2), Google GenAI (Gemini), LangChain, FAISS, Pydantic. Managed with [uv](https://docs.astral.sh/uv/).

### Project structure (high level)

```
apps/
├── frontend/           # React UI
│   ├── src/
│   │   ├── components/, pages/, stores/
│   │   ├── external/bot-skeleton/   # Blockly blocks & bot runtime
│   │   └── ...
│   ├── rsbuild.config.ts
│   └── vercel.json
├── backend/            # Agent Analysis API
│   ├── src/
│   │   ├── agents/     # Analyst, Tutor
│   │   ├── db/         # Models, CRUD, engine
│   │   ├── routes/     # analysis, transactions
│   │   ├── services/   # RAG, etc.
│   │   └── main.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── cloudbuild.yaml
packages/
└── shared/             # Shared TS types
scripts/
└── gcloud/             # Backend deploy (Cloud Run + Cloud SQL)
```

---

## Project guidelines

### Contributing

1. Fork the repo and create a feature branch: `git checkout -b feature/your-feature`.
2. Make changes, run tests (`npm test`) and lint (`npm run test:lint`).
3. Commit with a **conventional commit** and a **single-line subject** (e.g. `feat: add X`, `fix: resolve Y`). Do not add `Co-authored-by:` or other trailers unless explicitly required.
4. Push and open a Pull Request.

### Code standards

- TypeScript: follow project patterns; use functional components and hooks.
- Write tests for new behaviour; keep existing naming and structure.
- Update docs when changing behaviour or setup.

### Git workflow

- **Conventional commits:** `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`.
- One logical change per commit; single-line subject. Rebase feature branches before merge.

---

## Setup

### Prerequisites

- **Node.js 20.x** and **npm 9.x** – for the frontend.
- **Python 3.10+** and **[uv](https://docs.astral.sh/uv/)** – only if you run the backend locally.
- **git** – version control.

### Install and run (frontend)

```sh
git clone <repository-url>
cd ai-trader-education-bot
npm install
npm run build
npm start
```

App: **https://localhost:8443/** (or the port RSBuild reports).

### Run backend locally (optional)

```sh
# From repo root
npm run dev:agent
```

- Backend runs at **http://localhost:8000**.
- Copy `apps/backend/.env.example` → `apps/backend/.env` and set **GEMINI_API_KEY** (and optionally DB settings). See [apps/backend/.env.example](apps/backend/.env.example) and [scripts/gcloud/README.md](scripts/gcloud/README.md).

### Environment variables (quick ref)

**Frontend** – `apps/frontend/.env` (or root `.env`):

- **DERIV_APP_ID** (optional) – Use [Deriv third-party OAuth](https://developers.deriv.com/docs/authentication) and public WebSocket API when set. Register at [api.deriv.com](https://api.deriv.com), set OAuth redirect URL to your app origin.
- **AGENT_ANALYSIS_API_URL** (optional) – When unset, frontend uses same-origin `/api` (proxy to backend). When set (e.g. Cloud Run URL or `http://localhost:8000`), frontend calls the backend at that URL.

**Backend** – `apps/backend/.env`:

- **GEMINI_API_KEY** – Required for Analyst/Tutor. For production GCP, see [scripts/gcloud/README.md](scripts/gcloud/README.md) for `GCP_PROJECT`, `GCP_REGION`, `DATABASE_URL`, etc.

### Root scripts

| Command | Description |
|--------|-------------|
| `npm start` | Dev server (frontend, hot reload) |
| `npm run build` | Production build (frontend) |
| `npm run watch` | Build in watch mode |
| `npm run serve` | Serve production build locally |
| `npm run dev:agent` | Run backend locally (port 8000) |
| `npm run deploy` | Deploy frontend to Vercel (production) |
| `npm run deploy:preview` | Deploy frontend to Vercel (preview) |
| `npm test` | Run Jest tests (frontend) |
| `npm run coverage` | Coverage report |
| `npm run test:lint` | Lint + format check |
| `npm run test:fix` | Auto-fix lint/format |
| `npm run build:analyze` | Bundle size analysis |

---

## Vercel (frontend)

The frontend is one workspace in a **monorepo**. Deploy from the **repository root** so `packages/shared` and root config are available.

### Config

- **Root directory:** Leave empty in Vercel (use repo root).
- **Build:** Root [vercel.json](vercel.json) defines:
  - **Install:** `npm ci`
  - **Build:** `npm run build`
  - **Output:** `apps/frontend/dist`
  - SPA rewrites: `/*` → `index.html`

### Deploy

From repo root:

```sh
vercel link          # link to your Vercel project
npm run deploy       # production
# or
vercel --prod
```

For previews: `npm run deploy:preview` or `vercel` (no `--prod`).

### Important

- Do **not** set Vercel Root Directory to `apps/frontend` and do **not** run `vercel` from inside `apps/frontend`. The root install would fail and the monorepo would be incomplete.
- If you see `Command "cd ../.. && npm ci" exited with 1`, run from repo root or clear any custom Install Command in Vercel so the root [vercel.json](vercel.json) is used.

### Frontend env on Vercel

Set in Vercel project → Settings → Environment Variables:

- **AGENT_ANALYSIS_API_URL** – Your backend URL (e.g. Cloud Run) so the frontend can call the Agent Analysis API. Omit if you rely on same-origin proxy.

### Alternative: Cloudflare Pages

For Cloudflare Pages, set these in GitHub Actions (or your CI):

```env
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_PROJECT_NAME=your_project_name
```

---

## Google Cloud (backend)

The backend runs on **Cloud Run** with **Cloud SQL (PostgreSQL)** and **Secret Manager**. Scripts live in **scripts/gcloud/**; full details in [scripts/gcloud/README.md](scripts/gcloud/README.md).

### Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and logged in (`gcloud auth login`, `gcloud auth application-default login`).
- **Docker** (for local image build), or use Cloud Build.
- A **GCP project** and **GEMINI_API_KEY**.

### One-time setup (order matters)

Use a single env file: **apps/backend/.env**. Copy from `apps/backend/.env.example` and set at least `GCP_PROJECT`, `GCP_REGION`, `GEMINI_API_KEY`. Scripts source this file when present.

From repo root or `scripts/gcloud/`:

1. **setup-project.sh** – Enable APIs, Artifact Registry, service account `backend-runner` (Cloud SQL Client + Secret Manager).
2. **setup-database.sh** – Create Cloud SQL PostgreSQL instance, DB `trader_edu`, user; store password and `DATABASE_URL` in Secret Manager. (Can take several minutes.)
3. **setup-secrets.sh** – Create `GEMINI_API_KEY` secret; grant backend service account access.
4. **build-and-push.sh** – Build backend Docker image and push to Artifact Registry (needs Docker).
5. **deploy.sh** – Deploy to Cloud Run with Cloud SQL and secrets. Requires `IMAGE` and `CLOUD_SQL_CONNECTION_NAME` in `apps/backend/.env` (outputs from steps 2 and 4).

Example (first time):

```sh
cp apps/backend/.env.example apps/backend/.env
# Edit: GCP_PROJECT, GCP_REGION, GEMINI_API_KEY

cd scripts/gcloud
./setup-project.sh
./setup-database.sh
./setup-secrets.sh
./build-and-push.sh

# Add to apps/backend/.env (from script output):
# IMAGE=...
# CLOUD_SQL_CONNECTION_NAME=...
./deploy.sh
```

`deploy.sh` prints the Cloud Run service URL. Set **AGENT_ANALYSIS_API_URL** in Vercel (or your frontend host) to this URL.

### Build image in GCP (no local Docker)

```sh
gcloud builds submit --config=apps/backend/cloudbuild.yaml apps/backend
```

Then set `IMAGE` in `apps/backend/.env` to the built image URL and run `./deploy.sh`.

### Required env for gcloud scripts

| Variable | When | Description |
|----------|------|-------------|
| `GCP_PROJECT` | All | GCP project ID. |
| `GCP_REGION` | All | e.g. `europe-west1`. |
| `GEMINI_API_KEY` | setup-secrets | Gemini API key for agents. |
| `IMAGE` | deploy | Full image URL (e.g. from build-and-push or Cloud Build). |
| `CLOUD_SQL_CONNECTION_NAME` | deploy | `PROJECT:REGION:INSTANCE` (from setup-database.sh). |

More options in [apps/backend/.env.example](apps/backend/.env.example) and [scripts/gcloud/README.md](scripts/gcloud/README.md).

---

## Testing

Frontend tests (Jest + React Testing Library) from repo root:

```sh
npm test
npm run coverage
npm test -- --watch
npm test -- dashboard.spec.tsx
```

---

## Troubleshooting

- **Dev server won’t start:** `npm cache clean --force`, remove `node_modules` and `package-lock.json`, then `npm install`.
- **Build fails:** Ensure Node 20.x (`node --version`). Try `rm -rf dist` then `npm run build`.
- **Blockly issues:** Use a browser with Web Workers; check console; refresh to reinit workspace.
- **WebSocket/API errors:** Check network and env (DERIV_APP_ID, AGENT_ANALYSIS_API_URL).
- **Backend / agents not responding:** Ensure `apps/backend/.env` exists with **GEMINI_API_KEY**. For DB features, set `DATABASE_URL` or complete gcloud setup (see [scripts/gcloud/README.md](scripts/gcloud/README.md)).

**Performance:** Use `npm run build:analyze` for bundle size; consider React.lazy and DevTools Profiler for render hotspots.

---

For issues and questions, use the project’s issue tracker or contact the team.
