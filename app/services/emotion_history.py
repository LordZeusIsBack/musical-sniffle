from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmotionalSnapshot
from app.services.risk import calculate_risk_score
from app.services.state_machine import determine_state

Trend = str


async def create_snapshot(db: AsyncSession, *, user_id: UUID, vector: list[float], mode: str | None = None, risk_score: float | None = None) -> EmotionalSnapshot:
    """Persist a privacy-preserving emotional timeline point."""
    score = calculate_risk_score(vector) if risk_score is None else risk_score
    snapshot = EmotionalSnapshot(user_id=user_id, vector=vector, mode=mode or determine_state(vector, score).value, risk_score=score)
    db.add(snapshot)
    await db.flush()
    return snapshot


async def get_history(db: AsyncSession, *, user_id: UUID, limit: int = 100) -> list[EmotionalSnapshot]:
    result = await db.execute(select(EmotionalSnapshot).where(EmotionalSnapshot.user_id == user_id).order_by(EmotionalSnapshot.timestamp.desc()).limit(limit))
    return list(reversed(result.scalars().all()))


def calculate_moving_average(vectors: list[list[float]], window: int = 5) -> list[float]:
    sample = vectors[-window:]
    if not sample:
        return [0.0, 0.0, 0.0, 0.0]
    return [sum(row[i] for row in sample) / len(sample) for i in range(4)]


def calculate_volatility(vectors: list[list[float]], window: int = 10) -> float:
    sample = vectors[-window:]
    if len(sample) < 2:
        return 0.0
    risks = [calculate_risk_score(v) for v in sample]
    mean = sum(risks) / len(risks)
    return (sum((r - mean) ** 2 for r in risks) / len(risks)) ** 0.5


def calculate_trend(vectors: list[list[float]]) -> Trend:
    if len(vectors) < 2:
        return "STABLE"
    risks = [calculate_risk_score(v) for v in vectors]
    n = len(risks)
    mean_x = (n - 1) / 2
    mean_y = sum(risks) / n
    denom = sum((i - mean_x) ** 2 for i in range(n)) or 1.0
    slope = sum((i - mean_x) * (risk - mean_y) for i, risk in enumerate(risks)) / denom
    if slope < -0.01:
        return "IMPROVING"
    if slope > 0.01:
        return "DECLINING"
    return "STABLE"


async def calculate_momentum(db: AsyncSession, *, user_id: UUID) -> dict[str, list[float]]:
    history = await get_history(db, user_id=user_id, limit=2)
    current = list(history[-1].vector) if history else [0.0, 0.0, 0.0, 0.0]
    previous = list(history[-2].vector) if len(history) > 1 else [0.0, 0.0, 0.0, 0.0]
    return {"current_vector": current, "previous_vector": previous, "momentum": [c - p for c, p in zip(current, previous, strict=True)]}
