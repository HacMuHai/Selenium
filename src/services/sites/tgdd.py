"""
thegioididong.com — đọc thẳng DOM.

Đây là logic gốc của dự án, chuyển nguyên từ `ScraperService` sang, không đổi hành vi:
danh mục phân trang bằng `ul.pagination`, comment phân trang bằng `.pagcomment`.
"""
import logging
from typing import Optional

from bson import ObjectId
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from src.config.driver import get_driver, get_wait
from src.models.product import Comment
from src.services.sites.base import SHORT_WAIT, SiteScraper
from src.utils.helpers import click_safe, wait_count_grows, wait_for

logger = logging.getLogger(__name__)

COMMENT_LIST = (By.CSS_SELECTOR, ".comment-list")
VIEW_ALL_BTN = (By.CSS_SELECTOR, ".box-flex > a.c-btn-rate.btn-view-all")
PRODUCT_ITEM = (By.CSS_SELECTOR, "li.item > a.main-contain")
VIEW_MORE_BTN = (By.CSS_SELECTOR, ".view-more")
PAGINATION = (By.CSS_SELECTOR, "ul.pagination")
NEXT_PAGE_XPATH = (
    ".//li[contains(concat(' ', normalize-space(@class), ' '), ' active ')]"
    "/following-sibling::li[1][not(@id)]"
)

MAX_COMMENT_PAGES = 50
MAX_VIEW_MORE_CLICKS = 20


class TgddScraper(SiteScraper):
    name = "thegioididong"
    hosts = ("thegioididong.com",)

    # ----- danh mục -----

    def collect_product_links(
        self,
        driver: WebDriver,
        category_url: str,
        max_pages: int = 15,
        limit: Optional[int] = None,
    ) -> list[dict]:
        driver.get(category_url)
        collected: list[dict] = []
        seen: set[str] = set()

        for page_idx in range(max_pages):
            self._expand_view_more(driver)
            self._close_popup(driver)

            for anchor in driver.find_elements(*PRODUCT_ITEM):
                try:
                    link = anchor.get_attribute("href")
                    name = anchor.get_attribute("data-name")
                except WebDriverException:
                    continue
                if not link or link in seen:
                    continue
                seen.add(link)
                collected.append({"name": name or "", "link": link})
                if limit is not None and len(collected) >= limit:
                    logger.info("Đã đạt --limit %d sản phẩm", limit)
                    return collected

            if not self._goto_next_category_page(driver, page_idx):
                break

        logger.info("Thu được %d sản phẩm từ %s", len(collected), category_url)
        return collected

    def _expand_view_more(self, driver: WebDriver) -> None:
        """Bấm "Xem thêm" tới khi danh sách không tăng nữa."""
        for _ in range(MAX_VIEW_MORE_CLICKS):
            buttons = driver.find_elements(*VIEW_MORE_BTN)
            if not buttons or not buttons[0].is_displayed():
                return
            before = len(driver.find_elements(*PRODUCT_ITEM))
            if not click_safe(driver, buttons[0]):
                return
            if not wait_count_grows(driver, PRODUCT_ITEM, before, timeout=SHORT_WAIT):
                return

    def _close_popup(self, driver: WebDriver) -> None:
        popups = driver.find_elements(By.CLASS_NAME, "icon-close-popup")
        if popups:
            click_safe(driver, popups[0])

    def _goto_next_category_page(self, driver: WebDriver, page_idx: int) -> bool:
        """Sang trang danh mục kế tiếp. Trả False khi hết trang."""
        containers = driver.find_elements(*PAGINATION)
        if not containers:
            return False
        next_items = containers[0].find_elements(By.XPATH, NEXT_PAGE_XPATH)
        if not next_items:
            return False

        first_before = self._first_item_key(driver)
        if not click_safe(driver, next_items[0]):
            return False
        if not self._wait_list_changed(driver, first_before):
            logger.warning("Trang %d: danh sách không đổi sau khi sang trang", page_idx)
            return False
        return True

    def _first_item_key(self, driver: WebDriver) -> Optional[str]:
        items = driver.find_elements(*PRODUCT_ITEM)
        if not items:
            return None
        try:
            return items[0].get_attribute("href")
        except WebDriverException:
            return None

    def _wait_list_changed(self, driver: WebDriver, before: Optional[str]) -> bool:
        try:
            get_wait(driver, self.wait_timeout).until(
                lambda d: self._first_item_key(d) not in (None, before)
            )
            return True
        except TimeoutException:
            return False

    # ----- comment -----

    def crawl_comments(self, product_link: dict) -> list[Comment]:
        driver = get_driver()  # thread-local, tái sử dụng
        driver.get(product_link["link"])
        return self._crawl_comment_pages(driver)

    def _crawl_comment_pages(self, driver: WebDriver) -> list[Comment]:
        """Vào trang "xem tất cả đánh giá" (nếu có) rồi duyệt hết các trang comment."""
        view_all = wait_for(driver, VIEW_ALL_BTN, timeout=SHORT_WAIT)
        if view_all is not None:
            href = view_all.get_attribute("href")
            if href:
                driver.get(href)

        comments: list[Comment] = []
        for _ in range(MAX_COMMENT_PAGES):
            ul = wait_for(driver, COMMENT_LIST, timeout=self.wait_timeout)
            if ul is None:
                break

            for li in ul.find_elements(By.TAG_NAME, "li"):
                parsed = self._parse_comment(li)
                if parsed is not None:
                    comments.append(parsed)

            if not self._goto_next_comment_page(driver, ul):
                break
        else:
            logger.warning("Chạm trần %d trang comment", MAX_COMMENT_PAGES)

        return comments

    def _goto_next_comment_page(self, driver: WebDriver, current_ul: WebElement) -> bool:
        """Bấm sang trang comment kế tiếp, chờ danh sách cũ stale. False khi hết trang."""
        containers = driver.find_elements(By.CSS_SELECTOR, ".pagcomment")
        if not containers:
            return False
        next_items = containers[0].find_elements(
            By.XPATH, "./*[preceding-sibling::span[@class='active']]"
        )
        if not next_items:
            return False
        if not click_safe(driver, next_items[0]):
            return False
        try:
            get_wait(driver, self.wait_timeout).until(EC.staleness_of(current_ul))
            return True
        except TimeoutException:
            logger.warning("Danh sách comment không refresh sau khi sang trang")
            return False

    def _parse_comment(self, li: WebElement) -> Optional[Comment]:
        """Đọc 1 thẻ `li`. Trả None nếu element đã stale."""
        try:
            names = li.find_elements(By.CSS_SELECTOR, "p.cmt-top-name")
            contents = li.find_elements(By.CSS_SELECTOR, "p.cmt-txt")
            ratings = li.find_elements(
                By.CSS_SELECTOR, ".cmt-top-star .iconcmt-starbuy"
            )
        except WebDriverException:
            return None

        return {
            "id": str(ObjectId()),
            "name": names[0].text if names else "",
            "content": contents[0].text if contents else "",
            "rating": len(ratings),  # luôn int; 0 khi không có sao
        }
