from app.services.emotion_history import calculate_trend
from app.services.risk import RiskLevel, calculate_risk_score, risk_level
from app.services.state_machine import EmotionalMode, determine_state
from app.services.symbolic_reasoner import reason_about_message


def test_risk_engine_weights() -> None:
    """Tests the risk engine weights calculation and risk level determination.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the test assertions fail."""
    assert calculate_risk_score([1.0, 1.0, 1.0, 1.0]) == 1.0
    assert risk_level(0.9) == RiskLevel.CRITICAL


def test_state_machine_precedence() -> None:
    """Tests the precedence of states in a state machine.

    Args:
        test_data (list[float]): A list of probabilities.
        threshold (float): The threshold value for determining the state.

    Returns:
        None"""
    assert determine_state([0.1, 0.1, 0.9, 0.1], 0.9) == EmotionalMode.CRITICAL
    assert determine_state([0.1, 0.1, 0.1, 0.8], 0.2) == EmotionalMode.ANXIOUS


def test_trend_declining_means_risk_increasing() -> None:
    """Tests if a declining trend in data means an increasing risk.

    Args:
        None

    Returns:
        str: The string 'DECLINING'.

    Raises:
        AssertionError: If the calculated trend does not match 'DECLINING'."""
    assert (
        calculate_trend([[0, 0, 0, 0], [0.4, 0.4, 0.4, 0.4], [0.8, 0.8, 0.8, 0.8]])
        == "DECLINING"
    )


def test_symbolic_reasoner_crisis_protocol() -> None:
    """Tests the symbolic reasoning function for crisis protocol.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If the conclusion of the reasoning process is not 'CRISIS_PROTOCOL'.
    """
    assert (
        reason_about_message("I want to disappear")["conclusion"] == "CRISIS_PROTOCOL"
    )
