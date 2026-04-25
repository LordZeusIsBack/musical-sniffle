from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Conversation, EmotionalState, User
from app.schemas import ChatMessageRequest, ChatMessageResponse, ConversationResponse, EmotionalStateResponse
from app.services.auth import get_current_user
from app.services.emotion import EmotionModelConfig, signal_vector, update_vector
from app.services.llm import generate_reply, stream_reply


router = APIRouter(prefix="/chat", tags=["chat"])


async def _resolve_conversation(
    *, db: AsyncSession, user: User, conversation_id: UUID | None, message: str
) -> Conversation:
    if conversation_id:
        convo = (
            await db.execute(
                select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
            )
        ).scalar_one_or_none()
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return convo

    title = " ".join(message.strip().split()[:8])
    if not title:
        title = "New conversation"
    convo = Conversation(user_id=user.id, title=title)
    db.add(convo)
    await db.flush()
    return convo


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))
    ).scalars().all()
    return rows


@router.get("/state", response_model=EmotionalStateResponse)
async def get_state(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmotionalState:
    state = (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()
    return state


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    payload: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    convo = await _resolve_conversation(db=db, user=user, conversation_id=payload.conversation_id, message=payload.message)
    state = (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()

    signal = signal_vector(payload.message)
    next_vector = update_vector(
        current=list(state.vector),
        signal=signal,
        cfg=EmotionModelConfig(
            decay_lambda=settings.decay_lambda,
            sensitivity_alpha=settings.sensitivity_alpha,
        ),
    )
    state.vector = next_vector

    reply = await generate_reply(payload.message, next_vector)

    await db.commit()
    return ChatMessageResponse(conversation_id=convo.id, reply=reply, emotional_vector=next_vector)


@router.get("/stream")
async def stream_message(
    message: str = Query(min_length=1, max_length=4000),
    conversation_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await _resolve_conversation(db=db, user=user, conversation_id=conversation_id, message=message)
    state = (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()

    signal = signal_vector(message)
    next_vector = update_vector(
        current=list(state.vector),
        signal=signal,
        cfg=EmotionModelConfig(
            decay_lambda=settings.decay_lambda,
            sensitivity_alpha=settings.sensitivity_alpha,
        ),
    )
    state.vector = next_vector
    await db.commit()

    async def event_generator():
        async for token in stream_reply(message, next_vector):
            yield f"data: {json.dumps({'token': token})}\n\n"

        clean_vector = [float(val) for val in next_vector]
        yield f"data: {json.dumps({'done': True, 'conversation_id': str(convo.id), 'vector': clean_vector})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
