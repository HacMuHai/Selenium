"""
Comment Repository - Data access layer cho comments
"""
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
from config.database import get_collection
from models.product import Product


class CommentRepository:
    """Repository để lưu và truy vấn comments từ MongoDB"""

    def __init__(self):
        self.collection = get_collection("comments")

    def save_comments(self, product: Product) -> List[str]:
        try:

            result = self.collection.insert_one(product)
            print(
                f"✅ Đã lưu {len(product.get('comments', []))} comments({product.get('link')}) vào MongoDB với ID: {result.inserted_id}")

            # Trả về danh sách IDs của các comments đã lưu
            return [str(result.inserted_id)]

        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-save_comments. ❌ Lỗi khi lưu vào MongoDB: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def find_by_product_link(self, product_link: str) -> Optional[Dict]:
        """Tìm product theo link"""
        try:
            return self.collection.find_one({"link": product_link})
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-find_by_product_link. Exception find_by_product_link: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def find_comment_by_id(self, comment_id: str) -> Optional[Dict]:
        try:
            item = self.collection.find_one({"_id": ObjectId(comment_id)})

            if not item:
                return None

            result = {
                "id": str(item["_id"]),
                "product_link": item.get("product_link"),
                "product_name": item.get("product_name"),
                "name": item.get("name"),
                "content": item.get("content"),
                "rating": item.get("rating"),
            }
            print("find_comment_by_id result:", result)
            return result
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-find_comment_by_id. Exception find_comment_by_id: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def update_comment(self, comment_id: str, data: Dict) -> bool:
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(comment_id)},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-update_comment. Exception update_comment: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def delete_comment(self, comment_id: str) -> bool:
        try:
            result = self.collection.delete_one({"_id": ObjectId(comment_id)})
            return result.deleted_count > 0
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-delete_comment. Exception delete_comment: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def find_all(self) -> List[Dict]:
        try:
            items = list(self.collection.find())
            result = []
            for item in items:
                result.append({
                    "id": str(item["_id"]),
                    "product_link": item.get("product_link"),
                    "product_name": item.get("product_name"),
                    "name": item.get("name"),
                    "content": item.get("content"),
                    "rating": item.get("rating"),
                })
            return result
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-find_all. Exception find_all: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def find_all_products_cursor(self):
        """
        Trả về cursor để iterate qua products (tối ưu memory cho large datasets)
        Mỗi document trong collection là một Product với format: {link, name, comments, ...}
        """
        try:
            return self.collection.find()
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-find_all_products_cursor. Exception: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)

    def count_products(self) -> int:
        """Đếm tổng số products trong collection"""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            import traceback
            error_msg = f"Position: {__name__}-count_products. Exception: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)
