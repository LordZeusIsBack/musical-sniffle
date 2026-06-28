from __future__ import annotations

from typing import Any
from app.services.emotion import keyword_score

LABEL_TO_VECTOR: dict[str, list[float]] = {
    "sadness": [0.7, 0.1, 0.1, 0.2],
    "anger": [0.2, 0.2, 0.1, 0.4],
    "fear": [0.2, 0.1, 0.1, 0.8],
    "joy": [-0.4, 0.0, 0.0, -0.2],
    "neutral": [0.0, 0.0, 0.0, 0.0],
}


class EmotionClassifier:
    """Hybrid local classifier facade for DeBERTa-v3-small-mnli-fever-docnli-ling-2c with keyword fallback."""

    def __init__(self) -> None:
        self._pipe: Any = None

    def _get_pipeline(self) -> Any:
        if self._pipe is None:
            import torch
            from transformers import pipeline

            model_path = r"C:\Users\ASUS\.hf_models\DeBERTa-v3-small-mnli-fever-docnli-ling-2c" # nosec
            device = 0 if torch.cuda.is_available() else -1
            self._pipe = pipeline(
                "zero-shot-classification",
                model=model_path,
                device=device
            )
        return self._pipe

    def classify(self, text: str) -> dict[str, Any]:
        pipe = self._get_pipeline()
        candidate_labels = ["sadness", "anger", "fear", "joy", "neutral"]
        hypothesis_template = "This text expresses {}."

        # Run zero-shot classification
        res = pipe(text, candidate_labels, hypothesis_template=hypothesis_template)

        # Get top predicted label and individual scores
        predicted_label = res["labels"][0]
        scores = dict(zip(res["labels"], res["scores"]))

        # Map to vector and apply safety/suicide boosting
        mapped = LABEL_TO_VECTOR[predicted_label].copy()
        mapped[1] = max(mapped[1], keyword_score(text, "sh"))
        mapped[2] = max(mapped[2], keyword_score(text, "s"))

        return {
            "label": predicted_label,
            "scores": scores,
            "vector": mapped,
        }
