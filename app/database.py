import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

db_conn = os.environ["DB_CONN"]
schema = os.environ.get("SCHEMA")

# Primary backend: PostgreSQL 18
# DB_CONN format: postgresql://user:pass@host:5432/dbname


def _async_url(url: str) -> str:
    """Return the asyncpg-driver URL for an async SQLAlchemy engine."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unsupported DB URL scheme: {url!r}. Only PostgreSQL is supported.")


def _sync_url(url: str) -> str:
    """Return the psycopg2-driver URL for a sync SQLAlchemy engine."""
    url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql"):
        rest = url.split("://", 1)[1]
        return f"postgresql+psycopg2://{rest}"
    raise ValueError(f"Unsupported DB URL scheme: {url!r}. Only PostgreSQL is supported.")


# Async engine — all API routes (asyncpg driver)
async_engine = create_async_engine(_async_url(db_conn), echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine — thread pool operations only (psycopg2 driver)
engine = create_engine(_sync_url(db_conn))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata_obj = MetaData(schema=schema)
Base = declarative_base(metadata=metadata_obj)
