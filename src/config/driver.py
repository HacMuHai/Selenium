"""
Driver configuration - Selenium WebDriver setup
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

_driver = None


def get_driver():
    """Lấy WebDriver instance, tạo mới nếu chưa có"""
    global _driver
    if _driver is None:
        print("Đang khởi tạo driver lần đầu tiên...")
        _driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()))
        # _driver.get("https://www.thegioididong.com/")
        # _driver.get(
        #     "https://www.thegioididong.com/dtdd/iphone-16-pro-max?utm_recommendation=1")
        _driver.get(
            "https://www.thegioididong.com/dtdd/iphone-16-pro-max/danh-gia")
        print("Driver đã được khởi tạo thành công!")
        return _driver
    else:
        print("Driver đã tồn tại, sử dụng driver đã tồn tại!")
        return _driver


def close_driver():
    """Đóng WebDriver"""
    global _driver
    if _driver is not None:
        _driver.quit()
        _driver = None
        print("Driver đã được đóng")
