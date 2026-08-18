"""
Giao diện chung cho mỗi sàn (thegioididong / CellphoneS / FPT Shop).

Mỗi sàn tự quyết định lấy comment bằng cách nào: thegioididong đọc DOM, hai sàn còn lại
gọi thẳng JSON API mà chính trang web của họ dùng (xem docstring từng file). Phần thu thập
link sản phẩm thì sàn nào cũng cần Chrome vì danh sách render bằng JS.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from src.models.product import Comment
from src.utils.helpers import Locator, click_safe, wait_count_grows

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Chặn vòng lặp vô hạn khi nút "xem thêm" luôn tồn tại.
MAX_LOAD_MORE_CLICKS = 30
SHORT_WAIT = 5.0

_http: Optional[httpx.Client] = None


def http() -> httpx.Client:
    """Client HTTP dùng chung cho các API JSON. httpx.Client an toàn với thread."""
    global _http
    if _http is None:
        _http = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
            follow_redirects=True,
        )
    return _http


class SiteScraper(ABC):
    """Một sàn. `hosts` dùng để nhận diện sàn từ URL."""

    name: str
    hosts: tuple[str, ...]

    def __init__(self, wait_timeout: Optional[float] = None) -> None:
        self.wait_timeout = wait_timeout

    @abstractmethod
    def collect_product_links(
        self,
        driver: WebDriver,
        category_url: str,
        max_pages: int = 15,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Duyệt trang danh mục, trả list `{name, link}` đã khử trùng lặp."""

    @abstractmethod
    def crawl_comments(self, product_link: dict) -> list[Comment]:
        """Lấy toàn bộ comment của 1 sản phẩm. Luôn trả list (rỗng khi không có)."""


def collect_by_load_more(
    driver: WebDriver,
    category_url: str,
    item_locator: Locator,
    more_locator: Locator,
    max_clicks: int,
    limit: Optional[int],
) -> list[dict]:
    """
    Danh mục kiểu "Xem thêm": bấm tới khi hết nút hoặc đủ `limit`, rồi đọc một lượt.

    Khác thegioididong (phân trang, đọc từng trang), CellphoneS và FPT Shop nối thêm sản
    phẩm vào cuối danh sách nên chỉ cần đọc DOM một lần ở cuối.
    """
    driver.get(category_url)

    for _ in range(min(max_clicks, MAX_LOAD_MORE_CLICKS)):
        if limit is not None and len(driver.find_elements(*item_locator)) >= limit:
            break
        buttons = [b for b in driver.find_elements(*more_locator) if b.is_displayed()]
        if not buttons:
            break
        before = len(driver.find_elements(*item_locator))
        if not click_safe(driver, buttons[0]):
            break
        if not wait_count_grows(driver, item_locator, before, timeout=SHORT_WAIT):
            break

    collected: list[dict] = []
    seen: set[str] = set()
    for anchor in driver.find_elements(*item_locator):
        try:
            link = anchor.get_attribute("href")
            name = anchor.get_attribute("data-name") or _card_name(anchor)
        except WebDriverException:
            continue
        if not link or link in seen:
            continue
        seen.add(link)
        collected.append({"name": name, "link": link})
        if limit is not None and len(collected) >= limit:
            logger.info("Đã đạt --limit %d sản phẩm", limit)
            return collected

    logger.info("Thu được %d sản phẩm từ %s", len(collected), category_url)
    return collected


def _card_name(anchor) -> str:
    """Tên sản phẩm nằm trong thẻ h3 của card; text của cả anchor còn kèm giá."""
    try:
        titles = anchor.find_elements("css selector", "h3")
    except WebDriverException:
        return ""
    return titles[0].text.strip() if titles else ""
