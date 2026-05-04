import httpx

from app.config import settings

_HEADERS = {"Authorization": "Bearer ollama"}

_SAFETY_SYSTEM = (
    "You are a content safety classifier. "
    "Your only task is to decide whether the user message below violates "
    "any of these policies:\n"
    "  • Hate speech or discrimination targeting individuals or groups\n"
    "  • Harassment, threats, or targeted abuse\n"
    "  • Dangerous instructions (weapons, self-harm methods, illegal acts)\n\n"
    "Respond with EXACTLY one word — either SAFE or UNSAFE — and nothing else."
)


class SafetyClassificationError(Exception):
    """Raised when ShieldGemma cannot be reached or returns an unusable response."""


async def _classify(message: str) -> str:
    """
    Classify a user message as `SAFE` or `UNSAFE` by querying the external safety classifier.
    
    Sends the message to the configured external `/chat/completions` endpoint and normalizes the classifier's single-word response to uppercase. If the external service returns an HTTP error or is unreachable, a `SafetyClassificationError` is raised. If the response is malformed or missing the expected content, the function falls back to returning `'UNSAFE'`.
    
    Returns:
        verdict (str): Either `'SAFE'` or `'UNSAFE'`, uppercase.
    
    Raises:
        SafetyClassificationError: If the external service returns a non-success HTTP status or the request fails.
    """
    payload = {
        "model": settings.safety_model,
        "messages": [
            {"role": "system", "content": _SAFETY_SYSTEM},
            {"role": "user", "content": message},
        ],
        "temperature": 0.0,
        "max_tokens": 4,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/chat/completions",
                json=payload,
                headers=_HEADERS,
            )
            resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            return 'UNSAFE'
        return content.strip().upper()
    except httpx.HTTPStatusError as e:
        raise SafetyClassificationError(
            f"ShieldGemma returned HTTP {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        raise SafetyClassificationError(
            f"ShieldGemma unreachable or malformed response: {e}"
        ) from e
    except (KeyError, IndexError, TypeError, AttributeError, ValueError):
        return 'UNSAFE'


async def is_safe(message: str) -> bool:
    """
    Determine whether a user message is classified as safe.
    
    If the safety classifier cannot be reached or returns an error, the message is treated as unsafe.
    
    Returns:
        `true` if the classifier verdict does not contain "UNSAFE", `false` otherwise.
    """
    try:
        verdict = await _classify(message)
        return "UNSAFE" not in verdict
    except SafetyClassificationError as e:
        return False


SAFETY_REPLY = (
    "I'm not able to respond to that message. "
    "If you're in crisis or danger, please reach out for immediate support:\n\n"
    "• **AASRA**: +91-9820466726 (24/7)\n"
    "• **Kiran Mental Health Helpline**: 1800-599-0019 (24/7, Govt. of India)\n"
    "• **Snehi Foundation**: +91-22-2772-6771\n"
    "• **iCALL (TISS)**: +91-9152987821 (Mon–Sat, 10am–8pm)\n"
    "• **Vandrevala Foundation Helpline**: 9999 666 555 or 1860 2662 345\n"
    "• **Find more resources**: https://findahelpline.com/\n\n"
    "You don't have to face this alone."
)
