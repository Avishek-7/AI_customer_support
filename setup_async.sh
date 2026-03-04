#!/bin/bash
# Quick setup script for async migration

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
AI_ENGINE_DIR="$ROOT_DIR/ai_engine"

echo "=== Installing Backend Dependencies ==="
if [[ ! -d "$BACKEND_DIR" ]]; then
	echo "Error: backend directory not found at $BACKEND_DIR" >&2
	exit 1
fi

(
	cd "$BACKEND_DIR"
	pip install asyncpg httpx
)

echo ""
echo "=== Installing AI Engine Dependencies ==="
if [[ ! -d "$AI_ENGINE_DIR" ]]; then
	echo "Error: ai_engine directory not found at $AI_ENGINE_DIR" >&2
	exit 1
fi

(
	cd "$AI_ENGINE_DIR"
	pip install httpx
)

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure your DATABASE_URL is set in .env"
echo "2. Start backend: cd backend && uvicorn main:app --reload"
echo "3. Start AI engine: cd ai_engine && uvicorn app:app --port 9000 --reload"
echo ""
echo "Test endpoints:"
echo "  - POST /auth/register"
echo "  - POST /auth/login"
echo "  - POST /documents/upload"
echo "  - POST /chat/stream"
