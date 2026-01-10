<div align="center">

# 🤖 AI Customer Support

**An intelligent, full-stack customer support platform powered by RAG and Google Gemini**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://rabbitmq.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#️-architecture) • [API Reference](#-api-endpoints) • [Contributing](#-contributing)

---

</div>

## 📸 Screenshots

<div align="center">

| Chat Interface | Document Upload | Conversation History |
|:-:|:-:|:-:|
| ![Chat](docs/screenshots/chat.png) | ![Upload](docs/screenshots/upload.png) | ![History](docs/screenshots/history.png) |

</div>

> 

---

A full-stack AI-powered customer support application with a Next.js frontend, a FastAPI backend, and an AI engine for RAG-based document querying. Upload PDFs, ask questions, and get AI-powered answers with source citations.

## ✨ Features

> 🎯 **Built for production** — Async database operations, background task processing, and streaming responses for a smooth user experience.

<details>
<summary><b>🤖 AI-Powered Chat</b> (click to expand)</summary>

- **RAG (Retrieval-Augmented Generation)** - Answers grounded in your uploaded documents
- **Streaming responses** - Real-time token-by-token AI responses
- **Source citations** - See which documents and chunks were used for each answer
- **Chat history** - Session-based conversation memory for contextual follow-ups
- **Google Gemini LLM** - Powered by `gemini-2.5-flash` model
- **MMR Reranking** - Maximal Marginal Relevance for diverse, non-redundant results
- **Confidence Scoring** - Quality metrics for each answer
- **Hallucination Detection** - Automatic source-answer alignment checking
- **Answer Postprocessing** - Removes duplicates and cleans formatting

</details>

<details>
<summary><b>📄 Document Management</b> (click to expand)</summary>

- **PDF upload** - Drag & drop or browse to upload PDF documents
- **Floating upload modal** - Upload without leaving the chat page
- **Document selection** - Choose which documents to query (or use all)
- **Bulk delete** - Select and delete multiple documents at once
- **Auto-indexing** - Documents are automatically chunked, embedded, and indexed

</details>

<details>
<summary><b>🔐 Authentication</b> (click to expand)</summary>

- **JWT-based auth** - Secure token authentication
- **User registration & login** - Full auth flow with password hashing
- **Protected routes** - Chat and documents require authentication

</details>

<details>
<summary><b>🎨 Modern UI</b> (click to expand)</summary>

- **Dark theme** - Sleek dark mode interface
- **Responsive design** - Works on desktop and mobile
- **Real-time typing indicator** - "AI is thinking..." with animated dots
- **Markdown support** - AI responses render with proper formatting
- **Syntax highlighting** - Code blocks with language-specific highlighting

</details>

<details>
<summary><b>🎯 Advanced Quality Features</b> (click to expand)</summary>

- **Self-Critique** - LLM judges its own answers for accuracy and quality
- **Context Inspection** - Debug and verify retrieved chunks before answering
- **Answer Regeneration** - Regenerate answers with user-specified constraints
- **Hallucination Detection** - Embedding-based alignment scoring (0-1 scale)
- **Risk Assessment** - Low/Medium/High hallucination risk levels

</details>

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  AI Engine  │
│  (Next.js)  │     │  (FastAPI)  │     │    (RAG)    │
│  Port 3000  │     │  Port 8000  │     │  Port 9000  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ PostgreSQL  │ │  RabbitMQ   │ │    Redis    │
    │  Database   │ │   Broker    │ │    Cache    │
    │  Port 5432  │ │  Port 5672  │ │  Port 6379  │
    └─────────────┘ └─────────────┘ └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Celery    │
                    │   Worker    │
                    └─────────────┘
