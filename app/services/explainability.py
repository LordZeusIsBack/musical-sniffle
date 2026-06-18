from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExplanationRecord

ExplanationTrace = dict[str, Any]


async def store_trace(db: AsyncSession, *, user_id: UUID, trace: ExplanationTrace) -> ExplanationRecord:
    record = ExplanationRecord(user_id=user_id, trace=trace)
    db.add(record)
    await db.flush()
    return record


def build_trace(**kwargs: Any) -> ExplanationTrace:
    """Build a raw-text-free explainability trace from derived metadata only."""
    return dict(kwargs)
