from __future__ import annotations

from sqlalchemy import text, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


async_engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def _admin_url() -> str:
    if settings.database_admin_url:
        return settings.database_admin_url
    url = make_url(settings.database_url)
    return str(url.set(database="postgres").set(drivername="postgresql+psycopg2"))


def ensure_database_exists() -> None:
    target = make_url(settings.database_url)
    db_name = target.database
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()


async def get_db() -> AsyncSession:
    """
    Provide an async SQLAlchemy session for database operations suitable for use as a dependency.
    
    Returns:
        AsyncSession: An active AsyncSession instance yielded for use; the session is scoped to the caller's context.
    """
    async with AsyncSessionLocal() as session:
        yield session