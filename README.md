# AI Customer Support

An AI-powered support platform built with Next.js, FastAPI, PostgreSQL, Redis, and a separate RAG AI engine.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)

## Start Here

- Setup guide: `QUICK_START.md`
- Backend API reference: `docs/backend-api.md`
- AI engine API reference: `docs/ai-engine-api.md`
- Current product spec: `docs/conversation-investigator-v1-spec.md`
- Archived engineering notes: `docs/archive/`

## What This Project Does

This repository provides a full-stack customer support system with:

- A Next.js frontend for chat, document management, user profile, and admin tooling.
- A FastAPI backend for authentication, chat persistence, admin endpoints, and document workflows.
- A separate AI engine for retrieval-augmented generation, critique, hallucination analysis, and answer regeneration.

## Core Features

- RAG-based chat grounded in uploaded documents.
- Streaming responses with source citations.
- Document upload, indexing, search, edit, reindex, and deletion workflows.
- JWT authentication and role-based access.
- Conversation history with multi-conversation support.
- Admin dashboard for users, analytics, documents, chats, debug tools, and investigations.
- Quality tooling including confidence scoring, hallucination detection, critique, and constrained regeneration.

## Architecture

```text
Frontend (Next.js, port 3000)
  -> Backend (FastAPI, port 8000)
    -> AI Engine (RAG service, port 9000)

Supporting infrastructure:
- PostgreSQL for users, documents, conversations, chat history, and audit data
- Redis for caching and rate limiting
- FAISS for vector search
```

### Main request flow

1. User sends a message from the frontend.
2. Backend authenticates the user and forwards the request to the AI engine.
3. AI engine embeds the query, retrieves chunks from FAISS, reranks results, and calls Gemini.
4. Backend streams the answer back to the client and persists conversation history.

### Main document flow

1. User uploads a document.
2. Backend stores metadata and triggers indexing work.
3. AI engine parses, chunks, embeds, and indexes the document.
4. Indexed content becomes available for retrieval during chat.

## Project Structure

```text
frontend/   Next.js application
backend/    FastAPI application
ai_engine/  RAG pipeline and LLM service
docs/       API docs, product specs, archived notes
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL
- Redis optional for rate limiting and caching
- Google API key for Gemini

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Required backend environment variables include:

- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `AI_ENGINE_URL`

### AI Engine Setup

```bash
cd ai_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 9000
```

Required AI engine environment variables include:

- `GOOGLE_API_KEY`
- `BACKEND_URL`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Access URLs

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- AI engine docs: `http://localhost:9000/docs`

For fuller setup details, use `QUICK_START.md`.

## Key APIs

### Backend API Highlights

- `POST /auth/register`
- `POST /auth/login`
- `POST /chat/stream`
- `POST /documents/upload`
- `GET /admin/stats`
- `GET /admin/debug/conversations/{conversation_id}`
- `POST /admin/investigations/run`

### AI Engine API Highlights

- `POST /query`
- `POST /stream`
- `POST /inspect-context`
- `POST /critique`
- `POST /regenerate`

See `docs/backend-api.md` and `docs/ai-engine-api.md` for the full contract.

## Data Storage

- PostgreSQL stores users, documents, conversations, chat history, and admin audit data.
- Redis stores cache and rate-limit state.
- FAISS stores vector embeddings under `ai_engine/data/`.

## Security Notes

- Passwords are hashed with bcrypt.
- JWTs are used for authenticated requests.
- Admin endpoints require admin role checks.
- Internal service endpoints use internal API key checks.
- CORS is configured for development and should be hardened for production.

## Current Focus

The current product direction is an internal support copilot, starting with an admin-only, read-only Conversation Investigator. The authoritative V1 spec is in `docs/conversation-investigator-v1-spec.md`.

## Development Notes

- Run frontend, backend, and AI engine in separate terminals.
- Use backend and AI engine auto-reload during development.
- Check browser console and service logs together when debugging cross-service issues.
- Historical migration notes and summaries have been moved into `docs/archive/`.

## Roadmap Snapshot

- Complete: RAG chat, streaming, auth, document workflows, admin dashboard, critique/debug tooling
- In progress: internal support copilot workflow
- Planned: broader analytics, additional file types, OAuth, deployment hardening

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a pull request.

## Support

- Bug reports: `../../issues/new?template=bug_report.md`
- Feature requests: `../../issues/new?template=feature_request.md`
- Discussions: `../../discussions`

## Acknowledgments

- Google Gemini
- LangChain
- FAISS
- Sentence Transformers
- FastAPI
- Next.js

## License

This project is licensed under the MIT License. See `LICENSE` for details.
