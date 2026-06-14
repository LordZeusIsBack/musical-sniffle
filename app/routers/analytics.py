from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EmotionalState, ExplanationRecord, SystemEvent, User
from app.schemas import EventResponse, ExplanationResponse, HistoryResponse, RiskResponse, TrendsResponse
from app.services.auth import get_current_user
from app.services.emotion_history import calculate_momentum, calculate_moving_average, calculate_trend, calculate_volatility, get_history
from app.services.risk import calculate_risk_score, risk_level

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/history", response_model=HistoryResponse)
async def history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return {"history": await get_history(db, user_id=user.id)}


@router.get("/trends", response_model=TrendsResponse)
async def trends(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    rows = await get_history(db, user_id=user.id)
    vectors = [list(row.vector) for row in rows]
    return {"trend": calculate_trend(vectors), "momentum": await calculate_momentum(db, user_id=user.id), "moving_average": calculate_moving_average(vectors), "volatility": calculate_volatility(vectors)}


@router.get("/risk", response_model=RiskResponse)
async def risk(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    state = (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()
    score = calculate_risk_score(list(state.vector))
    return {"score": score, "level": risk_level(score).value}


@router.get("/explain/{id}", response_model=ExplanationResponse)
async def explain(id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ExplanationRecord:
    record = (await db.execute(select(ExplanationRecord).where(ExplanationRecord.id == id, ExplanationRecord.user_id == user.id))).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Explanation trace not found")
    return record


@router.get("/events", response_model=list[EventResponse])
async def events(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[SystemEvent]:
    rows = await db.execute(select(SystemEvent).where(SystemEvent.user_id == user.id).order_by(SystemEvent.timestamp.desc()).limit(100))
    return list(rows.scalars().all())
