# Async Migration Testing Checklist

## Pre-Testing Setup

### 1. Install Dependencies
```bash
# Backend
cd backend
pip install asyncpg httpx

# AI Engine
cd ../ai_engine
pip install httpx
```

### 2. Verify Environment
- Ensure `.env` file has `DATABASE_URL` configured
- Database should be PostgreSQL (asyncpg compatible)
- Redis optional (for background jobs)

### 3. Start Services
```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 - AI Engine
cd ai_engine
uvicorn app:app --reload --port 9000
```

## Testing Checklist

### ✅ Authentication Endpoints

#### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "email": "test@example.com", "password": "password123"}'
```
**Expected**: 200 OK with JWT token

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```
**Expected**: 200 OK with JWT token

#### Reset Password
```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token": "<single_use_reset_token_from_email>", "new_password": "newpass123"}'
```
**Expected**: 200 OK with new token (reset token is single-use and should fail if reused)

### ✅ Document Endpoints

#### Upload Document (requires PDF)
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "title=Test Document" \
  -F "file=@test.pdf"
```
**Expected**: 200 OK with document details

#### List Documents
```bash
curl -X GET http://localhost:8000/documents \
  -H "Authorization: Bearer <token>"
```
**Expected**: 200 OK with list of documents

#### Get Single Document
```bash
curl -X GET http://localhost:8000/documents/1 \
  -H "Authorization: Bearer <token>"
```
**Expected**: 200 OK with document details

#### Update Document
```bash
curl -X PUT http://localhost:8000/documents/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "content": "Updated content"}'
```
**Expected**: 200 OK with updated document

#### Delete Document
```bash
curl -X DELETE http://localhost:8000/documents/1 \
  -H "Authorization: Bearer <token>"
```
**Expected**: 200 OK with deletion confirmation

### ✅ Chat Endpoints

#### Chat (Non-Streaming)
```bash
curl -X POST http://localhost:8000/chat/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is this document about?", "document_ids": [1]}'
```
**Expected**: 200 OK with answer and sources

#### Chat (Streaming)
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain this document", "document_ids": [1]}' \
  --no-buffer
```
**Expected**: SSE stream with tokens

### ✅ User Management

#### Get Current User
```bash
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer <token>"
```
**Expected**: 200 OK with user profile

#### List All Users (Admin Only)
```bash
curl -X GET http://localhost:8000/users \
  -H "Authorization: Bearer <admin_token>"
```
**Expected**: 200 OK with user list

#### Create User (Admin Only)
```bash
curl -X POST http://localhost:8000/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "new@example.com", "name": "New User", "password": "pass123", "role": "user"}'
```
**Expected**: 201 Created with user details

### ✅ Admin Endpoints

#### System Stats
```bash
curl -X GET http://localhost:8000/admin/stats \
  -H "Authorization: Bearer <admin_token>"
```
**Expected**: 200 OK with system statistics

#### Usage Statistics
```bash
curl -X GET http://localhost:8000/admin/usage-stats \
  -H "Authorization: Bearer <admin_token>"
```
**Expected**: 200 OK with API usage data

#### All Documents (Admin)
```bash
curl -X GET http://localhost:8000/admin/documents \
  -H "Authorization: Bearer <admin_token>"
```
**Expected**: 200 OK with all documents

### ✅ Vector Metadata Endpoints

> Security note: `/vectors/sync` and `/vectors/document/{id}` are backend-internal operations in current implementation. Restrict via network isolation (private subnet / internal service mesh / reverse proxy ACLs) or add API auth middleware before public exposure.

#### Sync Metadata (Internal - called by AI engine)
```bash
curl -X POST http://localhost:8000/vectors/sync \
  -H "Content-Type: application/json" \
  -H "X-Internal-API-Key: <internal_service_token>" \
  -d '{"metadata": [{"document_id": 1, "chunk_id": 0, "text": "Sample chunk"}]}'
```
**Expected**: 200 OK with sync status

#### Get Vector Metadata
```bash
curl -X GET http://localhost:8000/vectors/document/1 \
  -H "X-Internal-API-Key: <internal_service_token>"
```
**Expected**: 200 OK with chunk list

### ✅ AI Engine Endpoints

> Security note: AI engine routes (`/index-document`, `/query`, `/stream`, `/debug/all-documents`) should be exposed only behind backend/proxy auth. If called directly, require internal network access and service credentials.

#### Index Document
```bash
curl -X POST http://localhost:9000/index-document \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <service_token>" \
  -d '{"document_id": 1, "title": "Test", "content": "Sample content"}'
```
**Expected**: 200 OK with indexing confirmation

