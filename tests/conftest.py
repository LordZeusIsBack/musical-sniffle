from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncGenerator, Generator
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from asgi_lifespan import LifespanManager
import httpx
from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Set database URL environment variable to the test database BEFORE importing the app
TEST_DB_NAME = "therapy_chatbot_test"
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://postgres:root@localhost:5432/{TEST_DB_NAME}"
# Ensure we disable real HF pipeline loading by setting up mocks
os.environ["ENABLE_DP"] = "false"  # Default off, but we can override in tests

# Ensure the project directory is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import get_db, _admin_url
from app.models import Base, User, EmotionalState
from app.services.auth import create_access_token, hash_password, pseudonymize
from app.services.classifier import EmotionClassifier

# Session-wide fake classifier mocking to prevent HF model downloads
@pytest.fixture(scope="session", autouse=True)
def mock_classifier_pipeline():
    """Globally mocks EmotionClassifier._get_pipeline to prevent loading or downloading the DeBERTa model."""
    mock_pipe = MagicMock()
    # Mock zero-shot-classification output. Keep it stable and neutral/joy/sadness depending on matches
    def fake_classify_call(text, candidate_labels, hypothesis_template=None):
        txt = text.lower()
        if "sad" in txt or "hopeless" in txt or "disappear" in txt or "end it" in txt:
            scores = {"sadness": 0.8, "fear": 0.1, "anger": 0.05, "joy": 0.02, "neutral": 0.03}
        elif "panic" in txt or "anxious" in txt or "fear" in txt:
            scores = {"fear": 0.8, "sadness": 0.1, "anger": 0.05, "joy": 0.02, "neutral": 0.03}
        elif "good" in txt or "great" in txt or "joy" in txt or "happy" in txt:
            scores = {"joy": 0.8, "neutral": 0.1, "sadness": 0.05, "anger": 0.03, "fear": 0.02}
        else:
            scores = {"neutral": 0.8, "joy": 0.05, "sadness": 0.05, "anger": 0.05, "fear": 0.05}

        # Sort labels by score desc
        sorted_labels = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return {
            "labels": sorted_labels,
            "scores": [scores[label] for label in sorted_labels]
        }

    mock_pipe.side_effect = fake_classify_call
    # Patch on the class itself so that all EmotionClassifier instances get the mock pipeline
    original_get_pipeline = EmotionClassifier._get_pipeline
    EmotionClassifier._get_pipeline = lambda self: mock_pipe
    yield mock_pipe
    # Restore
    EmotionClassifier._get_pipeline = original_get_pipeline


@pytest.fixture(scope="session", autouse=True)
def bypass_database_lifespan():
    """Bypasses app db-initialization lifespan during testing since we set it up session-wide."""
    from app.main import app
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_lifespan(_: FastAPI):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = mock_lifespan
    yield
    app.router.lifespan_context = original_lifespan



@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """Create the test database, load vector extension, compile tables, and drop database upon teardown."""
    # 1. Sync check/create test db
    target = make_url(settings.database_url)
    db_name = target.database

    # Establish connection to 'postgres' admin DB to create the database if missing
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    # 2. Run async setup (load vector extension + create all tables)
    async_test_engine = create_async_engine(settings.database_url, echo=False, future=True)

    async def create_schema():
        async with async_test_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

    # Run the schema setup
    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(create_schema())

    yield

    # 3. Teardown: close all connections, connect to admin, drop database
    loop.run_until_complete(async_test_engine.dispose())

    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Terminate any remaining connections to the test DB to allow dropping
        conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = :name
                  AND pid <> pg_backend_pid();
                """
            ),
            {"name": db_name},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-wide event loop for running async fixtures and tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session that rolls back after each test."""
    async_test_engine = create_async_engine(settings.database_url, echo=False, future=True)
    async_session_maker = async_sessionmaker(async_test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_test_engine.connect() as connection:
        # Begin connection-level transaction
        transaction = await connection.begin()
        # Bind session to the connection
        async_session = AsyncSession(bind=connection, expire_on_commit=False)

        yield async_session

        # Cleanup
        await async_session.close()
        await transaction.rollback()

    await async_test_engine.dispose()


@pytest.fixture
async def async_client(async_db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provides a lifespan-aware httpx.AsyncClient that overrides get_db dependency."""
    from app.main import app

    # Override database session dependency to use the transactional test session
    async def override_get_db():
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with LifespanManager(app) as manager:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app), base_url="http://testserver") as client:
            yield client

    # Clean up dependency override
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def faker_instance() -> Faker:
    """Fixture to provide a Faker instance."""
    return Faker()


@pytest.fixture
async def auth_client(async_client: httpx.AsyncClient, async_db_session: AsyncSession, faker_instance: Faker) -> dict:
    """Creates a user, saves them to the DB, creates a JWT token and returns the client with credentials."""
    import uuid
    email = faker_instance.email()
    password = "password123"
    user_id = uuid.uuid4()

    hashed = hash_password(password)
    pseudonym = pseudonymize(user_id)

    user = User(
        id=user_id,
        email=email,
        password_hash=hashed,
        pseudonym_id=pseudonym,
    )
    async_db_session.add(user)
    async_db_session.add(EmotionalState(user_id=user_id, vector=[0.0, 0.0, 0.0, 0.0]))
    await async_db_session.flush()

    token = create_access_token(str(user.id))

    # Inject token into async client headers
    async_client.headers["Authorization"] = f"Bearer {token}"

    return {
        "client": async_client,
        "user": user,
        "token": token,
        "raw_password": password,
        "email": email
    }
