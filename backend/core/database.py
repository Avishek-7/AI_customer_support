from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings

# ---------------------------------------------------------------------------
# Sync engine & session (for Celery workers and other sync contexts)
# ---------------------------------------------------------------------------
sync_engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


def get_sync_db():
    """Return a synchronous database session. Caller must close it."""
    return SyncSessionLocal()


# ---------------------------------------------------------------------------
# Async engine & session (for FastAPI endpoints)
# ---------------------------------------------------------------------------

# Convert database URL to use asyncpg driver
def _get_async_db_url(sync_url: str) -> str:
    """Convert sync database URL to async URL with asyncpg driver."""
    # Handle various PostgreSQL URL formats
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgres://"):
        return sync_url.replace("postgres://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgresql+psycopg://"):
        return sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    else:
        # Assume it's already async or needs no conversion
        return sync_url

async_db_url = _get_async_db_url(settings.DATABASE_URL)

engine = create_async_engine(async_db_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
        