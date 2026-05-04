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
from app.services.safety import SAFETY_REPLY, is_safe


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
    """
    Handle an incoming chat message by updating the user's emotional state, performing a safety check, and returning a reply.
    
    Parameters:
        payload (ChatMessageRequest): The message payload containing `message` and optional `conversation_id`. If `conversation_id` is absent, a new conversation may be created.
    
    Returns:
        ChatMessageResponse: An object containing `conversation_id`, `reply` (either a generated reply or the predefined safety reply when the message is unsafe), and `emotional_vector` updated to reflect the new message.
    
    Side effects:
        - Persists the updated EmotionalState.vector to the database and commits the transaction.
        - May create a new Conversation when no conversation_id is provided.
    """
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

    if not await is_safe(payload.message):
        await db.commit()
        return ChatMessageResponse(
            conversation_id=convo.id,
            reply=SAFETY_REPLY,
            emotional_vector=next_vector
        )

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
    """
    Stream a generated chat reply as Server-Sent Events while updating the user's emotional state.
    
    Updates the authenticated user's emotional vector based on `message` and commits the change before producing any events. If the message is considered unsafe, emits a single event containing the safety reply token; otherwise streams tokens produced by the reply generator. Always emits a final event with `done: True`, the `conversation_id`, and the updated emotional vector as a list of floats.
    
    Parameters:
        message (str): The message text to send (1–4000 characters).
        conversation_id (UUID | None): Optional conversation identifier to target or create.
    
    Returns:
        StreamingResponse: An SSE stream where each event contains a JSON object with a `token` string for reply tokens (or the safety token) and a final event containing `done: True`, `conversation_id` (string), and `vector` (list of floats).
    """
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

    message_safe = await is_safe(message)

    async def event_generator():
        """
        Produce Server-Sent Events (SSE) payloads representing either a safety response, a streamed reply, and a final completion event.
        
        Yields:
            SSE-formatted strings. Emits a single event containing `{'token': SAFETY_REPLY}` if the message is unsafe; otherwise emits one event per token produced by `stream_reply`. After those events, emits a final event with a JSON payload containing `done: True`, `conversation_id` (string), and `vector` (list of floats).
        """
        if not message_safe:
            yield f"data: {json.dumps({'token': SAFETY_REPLY})}\n\n"
        else:
            async for token in stream_reply(message, next_vector):
                yield f"data: {json.dumps({'token': token})}\n\n"

        clean_vector = [float(val) for val in next_vector]
        yield f"data: {json.dumps({'done': True, 'conversation_id': str(convo.id), 'vector': clean_vector})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
