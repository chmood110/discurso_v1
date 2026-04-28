"""
Database connection — SQLAlchemy async engine.
SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    # SQLite-specific: check_same_thread=False handled by aiosqlite
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables (used for dev/testing without Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
