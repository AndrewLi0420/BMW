#!/bin/bash
set -e

cd "$(dirname "$0")"

# 1. Python venv + deps
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q

# 2. Copy .env if missing
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  Created .env from .env.example — please add your API keys before running AI features."
fi

# 3. Seed DB on first run (downloads XLSX if needed)
python backend/seed.py

# 4. Start backend
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

# 5. Start frontend
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID $FRONTEND_PID)"

echo ""
echo "✅ BMW Battery Intelligence Dashboard running at http://localhost:5173"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on Ctrl+C
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
