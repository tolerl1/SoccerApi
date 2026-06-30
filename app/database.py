import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

db_conn = os.environ["DB_CONN"]
schema = os.environ.get("SCHEMA")


def _async_url(url: str) -> str:
    """Return the asyncpg-driver URL for an async SQLAlchemy engine."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unsupported DB URL scheme: {url!r}. Only PostgreSQL is supported.")


# Async engine — all API routes
async_engine = create_async_engine(_async_url(db_conn), echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine — Alembic migrations only
engine = create_engine(db_conn)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata_obj = MetaData(schema=schema)
Base = declarative_base(metadata=metadata_obj)
