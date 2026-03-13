"""Pytest configuration and fixtures for backend tests."""
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path so imports work correctly
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up test environment variables before any imports
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AI_ENGINE_URL", "http://localhost:9000")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-api-key-for-testing-only")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RATE_LIMIT_FAIL_CLOSED_ON_REDIS_UNAVAILABLE", "false")
os.environ.setdefault("PYTHONPATH", str(backend_dir))