#### Query (Non-Streaming)
```bash
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <service_token>" \
  -d '{"session_id": "test", "query": "What is this about?", "document_ids": [1], "k": 5}'
```
**Expected**: 200 OK with answer and sources

#### Stream Query
```bash
curl -X POST http://localhost:9000/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <service_token>" \
  -d '{"session_id": "test", "query": "Explain this", "document_ids": [1]}' \
  --no-buffer
```
**Expected**: SSE stream with tokens

#### Debug Documents
```bash
curl -X GET http://localhost:9000/debug/all-documents \
  -H "Authorization: Bearer <admin_or_internal_token>"
```
**Expected**: 200 OK with indexed documents (must be restricted to admin/internal access)

## Load Testing

### Concurrent Requests
```bash
# Using Apache Bench
ab -n 100 -c 10 -H "Authorization: Bearer <token>" \
  http://localhost:8000/documents

# Using wrk
wrk -t4 -c10 -d30s -H "Authorization: Bearer <token>" \
  http://localhost:8000/documents
```
**Expected**: High throughput, no errors

### Streaming Performance
```bash
# Multiple concurrent streams
for i in {1..10}; do
  curl -X POST http://localhost:8000/chat/stream \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"message": "Test '$i'"}' \
    --no-buffer &
done
wait
```
**Expected**: All streams complete successfully

## Async Compliance Checks

### ✅ Database Operations
- [ ] No blocking `db.query()` calls in async routes
- [ ] All queries use `await db.execute(select(...))`
- [ ] All commits use `await db.commit()`
- [ ] All refreshes use `await db.refresh()`
- [ ] Session cleanup with `async with` context manager

### ✅ HTTP Operations
- [ ] No `requests` library calls in async contexts
- [ ] All HTTP uses `httpx.AsyncClient`
- [ ] Proper `async with` for client management
- [ ] Timeouts configured appropriately

### ✅ Error Handling
- [ ] Database rollback on errors: `await db.rollback()`
- [ ] Proper exception propagation
- [ ] No silent failures
- [ ] Logging captures async context

### ✅ Performance
- [ ] No event loop blocking
- [ ] Concurrent request handling
- [ ] Efficient connection pooling
- [ ] Low latency for I/O operations

## Common Issues & Solutions

### Issue: asyncpg not found
```bash
pip install asyncpg
```

### Issue: Event loop errors
- Check that all async functions are properly awaited
- Ensure no sync functions call async without await

### Issue: Database connection errors
- Verify DATABASE_URL format: `postgresql+asyncpg://user:pass@host/db`
- Check PostgreSQL is running and accessible

### Issue: Slow response times
- Check database query performance
- Verify connection pool settings
- Monitor for blocking operations

### Issue: Streaming not working
- Ensure client supports SSE (Server-Sent Events)
- Check for buffering in proxies/load balancers
- Verify Content-Type: text/event-stream

## Performance Benchmarks

### Expected Metrics (After Async Migration)

#### Authentication
- Register: < 200ms
- Login: < 100ms

#### Documents
- Upload (small PDF): < 2s
- List: < 50ms
- Get Single: < 30ms

#### Chat
- Non-streaming: 2-5s (depends on LLM)
- Streaming first token: < 1s
- Streaming throughput: > 50 tokens/s

#### Admin
- Stats endpoints: < 100ms
- User lists: < 200ms

### Concurrency
- Support 100+ concurrent requests
- No degradation with multiple streams
- Efficient database connection usage

## Success Criteria

✅ All endpoints return expected responses
✅ No blocking I/O warnings in logs
✅ Concurrent requests handled efficiently
✅ Streaming works without buffering
✅ Database operations are non-blocking
✅ HTTP calls use async clients
✅ Error handling works correctly
✅ Performance meets benchmarks

## Rollback Plan

If issues occur:
1. Revert to previous commit with sync code
2. Check `ASYNC_MIGRATION_SUMMARY.md` for detailed changes
3. Review logs for specific async errors
4. Test individual endpoints in isolation

## Notes

- FAISS operations are CPU-bound; keep inline only for small-medium workloads (roughly <20–50ms CPU/request and <10–20 sustained QPS on a single-threaded async server), otherwise offload with `asyncio.to_thread(...)` or a worker pool
- Background jobs (RQ) remain sync - run in separate workers
- Database migration scripts may need separate async handling
- Monitor memory usage with async connection pooling
