from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemEvent


class EventType(StrEnum):
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    EMOTION_UPDATED = "EMOTION_UPDATED"
    RISK_EVALUATED = "RISK_EVALUATED"
    STATE_TRANSITION = "STATE_TRANSITION"
    SAFETY_CHECKED = "SAFETY_CHECKED"
    RESPONSE_GENERATED = "RESPONSE_GENERATED"


def make_json_safe(obj):
    if isinstance(obj, np.floating):
        return float(obj)

    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, list):
        return [make_json_safe(x) for x in obj]

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    return obj


async def emit_event(db: AsyncSession, *, user_id: UUID, event_type: EventType | str, payload: dict[str, Any]) -> SystemEvent:
    event = SystemEvent(user_id=user_id, event_type=str(event_type), payload=make_json_safe(payload))
    db.add(event)
    await db.flush()
    return event
