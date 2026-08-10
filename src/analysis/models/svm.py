"""
SVM + TF-IDF (port từ repo gốc), sửa 3 điểm:

1. `preprocessor=normalize_text` -> chuẩn hoá tiếng Việt trước khi tách từ.
2. `ngram_range=(1, 2)` -> bù việc không tách được từ ghép.
3. `class_weight="balanced"` + `predict_batch` vector hoá cả lô một lần.
"""
from pathlib import Path
from typing import Sequence

import joblib
import pandas as pd

from src.analysis.metrics import LABELS
from src.analysis.models.base import SentimentModel
from src.analysis.preprocessing import PREPROCESSING_VERSION, normalize_text

ARTIFACT = "svm.joblib"


class SVMModel(SentimentModel):
    name = "svm"

    def __init__(self, seed: int = 42) -> None:
        self.model = None
        self.vectorizer = None
        self.seed = seed

    def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import SVC

        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            preprocessor=normalize_text,
        )
        features = self.vectorizer.fit_transform(train_df["text"])

        self.model = SVC(
            kernel="linear",
            probability=True,
            class_weight="balanced" if class_weight else None,
            random_state=self.seed,
        )
        self.model.fit(features, train_df["sentiment"])

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        features = self.vectorizer.transform([text])
        label = self.model.predict(features)[0]
        proba = self.model.predict_proba(features)[0]
        scores = {cls: float(p) for cls, p in zip(self.model.classes_, proba)}
        return str(label), {k: scores.get(k, 0.0) for k in LABELS}

    def predict_batch(self, texts: Sequence[str]) -> list[str]:
        """Vector hoá + predict cả lô một lần - nhanh hơn vòng lặp hàng nghìn lần."""
        if not len(texts):
            return []
        return [str(x) for x in self.model.predict(self.vectorizer.transform(list(texts)))]

    def save(self, models_dir: Path) -> None:
        models_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"version": PREPROCESSING_VERSION, "model": self.model, "vectorizer": self.vectorizer},
            models_dir / ARTIFACT,
        )

    @classmethod
    def load(cls, models_dir: Path) -> "SVMModel":
        payload = joblib.load(models_dir / ARTIFACT)
        cls._check_version(payload.get("version"))
        model = cls()
        model.model = payload["model"]
        model.vectorizer = payload["vectorizer"]
        return model
