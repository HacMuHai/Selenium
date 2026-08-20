"""
ScraperService - crawl sản phẩm + comment từ thegioididong, CellphoneS và FPT Shop.

Service không biết gì về selector: nó chọn scraper theo hostname của URL
(`src/services/sites/`) rồi lo phần chung — bỏ qua sản phẩm đã có, ghi qua repository,
nuốt lỗi của từng sản phẩm. Repository được inject từ ngoài (Mongo hoặc in-memory) nên
service KHÔNG có nhánh nào rẽ theo chế độ chạy. Driver lấy từ pool thread-local và được
tái sử dụng; teardown do caller lo bằng `quit_all()`.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.config import version as version_module
from src.models.product import Comment
from src.services.sites import get_site

logger = logging.getLogger(__name__)


class ScraperService:
    """Crawl comment của từng sản phẩm và lưu qua repository được inject."""

    def __init__(self, repository, wait_timeout: Optional[float] = None) -> None:
        self.repository = repository
        self.wait_timeout = wait_timeout

    def collect_product_links(
        self,
        driver: WebDriver,
        category_url: str,
        max_pages: int = 15,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Duyệt các trang của 1 danh mục, trả danh sách `{name, link}` đã khử trùng lặp."""
        site = get_site(category_url, self.wait_timeout)
        logger.info("Sàn: %s", site.name)
        return site.collect_product_links(
            driver, category_url, max_pages=max_pages, limit=limit
        )

    def crawl_product(self, product_link: dict) -> list[Comment]:
        """Crawl 1 sản phẩm và lưu qua repository. Luôn trả list (rỗng khi lỗi/bỏ qua)."""
        link = product_link["link"]
        if self.repository.exists_by_link(link):
            logger.info("Bỏ qua (đã có trong DB): %s", link)
            return []

        try:
            site = get_site(link, self.wait_timeout)
            comments = site.crawl_comments(product_link)
            if not comments:
                logger.warning("Không tìm thấy comment nào: %s", link)

            self.repository.insert_product(
                {
                    **product_link,
                    "site": site.name,
                    "comments": comments,
                    "total_comments": len(comments),
                    "crawled_at": datetime.now(),
                    "version": version_module.version,
                }
            )
            return comments
        except Exception:
            # Nuốt lỗi ở đây để 1 sản phẩm hỏng không giết cả thread trong pool.
            logger.exception("Lỗi crawl %s", link)
            return []


def summarize(results: list[list[Any]]) -> dict:
    """Tổng kết một lần chạy để log ra cuối CLI."""
    total_comments = sum(len(item) for item in results)
    return {
        "products": len(results),
        "comments": total_comments,
        "empty_products": sum(1 for item in results if not item),
    }
