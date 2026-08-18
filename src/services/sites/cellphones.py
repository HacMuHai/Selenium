"""
cellphones.com.vn — danh mục đọc bằng Chrome, đánh giá lấy qua GraphQL.

Khối "Đánh giá" chỉ render sẵn 5 review đầu và không có nút xem thêm trong DOM tĩnh;
chính trang web gọi GraphQL để lật trang. Ta gọi đúng query đó (`reviews`) nên lấy được
toàn bộ review thay vì 5 cái, và không phải bấm nút.

    POST https://api.cellphones.com.vn/graphql-customer/graphql/query
    query { reviews(filter: {product_id: N}, page: P) { total matches { ... } } }

`product_id` nằm ngay trong HTML trang sản phẩm: `<div id="block-comment-cps"
product-id="84109">`, lấy bằng một request HTTP thường - không cần mở Chrome cho từng
sản phẩm.
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

PRODUCT_ITEM = (By.CSS_SELECTOR, ".product-info a.product__link")
LOAD_MORE = (By.CSS_SELECTOR, "a.button__show-more-product")

GRAPHQL_URL = "https://api.cellphones.com.vn/graphql-customer/graphql/query"
PRODUCT_ID_RE = re.compile(r'id="block-comment-cps"[^>]*product-id="(\d+)"')
TAG_RE = re.compile(r"<[^>]+>")

REVIEWS_PER_PAGE = 5  # API cố định, không nhận tham số size
MAX_REVIEW_PAGES = 60

REVIEWS_QUERY = """query {
  reviews(filter: {product_id: %d}, page: %d) {
    total
    matches {
      id
      content
      rating_id
      customer { fullname }
    }
  }
}"""


class CellphonesScraper(SiteScraper):
    name = "cellphones"
    hosts = ("cellphones.com.vn",)

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
        product_id = self._product_id(link)
        if product_id is None:
            logger.warning("Không tìm thấy product-id trong trang %s", link)
            return []

        comments: list[Comment] = []
        total = None
        for page in range(1, MAX_REVIEW_PAGES + 1):
            block = self._fetch_reviews(product_id, page)
            if block is None:
                break
            if total is None:
                total = block.get("total") or 0
            for match in block.get("matches") or []:
                parsed = self._parse_review(match)
                if parsed is not None:
                    comments.append(parsed)
            if len(comments) >= total or len(block.get("matches") or []) < REVIEWS_PER_PAGE:
                break
        else:
            logger.warning("Chạm trần %d trang review: %s", MAX_REVIEW_PAGES, link)

        return comments

    def _product_id(self, link: str) -> Optional[int]:
        try:
            html = http().get(link).text
        except Exception:
            logger.warning("Không tải được trang sản phẩm %s", link, exc_info=True)
            return None
        found = PRODUCT_ID_RE.search(html)
        return int(found.group(1)) if found else None

    def _fetch_reviews(self, product_id: int, page: int) -> Optional[dict]:
        query = REVIEWS_QUERY % (product_id, page)
        try:
            response = http().post(GRAPHQL_URL, json={"query": query, "variables": {}})
            payload = response.json()
        except Exception:
            logger.warning("Lỗi gọi GraphQL review (product %d)", product_id, exc_info=True)
            return None
        if payload.get("errors"):
            logger.warning("GraphQL trả lỗi cho product %d: %s", product_id, payload["errors"])
            return None
        return (payload.get("data") or {}).get("reviews")

    def _parse_review(self, match: dict[str, Any]) -> Optional[Comment]:
        content = TAG_RE.sub(" ", match.get("content") or "").strip()
        if not content:
            return None
        customer = match.get("customer") or {}
        return {
            "id": str(ObjectId()),
            "name": customer.get("fullname") or "",
            "content": content,
            # rating_id chính là số sao 1..5; thiếu sao thì ghi 0 như thegioididong.
            "rating": int(match.get("rating_id") or 0),
        }
