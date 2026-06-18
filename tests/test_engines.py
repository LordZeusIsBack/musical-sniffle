from app.services.emotion_history import calculate_trend
from app.services.risk import RiskLevel, calculate_risk_score, risk_level
from app.services.state_machine import EmotionalMode, determine_state
from app.services.symbolic_reasoner import reason_about_message


def test_risk_engine_weights() -> None:
    assert calculate_risk_score([1.0, 1.0, 1.0, 1.0]) == 1.0
    assert risk_level(0.9) == RiskLevel.CRITICAL


def test_state_machine_precedence() -> None:
    assert determine_state([0.1, 0.1, 0.9, 0.1], 0.9) == EmotionalMode.CRITICAL
    assert determine_state([0.1, 0.1, 0.1, 0.8], 0.2) == EmotionalMode.ANXIOUS


def test_trend_declining_means_risk_increasing() -> None:
    assert calculate_trend([[0, 0, 0, 0], [0.4, 0.4, 0.4, 0.4], [0.8, 0.8, 0.8, 0.8]]) == "DECLINING"


def test_symbolic_reasoner_crisis_protocol() -> None:
    assert reason_about_message("I want to disappear")["conclusion"] == "CRISIS_PROTOCOL"