```

### 💬 Chat Request Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   User   │    │ Frontend │    │ Backend  │    │AI Engine │
└────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │               │
     │  Send Message │               │               │
     │──────────────▶│               │               │
     │               │  POST /stream │               │
     │               │──────────────▶│               │
     │               │               │ POST /stream  │
     │               │               │──────────────▶│
     │               │               │               │
     │               │               │   ┌───────────┴───────────┐
     │               │               │   │  1. Embed query       │
     │               │               │   │  2. FAISS search      │
     │               │               │   │  3. MMR reranking     │
     │               │               │   │  4. LLM generation    │
     │               │               │   └───────────┬───────────┘
     │               │               │               │
     │               │               │◀─ SSE tokens ─│
     │               │◀─ SSE tokens ─│               │
     │◀─ Live typing─│               │               │
     │               │               │               │
     │               │               │──┐            │
     │               │               │  │ Save to DB │
     │               │               │◀─┘ (Background)
     │               │               │               │
     ▼               ▼               ▼               ▼
```

### 📄 Document Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT UPLOAD FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

  ┌─────────┐      ┌─────────────┐      ┌─────────────┐      ┌──────────┐
  │  User   │      │   Backend   │      │   Celery    │      │AI Engine │
  │ Upload  │─────▶│  Save Meta  │─────▶│   Worker    │─────▶│  Index   │
  │  PDF    │      │  to DB      │      │  (Async)    │      │ Document │
  └─────────┘      └─────────────┘      └─────────────┘      └──────────┘
                                                                   │
                                                                   ▼
                   ┌─────────────────────────────────────────────────────┐
                   │              AI ENGINE PROCESSING                   │
                   ├─────────────────────────────────────────────────────┤
                   │                                                     │
                   │  ┌──────────┐   ┌──────────┐   ┌──────────────────┐│
                   │  │  Parse   │   │  Chunk   │   │     Embed        ││
                   │  │   PDF    │──▶│  Text    │──▶│   (MiniLM-L6)    ││
                   │  │ (PyMuPDF)│   │(LangChain)│  │                  ││
                   │  └──────────┘   └──────────┘   └────────┬─────────┘│
                   │                                          │         │
                   │                                          ▼         │
                   │                               ┌──────────────────┐ │
                   │                               │   Store in FAISS │ │
                   │                               │   Vector Index   │ │
                   │                               └──────────────────┘ │
                   └─────────────────────────────────────────────────────┘
```

### 🤖 RAG Pipeline (AI Engine)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL-AUGMENTED GENERATION                      │
└─────────────────────────────────────────────────────────────────────────┘

     User Query
         │
         ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Embed     │     │   FAISS     │     │     MMR     │
  │   Query     │────▶│   Search    │────▶│  Reranking  │
  │ (MiniLM-L6) │     │  (top-20)   │     │   (top-5)   │
  └─────────────┘     └─────────────┘     └─────────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────┐
                                    │   Retrieved Chunks     │
                                    │ ┌────┐ ┌────┐ ┌────┐  │
                                    │ │ C1 │ │ C2 │ │ C3 │  │
                                    │ └────┘ └────┘ └────┘  │
                                    └───────────┬────────────┘
                                                │
         ┌──────────────────────────────────────┴──────────────────────┐
         │                                                             │
         ▼                                                             ▼
  ┌─────────────┐                                              ┌─────────────┐
  │   Prompt    │                                              │   Memory    │
  │  Template   │                                              │   (Chat     │
  │ + Context   │                                              │   History)  │
  └──────┬──────┘                                              └──────┬──────┘
         │                                                             │
         └─────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Google Gemini  │
                          │   (LLM Call)    │
                          │ gemini-2.5-flash│
                          └────────┬────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
  │ Confidence  │         │Hallucination│         │    Post     │
  │   Score     │         │  Detection  │         │  Processing │
  └─────────────┘         └─────────────┘         └─────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Final Answer   │
                          │  + Sources +    │
                          │  Quality Scores │
                          └─────────────────┘
```

### 🔐 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

  REGISTER                              LOGIN
  ────────                              ─────
      │                                    │
      ▼                                    ▼
