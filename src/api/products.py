"""
Router `/products`.

Mọi route là `def` (sync) - pymongo blocking, `async def` sẽ chặn event loop.
Không try/except trong route: exception handler ở `src/app.py` lo toàn bộ.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pymongo.errors import PyMongoError

from src.dto.product import (
    Acknowledged,
    AckResponse,
    CommentCreate,
    CommentCreateResponse,
    CommentUpdate,
    CreatedComment,
    ProductDetailResponse,
    ProductListResponse,
)
from src.repositories.product_repository import ProductRepository
from src.services.errors import DatabaseUnavailableError
from src.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def get_service() -> ProductService:
    """Dependency - override được trong test.

    App không còn fail-fast khi Mongo hỏng (để `/analyze` vẫn chạy), nên lỗi kết nối
    lộ ra ở đây. Map thành 503 với thông điệp rõ ràng thay vì 500 kèm stack trace.
    """
    try:
        return ProductService(ProductRepository())
    except PyMongoError as exc:
        raise DatabaseUnavailableError(
            "Không kết nối được MongoDB - kiểm tra MONGO_URI trong .env"
        ) from exc


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Lọc theo tên sản phẩm"),
    service: ProductService = Depends(get_service),
):
    """Danh sách product, KHÔNG kèm mảng comments."""
    return ProductListResponse(
        data=service.list_products(page, limit, q), success=True, message="Thành công"
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: str,
    comment_page: int = Query(1, ge=1),
    comment_limit: int = Query(20, ge=1, le=100),
    service: ProductService = Depends(get_service),
):
    """Chi tiết product kèm 1 trang comments."""
    return ProductDetailResponse(
        data=service.get_product(product_id, comment_page, comment_limit),
        success=True,
        message="Thành công",
    )


@router.post(
    "/{product_id}/comments",
    response_model=CommentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    product_id: str,
    payload: CommentCreate,
    service: ProductService = Depends(get_service),
):
    comment_id = service.add_comment(product_id, payload)
    return CommentCreateResponse(
        data=CreatedComment(comment_id=comment_id), success=True, message="Đã tạo"
    )


@router.patch("/{product_id}/comments/{comment_id}", response_model=AckResponse)
def update_comment(
    product_id: str,
    comment_id: str,
    payload: CommentUpdate,
    service: ProductService = Depends(get_service),
):
    service.update_comment(product_id, comment_id, payload)
    return AckResponse(data=Acknowledged(), success=True, message="Đã cập nhật")


@router.delete("/{product_id}/comments/{comment_id}", response_model=AckResponse)
def delete_comment(
    product_id: str,
    comment_id: str,
    service: ProductService = Depends(get_service),
):
    service.delete_comment(product_id, comment_id)
    return AckResponse(data=Acknowledged(), success=True, message="Đã xoá")


@router.delete("/{product_id}", response_model=AckResponse)
def delete_product(product_id: str, service: ProductService = Depends(get_service)):
    service.delete_product(product_id)
    return AckResponse(data=Acknowledged(), success=True, message="Đã xoá")
