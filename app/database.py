from __future__ import annotations

from sqlalchemy import text, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


async_engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def _admin_url() -> str:
    """Returns the admin URL for the database.

    Args:
        None

    Returns:
        str: The admin URL of the database."""
    if settings.database_admin_url:
        return settings.database_admin_url
    url = make_url(settings.database_url)
    return str(url.set(database="postgres").set(drivername="postgresql+psycopg2"))


def ensure_database_exists() -> None:
    """Ensure that the database specified in settings.database_url exists.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: If an error occurs while checking or creating the database."""
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
    """Asynchronously retrieves a database session.

    Args:
        None

    Returns:
        An instance of `AsyncSession`.

    Raises:
        No exceptions are explicitly raised."""
    async with AsyncSessionLocal() as session:
        yield session
