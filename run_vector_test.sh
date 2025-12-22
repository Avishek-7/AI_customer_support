#!/bin/bash

# Quick test script for hybrid vector storage integration
# This script runs the test from the backend virtual environment

set -e

echo "🚀 Testing Hybrid Vector Storage Integration"
echo "=============================================="
echo ""

# Check if we're in the project root
if [ ! -d "backend" ] || [ ! -d "ai_engine" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env not found"
    echo "   Please create backend/.env with DATABASE_URL and JWT_SECRET_KEY"
    exit 1
fi

# Check if backend venv exists
if [ ! -d "backend/.venv" ]; then
    echo "❌ Error: backend/.venv not found"
    echo "   Please create virtual environment: cd backend && python -m venv .venv"
    exit 1
fi

echo "✓ Project structure verified"
echo "✓ Environment file found"
echo "✓ Virtual environment found"
echo ""

# Activate backend venv and run test
echo "Running tests in backend environment..."
echo ""

cd backend
source .venv/bin/activate
cd ..
python test_vector_integration.py

echo ""
echo "✅ Test completed!"
