"""
LSTM Keras (port từ repo gốc), sửa 4 điểm:

1. `import tensorflow` LÀ LAZY - nạp TF mất 5-10s, không được bắt CLI/API chờ khi không dùng.
2. `max_length` dùng **percentile 95** thay cho `max()`. Bản gốc pad mọi chuỗi tới độ dài
   của comment dài nhất (2246 ký tự) -> ma trận khổng lồ toàn số 0.
3. `class_weight` khi fit.
4. `verbose=0` - progress bar của Keras làm bẩn log.
"""
from pathlib import Path
from typing import Sequence

import joblib
import pandas as pd

from src.analysis.metrics import LABELS
from src.analysis.models.base import SentimentModel
from src.analysis.preprocessing import PREPROCESSING_VERSION, normalize_text

ARTIFACT_MODEL = "lstm.keras"
ARTIFACT_META = "lstm_meta.joblib"

VOCAB_SIZE = 5000
MIN_LENGTH = 10
LABEL_TO_ID = {label: i for i, label in enumerate(LABELS)}
ID_TO_LABEL = {i: label for label, i in LABEL_TO_ID.items()}


def tensorflow_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("tensorflow") is not None


class LSTMModel(SentimentModel):
    name = "lstm"

    def __init__(self, epochs: int = 5, seed: int = 42) -> None:
        self.model = None
        self.tokenizer = None
        self.max_length: int = MIN_LENGTH
        self.epochs = epochs
        self.seed = seed

    def _build(self, max_length: int):
        import tensorflow as tf

        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(max_length,)),
                tf.keras.layers.Embedding(VOCAB_SIZE, 100),
                tf.keras.layers.LSTM(64, return_sequences=True),
                tf.keras.layers.LSTM(32),
                tf.keras.layers.Dense(64, activation="relu"),
                tf.keras.layers.Dropout(0.5),
                tf.keras.layers.Dense(len(LABELS), activation="softmax"),
            ]
        )
        model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        return model

    def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None:
        import numpy as np
        import tensorflow as tf
        from tensorflow.keras.preprocessing.sequence import pad_sequences
        from tensorflow.keras.preprocessing.text import Tokenizer

        tf.keras.utils.set_random_seed(self.seed)

        texts = [normalize_text(t) for t in train_df["text"]]
        self.tokenizer = Tokenizer(num_words=VOCAB_SIZE, oov_token="<oov>")
        self.tokenizer.fit_on_texts(texts)

        sequences = self.tokenizer.texts_to_sequences(texts)
        lengths = [len(s) for s in sequences if s] or [MIN_LENGTH]
        # percentile 95, KHÔNG dùng max(): comment dài nhất 2246 ký tự sẽ pad mọi thứ tới đó
        self.max_length = max(MIN_LENGTH, int(np.percentile(lengths, 95)))

        features = pad_sequences(sequences, maxlen=self.max_length)
        targets = train_df["sentiment"].map(LABEL_TO_ID).to_numpy()

        weights = None
        if class_weight:
            weights = {
                LABEL_TO_ID[label]: w for label, w in self._class_weights(train_df).items()
            }

        self.model = self._build(self.max_length)
        self.model.fit(
            features,
            targets,
            epochs=self.epochs,
            batch_size=32,
            validation_split=0.1,
            class_weight=weights,
            verbose=0,
        )

    def _vectorize(self, texts: Sequence[str]):
        from tensorflow.keras.preprocessing.sequence import pad_sequences

        normalized = [normalize_text(t) for t in texts]
        return pad_sequences(
            self.tokenizer.texts_to_sequences(normalized), maxlen=self.max_length
        )

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        import numpy as np

        proba = self.model.predict(self._vectorize([text]), verbose=0)[0]
        scores = {ID_TO_LABEL[i]: float(p) for i, p in enumerate(proba)}
        return ID_TO_LABEL[int(np.argmax(proba))], scores

    def predict_batch(self, texts: Sequence[str]) -> list[str]:
        import numpy as np

        if not len(texts):
            return []
        proba = self.model.predict(self._vectorize(list(texts)), verbose=0)
        return [ID_TO_LABEL[int(i)] for i in np.argmax(proba, axis=1)]

    def save(self, models_dir: Path) -> None:
        models_dir.mkdir(parents=True, exist_ok=True)
        self.model.save(models_dir / ARTIFACT_MODEL)
        joblib.dump(
            {
                "version": PREPROCESSING_VERSION,
                "tokenizer": self.tokenizer,
                "max_length": self.max_length,
            },
            models_dir / ARTIFACT_META,
        )

    @classmethod
    def load(cls, models_dir: Path) -> "LSTMModel":
        import tensorflow as tf

        payload = joblib.load(models_dir / ARTIFACT_META)
        cls._check_version(payload.get("version"))
        model = cls()
        model.tokenizer = payload["tokenizer"]
        model.max_length = payload["max_length"]
        model.model = tf.keras.models.load_model(models_dir / ARTIFACT_MODEL)
        return model
