"""DTO cho API `/analyze`."""
from typing import Optional

from pydantic import BaseModel, Field

from src.dto.base import BaseResponse


class PredictRequest(BaseModel):
    # clamp độ dài: chặn payload khổng lồ ăn CPU
    text: str = Field(min_length=1, max_length=5000)
    model: Optional[str] = Field(default=None, description="nb | svm | lstm")


class PredictionOut(BaseModel):
    model_config = {"protected_namespaces": ()}  # cho phép field tên "model"

    model: str
    sentiment: str
    scores: dict[str, float]


class ModelInfo(BaseModel):
    name: str
    macro_f1: Optional[float] = None
    accuracy: Optional[float] = None
    train_seconds: Optional[float] = None


class ModelsOut(BaseModel):
    models: list[ModelInfo]
    baseline: dict = Field(default_factory=dict)
    trained_at: Optional[str] = None


class PredictResponse(BaseResponse[PredictionOut]):
    pass


class CompareResponse(BaseResponse[list[PredictionOut]]):
    pass


class ModelListResponse(BaseResponse[ModelsOut]):
    pass
