"""
Huấn luyện + đánh giá + ghi `metadata.json`.

Đánh giá dùng `predict_batch` một lần cho cả tập test, KHÔNG lặp `iterrows()` gọi `predict()`
như bản gốc (vừa chậm vừa chỉ trả accuracy).
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from src.analysis import metrics
from src.analysis.dataset import CleaningStats, describe_split
from src.analysis.preprocessing import PREPROCESSING_VERSION
from src.analysis.registry import get_model_class

logger = logging.getLogger(__name__)

METADATA_FILE = "metadata.json"
SCHEMA_VERSION = 1
MAX_ERROR_SAMPLES = 10


@dataclass
class TrainResult:
    name: str
    train_seconds: float
    n_train: int


class Trainer:
    def __init__(self, models_dir: str | Path, seed: int = 42) -> None:
        self.models_dir = Path(models_dir)
        self.seed = seed

    def train(
        self,
        names: Sequence[str],
        train_df: pd.DataFrame,
        class_weight: bool = True,
        epochs: int = 5,
    ) -> dict[str, TrainResult]:
        if self.models_dir.exists() and any(self.models_dir.iterdir()):
            logger.warning("Ghi đè artifact cũ trong %s", self.models_dir)

        results: dict[str, TrainResult] = {}
        for name in names:
            cls = get_model_class(name)
            model = cls(epochs=epochs, seed=self.seed) if name == "lstm" else cls()
            logger.info("Đang train %s trên %d mẫu...", name, len(train_df))

            started = time.perf_counter()
            model.train(train_df, class_weight=class_weight)
            elapsed = time.perf_counter() - started

            model.save(self.models_dir)
            results[name] = TrainResult(name, elapsed, len(train_df))
            logger.info("Xong %s trong %.1fs", name, elapsed)
        return results

    def evaluate(self, names: Sequence[str], test_df: pd.DataFrame) -> dict[str, dict]:
        y_true = list(test_df["sentiment"])
        texts = list(test_df["text"])

        out: dict[str, dict] = {}
        for name in names:
            model = get_model_class(name).load(self.models_dir)

            started = time.perf_counter()
            y_pred = model.predict_batch(texts)
            predict_seconds = time.perf_counter() - started

            report = metrics.evaluation_report(y_true, y_pred)
            report["predict_seconds"] = predict_seconds
            report["errors_sample"] = self._error_samples(texts, y_true, y_pred)
            out[name] = report
            logger.info(
                "%s: accuracy=%.3f macro_f1=%.3f (%.1fs)",
                name, report["accuracy"], report["macro_f1"], predict_seconds,
            )
        return out

    @staticmethod
    def _error_samples(
        texts: Sequence[str], y_true: Sequence[str], y_pred: Sequence[str]
    ) -> list[dict]:
        """Vài ví dụ đoán sai - hữu ích để biết model yếu ở đâu."""
        samples = []
        for text, true, pred in zip(texts, y_true, y_pred):
            if true == pred:
                continue
            samples.append({"text": str(text)[:200], "true": true, "pred": pred})
            if len(samples) >= MAX_ERROR_SAMPLES:
                break
        return samples

    def write_metadata(
        self,
        stats: CleaningStats,
        split_info: dict,
        results: dict[str, TrainResult],
        evaluations: dict[str, dict],
        baseline: dict,
        test_size: float,
        binary: Optional[dict] = None,
    ) -> Path:
        try:
            import sklearn

            sklearn_version = sklearn.__version__
        except ImportError:  # pragma: no cover - sklearn luôn có khi train
            sklearn_version = None

        payload = {
            "schema": SCHEMA_VERSION,
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "seed": self.seed,
            "test_size": test_size,
            "preprocessing_version": PREPROCESSING_VERSION,
            "sklearn_version": sklearn_version,
            "dataset": stats.as_dict(),
            "split": split_info,
            "baseline": baseline,
            # Kết quả 2 lớp (bỏ neutral) - để so được với các bài chỉ phân cực/tiêu cực.
            # Không thay bảng chính, chỉ là bảng phụ giải thích vì sao bảng chính thấp hơn.
            "binary": binary,
            "models": {
                name: {
                    "train_seconds": results[name].train_seconds if name in results else None,
                    "metrics": evaluations.get(name, {}),
                }
                for name in evaluations
            },
        }
        self.models_dir.mkdir(parents=True, exist_ok=True)
        path = self.models_dir / METADATA_FILE
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def load_metadata(models_dir: str | Path) -> Optional[dict]:
    """Đọc `metadata.json`; trả `None` nếu chưa train (không phải lỗi)."""
    path = Path(models_dir) / METADATA_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
