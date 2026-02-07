#!/usr/bin/env bash
# Push .env.prod to Vercel (production + preview).
# Run from repo root or apps/frontend: npm run vercel:env  OR  ./apps/frontend/scripts/vercel-env-push.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$FRONTEND_DIR/.env.prod"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

cd "$FRONTEND_DIR"

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"   # strip comment
  line="$(printf '%s' "$line" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  name="${line%%=*}"
  value="${line#*=}"
  name="$(printf '%s' "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  value="$(printf '%s' "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$name" ]] && continue
  printf '%s' "$value" | vercel env add "$name" production 2>/dev/null || true
  printf '%s' "$value" | vercel env add "$name" preview 2>/dev/null || true
  echo "Added: $name"
done < "$ENV_FILE"

echo "Done. List with: cd $FRONTEND_DIR && vercel env ls"
