from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.database import async_engine, ensure_database_exists
from app.models import Base
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manages the application's lifespan.

    Args:
        _: The FastAPI instance, not used within the function.

    Returns:
        None

    Raises:
        DatabaseError: If there is an issue creating the database or extensions."""
    ensure_database_exists()
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(analytics_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Returns a JSON object indicating the health status of the application.

    Args:
        None

    Returns:
        A dictionary with a single key-value pair: {"status": "ok"}"""
    return {"status": "ok"}
