"""
InMemoryProductRepository - cùng interface với `ProductRepository` nhưng giữ dữ liệu trong RAM.

Dùng cho chế độ `--no-db`: `ScraperService` và `ExportService` không cần biết đang chạy
chế độ nào, không có một dòng `if no_db` nào trong tầng service.
"""
import logging
from typing import Iterator, Optional

from bson import ObjectId

from src.models.product import Product

logger = logging.getLogger(__name__)


class InMemoryProductRepository:
    """Null-object có state, thay thế `ProductRepository` khi chạy `--no-db`."""

    def __init__(self) -> None:
        self._docs: list[dict] = []

    # ----- crawler -----

    def exists_by_link(self, link: str) -> bool:
        """Luôn False: chế độ no-db không đọc Mongo nên không dedup theo DB."""
        return False

    def insert_product(self, product: Product) -> str:
        doc = {"_id": ObjectId(), **dict(product)}
        self._docs.append(doc)
        logger.info(
            "[no-db] %s - %d comments",
            product.get("link"),
            product.get("total_comments", 0),
        )
        return str(doc["_id"])

    def replace_by_link(self, link: str, product: Product) -> Optional[str]:
        """Thay document cùng `link` (không có thì chèn mới)."""
        for index, doc in enumerate(self._docs):
            if doc.get("link") == link:
                self._docs[index] = {"_id": doc["_id"], **dict(product)}
                return None
        return self.insert_product(product)

    # ----- export -----

    def iter_products(self, projection: Optional[dict] = None) -> Iterator[dict]:
        # projection bỏ qua: dữ liệu đã nằm sẵn trong RAM, cắt field không tiết kiệm gì.
        return iter(list(self._docs))

    def count_products(self) -> int:
        return len(self._docs)

    # ----- API-only: CLI không gọi tới -----

    def list_products(self, page: int, limit: int, q: Optional[str] = None):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def get_product(self, product_id: str):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def get_product_with_comment_page(self, product_id: str, skip: int, limit: int):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def delete_product(self, product_id: str):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def add_comment(self, product_id: str, comment):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def update_comment(self, product_id: str, comment_id: str, data: dict):
        raise NotImplementedError("Chế độ no-db không phục vụ API")

    def delete_comment(self, product_id: str, comment_id: str):
        raise NotImplementedError("Chế độ no-db không phục vụ API")
