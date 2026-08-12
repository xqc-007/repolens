#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "RepoLens development setup"
echo "Backend:  cd $ROOT/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "Frontend: cd $ROOT/frontend && npm install && npm run dev"
echo "Open:     http://localhost:5173"
