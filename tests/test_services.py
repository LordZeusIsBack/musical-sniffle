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
from app.services.emotion import EmotionModelConfig, update_vector, signal_vector, polarity_score, negativity_score, keyword_score
from app.services.auth import create_access_token, decode_token, hash_password, verify_password, TOKEN_BLACKLIST
from app.services.llm import generate_reply, stream_reply
from app.services.safety import is_safe, SafetyClassificationError, SAFETY_REPLY
from app.services.classifier import EmotionClassifier


# ==========================================
# 1. RISK ENGINE TESTS
# ==========================================
def test_risk_engine_logic() -> None:
    # Formula: 0.40 * suicidality + 0.30 * self_harm + 0.20 * depression + 0.10 * anxiety
    # Low Risk
    low_vector = [0.1, 0.1, 0.1, 0.1]
    # 0.40*0.1 + 0.30*0.1 + 0.20*0.1 + 0.10*0.1 = 0.1
    assert calculate_risk_score(low_vector) == 0.1
    assert risk_level(0.1) == RiskLevel.LOW

    # Medium Risk
    med_vector = [0.5, 0.4, 0.2, 0.1]
    # 0.40*0.2 + 0.30*0.4 + 0.20*0.5 + 0.10*0.1 = 0.08 + 0.12 + 0.10 + 0.01 = 0.31
    assert calculate_risk_score(med_vector) == 0.31
    assert risk_level(0.31) == RiskLevel.MEDIUM

    # High Risk
    high_vector = [0.8, 0.6, 0.5, 0.4]
    # 0.40*0.5 + 0.30*0.6 + 0.20*0.8 + 0.10*0.4 = 0.20 + 0.18 + 0.16 + 0.04 = 0.58 -> wait, 0.58 is MEDIUM?
    # Let's verify risk_level thresholds: LOW (<0.3), MEDIUM (<0.6), HIGH (<0.85), CRITICAL (>=0.85)
    assert risk_level(0.58) == RiskLevel.MEDIUM
    assert risk_level(0.60) == RiskLevel.HIGH

    # Critical Risk
    crit_vector = [0.9, 0.9, 0.9, 0.9]
    assert risk_level(0.85) == RiskLevel.CRITICAL
    assert calculate_risk_score(crit_vector) == 0.9
    assert risk_level(calculate_risk_score(crit_vector)) == RiskLevel.CRITICAL

    # Edge cases - clipping
    assert calculate_risk_score([2.0, 2.0, 2.0, 2.0]) == 1.0
    assert calculate_risk_score([-1.0, -1.0, -1.0, -1.0]) == 0.0


# ==========================================
# 2. STATE MACHINE TESTS
# ==========================================
def test_state_machine_transitions() -> None:
    # Precedence:
    # 1. risk_score >= critical_threshold -> CRITICAL
    # 2. risk_score >= high_threshold -> HIGH_RISK
    # 3. anxiety > 0.70 -> ANXIOUS
    # 4. depression > 0.60 -> DISTRESSED
    # 5. default -> STABLE

    # CRITICAL
    assert determine_state([0, 0, 0, 0], 0.9) == EmotionalMode.CRITICAL

    # HIGH_RISK
    assert determine_state([0, 0, 0, 0], 0.7) == EmotionalMode.HIGH_RISK

    # ANXIOUS (anxiety = 0.8)
    assert determine_state([0.1, 0.1, 0.1, 0.8], 0.3) == EmotionalMode.ANXIOUS

    # DISTRESSED (depression = 0.7)
    assert determine_state([0.7, 0.1, 0.1, 0.1], 0.3) == EmotionalMode.DISTRESSED

    # STABLE
    assert determine_state([0.2, 0.1, 0.1, 0.2], 0.2) == EmotionalMode.STABLE


# ==========================================
# 3. PRIVACY ENGINE TESTS
# ==========================================
def test_privacy_engine_noise(mocker) -> None:
    vector = [0.5, 0.2, -0.1, 0.8]

    # When disabled
    res_disabled = add_privacy_noise(vector, enabled=False)
    assert res_disabled == vector

    # When enabled, with random mock
    mocker.patch("random.gauss", return_value=0.1)
    res_enabled = add_privacy_noise(vector, enabled=True, sigma=0.01)
    # Each value should have 0.1 added and be clipped within [-1.0, 1.0]
    expected = [0.6, 0.3, 0.0, 0.9]
    for r, e in zip(res_enabled, expected):
        assert abs(r - e) < 1e-9

    # Test clipping upper boundary
    mocker.patch("random.gauss", return_value=2.0)
    res_upper = add_privacy_noise(vector, enabled=True, sigma=1.0)
    assert res_upper == [1.0, 1.0, 1.0, 1.0]

    # Test clipping lower boundary
    mocker.patch("random.gauss", return_value=-2.0)
    res_lower = add_privacy_noise(vector, enabled=True, sigma=1.0)
    assert res_lower == [-1.0, -1.0, -1.0, -1.0]


