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

CẠM BẪY: API trả đúng MỘT thông báo lỗi `"Unable to process request"` cho mọi tình
huống sai, nên không thể phân biệt qua nội dung lỗi. Đã kiểm chứng bằng tay:

- xin trang VƯỢT QUÁ trang cuối -> lỗi (product 85242 có 127 review = 26 trang; trang
  26 trở đi đều lỗi). Đây là kết thúc bình thường, KHÔNG phải hỏng.
- thêm tham số lạ (`size`, `limit`, `pageSize`) -> cũng lỗi y hệt. API chỉ nhận
  `product_id` và `page`, mỗi trang cố định 5 review.
- sản phẩm không có đánh giá -> KHÔNG lỗi, trả `total: 0` bình thường.
- gọi quá dày -> cũng lỗi y hệt, nhưng chờ một chút rồi thử lại là được.

Vì vậy: lỗi ở trang 1 mới coi là hỏng thật (ném `ReviewFetchError`, không ghi DB để lần
sau crawl lại); lỗi ở trang sau thì coi là hết dữ liệu và giữ phần đã lấy.
"""
import logging
import re
from time import sleep
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

# API trả "Unable to process request" khi bị gọi quá dày. Thử lại có giãn cách thay vì
# coi là "sản phẩm không có đánh giá" - nhầm hai thứ đó sẽ ghi vào DB một sản phẩm rỗng
# và lần chạy sau `exists_by_link` bỏ qua luôn, mất hẳn dữ liệu.
FETCH_RETRIES = 4
RETRY_BACKOFF = 2.0     # giây, nhân đôi sau mỗi lần hụt
REQUEST_PAUSE = 0.4     # giãn cách tối thiểu giữa hai lần gọi API

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


class ReviewFetchError(RuntimeError):
    """Gọi API đánh giá hỏng sau khi đã thử lại. KHÁC với sản phẩm không có đánh giá."""


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
        """
        Ném `ReviewFetchError` khi API hỏng - KHÔNG trả list rỗng.

        `ScraperService` bắt exception và bỏ qua sản phẩm, nên sản phẩm hỏng sẽ không
        bị ghi vào DB dưới dạng "0 comment" và lần chạy sau vẫn crawl lại được.
        """
        link = product_link["link"]
        product_id = self._product_id(link)
        if product_id is None:
            raise ReviewFetchError(f"Không tìm thấy product-id trong trang {link}")

        comments: list[Comment] = []
        total = None
        for page in range(1, MAX_REVIEW_PAGES + 1):
            block = self._fetch_reviews(product_id, page)
            if block is None:
                if page == 1:
                    # Chưa lấy được gì -> coi là hỏng thật, để lần chạy sau thử lại.
                    raise ReviewFetchError(f"API đánh giá hỏng ở trang 1 của {link}")
                # Trang sau trang cuối LUÔN trả lỗi (xem docstring đầu file), nên lỗi ở
                # đây gần như chắc chắn là "hết dữ liệu" chứ không phải hỏng. Giữ lại
                # những gì đã lấy thay vì vứt cả sản phẩm.
                logger.info(
                    "Dừng phân trang ở trang %d, giữ %d comment đã lấy: %s",
                    page, len(comments), link,
                )
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
            sleep(REQUEST_PAUSE)
            html = http().get(link).text
        except Exception:
            logger.warning("Không tải được trang sản phẩm %s", link, exc_info=True)
            return None
        found = PRODUCT_ID_RE.search(html)
        return int(found.group(1)) if found else None

    def _fetch_reviews(self, product_id: int, page: int) -> Optional[dict]:
        """Gọi API, thử lại có giãn cách. Trả None khi đã hết lượt thử."""
        delay = RETRY_BACKOFF
        for attempt in range(1, FETCH_RETRIES + 1):
            sleep(REQUEST_PAUSE)
            query = REVIEWS_QUERY % (product_id, page)
            try:
                response = http().post(
                    GRAPHQL_URL, json={"query": query, "variables": {}}
                )
                payload = response.json()
            except Exception:
                logger.warning(
                    "Lỗi gọi GraphQL review (product %d, lần %d/%d)",
                    product_id, attempt, FETCH_RETRIES, exc_info=True,
                )
                payload = None

            if payload is not None and not payload.get("errors"):
                return (payload.get("data") or {}).get("reviews")

            if payload is not None:
                logger.info(
                    "GraphQL trả lỗi cho product %d (lần %d/%d): %s",
                    product_id, attempt, FETCH_RETRIES, payload["errors"],
                )
            if attempt < FETCH_RETRIES:
                sleep(delay)
                delay *= 2

        logger.info(
            "product %d trang %d: API vẫn lỗi sau %d lần thử",
            product_id, page, FETCH_RETRIES,
        )
        return None

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
