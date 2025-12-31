# Quick Reference: Async vs Sync Patterns

## Database Operations

### ❌ Before (Sync - Blocking)
```python
from sqlalchemy.orm import Session

def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return user
```

### ✅ After (Async - Non-blocking)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    db.add(new_obj)
    await db.commit()
    await db.refresh(new_obj)
    return user
```

## HTTP Requests

### ❌ Before (Blocking)
```python
import requests

def sync_data():
    response = requests.post(url, json=data)
    return response.json()
```

### ✅ After (Async)
```python
import httpx

async def sync_data():
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
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

## Common Query Patterns

### Count
```python
# ❌ Before
count = db.query(User).count()

# ✅ After
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
    result = await db.execute(select(User).filter(User.email == user.email))
    existing = result.scalar_one_or_none()
    # ...
```

## Background Tasks

### Sync Fallback (if no event loop)
```python
try:
    asyncio.create_task(async_function())
except RuntimeError:
    # No event loop - use sync fallback
    sync_function()
```

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
