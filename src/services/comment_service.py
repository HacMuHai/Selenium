"""
Comment Service - xử lý nghiệp vụ CRUD comment
"""
from typing import List, Dict, Optional
from models.product import Product
from repositories.comment_repository import CommentRepository


class CommentService:
    def __init__(self) -> None:
        self.repo = CommentRepository()

    def get_all(self) -> List[Dict]:
        docs = self.repo.find_all()
        return [self._to_out(doc) for doc in docs]

    def get_by_id(self, comment_id: str) -> Optional[Dict]:
        doc = self.repo.find_comment_by_id(comment_id)
        return self._to_out(doc) if doc else None

    def create_many(self, product: Product) -> List[str]:
        return self.repo.save_comments(product)

    def update(self, comment_id: str, data: Dict) -> bool:
        return self.repo.update_comment(comment_id, data)

    def delete(self, comment_id: str) -> bool:
        return self.repo.delete_comment(comment_id)

    # Private helper
    def _to_out(self, doc: Dict) -> Dict:
        """Chuẩn hoá output: map _id -> id, giữ các field còn lại."""
        if not doc:
            return doc
        out = {**doc}
        if "_id" in out:
            out["id"] = str(out["_id"])
            del out["_id"]
        return out
