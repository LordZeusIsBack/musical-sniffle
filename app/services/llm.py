from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx

from app.config import settings

_HEADERS = {"Authorization": "Bearer ollama"}


SYSTEM_PROMPT = (
    "You are a compassionate therapy support assistant. Be non-judgmental, concise, and safe. "
    "If user expresses imminent self-harm/suicide risk, encourage contacting emergency services or a crisis line."
)


async def generate_reply(message: str, emotional_vector: list[float]) -> str:
    payload = {
        "model": settings.generator_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "User message (do not repeat verbatim): "
                    f"{message}\nEmotional state vector: {emotional_vector}"
                ),
            },
        ],
        "temperature": 0.5,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{settings.ollama_base_url}/chat/completions", json=payload, headers=_HEADERS)
        resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def stream_reply(message: str, emotional_vector: list[float]) -> AsyncGenerator[str, None]:
    reply = await generate_reply(message=message, emotional_vector=emotional_vector)
    for token in reply.split():
        yield token + " "