"""
Helper cho Selenium - toàn bộ chờ đợi đi qua WebDriverWait, không `time.sleep` cố định.
"""
import logging
from typing import Callable, Optional

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from src.config.driver import get_wait

logger = logging.getLogger(__name__)

Locator = tuple[str, str]


def wait_for(
    driver: WebDriver,
    locator: Locator,
    timeout: Optional[float] = None,
    condition: Callable = EC.presence_of_element_located,
) -> Optional[WebElement]:
    """Chờ element khớp `locator`. Trả `None` khi hết timeout thay vì ném exception."""
    try:
        return get_wait(driver, timeout).until(condition(locator))
    except TimeoutException:
        return None


def click_safe(driver: WebDriver, element: WebElement) -> bool:
    """Click element, fallback sang JS click khi bị che. Trả False nếu cả hai đều hỏng."""
    try:
        element.click()
        return True
    except WebDriverException as exc:
        logger.warning("Click thường thất bại (%s), thử JS click", type(exc).__name__)
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except WebDriverException:
        logger.warning("JS click cũng thất bại", exc_info=True)
        return False


def wait_count_grows(
    driver: WebDriver,
    locator: Locator,
    before: int,
    timeout: Optional[float] = None,
) -> bool:
    """Chờ số element khớp `locator` vượt `before`. Trả False khi hết timeout."""
    try:
        get_wait(driver, timeout).until(
            lambda d: len(d.find_elements(*locator)) > before
        )
        return True
    except TimeoutException:
        return False


def go_back(driver: WebDriver) -> None:
    """Quay lại trang trước qua nút back trong `.pagcomment`."""
    try:
        containers = driver.find_elements("css selector", ".pagcomment")
        if not containers:
            return
        children = containers[0].find_elements("xpath", "./*")
        if len(children) > 1:
            children[1].click()
    except WebDriverException:
        logger.warning("Không thể go back", exc_info=True)
