#!/bin/bash
# Quick setup script for async migration

echo "=== Installing Backend Dependencies ==="
cd backend
pip install asyncpg httpx

echo ""
echo "=== Installing AI Engine Dependencies ==="
cd ../ai_engine
pip install httpx

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure your DATABASE_URL is set in .env"
echo "2. Start backend: cd backend && uvicorn main:app --reload"
echo "3. Start AI engine: cd ai_engine && uvicorn app:app --port 8001 --reload"
echo ""
echo "Test endpoints:"
echo "  - POST /auth/register"
echo "  - POST /auth/login"
echo "  - POST /documents/upload"
echo "  - POST /chat/stream"
