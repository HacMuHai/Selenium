"""
Giao diện chung cho mỗi sàn (thegioididong / CellphoneS / FPT Shop).

Mỗi sàn tự quyết định lấy comment bằng cách nào: thegioididong đọc DOM, hai sàn còn lại
gọi thẳng JSON API mà chính trang web của họ dùng (xem docstring từng file). Phần thu thập
link sản phẩm thì sàn nào cũng cần Chrome vì danh sách render bằng JS.
"""
import logging
from abc import ABC, abstractmethod
from time import sleep
from typing import Optional

import httpx
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.models.product import Comment
from src.utils.helpers import Locator, click_safe, wait_count_grows, wait_for

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Chặn vòng lặp vô hạn khi nút "xem thêm" luôn tồn tại. Không phải mục tiêu độ phủ:
# danh mục lớn của CellphoneS có ~900 sản phẩm (~46 lô), nên trần thấp sẽ cắt mất dữ liệu.
# Vòng lặp vẫn tự dừng khi hết nút hoặc bấm hụt liên tiếp, đây chỉ là chốt an toàn.
MAX_LOAD_MORE_CLICKS = 60
SHORT_WAIT = 5.0
# Bấm "Xem thêm" gọi API rồi render lại danh sách - chậm hơn hẳn một thao tác DOM
# thường, nên chờ riêng và chờ lâu hơn SHORT_WAIT (5s từng làm hụt ngay cú bấm đầu).
LOAD_MORE_WAIT = 15.0
# Nghỉ giữa hai cú bấm: bấm liên tục không nghỉ đã khiến CellphoneS trả captcha.
LOAD_MORE_PAUSE = 1.5
# Nút "Xem thêm" biến mất tạm thời trong lúc render lô mới -> chờ nó quay lại rồi mới
# kết luận là đã hết.
MORE_BUTTON_WAIT = 8.0
MORE_BUTTON_POLL = 0.5
# Số lần tìm-lại-rồi-bấm trước khi coi là hỏng (element stale là chuyện thường ở đây).
CLICK_RETRIES = 3
# Số cú bấm hụt LIÊN TIẾP chấp nhận được trước khi kết luận là hết/hỏng.
MAX_STALLS = 3

# Trang chặn bot trả về interstitial thay cho nội dung. Nhận diện để log rõ ràng thay vì
# báo "thu được 0 sản phẩm" - hai nguyên nhân này cần hai cách xử lý hoàn toàn khác nhau.
BLOCK_MARKERS = (
    "verify to continue",
    "drag the puzzle piece",
    "checking your browser",
    "are you a human",
)

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


def is_blocked(driver: WebDriver) -> bool:
    """Trang hiện tại có phải màn chặn bot (captcha) thay vì nội dung thật không."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
    except WebDriverException:
        return False
    return any(marker in body for marker in BLOCK_MARKERS)


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

    Log rõ số lần bấm và LÝ DO dừng: bản trước dừng im lặng nên "chỉ lấy được 20 sản
    phẩm" trông y hệt "danh mục chỉ có 20 sản phẩm".
    """
    driver.get(category_url)

    if is_blocked(driver):
        logger.error(
            "Bị chặn bot (captcha) tại %s - hãy nghỉ một lúc, giảm --workers, "
            "hoặc dùng --attach vào Chrome đã qua xác minh",
            category_url,
        )
        return []

    # Lưới sản phẩm render bằng JS SAU khi driver.get() trả về. Không chờ ở đây thì vòng
    # lặp dưới đo `before` trên một trang gần như trống, `wait_count_grows` thoả mãn ngay
    # và ta kết luận nhầm là "hết nút" - đúng lỗi làm FPT Shop chỉ ra 9 sản phẩm.
    if wait_for(driver, item_locator, timeout=LOAD_MORE_WAIT) is None:
        logger.warning("Không thấy sản phẩm nào render tại %s", category_url)
        return []

    collected: dict[str, dict] = {}

    def harvest() -> int:
        """Gom link đang có trong DOM. Gọi sau mỗi lần bấm chứ không đợi tới cuối:
        danh sách được render lại mỗi lần tải thêm, đọc một lượt ở cuối là mất dữ liệu."""
        for anchor in driver.find_elements(*item_locator):
            try:
                link = anchor.get_attribute("href")
                name = anchor.get_attribute("data-name") or _card_name(anchor)
            except WebDriverException:
                continue
            if link and link not in collected:
                collected[link] = {"name": name, "link": link}
        return len(collected)

    harvest()
    clicks = 0
    stalls = 0
    limit_clicks = min(max_clicks, MAX_LOAD_MORE_CLICKS)

    for _ in range(limit_clicks):
        if limit is not None and len(collected) >= limit:
            logger.info("Đủ --limit, dừng bấm 'Xem thêm' sau %d lần", clicks)
            break
        before = len(driver.find_elements(*item_locator))
        clicked = _click_more(driver, more_locator)
        if clicked is None:
            logger.info("Hết nút 'Xem thêm' sau %d lần bấm (%d sản phẩm)",
                        clicks, len(collected))
            break
        if not clicked:
            logger.warning("Không bấm được 'Xem thêm' sau %d lần bấm", clicks)
            break
        if not wait_count_grows(driver, item_locator, before, timeout=LOAD_MORE_WAIT):
            if is_blocked(driver):
                logger.error(
                    "Bị chặn bot ngay sau khi bấm 'Xem thêm' lần %d tại %s",
                    clicks + 1, category_url,
                )
                break
            # Cú bấm hụt là chuyện thường (trang render chậm, nút vừa bị thay). Chỉ bỏ
            # cuộc khi hụt liên tiếp - dừng ngay lần đầu từng cắt danh mục còn 28 sản phẩm.
            stalls += 1
            logger.warning(
                "Bấm 'Xem thêm' lần %d không làm danh sách dài ra trong %.0fs "
                "(vẫn %d sản phẩm), hụt %d/%d",
                clicks + 1, LOAD_MORE_WAIT, before, stalls, MAX_STALLS,
            )
            if stalls >= MAX_STALLS:
                logger.warning(
                    "Dừng ở %d sản phẩm - nút có thể đã đổi selector hoặc site đang chặn",
                    len(collected),
                )
                break
            sleep(LOAD_MORE_PAUSE)
            continue
        stalls = 0
        clicks += 1
        total = harvest()
        logger.info("Bấm 'Xem thêm' lần %d -> %d sản phẩm", clicks, total)
        sleep(LOAD_MORE_PAUSE)
    else:
        logger.info("Chạm trần %d lần bấm 'Xem thêm' - có thể còn sản phẩm chưa lấy",
                    limit_clicks)

    harvest()
    result = list(collected.values())
    if limit is not None and len(result) > limit:
        logger.info("Đã đạt --limit %d sản phẩm", limit)
        result = result[:limit]

    logger.info("Thu được %d sản phẩm từ %s", len(result), category_url)
    return result


