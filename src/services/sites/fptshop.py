"""
fptshop.com.vn — danh mục đọc bằng Chrome, đánh giá lấy qua REST API.

Trang FPT Shop render sẵn 5 comment đầu rồi lật trang bằng API nội bộ:

    POST https://papi.fptshop.com.vn/gw/v1/public/bff-before-order/comment/list
    header `order-channel: 1` (thiếu header này API trả 400 "Kênh bán hàng không xác định")
    body  {"content": {"id": <upc>, "type": "PRODUCT"}, "state": ["ACTIVE"],
           "maxResultCount": <=30, "skipCount": N, "sortMethod": 1}

`upc` là mã sản phẩm (khác SKU hiển thị trên trang), nằm trong payload RSC của HTML:
`\\"upc\\":\\"389886926265\\"`. Lấy bằng một request HTTP thường.

API trả cả đánh giá có sao lẫn câu hỏi không sao — `score` null nghĩa là không chấm điểm,
ghi rating 0 giống thegioididong. Phản hồi của nhân viên nằm trong `children` nên bị bỏ.

Lưu ý về chất lượng dữ liệu: phần lớn nội dung FPT Shop trả về là câu hỏi giá/tồn kho chứ
không phải nhận xét sản phẩm — Galaxy S25 Ultra có 163 mục thì chỉ 12 mục có sao. Bộ lọc
`commentType: ["RATING"]` của chính trang web KHÔNG tách được (80 mục "RATING" vẫn đầy câu
hỏi giá), nên ở đây giữ lại tất cả và để tầng phân tích lọc theo `rating > 0`.
"""
import logging
import re
from typing import Any, Optional

from bson import ObjectId
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.models.product import Comment
from src.services.sites.base import SiteScraper, collect_by_load_more, http

logger = logging.getLogger(__name__)

PRODUCT_ITEM = (By.CSS_SELECTOR, ".cardInfo a[href]")
LOAD_MORE = (By.XPATH, "//button[contains(., 'Xem thêm') and contains(., 'kết quả')]")

COMMENT_URL = (
    "https://papi.fptshop.com.vn/gw/v1/public/bff-before-order/comment/list"
)
ORDER_CHANNEL = "1"
UPC_RE = re.compile(r'upc\\":\\"(\d+)\\"')
TAG_RE = re.compile(r"<[^>]+>")

PAGE_SIZE = 30  # API từ chối maxResultCount > 30
MAX_COMMENT_PAGES = 60


class FptShopScraper(SiteScraper):
    name = "fptshop"
    hosts = ("fptshop.com.vn",)

    def collect_product_links(
        self,
        driver: WebDriver,
        category_url: str,
        max_pages: int = 15,
        limit: Optional[int] = None,
    ) -> list[dict]:
        return collect_by_load_more(
            driver, category_url, PRODUCT_ITEM, LOAD_MORE, max_pages, limit
        )

    def crawl_comments(self, product_link: dict) -> list[Comment]:
        link = product_link["link"]
        upc = self._upc(link)
        if upc is None:
            logger.warning("Không tìm thấy upc trong trang %s", link)
            return []

        comments: list[Comment] = []
        total = None
        for page in range(MAX_COMMENT_PAGES):
            block = self._fetch_comments(upc, page * PAGE_SIZE)
            if block is None:
                break
            if total is None:
                total = block.get("totalCount") or 0
            items = block.get("items") or []
            for item in items:
                parsed = self._parse_comment(item)
                if parsed is not None:
                    comments.append(parsed)
            if len(items) < PAGE_SIZE or (page + 1) * PAGE_SIZE >= total:
                break
        else:
            logger.warning("Chạm trần %d trang comment: %s", MAX_COMMENT_PAGES, link)

        return comments

    def _upc(self, link: str) -> Optional[str]:
        try:
            html = http().get(link).text
        except Exception:
            logger.warning("Không tải được trang sản phẩm %s", link, exc_info=True)
            return None
        found = UPC_RE.search(html)
        return found.group(1) if found else None

    def _fetch_comments(self, upc: str, skip: int) -> Optional[dict]:
        body = {
            "content": {"id": upc, "type": "PRODUCT"},
            "state": ["ACTIVE"],
            "maxResultCount": PAGE_SIZE,
            "skipCount": skip,
            "sortMethod": 1,
        }
        try:
            response = http().post(
                COMMENT_URL, json=body, headers={"order-channel": ORDER_CHANNEL}
            )
            payload = response.json()
        except Exception:
            logger.warning("Lỗi gọi API comment (upc %s)", upc, exc_info=True)
            return None
        if payload.get("status") != 200:
            logger.warning("API comment trả %s cho upc %s", payload.get("status"), upc)
            return None
        return payload.get("data")

    def _parse_comment(self, item: dict[str, Any]) -> Optional[Comment]:
        if item.get("isAdministrator"):
            return None
        content = TAG_RE.sub(" ", item.get("content") or "").strip()
        if not content:
            return None
        return {
            "id": str(ObjectId()),
            "name": item.get("fullName") or "",
            "content": content,
            "rating": int(item.get("score") or 0),
        }
