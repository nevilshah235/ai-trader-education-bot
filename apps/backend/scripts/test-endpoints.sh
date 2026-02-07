#!/bin/bash
# Test Agent Analysis endpoints (run backend first: uvicorn apps.backend.src.main:app --reload --port 8000)

BASE="http://localhost:8000"

echo "=== 1. Health check ==="
curl -s "$BASE/health" | jq .

echo -e "\n=== 2. POST /api/agent_analysis/analyse/json (JSON only) ==="
curl -s -X POST "$BASE/api/agent_analysis/analyse/json" \
  -H "Content-Type: application/json" \
  -d '{
    "contract": {
      "contract_id": "test-123",
      "buy_price": 10,
      "payout": 18,
      "profit": 8,
      "currency": "USD",
      "contract_type": "CALL",
      "shortcode": "CALL_R_100_5M",
      "date_start": "2025-02-07T10:00:00Z",
      "date_expiry": "2025-02-07T10:05:00Z",
      "entry_tick": "250.50",
      "exit_tick": "251.00"
    },
    "behavioral_summary": {
      "run_id": "run-1",
      "trade_index_in_run": 2,
      "total_trades_in_run_so_far": 2,
      "recent_outcomes": ["win", "loss"]
    }
  }' | jq .

echo -e "\n=== 3. POST /api/agent_analysis/analyse/json (with past_trades_summaries) ==="
curl -s -X POST "$BASE/api/agent_analysis/analyse/json" \
  -H "Content-Type: application/json" \
  -d '{
    "contract": {
      "contract_id": "test-456",
      "buy_price": 5,
      "payout": 10,
      "profit": -5,
      "currency": "USD",
      "contract_type": "PUT",
      "shortcode": "PUT_R_50_1M",
      "date_start": "2025-02-07T11:00:00Z",
      "date_expiry": "2025-02-07T11:01:00Z",
      "entry_tick": "100.25",
      "exit_tick": "100.50"
    },
    "past_trades_summaries": [
      "Won a CALL trade on R_100; price moved up as expected.",
      "Lost a PUT trade; exited early due to adverse movement."
    ]
  }' | jq .

echo -e "\n=== 4. POST /api/agent_analysis/analyse (JSON + chart) ==="
# Use payload=@file.json (no shell escaping issues); chart needs @ to upload
if [ -f "apps/backend/scripts/chart1.png" ]; then
  curl -s -X POST "$BASE/api/agent_analysis/analyse" \
    -F "payload=@apps/backend/scripts/sample-payload.json" \
    -F "chart_screenshot=@apps/backend/scripts/chart1.png" | jq .
else
  echo "curl -X POST $BASE/api/agent_analysis/analyse -F 'payload=@apps/backend/scripts/sample-payload.json' -F 'chart_screenshot=@path/to/chart.png'"
fi
