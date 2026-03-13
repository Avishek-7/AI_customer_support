# Async Migration Summary

## Overview
Migrated backend and AI engine to async-first I/O patterns and removed blocking calls from async request paths.

## Backend Changes

### 1. Database Layer (`backend/core/database.py`)
- **Before**: Sync `create_engine` with `Session`
- **After**: `create_async_engine` with `AsyncSession` and `async_sessionmaker`
- URL conversion: `DATABASE_URL` may use `postgresql://`, `postgres://`, or an existing async scheme; `backend/core/database.py` transparently upgrades supported PostgreSQL URLs to `postgresql+asyncpg://` for runtime async use
- Dependency: `get_db()` is now async with `async with` context manager

### 2. API Routes - All Converted to Async

#### `backend/api/auth.py`
- All routes (`register_user`, `login_user`, `reset_password`, `forgot_password`) now `async def`
- Database queries use `await db.execute(select(...))` with `.scalar_one_or_none()`
- Commits/refreshes are awaited: `await db.commit()`, `await db.refresh()`

#### `backend/api/documents.py`
- All document operations async: upload, get, update, delete, search, reindex
- HTTP calls already used `httpx.AsyncClient` ✓
- Database operations migrated to async pattern
- Helper function `check_document_ownership` updated to async

#### `backend/api/chat.py`
- `chat_with_ai` and `chat_stream` migrated to async
- Document queries use async SELECT statements
- Already used `httpx.AsyncClient` for AI engine communication ✓

#### `backend/api/users.py`
- All CRUD operations async: `get_me`, `list_users`, `get_user`, `create_user`, `update_user`, `delete_user`
- Email uniqueness checks use async queries
- Admin operations properly await commits

#### `backend/api/vectors.py`
- `sync_vector_metadata`: Async with batch delete and insert
- `delete_vector_metadata`: Uses `sql_delete()` with async execution
- `get_vector_metadata`: Async query with `.scalars().all()`

### 3. Utilities

#### `backend/utils/permissions.py`
- All helpers converted to async:
  - `get_conversation()`
  - `check_document_ownership()`
  - `check_chat_ownership()`
- Use `select()` with `await db.execute()`

### 4. Dependencies
**Added to `backend/requirements.txt`:**
- `httpx` - Async HTTP client
- `asyncpg` - Async PostgreSQL driver for SQLAlchemy

## AI Engine Changes

### 1. Vectorstore (`ai_engine/vectorstore/vector_store.py`)
- **Before**: Used blocking `requests.post/delete`
- **After**: Uses explicit sync path for sync callers and async path for async callers
- Avoid async-to-sync runtime fallback in async execution paths
- Background tasks should use lifecycle-safe patterns (task tracking + callbacks / safe wrapper / TaskGroup)

### 2. Pipeline (`ai_engine/rag/pipeline.py`)
- `index_document` already async ✓
- `update_status` already async ✓
- `answer_query_stream` already async ✓
- All use proper async/await chains

### 3. Dependencies
**Added to `ai_engine/requirements.txt`:**
- `httpx` - Async HTTP client

## Async Rules Compliance

### ✅ Fixed Issues

1. **No blocking DB calls in async routes**: All `Session` operations replaced with `AsyncSession` + await
2. **No blocking HTTP in async contexts**: All `requests` replaced with `httpx.AsyncClient`
3. **Proper async propagation**: All functions calling async operations are themselves async
4. **Event loop friendly**: I/O operations use `await`; offload CPU-bound FAISS/embedding ops with `asyncio.to_thread(...)` or a worker pool when per-request CPU work is no longer trivial (for example search/embedding CPU time consistently above ~20–50ms, or sustained load above ~10–20 QPS on a single-threaded async server)

### Key Patterns Used

```python
# Database queries
result = await db.execute(select(Model).where(...))
obj = result.scalar_one_or_none()  # or .scalars().all()

# Commits and refreshes
await db.commit()
await db.refresh(obj)

# HTTP calls
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)

# Rollback on failure
try:
   ...
   await db.commit()
except Exception:
   await db.rollback()
   raise
```

## Migration Checklist

