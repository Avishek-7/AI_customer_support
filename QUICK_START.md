# Quick Start

This guide is for running the project locally. For architecture, product direction, and API details, start with `README.md`.

## Before You Start

You need:

- Python 3.10+
- Node.js 18+
- PostgreSQL
- Redis optional for rate limiting and caching
- Google API key for Gemini

## 1. Start PostgreSQL

Create the database before starting the services.

```bash
createdb ai_support
```

If you use a custom database user, make sure your backend `DATABASE_URL` matches it.

## 2. Configure the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with at least:

```env
JWT_SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_support
AI_ENGINE_URL=http://localhost:9000
REDIS_URL=redis://localhost:6379/0
```

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## 3. Configure the AI Engine

```bash
cd ai_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `ai_engine/.env` with at least:

```env
GOOGLE_API_KEY=your-gemini-api-key
BACKEND_URL=http://localhost:8000
```

Start the AI engine:

```bash
cd ai_engine
source .venv/bin/activate
uvicorn app:app --reload --port 9000
```

## 4. Configure the Frontend

```bash
cd frontend
npm install
npm run dev
```

## 5. Open the App

Use these local URLs:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- AI engine docs: `http://localhost:9000/docs`

## 6. Verify the Core Flow

Use this order for a basic sanity check:

1. Register or log in.
2. Upload one document.
3. Ask a question that should retrieve from that document.
4. Confirm the answer includes source-backed behavior.
5. Check admin pages if you need debug or investigation tooling.

## Optional: Verify Vector Metadata Sync

If you are specifically validating the hybrid vector metadata integration:

Run the migration:

```bash
cd backend
python -m migrations.add_vector_metadata
```

Run the integration test helper:

```bash
./run_vector_test.sh
```

Or manually:

```bash
cd backend
source .venv/bin/activate
cd ..
python test_vector_integration.py
```

Inspect vector stats:

```bash
curl http://localhost:8000/vectors/stats \
  -H "X-Internal-API-Key: <internal_service_token>"
```

## Common Problems

### Backend cannot connect to the database

Check:

- PostgreSQL is running.
- `DATABASE_URL` is correct.
- The database exists.

### AI engine fails to answer

Check:

- `GOOGLE_API_KEY` is set.
- Backend is reachable at `BACKEND_URL`.
- AI engine is running on port 9000.

### Frontend loads but requests fail

Check:

- Backend is running on port 8000.
- Frontend environment points to the correct backend URL.
- Browser console shows no auth or CORS failures.

## Related Docs

- Overview and architecture: `README.md`
- Backend contract: `docs/backend-api.md`
- AI engine contract: `docs/ai-engine-api.md`
- Conversation Investigator spec: `docs/conversation-investigator-v1-spec.md`
- Archived implementation notes: `docs/archive/`
