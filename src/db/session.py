from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis import Redis
from sqlalchemy.ext.declarative import declarative_base

from config.settings import get_settings

settings = get_settings()

# SQLAlchemy setup
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL or settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    echo=settings.is_development,
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Redis setup
redis_client: Optional[Redis] = None
if settings.REDIS_ENABLED and settings.REDIS_URL:
    redis_client = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )

async def init_db() -> None:
    """Initialize database and create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_redis() -> Optional[Redis]:
    """Get Redis client if enabled."""
    return redis_client

# Database health check
async def check_db_health() -> bool:
    """Check database connection health."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False

# Redis health check
def check_redis_health() -> bool:
    """Check Redis connection health if enabled."""
    if not settings.REDIS_ENABLED:
        return True
    try:
        if redis_client:
            redis_client.ping()
        return True
    except Exception:
        return False