┌───────────┐                        ┌───────────┐
│  Frontend │                        │  Frontend │
│  /register│                        │  /login   │
└─────┬─────┘                        └─────┬─────┘
      │                                    │
      │ POST /auth/register                │ POST /auth/login
      ▼                                    ▼
┌───────────────────┐              ┌───────────────────┐
│     Backend       │              │     Backend       │
├───────────────────┤              ├───────────────────┤
│ 1. Validate input │              │ 1. Find user      │
│ 2. Hash password  │              │ 2. Verify password│
│    (bcrypt)       │              │ 3. Generate JWT   │
│ 3. Save to DB     │              │                   │
└─────────┬─────────┘              └─────────┬─────────┘
          │                                  │
          ▼                                  ▼
   ┌─────────────┐                    ┌─────────────┐
   │   Success   │                    │ JWT Token   │
   │   Message   │                    │  Returned   │
   └─────────────┘                    └──────┬──────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  Store in       │
                                    │  localStorage   │
                                    └─────────────────┘

  PROTECTED REQUEST
  ─────────────────
      │
      ▼
┌───────────────────────────────────────────────┐
│  Request with Authorization: Bearer <token>  │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────┐     ┌───────────────────┐
│  Verify JWT       │────▶│  Get Current User │
│  (python-jose)    │     │  from Database    │
└───────────────────┘     └─────────┬─────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │  Process Request  │
                          │  (chat, docs...)  │
                          └───────────────────┘
