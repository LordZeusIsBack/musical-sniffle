from __future__ import annotations
import random
from datetime import datetime, timezone, timedelta
import pytest
import respx
from httpx import Response
from freezegun import freeze_time
from unittest.mock import MagicMock
from app.config import settings
from app.services.risk import calculate_risk_score, risk_level, RiskLevel
from app.services.state_machine import determine_state, EmotionalMode
from app.services.privacy import add_privacy_noise
from app.services.symbolic_reasoner import reason_about_message
from app.services.emotion import (
    EmotionModelConfig,
    update_vector,
    signal_vector,
    polarity_score,
    negativity_score,
    keyword_score,
)
from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
    TOKEN_BLACKLIST,
)
from app.services.llm import generate_reply, stream_reply
from app.services.safety import is_safe, SafetyClassificationError, SAFETY_REPLY
from app.services.classifier import EmotionClassifier


def test_risk_engine_logic() -> None:
    """Tests the logic of the risk engine.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail."""
    low_vector = [0.1, 0.1, 0.1, 0.1]
    assert calculate_risk_score(low_vector) == 0.1
    assert risk_level(0.1) == RiskLevel.LOW
    med_vector = [0.5, 0.4, 0.2, 0.1]
    assert calculate_risk_score(med_vector) == 0.31
    assert risk_level(0.31) == RiskLevel.MEDIUM
    high_vector = [0.8, 0.6, 0.5, 0.4]
    assert risk_level(0.58) == RiskLevel.MEDIUM
    assert risk_level(0.6) == RiskLevel.HIGH
    crit_vector = [0.9, 0.9, 0.9, 0.9]
    assert risk_level(0.85) == RiskLevel.CRITICAL
    assert calculate_risk_score(crit_vector) == 0.9
    assert risk_level(calculate_risk_score(crit_vector)) == RiskLevel.CRITICAL
    assert calculate_risk_score([2.0, 2.0, 2.0, 2.0]) == 1.0
    assert calculate_risk_score([-1.0, -1.0, -1.0, -1.0]) == 0.0


def test_state_machine_transitions() -> None:
    """Tests the state machine transitions based on input data and threshold.

    Args:
        data (List[float]): A list of float values representing some emotional indicators.
        threshold (float): A float value used as a threshold for determining the emotional mode.

    Returns:
        None"""
    assert determine_state([0, 0, 0, 0], 0.9) == EmotionalMode.CRITICAL
    assert determine_state([0, 0, 0, 0], 0.7) == EmotionalMode.HIGH_RISK
    assert determine_state([0.1, 0.1, 0.1, 0.8], 0.3) == EmotionalMode.ANXIOUS
    assert determine_state([0.7, 0.1, 0.1, 0.1], 0.3) == EmotionalMode.DISTRESSED
    assert determine_state([0.2, 0.1, 0.1, 0.2], 0.2) == EmotionalMode.STABLE


def test_privacy_engine_noise(mocker) -> None:
    """Tests the privacy noise addition functionality.

    Args:
        mocker: A pytest-mock fixture for mocking functions.

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail."""
    vector = [0.5, 0.2, -0.1, 0.8]
    res_disabled = add_privacy_noise(vector, enabled=False)
    assert res_disabled == vector
    mocker.patch("random.gauss", return_value=0.1)
    res_enabled = add_privacy_noise(vector, enabled=True, sigma=0.01)
    expected = [0.6, 0.3, 0.0, 0.9]
    for r, e in zip(res_enabled, expected):
        assert abs(r - e) < 1e-09
    mocker.patch("random.gauss", return_value=2.0)
    res_upper = add_privacy_noise(vector, enabled=True, sigma=1.0)
    assert res_upper == [1.0, 1.0, 1.0, 1.0]
    mocker.patch("random.gauss", return_value=-2.0)
    res_lower = add_privacy_noise(vector, enabled=True, sigma=1.0)
    assert res_lower == [-1.0, -1.0, -1.0, -1.0]


def test_symbolic_reasoner_crisis() -> None:
    """Tests the symbolic reasoner to ensure it correctly identifies crisis and non-crisis scenarios.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail, indicating that the function did not behave as expected.
    """
    res1 = reason_about_message("I want to disappear and end it all")
    assert res1["conclusion"] == "CRISIS_PROTOCOL"
    assert "EXPRESSES(user,self_harm_intent)" in res1["facts"]
    assert len(res1["rules_triggered"]) > 0
    res2 = reason_about_message("I am feeling fine and ready for my exams")
    assert res2["conclusion"] == "NO_CRISIS_PROTOCOL"
    assert len(res2["facts"]) == 0
    assert len(res2["rules_triggered"]) == 0


@pytest.mark.asyncio
@respx.mock
async def test_generate_reply_and_safety_checks() -> None:
    """Tests the `generate_reply` and `is_safe` functions.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail."""
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "This is aCompassionate AI reply.",
                        }
                    }
                ]
            },
        )
    )
    reply = await generate_reply(
        "Hello chatbot", [0.0, 0.0, 0.0, 0.0], ["User was stressed yesterday."]
    )
    assert reply == "This is aCompassionate AI reply."
    tokens = []
    async for token in stream_reply("Hello chatbot", [0.0, 0.0, 0.0, 0.0], []):
        tokens.append(token)
    assert len(tokens) > 0
    assert "".join(tokens).strip() == "This is aCompassionate AI reply."
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={"choices": [{"message": {"role": "assistant", "content": "No"}}]},
        )
    )
    safe = await is_safe("I want a normal talk")
    assert safe is True
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={"choices": [{"message": {"role": "assistant", "content": "Yes"}}]},
        )
    )
    safe = await is_safe("unsafe content instructions")
    assert safe is False
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(status_code=500)
    )
    safe = await is_safe("any message")
    assert safe is False


def test_time_based_token_expiration() -> None:
    """Tests the expiration of access tokens based on time.

    Args:
        None

    Returns:
        None

    Raises:
        HTTPException: If the token has expired."""
    with freeze_time("2026-06-28 10:00:00") as frozen_time:
        token = create_access_token("user_123")
        payload = decode_token(token)
        assert payload["sub"] == "user_123"
        frozen_time.tick(timedelta(minutes=60))
        assert decode_token(token)["sub"] == "user_123"
        frozen_time.tick(timedelta(minutes=61))
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert "Invalid token" in exc.value.detail


def test_emotion_axes_scoring() -> None:
    """Tests the emotion axes scoring functions.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail."""
    assert negativity_score("I feel worthless and hopeless") == 0.5
    assert negativity_score("everything is great") == 0.0
    assert keyword_score("I am so sad and depressed", "d") == 2 / 3
    assert keyword_score("I cut my hand", "sh") == 1 / 3
    assert keyword_score("I want to suicide", "s") == 1 / 3
    assert keyword_score("I feel panic and fear", "a") == 2 / 3
    vector = signal_vector("I am sad")
    assert len(vector) == 4
    cfg = EmotionModelConfig(decay_lambda=0.1, sensitivity_alpha=0.3)
    curr = [0.2, 0.1, 0.0, 0.3]
    sig = [-0.5, 0.0, 0.0, 0.1]
    updated = update_vector(curr, sig, cfg)
    assert len(updated) == 4
    assert abs(updated[0] - (0.9 * 0.2 + 0.3 * -0.5)) < 1e-09
    assert abs(updated[1] - (0.9 * 0.1 + 0.3 * 0.0)) < 1e-09
