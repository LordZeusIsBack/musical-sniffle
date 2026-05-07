from __future__ import annotations

from dataclasses import dataclass


NEGATIVE_PHRASES = {
    "hopeless",
    "worthless",
    "empty",
    "can't go on",
    "cant go on",
    "panic",
    "anxious",
    "hurt",
    "die",
    "kill myself",
    "suicide",
}

AXIS_KEYWORDS: dict[str, set[str]] = {
    "d": {"sad", "empty", "hopeless", "worthless", "depressed"},
    "sh": {"hurt", "cut", "self-harm", "burn"},
    "s": {"die", "suicide", "kill myself", "end it", "not exist"},
    "a": {"panic", "anxious", "fear", "worry", "overwhelmed"},
}

AXIS_WEIGHTS = {
    "d": (0.55, 0.25, 0.20),
    "sh": (0.35, 0.25, 0.40),
    "s": (0.30, 0.30, 0.40),
    "a": (0.45, 0.35, 0.20),
}


@dataclass
class EmotionModelConfig:
    decay_lambda: float
    sensitivity_alpha: float


def _clip(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def polarity_score(text: str) -> float:
    txt = text.lower()
    if any(word in txt for word in ["better", "hopeful", "calm", "okay", "good"]):
        return 0.4
    if any(word in txt for word in ["bad", "sad", "hopeless", "worthless", "panic", "die"]):
        return -0.7
    return 0.0


def negativity_score(text: str) -> float:
    txt = text.lower()
    matches = sum(1 for phrase in NEGATIVE_PHRASES if phrase in txt)
    return _clip(matches / 4.0, 0.0, 1.0)


def keyword_score(text: str, axis: str) -> float:
    txt = text.lower()
    matches = sum(1 for word in AXIS_KEYWORDS[axis] if word in txt)
    return _clip(matches / 3.0, 0.0, 1.0)


def signal_vector(text: str) -> list[float]:
    sentiment = polarity_score(text)
    negativity = negativity_score(text)
    signal = []
    for axis in ["d", "sh", "s", "a"]:
        w1, w2, w3 = AXIS_WEIGHTS[axis]
        kw = keyword_score(text, axis)
        score = (w1 * sentiment) + (w2 * negativity) + (w3 * kw)
        signal.append(_clip(score))
    return signal


def update_vector(current: list[float], signal: list[float], cfg: EmotionModelConfig) -> list[float]:
    lam = _clip(cfg.decay_lambda, 0.05, 0.2)
    alpha = _clip(cfg.sensitivity_alpha, 0.1, 0.5)

    next_state = []
    for cur, sig in zip(current, signal, strict=True):
        value = ((1 - lam) * cur) + (alpha * sig)
        next_state.append(_clip(value))
    return next_state