"""
Comment Repository - Data access layer cho comments
"""
from typing import List, Dict, Optional
from datetime import datetime
from config.database import get_collection
from config.driver import get_driver
from models import Product


class CommentRepository:
    """Repository để lưu và truy vấn comments từ MongoDB"""

    def __init__(self):
        self.collection = get_collection()

    def save_comments(self, product_link: Product, comments: List[Dict]) -> Optional[str]:
        """
        Lưu comments vào MongoDB

        Args:
            product_link: Thông tin sản phẩm (name, link)
            comments: Danh sách comments

        Returns:
            inserted_id nếu thành công, None nếu lỗi
        """
        try:
            document = {
                "product_name": product_link.get("name", ""),
                "product_link": product_link.get("link", ""),
                "comments": comments,
                "total_comments": len(comments),
                "crawled_at": datetime.now(),
                "url": product_link.get("link", "")
            }

            result = self.collection.insert_one(document)
            print(
                f"✅ Đã lưu {len(comments)} comments vào MongoDB với ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            import traceback
            print(f"❌ Lỗi khi lưu vào MongoDB: {type(e).__name__} - {e}")
            traceback.print_exc()
            return None

    def find_by_product_link(self, product_link: str) -> Optional[Dict]:
        """Tìm comments theo product link"""
        return self.collection.find_one({"product_link": product_link})

    def find_all(self) -> List[Dict]:
        """Lấy tất cả comments"""
        return list(self.collection.find())
