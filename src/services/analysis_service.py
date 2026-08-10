"""
Nghiệp vụ cho API `/analyze`. Ném exception domain; router không try/except.
"""
import logging
from typing import Optional

from src.analysis.predictor import ModelNotTrained, Predictor
from src.analysis.registry import available_names
from src.analysis.report import render_html
from src.analysis.trainer import load_metadata
from src.dto.analysis import ModelInfo, ModelsOut, PredictionOut  # noqa: F401
from src.services.errors import ModelNotTrainedError, UnknownModelError

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, predictor: Predictor, default_model: str) -> None:
        self.predictor = predictor
        self.default_model = default_model

    def predict(self, text: str, model: Optional[str] = None) -> PredictionOut:
        name = (model or self.default_model).strip().lower()
        # whitelist theo registry - KHÔNG bao giờ ghép tên vào đường dẫn file
        if name not in available_names():
            raise UnknownModelError(
                f"Model {name!r} không dùng được. Hợp lệ: {', '.join(available_names())}"
            )
        try:
            result = self.predictor.predict_text(text, name)
        except ModelNotTrained as exc:
            raise ModelNotTrainedError(str(exc)) from exc
        return PredictionOut(**result)

    def compare(self, text: str) -> list[PredictionOut]:
        """Cho MỌI model đã train cùng đoán 1 câu - để so sánh trực tiếp.

        Model nào chưa train thì bỏ qua, không làm hỏng cả request.
        """
        out: list[PredictionOut] = []
        for name in available_names():
            try:
                out.append(PredictionOut(**self.predictor.predict_text(text, name)))
            except ModelNotTrained:
                logger.debug("Bỏ qua model chưa train: %s", name)
        if not out:
            raise ModelNotTrainedError(
                "Chưa có model nào. Chạy: python -m src.analyze train"
            )
        return out

    def list_models(self) -> ModelsOut:
        """Chưa train không phải lỗi - trả list rỗng để FE hiển thị 'chưa có model'."""
        metadata = load_metadata(self.predictor.models_dir)
        if metadata is None:
            return ModelsOut(models=[])

        models = [
            ModelInfo(
                name=name,
                macro_f1=info.get("metrics", {}).get("macro_f1"),
                accuracy=info.get("metrics", {}).get("accuracy"),
                train_seconds=info.get("train_seconds"),
            )
            for name, info in metadata.get("models", {}).items()
        ]
        models.sort(key=lambda m: m.macro_f1 or 0, reverse=True)
        return ModelsOut(
            models=models,
            baseline=metadata.get("baseline", {}),
            trained_at=metadata.get("trained_at"),
        )

    def report_html(self) -> str:
        metadata = load_metadata(self.predictor.models_dir)
        if metadata is None:
            raise ModelNotTrainedError(
                "Chưa có model. Chạy: python -m src.analyze train"
            )
        return render_html(metadata)
