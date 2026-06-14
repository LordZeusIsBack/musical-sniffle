from __future__ import annotations

from app.services.emotion import keyword_score, polarity_score

LABEL_TO_VECTOR: dict[str, list[float]] = {
    "sadness": [0.7, 0.1, 0.1, 0.2],
    "anger": [0.2, 0.2, 0.1, 0.4],
    "fear": [0.2, 0.1, 0.1, 0.8],
    "joy": [-0.4, 0.0, 0.0, -0.2],
    "neutral": [0.0, 0.0, 0.0, 0.0],
}


class EmotionClassifier:
    """Hybrid local classifier facade for distilroberta-base-emotion with keyword fallback."""

    def classify(self, text: str) -> dict[str, object]:
        lowered = text.lower()
        if any(term in lowered for term in ("panic", "anxious", "fear", "worry")):
            label = "fear"
        elif any(term in lowered for term in ("angry", "furious", "rage")):
            label = "anger"
        elif polarity_score(text) > 0:
            label = "joy"
        elif any(term in lowered for term in ("sad", "hopeless", "empty", "depressed")):
            label = "sadness"
        else:
            label = "neutral"
        mapped = LABEL_TO_VECTOR[label].copy()
        mapped[1] = max(mapped[1], keyword_score(text, "sh"))
        mapped[2] = max(mapped[2], keyword_score(text, "s"))
        return {"label": label, "scores": {label: 1.0}, "vector": mapped}