# Selenium `is_displayed()` KHÔNG dùng được để lọc nút ở đây: trên danh mục CellphoneS,
# từ lô thứ 7 trở đi nó trả False cho một nút mà CSS vẫn là display:flex, visibility:
# visible, opacity:1, kích thước 260x48 - tức nút hiển thị bình thường. Tin vào nó thì
# danh mục 919 sản phẩm dừng ở 202. Tự hỏi CSS + bounding box thay vào đó.
VISIBLE_JS = """
const s = getComputedStyle(arguments[0]);
const r = arguments[0].getBoundingClientRect();
return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0'
       && r.width > 0 && r.height > 0;
"""


def _is_visible(driver: WebDriver, element) -> bool:
    try:
        return bool(driver.execute_script(VISIBLE_JS, element))
    except WebDriverException:
        return False


def _find_more_button(driver: WebDriver, more_locator: Locator):
    """
    Nút "Xem thêm" bị gỡ rồi gắn lại trong lúc render danh sách mới, nên nhìn một phát
    ngay sau khi tải xong dễ thấy "không có nút". Thử lại vài nhịp trước khi kết luận.
    """
    for _ in range(int(MORE_BUTTON_WAIT / MORE_BUTTON_POLL)):
        try:
            buttons = [b for b in driver.find_elements(*more_locator)
                       if _is_visible(driver, b)]
        except WebDriverException:
            buttons = []
        if buttons:
            return buttons[0]
        sleep(MORE_BUTTON_POLL)
    return None


def _click_more(driver: WebDriver, more_locator: Locator) -> Optional[bool]:
    """
    Bấm nút "Xem thêm". Trả None khi thật sự không còn nút, True/False cho bấm được /
    không bấm được.

    Tìm lại nút trước MỖI lần thử: giữa lúc tìm và lúc bấm, trang có thể render lại và
    biến element thành stale - bấm một phát rồi bỏ cuộc làm FPT Shop dừng ở 32 sản phẩm.
    """
    for attempt in range(CLICK_RETRIES):
        button = _find_more_button(driver, more_locator)
        if button is None:
            return None
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", button
            )
            sleep(0.4)
        except WebDriverException:
            continue  # element vừa stale -> vòng sau tìm lại
        if click_safe(driver, button):
            return True
        logger.info("Bấm 'Xem thêm' hụt (lần thử %d/%d), tìm lại nút",
                    attempt + 1, CLICK_RETRIES)
        sleep(MORE_BUTTON_POLL)
    return False


def _card_name(anchor) -> str:
    """Tên sản phẩm nằm trong thẻ h3 của card; text của cả anchor còn kèm giá."""
    try:
        titles = anchor.find_elements("css selector", "h3")
    except WebDriverException:
        return ""
    return titles[0].text.strip() if titles else ""
