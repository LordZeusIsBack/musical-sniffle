from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx

from app.config import settings


SYSTEM_PROMPT = (
    "You are a compassionate therapy support assistant. Be non-judgmental, concise, and safe. "
    "If user expresses imminent self-harm/suicide risk, encourage contacting emergency services or a crisis line."
)


async def generate_reply(message: str, emotional_vector: list[float]) -> str:
    if not settings.openai_api_key:
        return (
            "I hear you. Thank you for sharing this. Let's take one small step together: "
            "try a slow breath in for 4 seconds, hold 4, and out for 6. "
            f"Current emotional signal snapshot: {emotional_vector}."
        )

    payload = {
        "model": settings.openai_model,
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
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.openai_base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


async def stream_reply(message: str, emotional_vector: list[float]) -> AsyncGenerator[str, None]:
    reply = await generate_reply(message=message, emotional_vector=emotional_vector)
    for token in reply.split():
        yield token + " "
