"""
Helper utilities
"""
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By


def go_back(driver: WebDriver) -> None:
    """Điều hướng về trang trước bằng cách click nút back trong pagination"""
    try:
        pagcomment_new = driver.find_elements(By.CSS_SELECTOR, ".pagcomment")
        el_a = pagcomment_new[0].find_elements(
            By.XPATH, "./*") if pagcomment_new else None
        if el_a and len(el_a) > 0:
            el_a[1].click()
    except Exception as e:
        print(f"Không thể go back: {e}")
