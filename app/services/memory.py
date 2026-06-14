from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MemoryEmbedding

EMBEDDING_DIMENSIONS = 768


def summarize_message(text: str) -> str:
    """Create a privacy-preserving thematic summary without persisting raw text."""
    lowered = text.lower()
    if "interview" in lowered or "job" in lowered:
        return "User discussed work or interview anxiety"
    if "sleep" in lowered:
        return "User discussed sleep-related distress"
    if "school" in lowered or "exam" in lowered:
        return "User discussed academic stress"
    if "panic" in lowered or "anxious" in lowered:
        return "User discussed anxiety symptoms"
    if "sad" in lowered or "hopeless" in lowered:
        return "User discussed low mood"
    return "User discussed emotional wellbeing"


def embed_text(text: str) -> list[float]:
    """Local deterministic embedding fallback sized for pgvector Vector(768).

    Deployments can replace this with sentence-transformers/all-MiniLM-L6-v2 while
    preserving the database contract and privacy boundary.
    """
    digest = hashlib.sha256(text.encode()).digest()
    return [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(EMBEDDING_DIMENSIONS)]


async def store_memory(db: AsyncSession, *, user_id: UUID, message: str) -> MemoryEmbedding:
    summary = summarize_message(message)
    memory = MemoryEmbedding(user_id=user_id, summary=summary, embedding=embed_text(summary))
    db.add(memory)
    await db.flush()
    return memory


async def retrieve_memories(db: AsyncSession, *, user_id: UUID, query: str, top_k: int = 3) -> list[MemoryEmbedding]:
    query_embedding = embed_text(summarize_message(query))
    stmt = select(MemoryEmbedding).where(MemoryEmbedding.user_id == user_id).order_by(MemoryEmbedding.embedding.cosine_distance(query_embedding)).limit(top_k)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())