# ==========================================
# 4. SYMBOLIC REASONER TESTS
# ==========================================
def test_symbolic_reasoner_crisis() -> None:
    # Triggers crisis
    res1 = reason_about_message("I want to disappear and end it all")
    assert res1["conclusion"] == "CRISIS_PROTOCOL"
    assert "EXPRESSES(user,self_harm_intent)" in res1["facts"]
    assert len(res1["rules_triggered"]) > 0

    # Does not trigger crisis
    res2 = reason_about_message("I am feeling fine and ready for my exams")
    assert res2["conclusion"] == "NO_CRISIS_PROTOCOL"
    assert len(res2["facts"]) == 0
    assert len(res2["rules_triggered"]) == 0


# ==========================================
# 5. LLM AND SAFETY ENGINE MOCKING (RESPX)
# ==========================================
@pytest.mark.asyncio
@respx.mock
async def test_generate_reply_and_safety_checks() -> None:
    # 5a. Test generate_reply success
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "This is aCompassionate AI reply."
                        }
                    }
                ]
            }
        )
    )

    reply = await generate_reply("Hello chatbot", [0.0, 0.0, 0.0, 0.0], ["User was stressed yesterday."])
    assert reply == "This is aCompassionate AI reply."

    # 5b. Test stream_reply generator
    tokens = []
    async for token in stream_reply("Hello chatbot", [0.0, 0.0, 0.0, 0.0], []):
        tokens.append(token)

    # stream_reply calls generate_reply, then splits the string by space and yields tokens
    assert len(tokens) > 0
    assert "".join(tokens).strip() == "This is aCompassionate AI reply."

    # 5c. Test is_safe with positive verdict (No policy violation -> safe)
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "No"
                        }
                    }
                ]
            }
        )
    )
    safe = await is_safe("I want a normal talk")
    assert safe is True

    # 5d. Test is_safe with negative verdict (Yes policy violation -> unsafe)
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Yes"
                        }
                    }
                ]
            }
        )
    )
    safe = await is_safe("unsafe content instructions")
    assert safe is False

    # 5e. Test is_safe with classification error (ShieldGemma returns error)
    respx.post(f"{settings.ollama_base_url}/chat/completions").mock(
        return_value=Response(status_code=500)
    )
    # If the safety check fails, it should default to unsafe (False)
    safe = await is_safe("any message")
    assert safe is False


# ==========================================
# 6. TIME-BASED LOGIC (FREEZEGUN)
# ==========================================
def test_time_based_token_expiration() -> None:
    # Create token at frozen time
    with freeze_time("2026-06-28 10:00:00") as frozen_time:
        token = create_access_token("user_123")
        payload = decode_token(token)
        assert payload["sub"] == "user_123"

        # Advance time by 60 minutes (expires in 120 minutes by default config)
        frozen_time.tick(timedelta(minutes=60))
        # Decoding should still succeed
        assert decode_token(token)["sub"] == "user_123"

        # Advance past expiration (121 minutes total elapsed)
        frozen_time.tick(timedelta(minutes=61))
        # Decoding should raise invalid token error due to expiration
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert "Invalid token" in exc.value.detail


# ==========================================
# 7. EMOTIONAL CLASSIFIER / KEYWORD AXES
# ==========================================
def test_emotion_axes_scoring() -> None:
    # Test negativity score calculation
    assert negativity_score("I feel worthless and hopeless") == 0.5  # 2 matching phrases out of 4 max (worthless, hopeless)
    assert negativity_score("everything is great") == 0.0

    # Test keyword scores
    assert keyword_score("I am so sad and depressed", "d") == 2 / 3  # sad, depressed in AXIS_KEYWORDS['d']
    assert keyword_score("I cut my hand", "sh") == 1 / 3            # cut in AXIS_KEYWORDS['sh']
    assert keyword_score("I want to suicide", "s") == 1 / 3         # suicide in AXIS_KEYWORDS['s']
    assert keyword_score("I feel panic and fear", "a") == 2 / 3     # panic, fear in AXIS_KEYWORDS['a']

    # Test signal vector construction
    vector = signal_vector("I am sad")
    assert len(vector) == 4

    # Test vector updating with EmotionModelConfig
    cfg = EmotionModelConfig(decay_lambda=0.1, sensitivity_alpha=0.3)
    curr = [0.2, 0.1, 0.0, 0.3]
    sig = [-0.5, 0.0, 0.0, 0.1]
    updated = update_vector(curr, sig, cfg)
    assert len(updated) == 4
    # Check formula: (1 - 0.1) * curr + 0.3 * sig
    assert abs(updated[0] - ((0.9 * 0.2) + (0.3 * -0.5))) < 1e-9  # 0.18 - 0.15 = 0.03
    assert abs(updated[1] - ((0.9 * 0.1) + (0.3 * 0.0))) < 1e-9   # 0.09