```

### 🗄️ Database Schema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE RELATIONSHIPS                          │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐       ┌──────────────────────┐
│        users         │       │     conversations    │
├──────────────────────┤       ├──────────────────────┤
│ id (PK)              │───┐   │ id (PK)              │
│ email                │   │   │ user_id (FK)    ─────┼───┐
│ hashed_password      │   │   │ title                │   │
│ role                 │   │   │ created_at           │   │
│ created_at           │   │   │ updated_at           │   │
└──────────────────────┘   │   └──────────────────────┘   │
           │               │              │               │
           │               │              │               │
           │               │              ▼               │
           │               │   ┌──────────────────────┐   │
           │               │   │    chat_history      │   │
           │               │   ├──────────────────────┤   │
           │               └──▶│ id (PK)              │   │
           │                   │ conversation_id (FK) │◀──┘
           │                   │ user_id (FK)    ─────┼───┐
           │                   │ role (user/assistant)│   │
           │                   │ content              │   │
           │                   │ created_at           │   │
           │                   └──────────────────────┘   │
           │                                              │
           │               ┌──────────────────────────────┘
           │               │
           ▼               ▼
┌──────────────────────┐
│      documents       │
├──────────────────────┤
│ id (PK)              │
│ owner_id (FK)   ─────┼───▶ users.id
│ title                │
│ filename             │
│ file_path            │
│ status               │
│ created_at           │
└──────────────────────┘

Legend: (PK) = Primary Key, (FK) = Foreign Key
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
│   ├── jobs/          # Celery worker and background tasks
│   ├── models/        # SQLAlchemy models
│   └── schemas/       # Pydantic schemas
└── ai_engine/         # RAG pipeline (Python)
    ├── embeddings/    # Sentence transformer embeddings
    ├── llm/           # Gemini LLM integration, prompts, critique & regeneration
    ├── rag/           # Chunking & pipeline orchestration
    ├── retriever/     # FAISS retriever & MMR reranking
    ├── vectorstore/   # FAISS index management
    └── utils/         # Confidence, hallucination detection, postprocessing
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL
- RabbitMQ (for Celery message broker)
- Redis (for caching and rate limiting)
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
DATABASE_URL=postgresql+asyncpg://ai_user:your_password@localhost:5432/ai_support
AI_ENGINE_URL=http://localhost:9000
celery_broker_url=amqp://guest:guest@localhost:5672//
celery_result_backend=rpc://
EOF

# Run the server
uvicorn main:app --reload --port 8000

# In a separate terminal, run the Celery worker
celery -A jobs.worker worker --loglevel=info
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
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | ✅ |
| `AI_ENGINE_URL` | AI engine service URL | ✅ (default: `http://localhost:9000`) |
| `JWT_ALGORITHM` | JWT algorithm | ❌ (default: `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | ❌ (default: `1440`) |
| `celery_broker_url` | RabbitMQ connection URL | ❌ |
| `celery_result_backend` | Celery result backend | ❌ |

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
| POST | `/inspect-context` | View retrieved chunks without generating answer |
| POST | `/critique` | LLM self-critique of answer quality |
| POST | `/regenerate` | Regenerate answer with constraints |

## 🛠️ Tech Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **React Markdown** - Markdown rendering
- **React Syntax Highlighter** - Code highlighting

### Backend
- **FastAPI** - High-performance Python API
- **SQLAlchemy** - Async ORM for PostgreSQL
- **Pydantic** - Data validation
- **bcrypt** - Password hashing
- **python-jose** - JWT handling
- **httpx** - Async HTTP client
- **Celery** - Distributed task queue
- **RabbitMQ** - Message broker for Celery
- **Redis** - Caching and rate limiting

### AI Engine
- **Google Gemini** - LLM (gemini-2.5-flash)
- **Sentence Transformers** - Text embeddings (all-MiniLM-L6-v2)
- **FAISS** - Vector similarity search
- **LangChain** - Text chunking & chat memory
- **PyMuPDF** - PDF text extraction
- **scikit-learn** - Cosine similarity & MMR reranking
- **NumPy** - Vector operations for hallucination detection

## 📁 Data Storage

- **PostgreSQL** - Users, documents, chat history, conversations
- **Redis** - Session caching, rate limiting counters
- **RabbitMQ** - Task queue messages for Celery workers
- **FAISS Index** - Vector embeddings stored in `ai_engine/data/`
  - `faiss_index.bin` - Vector index
  - `metadata.json` - Chunk metadata (text, document_id, title)

## 🔒 Security Notes

- Passwords hashed with bcrypt (12 rounds)
- JWT tokens expire after 24 hours by default
- All document endpoints require authentication
- CORS configured for development (update for production)

## 🧪 Development Tips

> ⚡ **Pro Tip:** Run all three services in separate terminal tabs for the best development experience.

- Use `develop` branch for active work; PR into `main`
- Backend auto-reloads with `--reload` flag
- AI Engine auto-reloads with `--reload` flag
- Frontend has hot module replacement built-in
- Check browser console and terminal for errors

---

## 🗺️ Roadmap

| Status | Feature |
|:------:|:--------|
| ✅ | RAG-based document querying |
| ✅ | Streaming chat responses |
| ✅ | JWT authentication |
| ✅ | Celery background tasks |
| ✅ | Conversation management |
| 🚧 | Multi-language support |
| 🚧 | Admin dashboard |
| 📋 | Docker Compose setup |
| 📋 | Kubernetes deployment |
| 📋 | OAuth (Google, GitHub) |
| 📋 | File type support (DOCX, TXT) |
| 📋 | Analytics & usage metrics |

**Legend:** ✅ Complete | 🚧 In Progress | 📋 Planned

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

> 📝 Please read our contributing guidelines before submitting a PR.

---

## 💬 Support

Having issues? Here's how to get help:

- 🐛 **Bug Reports:** [Open an issue](../../issues/new?template=bug_report.md)
- 💡 **Feature Requests:** [Open an issue](../../issues/new?template=feature_request.md)
- 💬 **Discussions:** [Start a discussion](../../discussions)

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev) - LLM provider
- [LangChain](https://langchain.com) - RAG framework components
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [Sentence Transformers](https://sbert.net) - Text embeddings
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [Next.js](https://nextjs.org) - Frontend framework

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ by [Avishek](https://github.com/avishek)

</div>
