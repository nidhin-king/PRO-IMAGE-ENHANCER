#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

mkdir -p data/jobs data/models

# Start backend API (worker runs in-process)
cd "$ROOT/backend"
python3 -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start frontend (exposed preview port)
cd "$ROOT/frontend"
npm run dev -- --host 0.0.0.0 --port 5173
