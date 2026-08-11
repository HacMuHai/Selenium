"""
Tra cứu model theo tên. LSTM tự bị loại nếu chưa cài TensorFlow - đó là lựa chọn hợp lệ,
không phải lỗi, nên chỉ log INFO.
"""
import logging
from typing import Type

from paper.analysis.models.base import SentimentModel

logger = logging.getLogger(__name__)

_ALL_NAMES = ("nb", "svm", "lstm")


def _tensorflow_installed() -> bool:
    import importlib.util

    return importlib.util.find_spec("tensorflow") is not None


def available_names() -> list[str]:
    """Tên các model dùng được trong môi trường hiện tại."""
    if _tensorflow_installed():
        return list(_ALL_NAMES)
    logger.info("Chưa cài TensorFlow - bỏ qua model 'lstm'")
    return [n for n in _ALL_NAMES if n != "lstm"]


def get_model_class(name: str) -> Type[SentimentModel]:
    """Import trễ để không kéo sklearn/tensorflow khi chỉ cần một model."""
    key = name.strip().lower()
    if key == "nb":
        from paper.analysis.models.naive_bayes import NaiveBayesModel

        return NaiveBayesModel
    if key == "svm":
        from paper.analysis.models.svm import SVMModel

        return SVMModel
    if key == "lstm":
        if not _tensorflow_installed():
            raise ValueError("Model 'lstm' cần TensorFlow: pip install tensorflow")
        from paper.analysis.models.lstm import LSTMModel

        return LSTMModel
    raise ValueError(f"Model không hợp lệ: {name!r}. Hợp lệ: {', '.join(_ALL_NAMES)}")


def parse_model_list(raw: str) -> list[str]:
    """`"nb,svm"` -> `["nb", "svm"]`, validate từng tên."""
    names = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not names:
        raise ValueError("Danh sách model rỗng")
    for name in names:
        if name not in _ALL_NAMES:
            raise ValueError(f"Model không hợp lệ: {name!r}. Hợp lệ: {', '.join(_ALL_NAMES)}")
    return names
