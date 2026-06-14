from __future__ import annotations

import random

from app.config import settings


def add_privacy_noise(vector: list[float], *, enabled: bool | None = None, sigma: float | None = None) -> list[float]:
    """Add Gaussian differential-privacy style noise to an emotional vector.

    The mechanism returns x' = clip(x + N(0, sigma^2)). It is disabled by default
    because clinical UX should remain stable unless ENABLE_DP=true is explicitly set.
    """
    use_noise = settings.enable_dp if enabled is None else enabled
    noise_sigma = settings.dp_noise_sigma if sigma is None else sigma
    if not use_noise or noise_sigma <= 0:
        return [float(v) for v in vector]
    return [max(-1.0, min(1.0, float(v) + random.gauss(0.0, noise_sigma))) for v in vector]
