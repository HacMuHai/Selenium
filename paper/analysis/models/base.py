"""
Interface chung cho 3 model. Giữ đúng khuôn `train` / `predict` của repo gốc, thêm:

- `predict_batch`: predict từng dòng một cho 250k comment là bất khả thi về thời gian.
  Đây là yêu cầu chức năng, không phải tối ưu sớm.
- `save` / `load`: train một lần, dùng nhiều lần ở CLI lẫn API.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Sequence

import pandas as pd

from paper.analysis.preprocessing import PREPROCESSING_VERSION


class ModelVersionMismatch(RuntimeError):
    """Artifact được train bằng phiên bản preprocessing khác -> phải train lại."""


class SentimentModel(ABC):
    """Model phân loại cảm xúc 3 lớp: negative / neutral / positive."""

    name: ClassVar[str] = "base"

    @abstractmethod
    def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None:
        """`train_df` có 2 cột bắt buộc: `text`, `sentiment`."""

    @abstractmethod
    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        """Trả `(nhãn, điểm số từng lớp)`."""

    def predict_batch(self, texts: Sequence[str]) -> list[str]:
        """Mặc định gọi `predict` lần lượt; lớp con nào nhanh hơn thì override."""
        return [self.predict(t)[0] for t in texts]

    @abstractmethod
    def save(self, models_dir: Path) -> None: ...

    @classmethod
    @abstractmethod
    def load(cls, models_dir: Path) -> "SentimentModel": ...

    # ----- dùng chung cho phần lưu/nạp -----

    @staticmethod
    def _check_version(version: object) -> None:
        if version != PREPROCESSING_VERSION:
            raise ModelVersionMismatch(
                f"Artifact dùng preprocessing {version!r}, code hiện tại là "
                f"{PREPROCESSING_VERSION!r}. Chạy lại `python -m src.analyze train`."
            )

    @staticmethod
    def _class_weights(train_df: pd.DataFrame) -> dict[str, float]:
        """Trọng số nghịch đảo tần suất, kiểu `balanced` của sklearn."""
        counts = train_df["sentiment"].value_counts()
        total, n_classes = len(train_df), len(counts)
        return {label: total / (n_classes * count) for label, count in counts.items()}
