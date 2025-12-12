# AI Customer Support

A full-stack AI-powered customer support application with a Next.js frontend, a FastAPI backend, and an AI engine for RAG-based document querying. Upload PDFs, ask questions, and get AI-powered answers with source citations.

## ✨ Features

### 🤖 AI-Powered Chat
- **RAG (Retrieval-Augmented Generation)** - Answers grounded in your uploaded documents
- **Streaming responses** - Real-time token-by-token AI responses
- **Source citations** - See which documents and chunks were used for each answer
- **Chat history** - Session-based conversation memory for contextual follow-ups
- **Google Gemini LLM** - Powered by `gemini-2.5-flash` model

### 📄 Document Management
- **PDF upload** - Drag & drop or browse to upload PDF documents
- **Floating upload modal** - Upload without leaving the chat page
- **Document selection** - Choose which documents to query (or use all)
- **Bulk delete** - Select and delete multiple documents at once
- **Auto-indexing** - Documents are automatically chunked, embedded, and indexed

### 🔐 Authentication
- **JWT-based auth** - Secure token authentication
- **User registration & login** - Full auth flow with password hashing
- **Protected routes** - Chat and documents require authentication

### 🎨 Modern UI
- **Dark theme** - Sleek dark mode interface
- **Responsive design** - Works on desktop and mobile
- **Real-time typing indicator** - "AI is thinking..." with animated dots
- **Markdown support** - AI responses render with proper formatting
- **Syntax highlighting** - Code blocks with language-specific highlighting

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  AI Engine  │
│  (Next.js)  │     │  (FastAPI)  │     │    (RAG)    │
│  Port 3000  │     │  Port 8000  │     │  Port 9000  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │  Database   │
                    └─────────────┘
```

## Project Structure

```
ai-customer-support/
├── frontend/          # Next.js 15 app (TypeScript, Tailwind CSS)
│   ├── app/           # App router pages (chat, login, register, documents)
│   └── components/    # Reusable components (ChatBubble, UploadModal, etc.)
├── backend/           # FastAPI service (Python)
│   ├── api/           # Route handlers (auth, chat, documents)
│   ├── core/          # Config, database, security
│   ├── models/        # SQLAlchemy models
│   └── schemas/       # Pydantic schemas
└── ai_engine/         # RAG pipeline (Python)
    ├── embeddings/    # Sentence transformer embeddings
    ├── llm/           # Gemini LLM integration & prompts
    ├── rag/           # Chunking & pipeline orchestration
    ├── retriever/     # FAISS retriever
    └── vectorstore/   # FAISS index management
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL
- Google API Key (for Gemini)

### 1. Database Setup
```bash
# Create PostgreSQL database
createdb ai_support

# Or with user/password
psql -c "CREATE DATABASE ai_support;"
psql -c "CREATE USER ai_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_support TO ai_user;"
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
JWT_SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql+psycopg2://ai_user:your_password@localhost:5432/ai_support
AI_ENGINE_URL=http://localhost:9000
EOF

# Run the server
uvicorn main:app --reload --port 8000
```

### 3. AI Engine Setup
```bash
cd ai_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your-gemini-api-key
BACKEND_URL=http://localhost:8000
EOF

# Run the server
uvicorn app:app --reload --port 9000
```

### 4. Frontend Setup
```bash
cd frontend
npm install

# Run the dev server
npm run dev
```

### 5. Access the App
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- AI Engine API: http://localhost:9000/docs

## 📝 Environment Variables

### Backend `.env`
| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET_KEY` | Secret key for JWT signing | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `AI_ENGINE_URL` | AI engine service URL | ✅ (default: `http://localhost:9000`) |
| `JWT_ALGORITHM` | JWT algorithm | ❌ (default: `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | ❌ (default: `1440`) |

### AI Engine `.env`
| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key | ✅ |
| `BACKEND_URL` | Backend service URL | ❌ (default: `http://localhost:8000`) |

## 🔌 API Endpoints

### Backend (Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/documents/` | List user's documents |
| POST | `/documents/upload` | Upload PDF document |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/chat/stream` | Stream chat response (SSE) |

### AI Engine (Port 9000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/index-document` | Index document for RAG |
| POST | `/query` | Query documents (non-streaming) |
| POST | `/stream` | Query documents (streaming) |
| PUT | `/update-document` | Re-index updated document |
| DELETE | `/delete-document/{id}` | Remove document from index |

## 🛠️ Tech Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **React Markdown** - Markdown rendering
- **React Syntax Highlighter** - Code highlighting

### Backend
- **FastAPI** - High-performance Python API
- **SQLAlchemy** - ORM for PostgreSQL
- **Pydantic** - Data validation
- **bcrypt** - Password hashing
- **python-jose** - JWT handling
- **httpx** - Async HTTP client

### AI Engine
- **Google Gemini** - LLM (gemini-2.0-flash-exp)
- **Sentence Transformers** - Text embeddings (all-MiniLM-L6-v2)
- **FAISS** - Vector similarity search
- **LangChain** - Text chunking utilities
- **PyMuPDF** - PDF text extraction

## 📁 Data Storage

- **PostgreSQL** - Users, documents, chat history
- **FAISS Index** - Vector embeddings stored in `ai_engine/data/`
  - `faiss_index.bin` - Vector index
  - `metadata.json` - Chunk metadata (text, document_id, title)

## 🔒 Security Notes

- Passwords hashed with bcrypt (12 rounds)
- JWT tokens expire after 24 hours by default
- All document endpoints require authentication
- CORS configured for development (update for production)

## 🧪 Development Tips

- Use `develop` branch for active work; PR into `main`
- Backend auto-reloads with `--reload` flag
- AI Engine auto-reloads with `--reload` flag
- Frontend has hot module replacement built-in
- Check browser console and terminal for errors

## 📄 License

TBD
