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

Security controls for `backend/api/vectors.py`:

Implemented:
- Require authenticated service-to-service access for `POST /vectors/sync`, `DELETE /vectors/document/{id}`, `GET /vectors/document/{id}`, and `GET /vectors/stats}` via `X-Internal-API-Key`
- Require authenticated service-to-service access for `POST /vectors/sync`, `DELETE /vectors/document/{id}`, `GET /vectors/document/{id}`, and `GET /vectors/stats` via `X-Internal-API-Key`
- Restrict sensitive write/delete routes to internal-network callers
- Validate `{id}` as an integer at the FastAPI route layer

Recommended:
- Enforce finer-grained authorization scopes such as `vectors:write` / `vectors:delete`
- Add explicit request auditing fields (actor, timestamp, request metadata, outcome)
- Apply rate limiting where operationally appropriate
- Enforce TLS in transit and avoid leaking internal error details in responses

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
curl http://localhost:8000/vectors/stats \
    -H "X-Internal-API-Key: <internal_service_token>"

# Check specific document vectors
curl http://localhost:8000/vectors/document/1 \
    -H "X-Internal-API-Key: <internal_service_token>"
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
4. FAISS and DB are updated using best-effort, eventually-consistent synchronization (not a distributed atomic transaction)

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
    -H "X-Internal-API-Key: <internal_service_token>" \
  -d @data/metadata.json
```

`data/metadata.json` should match the `VectorMetadata` contract used by `/vectors/sync`:

```json
{
    "metadata": [
        {
            "document_id": 1,
            "chunk_index": 0,
            "title": "Getting Started",
            "text": "Sample chunk text..."
        },
        {
            "document_id": 1,
            "chunk_index": 1,
            "title": "Getting Started",
            "text": "Another chunk..."
        }
    ]
}
```

Required fields per chunk item: `document_id` (int), `chunk_index` (int), `text` (string).
Optional but recommended: `title` (string).

Backward-compatibility note: the current sync endpoint accepts legacy `chunk_id` payloads, but the canonical contract is `chunk_index`.

### Check Sync Status
```bash
# FAISS count
curl http://localhost:9000/health

# Database count
curl http://localhost:8000/vectors/stats \
    -H "X-Internal-API-Key: <internal_service_token>"
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
- **Best-effort / eventual consistency**: FAISS does not provide ACID transactions and there is no 2PC across FAISS and PostgreSQL
- **Fast**: Batch inserts with SQLAlchemy

## Testing

```bash
# Test metadata sync
pytest tests/test_vector_integration.py

# Test API endpoints
pytest tests/test_vectors_api.py
```

---

**Status**: ✅ Integrated - Review deployment checklist

### Consistency & Atomicity
- Current model is eventually consistent with best-effort sync between FAISS and PostgreSQL.
- True cross-store atomicity is not implemented (no distributed transaction mechanism).

### Authentication & Authorization
- Protect `/vectors/sync` and `/vectors/document/{id}` behind authenticated service routes.
- Restrict destructive operations to admin/service identities only.

### Error Handling & Monitoring
- Surface sync failures in logs/metrics and retry with bounded backoff where appropriate.
- Track divergence indicators (FAISS count vs DB metadata count) and alert on sustained mismatch.

### Retry and Backoff Behavior
- Current implementation: no automatic retry/backoff is implemented in the live sync path; sync is best-effort and failures are logged.
- Recommended future strategy: exponential backoff with jitter, for example base delay 1s, doubling up to a 30s cap, with 3 to 5 attempts per sync operation.
- Operator mitigation today: review structured logs, compare `/vectors/stats` output against expected indexed documents, and run a manual re-sync when needed.
- Recommended monitoring: counters for sync failures, alerts on sustained divergence, and a manual or queued reconciliation procedure for repeated failures.

### Monitoring & Metrics
📋 **Recommended metrics**

- Expose these metrics on application `/metrics` (Prometheus format):
    - `vector_storage.faiss.count` gauge (Prometheus name: `vector_storage_faiss_count`)
    - `vector_storage.db.count` gauge (Prometheus name: `vector_storage_db_count`)
    - `vector_storage.sync.failures` counter (Prometheus name: `vector_storage_sync_failures`)
    - `vector_storage.divergence` gauge = `abs(faiss_count - db_count)`
- Emit/update all four metrics during sync, delete, and periodic reconciliation jobs so dashboards reflect both write-path and background consistency checks.
- Log every sync failure with structured fields (`document_id`, operation type, status/error, retry attempt, request/correlation id) so metric spikes can be traced to concrete failures.

Alerting examples:
- **Warning**: divergence > 100 vectors or >5% for 15m.
- **Critical**: divergence > 1000 vectors or >10% for 30m.
- **Warning**: sync failure rate >5% over 15m.

Recommended integrations:
- Prometheus + Alertmanager (primary reference stack).
- CloudWatch/Datadog equivalent monitors for teams not running Prometheus directly.

### Sync Failure Runbook
1. Detect mismatch via `/vectors/stats` and operational metrics.
2. Triage recent indexing/deletion logs for failed sync attempts.
3. Re-run controlled metadata sync from `data/metadata.json`.
4. Re-verify counts and sample retrievals before resuming normal write traffic.

The hybrid storage system is now active and synchronizing vector metadata to PostgreSQL!