- [x] Backend database layer (AsyncEngine, AsyncSession)
- [x] Auth routes (register, login, reset password)
- [x] Document routes (upload, get, update, delete, search, reindex)
- [x] Chat routes (chat, stream)
- [x] User routes (CRUD operations)
- [x] Vector metadata routes (sync, delete, get)
- [x] Permission helpers (async ownership checks)
- [x] AI engine HTTP calls (httpx.AsyncClient)
- [x] Dependencies updated (asyncpg, httpx)
- [x] Async audit of remaining DB helper modules completed
   - `backend/utils/usage_tracker.py` - async-safe (`await db.commit()` / rollback handling)
   - `backend/utils/chat_persistence.py` - async-safe (`AsyncSession`, awaited queries and commit)
   - `backend/utils/permissions.py` - async-safe (`AsyncSession`, awaited select queries)

## Testing Steps

1. **Install new dependencies:**
   ```bash
   cd backend
   pip install asyncpg httpx
   
   cd ../ai_engine
   pip install httpx
   ```

2. **Update database connection:**
   - `DATABASE_URL` may remain `postgresql://...`; the runtime converts supported PostgreSQL URLs to `postgresql+asyncpg://...` automatically.
   - For clarity, you can still set `DATABASE_URL` in `.env` directly to `postgresql+asyncpg://...`, but it is recommended rather than required.
   - No schema changes needed

3. **Run backend:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

4. **Run AI engine:**
   ```bash
   cd ai_engine
   uvicorn app:app --port 9000 --reload
   ```

5. **Test endpoints:**
   - User registration/login
   - Document upload/retrieval
   - Chat streaming
   - Admin operations

   Async-specific checklist:
   - Install `pytest-asyncio` and `httpx`
   - Set `asyncio_mode = auto` in `pytest.ini`/`pyproject.toml`
   - Use `httpx.AsyncClient` with `@pytest.mark.asyncio` for endpoint tests
   - Verify concurrent request behavior and DB pool behavior under load
   - Verify async error handling, cleanup, and background task completion

## Potential Issues & Solutions

### Issue: ImportError for asyncpg
**Solution:** `pip install asyncpg`

### Issue: RuntimeError: no running event loop
**Solution:** Do not auto-fallback from async to sync at runtime. Keep explicit sync and async entry points and ensure async functions are called only from async contexts (or via an explicit event loop runner in sync code).

### Issue: Database session not closing
**Solution:** Using `async with` context manager ensures proper cleanup

### Issue: Blocking FAISS operations
**Solution:** FAISS and embedding operations are CPU-bound and can block the event loop under load, which increases tail latency (p95/p99) and reduces concurrency. Treat “small-medium workloads” as roughly per-search CPU under ~20–50ms or sustained load under ~10–20 QPS on a single-threaded async server. If expected per-request CPU time or concurrent load exceeds those heuristics—or you observe rising latency under load—offload with `await asyncio.to_thread(...)` (for example around `model.embed(...)` / `vector_store.search(...)`) or move this work to a worker pool.

## Performance Benefits

1. **Higher concurrency**: Event loop can handle multiple requests during I/O waits
2. **Better resource utilization**: No thread pool overhead for I/O
3. **Streaming efficiency**: Async streaming is native and efficient
4. **Database connection pooling**: AsyncEngine manages connections efficiently

## Notes

- **Action required:** all database helper functions (including helpers like `utils/usage_tracker.py`) MUST be async-safe when invoked from async routes; sync DB calls in async paths block the event loop.
   - Audit step: identify all helper functions called from async contexts.
   - Verification: run async route performance tests and confirm no blocking DB helper calls remain.
- Prefer lifecycle-managed shared `httpx.AsyncClient` instances for high-throughput service-to-service calls instead of creating a fresh client per request.
- Background jobs (RQ/Redis) remain sync - acceptable as they run in separate workers
- FAISS operations (embedding, search) may run inline only for small-medium workloads (roughly <20–50ms CPU per request and <10–20 sustained QPS on a single-threaded async server). Above that, offload with `asyncio.to_thread(...)` or a worker pool to avoid event-loop blocking.
