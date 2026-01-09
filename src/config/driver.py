"""
Driver configuration - Selenium WebDriver setup
"""
import os
import stat
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

_driver = None


def _fix_chromedriver_permissions(driver_path: str):
    """Cấp quyền thực thi và xóa quarantine attribute cho ChromeDriver"""
    try:
        # Cấp quyền thực thi
        os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP |
                 stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Xóa quarantine attribute (macOS Gatekeeper)
        import subprocess
        subprocess.run(['xattr', '-d', 'com.apple.quarantine', driver_path],
                       capture_output=True, check=False)
        print(f"✅ Đã cấp quyền cho ChromeDriver: {driver_path}")
    except Exception as e:
        print(f"⚠️ Không thể cấp quyền cho ChromeDriver: {e}")


def get_driver():
    """Lấy WebDriver instance, tạo mới nếu chưa có"""
    global _driver
    if _driver is None:
        print("Đang khởi tạo driver lần đầu tiên...")
        try:
            driver_path = ChromeDriverManager().install()
            # Cấp quyền thực thi cho ChromeDriver (fix lỗi status code -9 trên macOS)
            # _fix_chromedriver_permissions(driver_path)

            _driver = webdriver.Chrome(service=Service(driver_path))
            # _driver.get("https://www.thegioididong.com/")
            # _driver.get(
            #     "https://www.thegioididong.com/dtdd/iphone-16-pro-max?utm_recommendation=1")
            # _driver.get(
            #     "https://www.thegioididong.com/dtdd/tecno-spark-40c-4gb-128gb")
            # _driver.get(
            #     "https://www.thegioididong.com/sac-dtdd/pin-sac-du-phong-polymer-10000mah-type-c-pd-30w-baseus-qpow-2-ppqd4-10c")

            print("Driver đã được khởi tạo thành công!")
            return _driver
        except Exception as e:
            error_msg = str(e)
            if "Status code was: -9" in error_msg or "unexpectedly exited" in error_msg:
                print("\n❌ Lỗi ChromeDriver (Status code -9):")
                print("   Đây là lỗi quyền truy cập trên macOS.")
                print("   Thử các cách sau:")
                print("   1. Xóa cache: rm -rf ~/.wdm/drivers/chromedriver")
                print(
                    "   2. Cấp quyền: chmod +x ~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver")
                print("   3. Xóa quarantine: xattr -d com.apple.quarantine ~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver")
            raise
    else:
        print("- Sử dụng driver đã tạo trước đó!")
        return _driver


def close_driver():
    """Đóng WebDriver"""
    global _driver
    if _driver is not None:
        _driver.quit()
        _driver = None
        print("Driver đã được đóng")
