#!/usr/bin/env bash
# Run the verification sequence for backend with local Postgres.
# Prereqs: Postgres running (e.g. docker compose up -d postgres), DATABASE_URL in project root .env,
#          backend running (npm run dev:agent from repo root).
# Usage: from repo root, . apps/backend/scripts/test_postgres_local.sh
#    or: bash apps/backend/scripts/test_postgres_local.sh

set -e
BASE_URL="${BASE_URL:-http://localhost:8000}"
LOGINID="${TEST_LOGINID:-test_loginid_001}"
CONTRACT_ID="${TEST_CONTRACT_ID:-test_contract_$(date +%s)}"

echo "Using BASE_URL=$BASE_URL LOGINID=$LOGINID CONTRACT_ID=$CONTRACT_ID"

# 4.1 Health
echo "--- GET /health ---"
health=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
body=$(echo "$health" | head -n -1)
code=$(echo "$health" | tail -n 1)
if [ "$code" != "200" ]; then
  echo "Health check failed: HTTP $code"
  echo "$body"
  exit 1
fi
echo "$body"
echo ""

# 4.2 POST single transaction
echo "--- POST /api/transactions (single) ---"
tx_body=$(cat <<EOF
{
  "loginid": "$LOGINID",
  "contract_id": "$CONTRACT_ID",
  "run_id": "run_001",
  "buy_price": 10.5,
  "payout": 20.0,
  "profit": 9.5,
  "currency": "USD",
  "contract_type": "CALL",
  "shortcode": "R_10",
  "date_start": "2025-01-01 00:00:00",
  "date_expiry": "2025-01-01 01:00:00"
}
EOF
)
sync_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "$tx_body")
sync_body=$(echo "$sync_resp" | head -n -1)
sync_code=$(echo "$sync_resp" | tail -n 1)
if [ "$sync_code" != "201" ]; then
  echo "POST /api/transactions failed: HTTP $sync_code"
  echo "$sync_body"
  exit 1
fi
echo "$sync_body"
echo ""

# Idempotent upsert: same payload again
echo "--- POST /api/transactions (upsert same) ---"
sync_resp2=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "$tx_body")
sync_code2=$(echo "$sync_resp2" | tail -n 1)
if [ "$sync_code2" != "201" ]; then
  echo "Upsert failed: HTTP $sync_code2"
  exit 1
fi
echo "$(echo "$sync_resp2" | head -n -1)"
echo ""

# 4.3 GET transactions
echo "--- GET /api/transactions?loginid=$LOGINID ---"
list_resp=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/transactions?loginid=$LOGINID")
list_body=$(echo "$list_resp" | head -n -1)
list_code=$(echo "$list_resp" | tail -n 1)
if [ "$list_code" != "200" ]; then
  echo "GET /api/transactions failed: HTTP $list_code"
  echo "$list_body"
  exit 1
fi
echo "$list_body"
echo ""

# 4.5 Optional: POST analyse/json (skipped if GEMINI_API_KEY not set)
if [ -n "$GEMINI_API_KEY" ]; then
  echo "--- POST /api/agent_analysis/analyse/json (optional) ---"
  payload=$(cat <<EOF
{
  "contract": {
    "contract_id": "$CONTRACT_ID",
    "buy_price": 10.5,
    "payout": 20.0,
    "profit": 9.5,
    "currency": "USD",
    "contract_type": "CALL",
    "shortcode": "R_10",
    "date_start": "2025-01-01 00:00:00",
    "date_expiry": "2025-01-01 01:00:00"
  },
  "behavioral_summary": {
    "run_id": "run_001",
    "trade_index_in_run": 1,
    "total_trades_in_run_so_far": 1,
    "recent_outcomes": []
  }
}
EOF
)
  analyse_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/agent_analysis/analyse/json?loginid=$LOGINID" \
    -H "Content-Type: application/json" \
    -d "$payload")
  analyse_code=$(echo "$analyse_resp" | tail -n 1)
  if [ "$analyse_code" = "200" ]; then
    echo "Analysis persisted (HTTP 200)"
    echo "$(echo "$analyse_resp" | head -n -1)" | head -c 500
    echo "..."
  else
    echo "Analysis request returned HTTP $analyse_code (optional; may need GEMINI_API_KEY in .env)"
  fi
else
  echo "--- Skipping POST /api/agent_analysis/analyse/json (GEMINI_API_KEY not set) ---"
fi

echo ""
echo "Done. Check Postgres: SELECT * FROM transactions; SELECT * FROM analysis_results;"
