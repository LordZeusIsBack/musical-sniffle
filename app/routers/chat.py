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
from app.services.classifier import EmotionClassifier
from app.services.emotion import EmotionModelConfig, keyword_score, negativity_score, polarity_score, signal_vector, update_vector
from app.services.emotion_history import create_snapshot
from app.services.events import EventType, emit_event
from app.services.explainability import build_trace, store_trace
from app.services.llm import generate_reply, stream_reply
from app.services.memory import retrieve_memories, store_memory
from app.services.privacy import add_privacy_noise
from app.services.risk import RiskLevel, calculate_risk_score, risk_level
from app.services.safety import SAFETY_REPLY, is_safe
from app.services.state_machine import determine_state
from app.services.symbolic_reasoner import reason_about_message

router = APIRouter(prefix="/chat", tags=["chat"])
_classifier = EmotionClassifier()


async def _resolve_conversation(*, db: AsyncSession, user: User, conversation_id: UUID | None, message: str) -> Conversation:
    if conversation_id:
        convo = (await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))).scalar_one_or_none()
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return convo
    convo = Conversation(user_id=user.id, title=" ".join(message.strip().split()[:8]) or "New conversation")
    db.add(convo)
    await db.flush()
    return convo


async def _process_message(db: AsyncSession, user: User, message: str) -> tuple[list[float], str, str, list[str], bool, object]:
    state = (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()
    previous = list(state.vector)
    classifier_result = _classifier.classify(message)
    signal = signal_vector(message)
    hybrid_signal = [(a + b) / 2 for a, b in zip(signal, classifier_result["vector"], strict=True)]
    next_vector = add_privacy_noise(update_vector(previous, hybrid_signal, EmotionModelConfig(settings.decay_lambda, settings.sensitivity_alpha)))
    score = calculate_risk_score(next_vector)
    symbolic = reason_about_message(message)
    if symbolic["conclusion"] == "CRISIS_PROTOCOL":
        score = max(score, settings.critical_risk_threshold)
    level = risk_level(score)
    mode = determine_state(next_vector, score, settings.high_risk_threshold, settings.critical_risk_threshold).value
    state.vector = next_vector
    await emit_event(db, user_id=user.id, event_type=EventType.MESSAGE_RECEIVED, payload={"conversation_content": "redacted"})
    await emit_event(db, user_id=user.id, event_type=EventType.EMOTION_UPDATED, payload={"previous": previous, "updated": next_vector})
    await emit_event(db, user_id=user.id, event_type=EventType.RISK_EVALUATED, payload={"score": score, "level": level.value, "symbolic": symbolic})
    snapshot = await create_snapshot(db, user_id=user.id, vector=next_vector, mode=mode, risk_score=score)
    memories = await retrieve_memories(db, user_id=user.id, query=message, top_k=3)
    await store_memory(db, user_id=user.id, message=message)
    safe = await is_safe(message)
    await emit_event(db, user_id=user.id, event_type=EventType.SAFETY_CHECKED, payload={"safe": safe, "mode": mode})
    momentum = {"current_vector": next_vector, "previous_vector": previous, "momentum": [c - p for c, p in zip(next_vector, previous, strict=True)]}
    trace = build_trace(message_analysis={"sentiment": polarity_score(message), "negativity": negativity_score(message), "keyword_scores": {axis: keyword_score(message, axis) for axis in ("d", "sh", "s", "a")}, "classifier": classifier_result}, signal_vector=hybrid_signal, previous_state=previous, updated_state=next_vector, momentum=momentum["momentum"], risk_score=score, risk_level=level.value, state_machine_mode=mode, safety_check={"safe": safe, "symbolic_reasoning": symbolic})
    await store_trace(db, user_id=user.id, trace=trace)
    await emit_event(db, user_id=user.id, event_type=EventType.STATE_TRANSITION, payload={"mode": mode})
    return next_vector, level.value, mode, [m.summary for m in memories], safe, snapshot


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))).scalars().all()


@router.get("/state", response_model=EmotionalStateResponse)
async def get_state(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmotionalState:
    return (await db.execute(select(EmotionalState).where(EmotionalState.user_id == user.id))).scalar_one()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(payload: ChatMessageRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ChatMessageResponse:
    convo = await _resolve_conversation(db=db, user=user, conversation_id=payload.conversation_id, message=payload.message)
    next_vector, level, _mode, memories, safe, _snapshot = await _process_message(db, user, payload.message)
    if level == RiskLevel.CRITICAL.value or not safe:
        reply = SAFETY_REPLY
    else:
        reply = await generate_reply(payload.message, next_vector, memories)
    await emit_event(db, user_id=user.id, event_type=EventType.RESPONSE_GENERATED, payload={"llm_bypassed": level == RiskLevel.CRITICAL.value or not safe})
    await db.commit()
    return ChatMessageResponse(conversation_id=convo.id, reply=reply, emotional_vector=next_vector)


@router.get("/stream")
async def stream_message(message: str = Query(min_length=1, max_length=4000), conversation_id: UUID | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    convo = await _resolve_conversation(db=db, user=user, conversation_id=conversation_id, message=message)
    next_vector, level, _mode, memories, safe, _snapshot = await _process_message(db, user, message)
    await db.commit()

    async def event_generator():
        if level == RiskLevel.CRITICAL.value or not safe:
            yield f"data: {json.dumps({'token': SAFETY_REPLY})}\n\n"
        else:
            async for token in stream_reply(message, next_vector, memories):
                yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True, 'conversation_id': str(convo.id), 'vector': [float(v) for v in next_vector]})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
