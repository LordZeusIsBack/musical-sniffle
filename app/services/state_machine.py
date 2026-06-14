from __future__ import annotations

from enum import StrEnum


class EmotionalMode(StrEnum):
    STABLE = "STABLE"
    DISTRESSED = "DISTRESSED"
    ANXIOUS = "ANXIOUS"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


def determine_state(vector: list[float], risk_score: float, high_threshold: float = 0.60, critical_threshold: float = 0.85) -> EmotionalMode:
    """Map each vector to exactly one deterministic safety/emotional state by precedence."""
    depression, _self_harm, _suicidality, anxiety = (list(vector) + [0.0] * 4)[:4]
    if risk_score >= critical_threshold:
        return EmotionalMode.CRITICAL
    if risk_score >= high_threshold:
        return EmotionalMode.HIGH_RISK
    if anxiety > 0.70:
        return EmotionalMode.ANXIOUS
    if depression > 0.60:
        return EmotionalMode.DISTRESSED
    return EmotionalMode.STABLE
