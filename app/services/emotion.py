from __future__ import annotations
from dataclasses import dataclass
NEGATIVE_PHRASES = {'hopeless', 'worthless', 'empty', "can't go on", 'cant go on', 'panic', 'anxious', 'hurt', 'die', 'kill myself', 'suicide'}
AXIS_KEYWORDS: dict[str, set[str]] = {'d': {'sad', 'empty', 'hopeless', 'worthless', 'depressed'}, 'sh': {'hurt', 'cut', 'self-harm', 'burn'}, 's': {'die', 'suicide', 'kill myself', 'end it', 'not exist'}, 'a': {'panic', 'anxious', 'fear', 'worry', 'overwhelmed'}}
AXIS_WEIGHTS = {'d': (0.55, 0.25, 0.2), 'sh': (0.35, 0.25, 0.4), 's': (0.3, 0.3, 0.4), 'a': (0.45, 0.35, 0.2)}

@dataclass
class EmotionModelConfig:
    decay_lambda: float
    sensitivity_alpha: float

def _clip(value: float, lower: float=-1.0, upper: float=1.0) -> float:
    """Clips a given value to be within a specified range.

Args:
    value (float): The value to clip.
    lower (float, optional): The lower bound of the clipping range. Defaults to -1.0.
    upper (float, optional): The upper bound of the clipping range. Defaults to 1.0.

Returns:
    float: The clipped value."""
    return max(lower, min(upper, value))

def polarity_score(text: str) -> float:
    """Calculate the polarity score of a given text.

Args:
    text (str): The input text to analyze.

Returns:
    float: A polarity score indicating the sentiment of the text."""
    txt = text.lower()
    if any((word in txt for word in ['better', 'hopeful', 'calm', 'okay', 'good'])):
        return 0.4
    if any((word in txt for word in ['bad', 'sad', 'hopeless', 'worthless', 'panic', 'die'])):
        return -0.7
    return 0.0

def negativity_score(text: str) -> float:
    '''Calculate the negativity score of a given text.

Args:
    text (str): The input text to analyze for negativity.

Returns:
    float: A value between 0.0 and 1.0 representing the negativity score.
"""

def negativity_score(text: str) -> float:
    txt = text.lower()
    matches = sum((1 for phrase in NEGATIVE_PHRASES if phrase in txt))
    return _clip(matches / 4.0, 0.0, 1.0)'''
    txt = text.lower()
    matches = sum((1 for phrase in NEGATIVE_PHRASES if phrase in txt))
    return _clip(matches / 4.0, 0.0, 1.0)

def keyword_score(text: str, axis: str) -> float:
    """Calculates the keyword score for a given text based on specified axis.

Args:
    text (str): The input text to analyze.
    axis (str): The axis to use for keyword matching.

Returns:
    float: A normalized score between 0.0 and 1.0 indicating the presence of keywords."""
    txt = text.lower()
    matches = sum((1 for word in AXIS_KEYWORDS[axis] if word in txt))
    return _clip(matches / 3.0, 0.0, 1.0)

def signal_vector(text: str) -> list[float]:
    '''Computes a signal vector based on the text input.

Args:
    text (str): The input text to analyze.

Returns:
    list[float]: A list of four float values representing the signal in different axes.
"""'''
    sentiment = polarity_score(text)
    negativity = negativity_score(text)
    signal = []
    for axis in ['d', 'sh', 's', 'a']:
        w1, w2, w3 = AXIS_WEIGHTS[axis]
        kw = keyword_score(text, axis)
        score = w1 * sentiment + w2 * negativity + w3 * kw
        signal.append(_clip(score))
    return signal

def update_vector(current: list[float], signal: list[float], cfg: EmotionModelConfig) -> list[float]:
    """Updates a vector based on the current state and a new signal.

Args:
    current: A list of floats representing the current state.
    signal: A list of floats representing the new signal to be processed.
    cfg: An EmotionModelConfig object containing configuration parameters for the update process.

Returns:
    A list of floats representing the updated state after applying the signal and configuration settings."""
    lam = _clip(cfg.decay_lambda, 0.05, 0.2)
    alpha = _clip(cfg.sensitivity_alpha, 0.1, 0.5)
    next_state = []
    for cur, sig in zip(current, signal, strict=True):
        value = (1 - lam) * cur + alpha * sig
        next_state.append(_clip(value))
    return next_state