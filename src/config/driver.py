"""
Driver layer - Selenium WebDriver theo thread-local.

Mỗi thread của ThreadPoolExecutor lấy driver riêng qua `get_driver()`; driver được tạo
lazy lần đầu và tái sử dụng cho mọi sản phẩm mà thread đó xử lý. `quit_all()` đóng toàn bộ
(đăng ký sẵn `atexit`, nhưng caller vẫn nên gọi trong `finally` để đóng sớm).

Dùng Selenium Manager tích hợp (selenium >= 4.15) - KHÔNG cần webdriver-manager.
"""
import atexit
import logging
import threading
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_tls = threading.local()
_drivers: list[WebDriver] = []
_lock = threading.Lock()

# Khi attach vào Chrome do người dùng tự mở, `quit_all()` KHÔNG được giết browser đó.
_attach_address: Optional[str] = None


def set_attach_address(address: Optional[str]) -> None:
    """Đặt `host:port` của Chrome remote-debugging để mọi driver mới attach vào."""
    global _attach_address
    _attach_address = address


def build_options(headless: bool, attach_address: Optional[str] = None) -> ChromeOptions:
    """Dựng ChromeOptions. Khi attach thì bỏ qua headless/window-size (browser đã chạy sẵn)."""
    options = ChromeOptions()

    if attach_address:
        options.debugger_address = attach_address
        return options

    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument(f"--user-agent={_USER_AGENT}")
    options.add_experimental_option(
        "prefs", {"profile.default_content_setting_values.notifications": 2}
    )
    # DOM sẵn sàng là đủ - mọi truy cập element đều đi qua explicit wait.
    options.page_load_strategy = "eager"
    return options


def get_driver() -> WebDriver:
    """Trả về WebDriver của thread hiện tại, tạo lazy lần đầu."""
    driver = getattr(_tls, "driver", None)
    if driver is not None:
        return driver

    settings = get_settings()
    driver = webdriver.Chrome(options=build_options(settings.headless, _attach_address))
    # Không trộn implicit wait với explicit wait.
    driver.implicitly_wait(0)

    _tls.driver = driver
    with _lock:
        _drivers.append(driver)
    logger.info("Đã tạo driver mới cho thread %s", threading.current_thread().name)
    return driver


def get_wait(driver: WebDriver, timeout: Optional[float] = None) -> WebDriverWait:
    """WebDriverWait với timeout mặc định lấy từ Settings."""
    if timeout is None:
        timeout = get_settings().wait_timeout
    return WebDriverWait(driver, timeout, poll_frequency=0.3)


def quit_current() -> None:
    """Đóng driver của thread hiện tại."""
    driver = getattr(_tls, "driver", None)
    if driver is None:
        return
    _tls.driver = None
    with _lock:
        if driver in _drivers:
            _drivers.remove(driver)
    _quit_one(driver)


def quit_all() -> None:
    """Đóng mọi driver đã tạo. An toàn khi gọi nhiều lần."""
    if _attach_address:
        logger.warning(
            "Đang attach vào Chrome %s - không quit browser của bạn.", _attach_address
        )
        with _lock:
            _drivers.clear()
        _tls.driver = None
        return

    with _lock:
        drivers, _drivers[:] = list(_drivers), []
    for driver in drivers:
        _quit_one(driver)
    _tls.driver = None


def _quit_one(driver: WebDriver) -> None:
    try:
        driver.quit()
    except Exception:  # driver có thể đã chết - đừng để lỗi teardown che lỗi thật
        logger.debug("Bỏ qua lỗi khi quit driver", exc_info=True)


atexit.register(quit_all)
