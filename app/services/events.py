from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemEvent


class EventType(StrEnum):
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    EMOTION_UPDATED = "EMOTION_UPDATED"
    RISK_EVALUATED = "RISK_EVALUATED"
    STATE_TRANSITION = "STATE_TRANSITION"
    SAFETY_CHECKED = "SAFETY_CHECKED"
    RESPONSE_GENERATED = "RESPONSE_GENERATED"


async def emit_event(db: AsyncSession, *, user_id: UUID, event_type: EventType | str, payload: dict[str, Any]) -> SystemEvent:
    event = SystemEvent(user_id=user_id, event_type=str(event_type), payload=payload)
    db.add(event)
    await db.flush()
    return event
