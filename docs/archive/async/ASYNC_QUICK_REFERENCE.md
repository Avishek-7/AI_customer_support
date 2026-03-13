# Quick Reference: Async vs Sync Patterns

## Database Operations

### ❌ Before (Sync - Blocking)
```python
from sqlalchemy.orm import Session

def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

### ✅ After (Async - Non-blocking)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user
```

## HTTP Requests

### ❌ Before (Blocking)
```python
import requests

def send_data_sync():
    response = requests.post(url, json=data)
    return response.json()
```

### ✅ After (Async)
```python
import httpx

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return response.json()

```

## Database Setup

### ❌ Before
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### ✅ After
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Convert URL: postgresql+asyncpg://...
engine = create_async_engine(async_db_url)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Common Query Patterns

### Count
```python
# ❌ Before
count = db.query(User).count()

# ✅ After
from sqlalchemy import func

result = await db.execute(select(func.count(User.id)))
count = result.scalar()
```

### Filter + First
```python
# ❌ Before
user = db.query(User).filter(User.email == email).first()

# ✅ After
result = await db.execute(select(User).filter(User.email == email))
user = result.scalar_one_or_none()
```

### Filter + All
```python
# ❌ Before
users = db.query(User).filter(User.role == "admin").all()

# ✅ After
result = await db.execute(select(User).filter(User.role == "admin"))
users = result.scalars().all()
```

### Order By + Limit
```python
# ❌ Before
recent = db.query(Post).order_by(Post.created_at.desc()).limit(10).all()

# ✅ After
result = await db.execute(
    select(Post).order_by(Post.created_at.desc()).limit(10)
)
recent = result.scalars().all()
```

### Join
```python
# ❌ Before
results = db.query(User).join(Document).filter(Document.title.like("%test%")).all()

# ✅ After
result = await db.execute(
    select(User).join(Document).filter(Document.title.like("%test%"))
)
results = result.scalars().all()
```

### Delete
```python
# ❌ Before
db.query(User).filter(User.id == user_id).delete()
db.commit()

# ✅ After
from sqlalchemy import delete as sql_delete

await db.execute(sql_delete(User).filter(User.id == user_id))
await db.commit()

# Or with object
await db.delete(user_obj)
await db.commit()
```

### Update
```python
# ❌ Before
user = db.query(User).filter(User.id == user_id).first()
user.name = "New Name"
db.commit()

# ✅ After
result = await db.execute(select(User).filter(User.id == user_id))
user = result.scalar_one_or_none()
if user is not None:
    user.name = "New Name"
    await db.commit()
```

## Route Declarations

### ❌ Before
```python
@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    # ...
```

### ✅ After
```python
@router.post("/register")
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    existing = result.scalar_one_or_none()
    # ...
```

## Background Tasks

### Explicit Sync/Async Entry Points

```python
import asyncio

async def do_work_async(job_id: int) -> None:
    # Main async implementation used by async routes and workers.
    try:
        await some_async_io(job_id)
    except Exception:
        logger.exception("background job failed", extra={"job_id": job_id})
        raise

def do_work_sync(job_id: int) -> None:
    # Sync wrapper for CLI scripts or sync worker entry points.
    asyncio.run(do_work_async(job_id))
```

### FastAPI BackgroundTasks

```python
from fastapi import BackgroundTasks

@router.post("/jobs/{job_id}")
async def launch_job(job_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(do_work_sync, job_id)
    return {"status": "accepted"}
```

Use `BackgroundTasks` only for short in-process follow-up work where losing the task on process restart is acceptable.

### In-process async tasks

```python
task = asyncio.create_task(do_work_async(job_id))
task.add_done_callback(lambda t: logger.exception("task failed") if t.exception() else None)
```

Use `asyncio.create_task(...)` only when the task lifecycle is tied to the current process and you have explicit error handling, cancellation handling, and shutdown strategy.

### When to use a queue

Use Celery, RQ, or another external worker queue when work is long-running, retryable, business-critical, or should survive API process restarts.

Recommended split:
- In-process background task: quick post-response work, best-effort notifications, lightweight cache refreshes.
- External queue: document indexing, expensive reconciliation, retry-heavy tasks, scheduled jobs.

### Error handling and lifecycle guidance

- Always log task failures with job identifiers and context.
- Add bounded retries for transient failures; do not retry forever in-process.
- Ensure tasks are cancelled or awaited during application shutdown when appropriate.
- Do not rely on HTTP responses to surface failures from post-response background work; use logs, metrics, or queue state.

## Key Rules

1. **Always await async operations**: `await db.execute()`, `await db.commit()`, `await client.post()`
2. **Use async with for clients**: `async with httpx.AsyncClient() as client:`
3. **Convert all queries**: `db.query()` → `await db.execute(select())`
4. **Scalar vs Scalars**:
   - `.scalar()` or `.scalar_one_or_none()` for single value
   - `.scalars().all()` for list of objects
5. **Imports**: Add `from sqlalchemy import select` and `from sqlalchemy.ext.asyncio import AsyncSession`

## Dependencies

### Backend
```txt
asyncpg          # Async PostgreSQL driver
httpx            # Async HTTP client
```

### AI Engine
```txt
httpx            # Async HTTP client
```

## Connection String Format

```python
# Sync
DATABASE_URL = "postgresql://user:pass@localhost/db"

# Async (add +asyncpg)
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
```

## Quick Checks

✅ All route functions are `async def`
✅ All DB operations use `await`
✅ All HTTP uses `httpx.AsyncClient`
✅ No `requests.post/get` in async contexts
✅ No `db.query()` calls
✅ All imports updated to async variants
✅ `Session` changed to `AsyncSession`
✅ Dependencies installed: `asyncpg`, `httpx`
