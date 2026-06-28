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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

TEST_DB_NAME = "therapy_chatbot_test"
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://postgres:root@localhost:5432/{TEST_DB_NAME}"
)
os.environ["ENABLE_DP"] = "false"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import settings # noqa: E402
from app.database import get_db, _admin_url # noqa: E402
from app.models import Base, User, EmotionalState # noqa: E402
from app.services.auth import create_access_token, hash_password, pseudonymize # noqa: E402
from app.services.classifier import EmotionClassifier # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def mock_classifier_pipeline():
    """Globally mocks EmotionClassifier._get_pipeline to prevent loading or downloading the DeBERTa model."""
    mock_pipe = MagicMock()

    def fake_classify_call(text, candidate_labels, hypothesis_template=None):
        """Classifies the given text into one of several candidate labels based on keyword presence.

        Args:
            text (str): The input text to classify.
            candidate_labels (list of str): A list of candidate labels to choose from.
            hypothesis_template (str, optional): An optional template for generating a hypothesis.

        Returns:
            dict: A dictionary containing the sorted labels and their corresponding scores.
        """
        txt = text.lower()
        if "sad" in txt or "hopeless" in txt or "disappear" in txt or ("end it" in txt):
            scores = {
                "sadness": 0.8,
                "fear": 0.1,
                "anger": 0.05,
                "joy": 0.02,
                "neutral": 0.03,
            }
        elif "panic" in txt or "anxious" in txt or "fear" in txt:
            scores = {
                "fear": 0.8,
                "sadness": 0.1,
                "anger": 0.05,
                "joy": 0.02,
                "neutral": 0.03,
            }
        elif "good" in txt or "great" in txt or "joy" in txt or ("happy" in txt):
            scores = {
                "joy": 0.8,
                "neutral": 0.1,
                "sadness": 0.05,
                "anger": 0.03,
                "fear": 0.02,
            }
        else:
            scores = {
                "neutral": 0.8,
                "joy": 0.05,
                "sadness": 0.05,
                "anger": 0.05,
                "fear": 0.05,
            }
        sorted_labels = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return {
            "labels": sorted_labels,
            "scores": [scores[label] for label in sorted_labels],
        }

    mock_pipe.side_effect = fake_classify_call
    original_get_pipeline = EmotionClassifier._get_pipeline
    EmotionClassifier._get_pipeline = lambda self: mock_pipe
    yield mock_pipe
    EmotionClassifier._get_pipeline = original_get_pipeline


@pytest.fixture(scope="session", autouse=True)
def bypass_database_lifespan():
    """Bypasses app db-initialization lifespan during testing since we set it up session-wide."""
    from app.main import app
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_lifespan(_: FastAPI):
        """A context manager to simulate a lifespan event for an asynchronous application.

        Args:
            _: The FastAPI instance, which is not used within the context manager.

        Returns:
            None

        Raises:
            None"""
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = mock_lifespan
    yield
    app.router.lifespan_context = original_lifespan


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """Create the test database, load vector extension, compile tables, and drop database upon teardown."""
    target = make_url(settings.database_url)
    db_name = target.database
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()
    async_test_engine = create_async_engine(
        settings.database_url, echo=False, future=True
    )

    async def create_schema():
        """Creates the database schema.

        Args:
            None

        Returns:
            None

        Raises:
            SQLAlchemyError: If there is an error during the creation of the schema."""
        async with async_test_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(create_schema())
    yield
    loop.run_until_complete(async_test_engine.dispose())
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(
            text(
                "\n                SELECT pg_terminate_backend(pg_stat_activity.pid)\n                FROM pg_stat_activity\n                WHERE pg_stat_activity.datname = :name\n                  AND pid <> pg_backend_pid();\n                "
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
    async_test_engine = create_async_engine(
        settings.database_url, echo=False, future=True
    )
    async with async_test_engine.connect() as connection:
        transaction = await connection.begin()
        async_session = AsyncSession(bind=connection, expire_on_commit=False)
        yield async_session
        await async_session.close()
        await transaction.rollback()
    await async_test_engine.dispose()


@pytest.fixture
async def async_client(
    async_db_session: AsyncSession,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provides a lifespan-aware httpx.AsyncClient that overrides get_db dependency."""
    from app.main import app

    async def override_get_db():
        """Yields an asynchronous database session.

        Args:
            None

        Returns:
            AsyncGenerator[AsyncSession]: An asynchronous generator yielding a single instance of an asynchronous database session.
        """
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with LifespanManager(app) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app), base_url="http://testserver"
        ) as client:
            yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def faker_instance() -> Faker:
    """Fixture to provide a Faker instance."""
    return Faker()


@pytest.fixture
async def auth_client(
    async_client: httpx.AsyncClient,
    async_db_session: AsyncSession,
    faker_instance: Faker,
) -> dict:
    """Creates a user, saves them to the DB, creates a JWT token and returns the client with credentials."""
    import uuid

    email = faker_instance.email()
    password = "password123"
    user_id = uuid.uuid4()
    hashed = hash_password(password)
    pseudonym = pseudonymize(user_id)
    user = User(id=user_id, email=email, password_hash=hashed, pseudonym_id=pseudonym)
    async_db_session.add(user)
    async_db_session.add(EmotionalState(user_id=user_id, vector=[0.0, 0.0, 0.0, 0.0]))
    await async_db_session.flush()
    token = create_access_token(str(user.id))
    async_client.headers["Authorization"] = f"Bearer {token}"
    return {
        "client": async_client,
        "user": user,
        "token": token,
        "raw_password": password,
        "email": email,
    }
