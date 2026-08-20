"""
ProductRepository - data access layer, khớp đúng schema nested-array.

Cố ý KHÔNG bọc try/except quanh mỗi method: nuốt stack trace và biến `PyMongoError`
thành `Exception` chung khiến tầng trên không map được HTTP status. Để exception gốc bay lên.
"""
import logging
import re
from typing import Any, Iterator, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection

from src.config.database import get_collection
from src.models.product import Comment, Product

logger = logging.getLogger(__name__)

# Field không bao giờ trả về ở API danh sách (mảng comments có thể rất lớn).
SUMMARY_PROJECTION = {
    "name": 1,
    "link": 1,
    "crawled_at": 1,
    "version": 1,
    "total_comments": 1,
}


def to_object_id(value: str) -> ObjectId:
    """Ép chuỗi sang ObjectId, ném `ValueError` khi sai định dạng (tầng trên map 400)."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise ValueError(f"ID không hợp lệ: {value}") from exc


class ProductRepository:
    """Truy cập collection product (tên lịch sử là `comments`)."""

    def __init__(self, collection: Optional[Collection] = None) -> None:
        self.collection = collection if collection is not None else get_collection()

    # ----- crawler -----

    def exists_by_link(self, link: str) -> bool:
        """Đã crawl link này chưa."""
        return self.collection.find_one({"link": link}, {"_id": 1}) is not None

    def insert_product(self, product: Product) -> str:
        """Chèn 1 product, trả `_id` dạng chuỗi."""
        result = self.collection.insert_one(dict(product))
        logger.info(
            "Đã lưu product %s (%d comments)",
            product.get("link"),
            product.get("total_comments", 0),
        )
        return str(result.inserted_id)

    def replace_by_link(self, link: str, product: Product) -> Optional[str]:
        """Ghi đè toàn bộ document theo `link` (dùng khi import lại từ Excel)."""
        result = self.collection.replace_one({"link": link}, dict(product), upsert=True)
        logger.info("Đã ghi đè product %s (%d comments)", link,
                    product.get("total_comments", 0))
        return str(result.upserted_id) if result.upserted_id else None

    # ----- API: product -----

    def list_products(
        self, page: int, limit: int, q: Optional[str] = None
    ) -> tuple[list[dict], int]:
        """Danh sách product (KHÔNG kèm mảng comments) + tổng số bản ghi khớp."""
        match: dict[str, Any] = {}
        if q:
            # escape để tránh regex injection / ReDoS từ query param
            match["name"] = {"$regex": re.escape(q), "$options": "i"}

        pipeline: list[dict] = []
        if match:
            pipeline.append({"$match": match})
        pipeline += [
            {"$sort": {"_id": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {"$project": SUMMARY_PROJECTION},
        ]
        items = list(self.collection.aggregate(pipeline))

        if match:
            total = self.collection.count_documents(match)
        else:
            total = self.collection.estimated_document_count()
        return items, total

    def get_product(self, product_id: str) -> Optional[dict]:
        """Product đầy đủ (kèm toàn bộ comments)."""
        return self.collection.find_one({"_id": to_object_id(product_id)})

    def get_product_with_comment_page(
        self, product_id: str, skip: int, limit: int
    ) -> Optional[dict]:
        """Product kèm 1 trang comments, cắt ngay tại MongoDB bằng `$slice`."""
        return self.collection.find_one(
            {"_id": to_object_id(product_id)},
            {**SUMMARY_PROJECTION, "comments": {"$slice": [skip, limit]}},
        )

    def delete_product(self, product_id: str) -> bool:
        result = self.collection.delete_one({"_id": to_object_id(product_id)})
        return result.deleted_count > 0

    # ----- API: comment lồng bên trong -----

    def add_comment(self, product_id: str, comment: Comment) -> Optional[str]:
        """`$push` comment mới + `$inc` total_comments. Trả id, `None` nếu không có product."""
        oid = to_object_id(product_id)
        payload = dict(comment)
        payload.setdefault("id", str(ObjectId()))

        result = self.collection.update_one(
            {"_id": oid, "comments.id": {"$ne": payload["id"]}},
            {"$push": {"comments": payload}, "$inc": {"total_comments": 1}},
        )
        if result.matched_count == 0:
            return None
        return payload["id"]

    def update_comment(self, product_id: str, comment_id: str, data: dict) -> bool:
        """`$set` các field của đúng phần tử khớp `comment_id`."""
        if not data:
            return False
        updates = {f"comments.$.{key}": value for key, value in data.items()}
        result = self.collection.update_one(
            {"_id": to_object_id(product_id), "comments.id": comment_id},
            {"$set": updates},
        )
        # matched_count, KHÔNG modified_count: set giá trị y hệt sẽ trả 0 -> 404 sai.
        return result.matched_count > 0

    def delete_comment(self, product_id: str, comment_id: str) -> bool:
        """`$pull` comment + `$inc` -1. Filter chứa comments.id để total_comments không âm."""
        result = self.collection.update_one(
            {"_id": to_object_id(product_id), "comments.id": comment_id},
            {"$pull": {"comments": {"id": comment_id}}, "$inc": {"total_comments": -1}},
        )
        return result.matched_count > 0

    # ----- export -----

    def iter_products(self, projection: Optional[dict] = None) -> Iterator[dict]:
        """Cursor duyệt toàn bộ product (không nạp hết vào RAM)."""
        return self.collection.find({}, projection)

    def count_products(self) -> int:
        return self.collection.count_documents({})
