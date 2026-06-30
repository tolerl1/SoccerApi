import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

db_conn = os.environ["DB_CONN"]
schema = os.environ.get("SCHEMA")


def _async_url(url: str) -> str:
    """Convert a sync DB URL to its async-driver equivalent."""
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Sync engine — Alembic migrations only
engine = create_engine(db_conn)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine — all API routes
async_engine = create_async_engine(_async_url(db_conn), echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

metadata_obj = MetaData(schema=schema)
Base = declarative_base(metadata=metadata_obj)
