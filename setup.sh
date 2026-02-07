#!/bin/bash
# Setup script for ai-trader-education-bot

set -e

echo "=== Frontend setup ==="
npm install
echo "Frontend deps installed."

echo ""
echo "=== Backend setup ==="
cd apps/backend
uv sync
cd ../..

echo ""
echo "=== Setup complete ==="
echo "To start:"
echo "  Frontend: npm start"
echo "  Backend:  npm run dev:agent"
echo "(Run in separate terminals)"
