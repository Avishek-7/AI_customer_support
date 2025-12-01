# AI Customer Support

A full-stack AI-powered customer support application with a Next.js frontend, a FastAPI backend, and an AI engine for RAG-based document querying.

## Project Structure

- `frontend/`: Next.js app (UI)
- `backend/`: FastAPI service (API, auth, DB)
- `ai_engine/`: Retrieval-Augmented Generation pipeline and utilities

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Yarn or npm
- PostgreSQL (or your configured DB)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### AI Engine (RAG)
```bash
cd ai_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if present; else install needed libs
python app.py
```

## Configuration
- Backend config: `backend/core/config.py`
- AI engine config: `ai_engine/utils/config.py`
- Environment variables: create `.env` files per service as needed.

### Environment Variables

Create a `.env` file in each service folder (`backend/` and `ai_engine/`).

Backend `.env` (required):
```
JWT_SECRET_KEY=your-secret
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ai_support
# Optional overrides
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

AI Engine `.env` (required):
```
GOOGLE_API_KEY=your-gemini-api-key
```

### Database Setup
- The backend uses SQLAlchemy. Configure `DATABASE_URL` for PostgreSQL.
- Example local setup:
```bash
createdb ai_support
psql ai_support -c "CREATE USER ai_user WITH PASSWORD 'ai_pass';"
psql ai_support -c "GRANT ALL PRIVILEGES ON DATABASE ai_support TO ai_user;"
```
- Tables are defined in `backend/models/`. On first run, ensure models are imported and metadata is created (migrations TBD).

## Development Tips
- Use `develop` branch for active work; PR into `main`.
- Keep documents organized for ingestion under appropriate data folders.
- Run services independently during development (frontend, backend, ai_engine).

## AI Engine Dependencies
The AI engine uses:
- `google-generativeai` (Gemini LLM)
- `sentence-transformers` for embeddings
- `faiss` for vector search
- `langchain_core`, `langchain_text_splitters`, `langchain_community` for chunking/loading
- `PyPDFLoader` via `langchain_community` for PDF ingestion

Install manually if `ai_engine/requirements.txt` is not present:
```bash
pip install google-generativeai sentence-transformers faiss-cpu langchain langchain-text-splitters langchain-community
```

## License
TBD.
