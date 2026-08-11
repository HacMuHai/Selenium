"""
Nạp artifact và dự đoán - dùng chung cho CLI lẫn API.

Model nạp LAZY và cache theo tên: nạp cả 3 model (có TensorFlow) làm uvicorn khởi động
chậm 10-20s dù có thể không ai gọi tới.
"""
import logging
from pathlib import Path
from typing import Optional

from openpyxl import Workbook

from paper.analysis.dataset import iter_untagged_files
from paper.analysis.models.base import SentimentModel
from paper.analysis.registry import get_model_class

logger = logging.getLogger(__name__)

OUT_HEADER = ["link", "name_item", "comments_id", "comments_content", "sentiment", "sentiment_model"]


class ModelNotTrained(RuntimeError):
    """Chưa có artifact cho model được yêu cầu."""


class Predictor:
    def __init__(self, models_dir: str | Path) -> None:
        self.models_dir = Path(models_dir)
        self._cache: dict[str, SentimentModel] = {}

    def load(self, name: str) -> SentimentModel:
        if name in self._cache:
            return self._cache[name]
        cls = get_model_class(name)  # ném ValueError nếu tên sai
        try:
            model = cls.load(self.models_dir)
        except FileNotFoundError as exc:
            raise ModelNotTrained(
                f"Chưa có model {name!r} trong {self.models_dir}. "
                f"Chạy: python -m src.analyze train --models {name}"
            ) from exc
        self._cache[name] = model
        return model

    def predict_text(self, text: str, name: str) -> dict:
        label, scores = self.load(name).predict(text)
        return {"model": name, "sentiment": label, "scores": scores}

    def predict_dir(self, input_dir: str, output_dir: str, name: str) -> list[Path]:
        """Mỗi file Excel vào → một file ra, thêm cột `sentiment` + `sentiment_model`."""
        source = Path(input_dir).resolve()
        target = Path(output_dir).resolve()
        if source == target:
            raise ValueError("Thư mục đầu ra phải khác thư mục đầu vào")
        target.mkdir(parents=True, exist_ok=True)

        model = self.load(name)
        written: list[Path] = []
        total_rows = 0

        for index, (path, rows) in enumerate(iter_untagged_files(str(source)), start=1):
            if not rows:
                continue
            labels = model.predict_batch([r["comments_content"] for r in rows])

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Predictions"
            sheet.append(OUT_HEADER)
            for row, label in zip(rows, labels):
                sheet.append(
                    [
                        row["link"], row["name_item"], row["comments_id"],
                        row["comments_content"], label, name,
                    ]
                )

            out_path = target / f"{path.stem}_pred.xlsx"
            workbook.save(str(out_path))
            written.append(out_path)
            total_rows += len(rows)

            if index % 20 == 0:
                logger.info("Đã xử lý %d file (%d dòng)...", index, total_rows)

        logger.info("Hoàn thành: %d file, %d dòng -> %s", len(written), total_rows, target)
        return written
