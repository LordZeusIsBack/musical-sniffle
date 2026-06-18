from __future__ import annotations
from collections.abc import AsyncGenerator
import httpx
from app.config import settings
_HEADERS = {'Authorization': 'Bearer ollama'}
SYSTEM_PROMPT = 'You are a compassionate therapy support assistant. Be non-judgmental, concise, and safe. If user expresses imminent self-harm/suicide risk, encourage contacting emergency services or a crisis line.'

async def generate_reply(message: str, emotional_vector: list[float], memories: list[str] | None = None) -> str:
    """Generates a reply to a user message based on the provided emotional vector.

Args:
    message (str): The user's input message.
    emotional_vector (list[float]): A list of floats representing the user's emotional state.

Returns:
    str: The generated reply from the model.

Raises:
    httpx.HTTPStatusError: If the HTTP request returns an unsuccessful status code."""
    memory_block = '\n'.join(f'- {m}' for m in (memories or [])) or 'No prior summaries.'
    payload = {'model': settings.generator_model, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': f'Relevant privacy-preserving memory summaries:\n{memory_block}\nUser message (do not repeat verbatim): {message}\nEmotional state vector: {emotional_vector}'}], 'temperature': 0.5, 'stream': False}
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f'{settings.ollama_base_url}/chat/completions', json=payload, headers=_HEADERS)
        resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']

async def stream_reply(message: str, emotional_vector: list[float], memories: list[str] | None = None) -> AsyncGenerator[str, None]:
    """Stream a reply to a message with an emotional vector.

Args:
    message (str): The input message.
    emotional_vector (list[float]): A list of floats representing the emotional state.

Returns:
    AsyncGenerator[str, None]: An asynchronous generator yielding tokens from the generated reply."""
    reply = await generate_reply(message=message, emotional_vector=emotional_vector, memories=memories)
    for token in reply.split():
        yield (token + ' ')