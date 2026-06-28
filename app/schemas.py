from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class ChatMessageResponse(BaseModel):
    conversation_id: UUID
    reply: str
    emotional_vector: list[float]


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class EmotionalStateResponse(BaseModel):
    vector: list[float]
    updated_at: datetime


class EmotionalSnapshotResponse(BaseModel):
    id: UUID
    timestamp: datetime
    vector: list[float]
    mode: str
    risk_score: float


class HistoryResponse(BaseModel):
    history: list[EmotionalSnapshotResponse]


class TrendsResponse(BaseModel):
    trend: str
    momentum: dict[str, list[float]]
    moving_average: list[float]
    volatility: float


class RiskResponse(BaseModel):
    score: float
    level: str


class ExplanationResponse(BaseModel):
    id: UUID
    created_at: datetime
    trace: dict


class EventResponse(BaseModel):
    id: UUID
    timestamp: datetime
    event_type: str
    payload: dict


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

