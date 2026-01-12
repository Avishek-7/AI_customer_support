# AI Engine API Contract

> **Version**: 1.0.0  
> **Last Updated**: January 12, 2026  
> **Base URL**: `http://localhost:8001`  
> **Service**: RAG Microservice (Embedding, Retrieval, Generation)

This document defines the complete API contract for the AI Engine microservice. This is an internal service called by the Backend API.

---

## Table of Contents

1. [Overview](#overview)
2. [Health Endpoints](#health-endpoints)
3. [Document Indexing](#document-indexing)
4. [Query Endpoints](#query-endpoints)
5. [Quality & Critique](#quality--critique)
6. [Debug Endpoints](#debug-endpoints)
7. [Internal Architecture](#internal-architecture)
8. [Configuration](#configuration)
9. [Error Handling](#error-handling)

---

## Overview

The AI Engine is the core RAG (Retrieval-Augmented Generation) microservice that handles:

| Component | Technology | Description |
|-----------|------------|-------------|
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | 384-dim embeddings |
| **Vector Store** | FAISS (IndexFlatL2) | In-memory similarity search |
| **LLM** | Google Gemini 2.5 Flash | Answer generation |
| **Chunking** | LangChain RecursiveCharacterTextSplitter | 800 chars, 200 overlap |

### Authentication

| Property | Value |
|----------|-------|
| Auth Required | ❌ No (internal service) |
| Access | Backend API only |

---

## Health Endpoints

### `GET /`

Root endpoint with service info.

**Response (200):**
```json
{
  "status": "AI Engine is running",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "index": "POST /index-document",
    "query": "POST /query"
  }
}
```

---

### `GET /health`

Health check endpoint.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "ai-engine"
}
```

---

## Document Indexing

### `POST /index-document`

Index a new document into FAISS.

**Request Body:**
```json
{
  "document_id": 1,
  "title": "User Manual",
  "content": "Full document text content..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | integer | ✅ | Unique document ID from backend |
| `title` | string | ✅ | Document title |
| `content` | string | ✅ | Full document text |

**Response (200):**
```json
{
  "document_id": 1,
  "chunks_indexed": 0
}
```

> **Note**: Returns `chunks_indexed: 0` immediately because indexing runs in background.

**Side Effects:**
- Chunks document (800 chars, 200 overlap)
- Generates embeddings for each chunk
- Stores in FAISS index
- Syncs metadata to backend PostgreSQL
- Sends status callbacks to backend:
  - `processing` → `chunking` → `embedding` → `saving` → `completed`

**Processing Pipeline:**
```
content → chunk_text() → embed_texts() → add_embeddings() → save_index()
                                                      ↓
                                         POST /documents/update-status
```

---

### `PUT /update-document`

Update an existing document (delete + re-index).

**Request Body:**
```json
{
  "document_id": 1,
  "title": "Updated User Manual",
  "content": "Updated document text..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | integer | ✅ | Document ID to update |
| `title` | string | ✅ | New title |
| `content` | string | ✅ | New content |

**Response (200):**
```json
{
  "document_id": 1,
  "chunks_indexed": 15
}
```

**Side Effects:**
- Deletes all old vectors for document
- Deletes metadata from PostgreSQL
- Re-chunks and re-embeds content
- Adds new vectors to FAISS
- Syncs new metadata to backend

---

### `DELETE /delete-document/{document_id}`

Delete a document from FAISS.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `document_id` | integer | Document ID to delete |

**Response (200):**
```json
{
  "document_id": 1,
  "status": "deleted"
}
```

**Side Effects:**
- Removes all chunks from FAISS index
- Deletes metadata from PostgreSQL
- Rebuilds FAISS index (required for deletion)

---

## Query Endpoints

### `POST /query`

Run full RAG pipeline (synchronous).

**Request Body:**
```json
{
  "session_id": "user-123",
  "query": "How do I reset my password?",
  "system_prompt": "You are an AI customer support assistant.",
  "document_ids": [1, 2, 3],
  "k": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `session_id` | string | ✅ | - | User/session identifier for memory |
| `query` | string | ✅ | - | User's question |
| `system_prompt` | string | ❌ | "You are an AI customer support assistant." | Custom system instruction |
| `document_ids` | integer[] | ❌ | `null` (all docs) | Filter to specific documents |
| `k` | integer | ❌ | `5` | Number of chunks to retrieve |

**Response (200):**
```json
{
  "answer": "To reset your password, go to Settings > Security > Reset Password...",
  "sources": [
    {
      "document_id": 1,
      "chunk_id": 5,
      "title": "Security Guide",
      "text": "To reset your password, navigate to...",
      "score": 0.89
    }
  ]
}
```

| Response Field | Type | Description |
|----------------|------|-------------|
| `answer` | string | LLM-generated answer |
| `sources` | array | Retrieved chunks with metadata |
| `sources[].document_id` | integer | Source document ID |
| `sources[].chunk_id` | integer | Chunk index in document |
| `sources[].title` | string | Document title |
| `sources[].text` | string | Full chunk text |
| `sources[].score` | float | Similarity score (0-1) |

**RAG Pipeline:**
```
query → embed_text() → FAISS search → MMR rerank → LLM generate → postprocess
           ↓               ↓              ↓            ↓
       384-dim          top-k        diversity    Gemini 2.5
       vector          chunks        selection      Flash
```

---

### `POST /stream`

Run RAG pipeline with streaming response (SSE).

**Request Body:** Same as `/query`

**Response (SSE Stream):**
```
data: {"type": "token", "content": "To"}

data: {"type": "token", "content": " reset"}

data: {"type": "token", "content": " your"}

data: {"type": "sources", "sources": [...]}

data: {"type": "end"}
```

| Event Type | Description |
|------------|-------------|
| `token` | Individual response token |
| `sources` | Retrieved source documents |
| `error` | Error message if generation fails |
| `end` | Stream complete |

**Content-Type:** `text/event-stream`

---

### `POST /inspect-context`

Inspect retrieved chunks without generating an answer.

**Request Body:**
```json
{
  "query": "How do I reset my password?",
  "document_ids": [1, 2],
  "k": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | ✅ | - | Query to search for |
| `document_ids` | integer[] | ❌ | `null` (all) | Filter documents |
| `k` | integer | ❌ | `5` | Number of chunks |

**Response (200):**
```json
{
  "query": "How do I reset my password?",
  "chunks": [
    {
      "document_id": 1,
      "chunk_id": 5,
      "title": "Security Guide",
      "text": "To reset your password, navigate to Settings...",
      "score": 0.89
    }
  ],
  "total_retrieved": 5
}
```

**Use Cases:**
- Debug retrieval quality
- Understand what context LLM receives
- Verify document indexing

---

## Quality & Critique

### `POST /critique`

Self-critique an answer for quality, accuracy, and hallucination.

**Request Body:**
```json
{
  "question": "How do I reset my password?",
  "answer": "To reset your password, go to Settings > Security...",
  "sources": [
    {
      "text": "To reset your password, navigate to Settings...",
      "document_id": 1
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | ✅ | Original question |
| `answer` | string | ✅ | Answer to evaluate |
| `sources` | array | ✅ | Source chunks used |

**Response (200):**
```json
{
  "critique": {
    "llm_critique": {
      "accuracy_score": 9,
      "relevance_score": 10,
      "completeness_score": 8,
      "clarity_score": 9,
      "overall_score": 9,
      "strengths": ["Accurate", "Well-structured"],
      "weaknesses": ["Could add more detail"],
      "suggestions": ["Include screenshots"],
      "grounded_in_context": true,
      "summary": "Good answer that accurately addresses the question."
    },
    "hallucination_detection": {
      "hallucination_score": 0.12,
      "alignment_score": 0.88,
      "details": {
        "max_source_similarity": 0.91,
        "avg_source_similarity": 0.75,
        "keyword_overlap": 0.82,
        "num_sources": 3,
        "answer_length": 156,
        "risk_level": "low"
      }
    }
  }
}
```

**Critique Scores:**
| Score | Range | Description |
|-------|-------|-------------|
| `accuracy_score` | 0-10 | Factual correctness |
| `relevance_score` | 0-10 | Relevance to question |
| `completeness_score` | 0-10 | Answer completeness |
| `clarity_score` | 0-10 | Clarity of explanation |
| `overall_score` | 0-10 | Combined quality score |

**Hallucination Scores:**
| Score | Range | Description |
|-------|-------|-------------|
| `hallucination_score` | 0.0-1.0 | Risk of hallucination (lower = better) |
| `alignment_score` | 0.0-1.0 | Alignment with sources (higher = better) |
| `risk_level` | low/medium/high | Human-readable risk |

---

### `POST /regenerate`

Regenerate an answer with specific constraints.

**Request Body:**
```json
{
  "session_id": "user-123",
  "query": "How do I reset my password?",
  "constraints": "Make it shorter and use bullet points",
  "system_prompt": "You are an AI customer support assistant.",
  "document_ids": [1, 2],
  "k": 5,
  "previous_answer": "The previous long answer..."
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `session_id` | string | ✅ | - | Session identifier |
| `query` | string | ✅ | - | Original question |
| `constraints` | string | ✅ | - | Modification instructions |
| `system_prompt` | string | ❌ | Default | System prompt |
| `document_ids` | integer[] | ❌ | `null` | Document filter |
| `k` | integer | ❌ | `5` | Chunks to retrieve |
| `previous_answer` | string | ❌ | `null` | Previous answer to improve |

**Response (200):**
```json
{
  "answer": "To reset your password:\n• Go to Settings\n• Click Security\n• Select Reset Password",
  "sources": [...],
  "regeneration_info": {
    "constraints_applied": "Make it shorter and use bullet points",
    "had_previous_answer": true,
    "sources_used": 5
  }
}
```

**Example Constraints:**
- `"Make it shorter"`
- `"Add more detail"`
- `"Use simpler language"`
- `"Be more technical"`
- `"Use bullet points"`
- `"Include step-by-step instructions"`

---

## Debug Endpoints

### `GET /debug/document/{document_id}`

Show all chunks stored for a document.

**Response (200):**
```json
{
  "document_id": 1,
  "total_chunks_in_index": 150,
  "chunks_for_document": 15,
  "chunks": [
    {
      "chunk_id": 0,
      "title": "User Manual",
      "text_preview": "First 200 characters of chunk..."
    }
  ]
}
```

---

### `GET /debug/all-documents`

List all documents in FAISS index.

**Response (200):**
```json
{
  "total_vectors": 150,
  "documents": [
    {
      "document_id": 1,
      "title": "User Manual",
      "chunk_count": 15
    },
    {
      "document_id": 2,
      "title": "FAQ",
      "chunk_count": 8
    }
  ]
}
```

---

### `GET /debug/search-preview`

Preview search results for a query.

**Query Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | ✅ | - | Search query |
| `document_id` | integer | ❌ | `null` | Filter to document |
| `k` | integer | ❌ | `5` | Number of results |

**Response (200):**
```json
{
  "query": "password reset",
  "document_filter": null,
  "results_count": 5,
  "chunks": [
    {
      "document_id": 1,
      "chunk_id": 5,
      "title": "Security Guide",
      "score": 0.89,
      "text_preview": "First 300 characters..."
    }
  ]
}
```

---

## Internal Architecture

### Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `chunk_size` | 800 chars | Balance context vs. noise |
| `chunk_overlap` | 200 chars | Preserve context across boundaries |
| Splitter | `RecursiveCharacterTextSplitter` | Smart splitting at sentences |

### Embedding Model

| Property | Value |
|----------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimension | 384 |
| Type | Dense embeddings |
| Caching | LRU cache (model loads once) |

### Vector Store

| Property | Value |
|----------|-------|
| Backend | FAISS `IndexFlatL2` |
| Storage | `data/faiss_index.bin` |
| Metadata | `data/metadata.json` |
| Similarity | L2 (Euclidean) distance |

### LLM Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gemini-2.5-flash` |
| Temperature | 0.2 (focused) |
| Max Tokens | 1536 |
| Top-P | 0.8 (nucleus sampling) |

### Retrieval Pipeline

```
1. Query Embedding    → embed_text(query) → 384-dim vector
2. FAISS Search       → search_embeddings(k=10) → top-k candidates
3. Document Filter    → filter by document_ids if provided
4. MMR Reranking      → diversity selection (λ=0.7)
5. Context Assembly   → join chunks with separators
6. LLM Generation     → Gemini with prompt template
7. Postprocessing     → remove duplicates, clean formatting
```

### Hallucination Detection Algorithm

```python
# 1. Embedding-based similarity
answer_emb = embed_text(answer)
source_embs = embed_texts(sources)
max_similarity = max(cosine_similarity(answer_emb, source_embs))
avg_similarity = mean(cosine_similarity(answer_emb, source_embs))

# 2. Keyword overlap (after removing stop words)
keyword_overlap = |answer_words ∩ source_words| / |answer_words|

# 3. Combined score
alignment_score = 0.6 * max_similarity + 0.3 * avg_similarity + 0.1 * keyword_overlap
hallucination_score = 1.0 - alignment_score
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | ✅ | - | Gemini API key |
| `BACKEND_URL` | ❌ | `http://localhost:8000` | Backend API URL |

### Files

| File | Description |
|------|-------------|
| `data/faiss_index.bin` | FAISS index binary |
| `data/metadata.json` | Chunk metadata (document_id, text, etc.) |
| `logs/ai_engine.log` | Structured JSON logs |

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

| Code | Scenario | Description |
|------|----------|-------------|
| `400` | Invalid request | Missing required fields |
| `404` | Document not found | No vectors for document_id |
| `500` | LLM error | Gemini API failure |
| `500` | Index error | FAISS operation failed |

### Streaming Errors

```
data: {"type": "error", "message": "LLM generation failed: API timeout"}

data: {"type": "end"}
```

---

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|-----------------|-------|
| Embedding (single) | 10-50ms | GPU accelerated if available |
| Embedding (batch) | 100-500ms | Batched for efficiency |
| FAISS search (k=5) | 1-5ms | In-memory, very fast |
| LLM generation | 1-3s | Depends on output length |
| Full RAG query | 2-4s | End-to-end |
| Streaming (first token) | 500ms-1s | Time to first byte |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-12 | Initial API contract freeze |
