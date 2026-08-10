"""
Router `/analyze`.

Route là `def` (sync): predict là CPU-bound blocking, `async def` sẽ chặn event loop.
FastAPI tự đẩy route sync sang threadpool.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from src.analysis.predictor import Predictor
from src.config.settings import get_settings
from src.dto.analysis import (
    CompareResponse,
    ModelListResponse,
    PredictRequest,
    PredictResponse,
)
from src.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analyze", tags=["analyze"])


def get_service() -> AnalysisService:
    """Dependency - override được trong test."""
    settings = get_settings()
    return AnalysisService(Predictor(settings.models_dir), settings.default_model)


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, service: AnalysisService = Depends(get_service)):
    """Dự đoán cảm xúc của một đoạn text."""
    return PredictResponse(
        data=service.predict(payload.text, payload.model),
        success=True,
        message="Thành công",
    )


@router.post("/compare", response_model=CompareResponse)
def compare(payload: PredictRequest, service: AnalysisService = Depends(get_service)):
    """Cho cả 3 model cùng đoán một câu - dùng cho ô thử nghiệm trên trang report."""
    return CompareResponse(
        data=service.compare(payload.text), success=True, message="Thành công"
    )


@router.get("/models", response_model=ModelListResponse)
def list_models(service: AnalysisService = Depends(get_service)):
    """Model đã train + metrics. Chưa train thì trả list rỗng, không phải lỗi."""
    return ModelListResponse(
        data=service.list_models(), success=True, message="Thành công"
    )


@router.get("/report", response_class=HTMLResponse)
def report(service: AnalysisService = Depends(get_service)):
    """Trang HTML so sánh model - trả HTML thuần, không bọc envelope JSON."""
    return HTMLResponse(service.report_html())
