"""
FastAPI app. Chạy: `uvicorn src.app:app --reload` (từ repo root).

Mọi response - kể cả lỗi - giữ envelope `{data, success, message}`; điểm khác so với bản cũ
là HTTP status giờ đúng nghĩa (400/404/409/422/500) thay vì luôn 200.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.analysis import router as analysis_router
from src.api.products import router as products_router
from src.config.database import close_client, ensure_indexes, get_client
from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.services.errors import AppError

logger = logging.getLogger(__name__)


def _envelope(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": None, "success": False, "message": message},
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    # KHÔNG fail-fast: `/analyze` không cần MongoDB, không có lý do gì để DB hỏng
    # kéo sập cả app. Đánh đổi: lỗi cấu hình DB lộ ra lúc gọi API thay vì lúc khởi động,
    # nên log WARNING phải thật rõ.
    try:
        get_client()
        ensure_indexes()
    except Exception:
        logger.warning(
            "Không kết nối được MongoDB - /products sẽ lỗi, /analyze vẫn dùng được",
            exc_info=True,
        )

    yield

    try:
        close_client()
    except Exception:
        logger.debug("Bỏ qua lỗi khi đóng MongoDB", exc_info=True)


app = FastAPI(title="Selenium Scraper API", lifespan=lifespan)
app.include_router(products_router)
app.include_router(analysis_router)


@app.exception_handler(AppError)
def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return _envelope(exc.status_code, exc.message)


@app.exception_handler(StarletteHTTPException)
def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _envelope(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:])
    message = first.get("msg", "Dữ liệu không hợp lệ")
    return _envelope(422, f"{field}: {message}" if field else message)


@app.exception_handler(Exception)
def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    # KHÔNG trả stack trace ra client (bản cũ trả nguyên traceback - lộ path & schema).
    logger.exception("Lỗi không lường trước", exc_info=exc)
    return _envelope(500, "Lỗi hệ thống")


@app.get("/")
def root():
    return {"status": "ok"}
