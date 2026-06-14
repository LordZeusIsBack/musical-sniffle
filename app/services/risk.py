from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def calculate_risk_score(vector: list[float]) -> float:
    """Calculate normalized mental-health risk from [depression, self-harm, suicidality, anxiety]."""
    depression, self_harm, suicidality, anxiety = (list(vector) + [0.0] * 4)[:4]
    score = 0.40 * suicidality + 0.30 * self_harm + 0.20 * depression + 0.10 * anxiety
    return round(_clip(score), 6)


def risk_level(score: float) -> RiskLevel:
    """Map a normalized risk score to deterministic risk levels."""
    if score >= 0.85:
        return RiskLevel.CRITICAL
    if score >= 0.60:
        return RiskLevel.HIGH
    if score >= 0.30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
