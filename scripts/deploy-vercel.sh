#!/usr/bin/env bash
# Run Vercel from repo root so root vercel.json (monorepo install + build) is used.
# Usage: from repo root, run "npm run deploy" or "npm run deploy:preview".
# Do NOT run "vercel" from apps/frontend — that uploads only the frontend and breaks the install.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec vercel "$@"
