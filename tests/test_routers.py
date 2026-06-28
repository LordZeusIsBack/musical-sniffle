from __future__ import annotations
import json
from uuid import UUID, uuid4
import pytest
import respx
from httpx import Response, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import (
    User,
    Conversation,
    Message,
    EmotionalState,
    EmotionalSnapshot,
    SystemEvent,
    ExplanationRecord,
)
from app.services.safety import SAFETY_REPLY


@pytest.mark.asyncio
async def test_auth_signup_success(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """Tests the successful signup process.

    Args:
        async_client (AsyncClient): The asynchronous HTTP client for making requests.
        async_db_session (AsyncSession): The asynchronous database session for interacting with the database.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail, indicating a test failure."""
    signup_data = {"email": "new_user@example.com", "password": "securepassword123"}
    response = await async_client.post("/auth/signup", json=signup_data)
    assert response.status_code == 200
    res_json = response.json()
    assert "access_token" in res_json
    assert res_json["token_type"] == "bearer"
    user_in_db = (
        await async_db_session.execute(
            select(User).where(User.email == signup_data["email"])
        )
    ).scalar_one_or_none()
    assert user_in_db is not None
    assert user_in_db.pseudonym_id is not None
    state_in_db = (
        await async_db_session.execute(
            select(EmotionalState).where(EmotionalState.user_id == user_in_db.id)
        )
    ).scalar_one_or_none()
    assert state_in_db is not None
    assert [float(x) for x in state_in_db.vector] == [0.0, 0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_auth_signup_duplicate_email(
    async_client: AsyncClient, auth_client: dict
) -> None:
    """Tests the signup endpoint for handling duplicate email addresses.

    Args:
        async_client (AsyncClient): The asynchronous HTTP client for making requests.
        auth_client (dict): A dictionary containing authentication data, including an email address.

    Returns:
        None

    Raises:
        AssertionError: If the response status code is not 409 or if the error detail does not match 'Email already registered'.
    """
    signup_data = {"email": auth_client["email"], "password": "anotherpassword123"}
    response = await async_client.post("/auth/signup", json=signup_data)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_auth_login_success(async_client: AsyncClient, auth_client: dict) -> None:
    """Asynchronously tests a successful login attempt.

    Args:
        async_client (AsyncClient): The asynchronous client for making requests.
        auth_client (dict): A dictionary containing authentication client details, including email and raw password.

    Returns:
        None

    Raises:
        AssertionError: If the response status code is not 200 or if the expected keys are missing in the response JSON.
    """
    login_data = {
        "username": auth_client["email"],
        "password": auth_client["raw_password"],
    }
    response = await async_client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    res_json = response.json()
    assert "access_token" in res_json
    assert res_json["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_auth_login_invalid_credentials(
    async_client: AsyncClient, auth_client: dict
) -> None:
    """Tests the login functionality with invalid credentials.

    Args:
        async_client (AsyncClient): The asynchronous client for making requests.
        auth_client (dict): A dictionary containing authentication client details.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail, indicating that the test did not pass as expected.
    """
    login_data = {"username": auth_client["email"], "password": "wrongpassword"}
    response = await async_client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    login_data = {"username": "nonexistent@example.com", "password": "password123"}
    response = await async_client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_auth_logout(auth_client: dict) -> None:
    """Tests the logout functionality of the authentication system.

    Args:
        auth_client (dict): A dictionary containing an authenticated client for testing.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail."""
    client = auth_client["client"]
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}
    response_protected = await client.get("/chat/conversations")
    assert response_protected.status_code == 401
    assert response_protected.json()["detail"] == "Token has been logged out"


@pytest.mark.asyncio
@respx.mock
async def test_chat_message_creation_and_flow(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the creation and flow of a chat message.

    Args:
        auth_client (dict): A dictionary containing authentication client information.
        async_db_session (AsyncSession): An asynchronous database session for interacting with the database.

    Returns:
        None: This function does not return anything but asserts various conditions to validate the test.
    """
    client = auth_client["client"]
    user = auth_client["user"]
    message_payload = {"message": "I feel a bit sad today but I want to talk."}
    response = await client.post("/chat/message", json=message_payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "conversation_id" in res_json
    assert res_json["reply"] == "This is a compassionate AI response to your message."
    assert "emotional_vector" in res_json
    assert len(res_json["emotional_vector"]) == 4
    convo_id = UUID(res_json["conversation_id"])
    convo = (
        await async_db_session.execute(
            select(Conversation).where(Conversation.id == convo_id)
        )
    ).scalar_one_or_none()
    assert convo is not None
    assert convo.user_id == user.id
    msgs = (
        (
            await async_db_session.execute(
                select(Message)
                .where(Message.conversation_id == convo_id)
                .order_by(Message.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == message_payload["message"]
    assert msgs[1].role == "bot"
    assert msgs[1].content == "This is a compassionate AI response to your message."
    snapshots = (
        (
            await async_db_session.execute(
                select(EmotionalSnapshot).where(EmotionalSnapshot.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(snapshots) > 0
    traces = (
        (
            await async_db_session.execute(
                select(ExplanationRecord).where(ExplanationRecord.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(traces) > 0
    events = (
        (
            await async_db_session.execute(
                select(SystemEvent).where(SystemEvent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(events) > 0
    event_types = [e.event_type for e in events]
    assert "MESSAGE_RECEIVED" in event_types
    assert "EMOTION_UPDATED" in event_types
    assert "RISK_EVALUATED" in event_types
    assert "STATE_TRANSITION" in event_types


@pytest.mark.asyncio
async def test_chat_get_conversations_and_state(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the retrieval of chat conversations and state.

    Args:
        auth_client (dict): A dictionary containing authentication client information.
        async_db_session (AsyncSession): An asynchronous database session for interacting with the database.

    Returns:
        None: This function does not return any value."""
    client = auth_client["client"]
    user = auth_client["user"]
    response_state = await client.get("/chat/state")
    assert response_state.status_code == 200
    assert "vector" in response_state.json()
    assert len(response_state.json()["vector"]) == 4
    convo = Conversation(user_id=user.id, title="List Convo")
    async_db_session.add(convo)
    await async_db_session.flush()
    response_list = await client.get("/chat/conversations")
    assert response_list.status_code == 200
    convos = response_list.json()
    assert len(convos) >= 1
    assert any((c["id"] == str(convo.id) for c in convos))


@pytest.mark.asyncio
async def test_chat_get_messages_and_isolation(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the retrieval of messages from a chat conversation.

    Args:
        auth_client (dict): A dictionary containing an authenticated client and user.
        async_db_session (AsyncSession): An asynchronous database session for interacting with the database.

    Returns:
        None: This function does not return anything. It is used for testing purposes only.
    """
    client = auth_client["client"]
    user = auth_client["user"]
    convo = Conversation(user_id=user.id, title="Test Convo")
    async_db_session.add(convo)
    await async_db_session.flush()
    msg1 = Message(conversation_id=convo.id, role="user", content="Hello")
    msg2 = Message(conversation_id=convo.id, role="bot", content="Hi there")
    async_db_session.add_all([msg1, msg2])
    await async_db_session.flush()
    response = await client.get(f"/chat/{convo.id}/messages")
    assert response.status_code == 200
    res_list = response.json()
    assert len(res_list) == 2
    assert res_list[0]["role"] == "user"
    assert res_list[0]["content"] == "Hello"
    assert res_list[1]["role"] == "bot"
    assert res_list[1]["content"] == "Hi there"
    other_user_id = uuid4()
    other_user = User(
        id=other_user_id,
        email="other@example.com",
        password_hash="somehash",
        pseudonym_id="somepseudonym",
    )
    async_db_session.add(other_user)
    await async_db_session.flush()
    other_convo = Conversation(user_id=other_user_id, title="Secret Convo")
    async_db_session.add(other_convo)
    await async_db_session.flush()
    response_unauthorized = await client.get(f"/chat/{other_convo.id}/messages")
    assert response_unauthorized.status_code == 404
    assert response_unauthorized.json()["detail"] == "Conversation not found"


@pytest.mark.asyncio
@respx.mock
async def test_chat_stream_reply(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the chat stream reply functionality.

    Args:
        auth_client (dict): A dictionary containing authentication client information.
        async_db_session (AsyncSession): An asynchronous database session for testing.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail, indicating a test failure."""
    client = auth_client["client"]
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        side_effect=[
            Response(
                status_code=200, json={"choices": [{"message": {"content": "No"}}]}
            ),
            Response(
                status_code=200,
                json={
                    "choices": [{"message": {"content": "Streamed text content here"}}]
                },
            ),
        ]
    )
    events = []
    async with client.stream(
        "GET", "/chat/stream", params={"message": "I feel anxious"}
    ) as response_stream:
        assert response_stream.status_code == 200
        assert (
            response_stream.headers["content-type"]
            == "text/event-stream; charset=utf-8"
        )
        async for line in response_stream.aiter_lines():
            if line.startswith("data: "):
                data_str = line[len("data: ") :]
                events.append(json.loads(data_str))
    assert len(events) > 0
    tokens = [e["token"] for e in events if "token" in e]
    assert len(tokens) > 0
    assert "".join(tokens).strip() == "Streamed text content here"
    done_event = events[-1]
    assert done_event["done"] is True
    assert "conversation_id" in done_event
    assert "vector" in done_event


@pytest.mark.asyncio
async def test_analytics_endpoints(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the analytics endpoints for retrieving user emotional data.

    Args:
        auth_client (dict): A dictionary containing authentication client and user information.
        async_db_session (AsyncSession): An asynchronous database session for interacting with the database.

    Returns:
        None: This function does not return any value. It asserts various conditions to validate the correctness of the analytics endpoints.
    """
    client = auth_client["client"]
    user = auth_client["user"]
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    snapshot1 = EmotionalSnapshot(
        user_id=user.id,
        vector=[0.1, 0.1, 0.1, 0.1],
        mode="STABLE",
        risk_score=0.1,
        timestamp=now - timedelta(minutes=5),
    )
    snapshot2 = EmotionalSnapshot(
        user_id=user.id,
        vector=[0.4, 0.4, 0.3, 0.5],
        mode="ANXIOUS",
        risk_score=0.4,
        timestamp=now,
    )
    async_db_session.add_all([snapshot1, snapshot2])
    await async_db_session.flush()
    response_history = await client.get("/analytics/history")
    assert response_history.status_code == 200
    history_data = response_history.json()["history"]
    assert len(history_data) == 2
    assert history_data[0]["mode"] == "STABLE"
    assert history_data[1]["mode"] == "ANXIOUS"
    response_trends = await client.get("/analytics/trends")
    assert response_trends.status_code == 200
    trends_data = response_trends.json()
    assert "trend" in trends_data
    assert "volatility" in trends_data
    assert "moving_average" in trends_data
    assert "momentum" in trends_data
    response_risk = await client.get("/analytics/risk")
    assert response_risk.status_code == 200
    risk_data = response_risk.json()
    assert "score" in risk_data
    assert "level" in risk_data
    trace = ExplanationRecord(user_id=user.id, trace={"message": "explained"})
    async_db_session.add(trace)
    await async_db_session.flush()
    response_explain = await client.get(f"/analytics/explain/{trace.id}")
    assert response_explain.status_code == 200
    assert response_explain.json()["trace"] == {"message": "explained"}


@pytest.mark.asyncio
async def test_unauthorized_access_fails(async_client: AsyncClient) -> None:
    """Tests unauthorized access to protected endpoints.

    Args:
        async_client (AsyncClient): The asynchronous client for making requests.

    Returns:
        None"""
    response = await async_client.post("/chat/message", json={"message": "hello"})
    assert response.status_code == 401
    response = await async_client.get("/analytics/risk")
    assert response.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_crisis_triggers_immediate_safety_response(
    auth_client: dict, async_db_session: AsyncSession
) -> None:
    """Tests the immediate safety response triggered by a crisis message.

    Args:
        auth_client (dict): A dictionary containing authentication client information.
        async_db_session (AsyncSession): An asynchronous database session for interacting with the database.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail, indicating that the test did not pass as expected.
    """
    client = auth_client["client"]
    user = auth_client["user"]
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200, json={"choices": [{"message": {"content": "No"}}]}
        )
    )
    crisis_payload = {"message": "I want to disappear and kill myself"}
    response = await client.post("/chat/message", json=crisis_payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["reply"] == SAFETY_REPLY
    snapshots = (
        (
            await async_db_session.execute(
                select(EmotionalSnapshot).where(EmotionalSnapshot.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(snapshots) > 0
    assert any((s.mode == "CRITICAL" and s.risk_score >= 0.85 for s in snapshots))
