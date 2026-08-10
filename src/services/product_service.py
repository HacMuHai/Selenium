"""
ProductService - nghiệp vụ đọc/ghi product cho API.

Ném exception domain (`src.services.errors`); router không try/except, app map sang HTTP.
"""
import logging
from typing import Optional

from bson import ObjectId

from src.dto.product import (
    CommentCreate,
    CommentUpdate,
    PaginatedProducts,
    ProductDetail,
    ProductSummary,
)
from src.services.errors import EmptyPayloadError, InvalidIdError, NotFoundError

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_products(
        self, page: int, limit: int, q: Optional[str] = None
    ) -> PaginatedProducts:
        docs, total = self.repository.list_products(page, limit, q)
        return PaginatedProducts(
            items=[ProductSummary.model_validate(doc) for doc in docs],
            total=total,
            page=page,
            limit=limit,
        )

    def get_product(
        self, product_id: str, comment_page: int, comment_limit: int
    ) -> ProductDetail:
        skip = (comment_page - 1) * comment_limit
        doc = self._guard_id(
            lambda: self.repository.get_product_with_comment_page(
                product_id, skip, comment_limit
            )
        )
        if doc is None:
            raise NotFoundError(f"Không tìm thấy product {product_id}")
        return ProductDetail.model_validate(doc)

    def add_comment(self, product_id: str, payload: CommentCreate) -> str:
        comment = {**payload.model_dump(), "id": str(ObjectId())}
        comment_id = self._guard_id(
            lambda: self.repository.add_comment(product_id, comment)
        )
        if comment_id is None:
            raise NotFoundError(f"Không tìm thấy product {product_id}")
        return comment_id

    def update_comment(
        self, product_id: str, comment_id: str, payload: CommentUpdate
    ) -> None:
        data = payload.model_dump(exclude_none=True)
        if not data:
            raise EmptyPayloadError("Không có dữ liệu để cập nhật")
        ok = self._guard_id(
            lambda: self.repository.update_comment(product_id, comment_id, data)
        )
        if not ok:
            raise NotFoundError(f"Không tìm thấy comment {comment_id}")

    def delete_comment(self, product_id: str, comment_id: str) -> None:
        ok = self._guard_id(
            lambda: self.repository.delete_comment(product_id, comment_id)
        )
        if not ok:
            raise NotFoundError(f"Không tìm thấy comment {comment_id}")

    def delete_product(self, product_id: str) -> None:
        ok = self._guard_id(lambda: self.repository.delete_product(product_id))
        if not ok:
            raise NotFoundError(f"Không tìm thấy product {product_id}")

    @staticmethod
    def _guard_id(action):
        """`to_object_id` ném ValueError khi id sai định dạng -> đổi thành 400, không phải 500."""
        try:
            return action()
        except ValueError as exc:
            raise InvalidIdError(str(exc)) from exc
