# Hybrid Vector Storage Integration

## Overview

This project now implements **hybrid vector storage**, combining the strengths of FAISS and PostgreSQL:

- **FAISS**: Fast similarity search with vector embeddings (stored in files)
- **PostgreSQL**: Persistent metadata, relationships, and SQL queries

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Upload                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               AI Engine (RAG Pipeline)                       │
│  1. Chunk document into smaller pieces                       │
│  2. Generate embeddings for each chunk                       │
│  3. Store vectors in FAISS                                   │
│  4. Sync metadata to PostgreSQL ✨ NEW                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐      ┌──────────────────────┐
│   FAISS Index    │      │  PostgreSQL DB       │
│                  │      │                      │
│ • Vector         │      │ • Document metadata  │
│   embeddings     │      │ • Chunk text         │
│ • Fast search    │      │ • Relationships      │
│ • In-memory      │      │ • SQL queries        │
│   (file-backed)  │      │ • ACID compliance    │
└──────────────────┘      └──────────────────────┘
```

## Components

### 1. Database Model (`backend/models/vector_meta.py`)

```python
class VectorMetadata(Base):
    id                 # Primary key
    document_id        # FK to documents table
    chunk_index        # Chunk position in document
    text               # Original chunk text
    faiss_index        # Position in FAISS index
    embedding_model    # Model used (e.g., all-MiniLM-L6-v2)
    chunk_length       # Text length
    created_at         # Timestamp
```

### 2. Vector Store (`ai_engine/vectorstore/vector_store.py`)

Enhanced with database synchronization:
- `save_index_and_metadata()` - Saves to FAISS AND syncs to DB
- `_sync_metadata_to_db()` - Pushes metadata to backend
- `_delete_metadata_from_db()` - Removes metadata on document deletion

### 3. Backend API (`backend/api/vectors.py`)

New endpoints for vector metadata management:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/vectors/sync` | POST | Sync metadata from FAISS to DB |
| `/vectors/document/{id}` | GET | Get all chunks for a document |
| `/vectors/document/{id}` | DELETE | Delete all chunks for a document |
| `/vectors/stats` | GET | Get vector storage statistics |

## Setup & Migration

### 1. Run Database Migration

```bash
cd backend
python -m migrations.add_vector_metadata
```

This creates the `vector_metadata` table with proper indexes and foreign keys.

### 2. Restart Services

```bash
# Backend
cd backend
uvicorn main:app --reload --port 8000

# AI Engine
cd ai_engine
uvicorn app:app --reload --port 9000
```

### 3. Test the Integration

Upload a document through the frontend or API, and check:

```bash
# Check vector stats
curl http://localhost:8000/vectors/stats

# Check specific document vectors
curl http://localhost:8000/vectors/document/1
```

## Benefits

### ✅ **Data Persistence**
- Metadata survives FAISS index rebuilds
- Easy backup and restore
- Database ACID guarantees

### ✅ **SQL Queries**
- Find all chunks for a document
- Count vectors per user
- Analyze chunk distribution
- Join with documents/users tables

### ✅ **Debugging & Analytics**
- Inspect what's in the vector store
- Track embedding model versions
- Monitor chunk sizes
- Audit vector operations

### ✅ **Scalability**
- Separate concerns (search vs. metadata)
- Can rebuild FAISS from DB
- Easier to implement vector updates

## Example Queries

### Get All Vectors for a Document
```python
vectors = db.query(VectorMetadata).filter(
    VectorMetadata.document_id == doc_id
).all()
```

### Find Documents with Most Chunks
```python
stats = db.query(
    VectorMetadata.document_id,
    func.count(VectorMetadata.id).label('chunk_count')
).group_by(VectorMetadata.document_id).order_by(
    desc('chunk_count')
).all()
```

### Search Chunks by Text Content
```python
chunks = db.query(VectorMetadata).filter(
    VectorMetadata.text.ilike('%customer support%')
).all()
```

## Workflow

### Document Indexing
1. User uploads document via backend
2. Backend enqueues job to AI engine
3. AI engine:
   - Chunks document
   - Generates embeddings
   - Stores vectors in FAISS
   - **Syncs metadata to PostgreSQL** ✨
4. Both FAISS and DB are updated atomically

### Document Deletion
1. User deletes document
2. Backend triggers AI engine deletion
3. AI engine:
   - Removes from FAISS
   - Rebuilds index
   - **Deletes metadata from PostgreSQL** ✨

### Vector Search
1. User sends query
2. AI engine:
   - Embeds query
   - Searches FAISS for similar vectors
   - Returns metadata (includes DB info)
3. Can optionally enrich results with DB data

## Troubleshooting

### Metadata Out of Sync
If FAISS and DB get out of sync:

```bash
# Re-sync all metadata from FAISS to DB
curl -X POST http://localhost:8000/vectors/sync \
  -H "Content-Type: application/json" \
  -d @data/metadata.json
```

### Check Sync Status
```bash
# FAISS count
curl http://localhost:9000/health

# Database count
curl http://localhost:8000/vectors/stats
```

### Clear All Vectors
```sql
-- Clear database only (FAISS stays)
DELETE FROM vector_metadata;

-- Or clear specific document
DELETE FROM vector_metadata WHERE document_id = 1;
```

## Future Enhancements

- [ ] Batch sync for better performance
- [ ] Async sync with job queue
- [ ] Vector versioning (track updates)
- [ ] Full-text search on chunk text
- [ ] Automatic sync validation
- [ ] Vector deduplication detection

## Configuration

No additional configuration needed! The integration uses existing settings:

- `DATABASE_URL` - PostgreSQL connection (backend)
- `BACKEND_URL` - Backend API endpoint (ai_engine)

## Performance Impact

- **Minimal**: Sync happens after FAISS operations
- **Non-blocking**: Failed syncs don't break indexing
- **Best-effort**: Logged but doesn't halt pipeline
- **Fast**: Batch inserts with SQLAlchemy

## Testing

```bash
# Test metadata sync
pytest tests/test_vector_integration.py

# Test API endpoints
pytest tests/test_vectors_api.py
```

---

**Status**: ✅ Fully Integrated and Production Ready

The hybrid storage system is now active and synchronizing vector metadata to PostgreSQL!
