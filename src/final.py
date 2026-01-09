"""
Final script - Chỉ crawl data và print ra, không dùng MongoDB
"""
from concurrent.futures import ThreadPoolExecutor
from json import dumps
import traceback
import time
import os
import stat
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from bson import ObjectId
from openpyxl import Workbook


# ==================== DRIVER CONFIGURATION ====================
_driver = None


def get_driver():
    """Lấy WebDriver instance, tạo mới nếu chưa có"""
    global _driver
    if _driver is None:
        print("Đang khởi tạo driver lần đầu tiên...")
        try:
            driver_path = ChromeDriverManager().install()
            _driver = webdriver.Chrome(service=Service(driver_path))
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


# ==================== HELPER FUNCTIONS ====================
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


# ==================== SCRAPER SERVICE ====================
class ScraperService:
    """Service để crawl comments"""

    def __init__(self):
        pass

    def get_content(self, li: WebElement) -> dict:
        """Lấy nội dung comment từ element"""
        names = li.find_elements(
            By.CSS_SELECTOR, "p.cmt-top-name")
        contents = li.find_elements(
            By.CSS_SELECTOR, "p.cmt-txt")
        ratings = li.find_elements(
            By.CSS_SELECTOR, ".cmt-top-star .iconcmt-starbuy")
        return {
            "name": names[0].text if names else "",
            "content": contents[0].text if contents else "",
            "rating": len(ratings) if ratings else "",
            "id": str(ObjectId())
        }

    def crawl_comments(self, product_link: dict) -> list:
        """
        Crawl comments từ trang web

        Args:
            product_link: Thông tin sản phẩm (name, link)

        Returns:
            Danh sách comments
        """
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()))
        driver.get(product_link["link"])
        time.sleep(1.5)

        comments = []
        btn_view_more_cmts = driver.find_elements(
            By.CSS_SELECTOR, ".box-flex > a.c-btn-rate.btn-view-all")
        if btn_view_more_cmts:
            driver.get(btn_view_more_cmts[0].get_attribute("href"))
            time.sleep(1.5)

            try:
                while True:
                    ul = driver.find_elements(By.CSS_SELECTOR, ".comment-list")
                    lis = ul[0].find_elements(By.TAG_NAME, "li") if ul else []

                    for li in lis:
                        comments.append(self.get_content(li))

                    try:
                        containers = driver.find_elements(
                            By.CSS_SELECTOR, ".pagcomment")

                        next_element = containers[0].find_elements(
                            By.XPATH,
                            "./* [preceding-sibling::span[@class='active']]"
                        ) if containers else None

                        if next_element and len(next_element) > 0:
                            print("next_element",
                                  next_element[0].get_attribute("title"))
                            next_element[0].click()
                            time.sleep(1.5)
                        else:
                            break
                    except Exception as e:
                        print(
                            f"Lỗi khi tìm next element: {type(e).__name__} - {e}")
                        traceback.print_exc()
                        break

            except Exception as e:
                print(f"Lỗi khi crawl: {type(e).__name__} - {e}")
                traceback.print_exc()

                if driver.current_url != product_link["link"]:
                    go_back(driver)

                driver.quit()
                return []
        else:
            ul = driver.find_elements(By.CSS_SELECTOR, "ul.comment-list")
            lis = ul[0].find_elements(By.TAG_NAME, "li") if ul else []
            for li in lis:
                comments.append(self.get_content(li))

        driver.quit()
        return comments


# ==================== EXPORT TO EXCEL ====================
def export_to_excel(all_results: list, base_file_name: str = "comments_export", output_dir: str = "excel_comment_result"):
    """
    Export products với comments ra 1 file Excel duy nhất

    Args:
        all_results: list - Danh sách kết quả crawl (mỗi item có "product" và "comments")
        base_file_name: str - Tên file cơ bản
        output_dir: str - Thư mục để lưu file Excel
    """
    # Tạo thư mục output nếu chưa tồn tại
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Lưu file vào thư mục: {output_path.absolute()}")

    # Tạo workbook và worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"
    ws.append(["link", "name_item", "comments_id", "comments_content"])

    comment_count = 0
    product_count = 0

    try:
        for result in all_results:
            product_count += 1
            product = result.get("product", {})
            comments = result.get("comments", [])

            link = product.get("link", "")
            name_item = product.get("name", "")

            if comments:
                first = True
                for idx, comment in enumerate(comments):
                    # Lấy comments_id (có thể dùng index hoặc name)
                    comments_id = comment.get("id", str(idx))
                    comments_content = comment.get("content", "")

                    if first:
                        ws.append(
                            [link, name_item, comments_id, comments_content])
                        first = False
                    else:
                        # Các dòng sau để trống 2 cột đầu
                        ws.append(["", "", comments_id, comments_content])

                    comment_count += 1

        # Lưu file
        file_name = output_path / f"{base_file_name}.xlsx"
        wb.save(str(file_name))
        print(
            f"✅ Đã xuất file: {file_name} ({comment_count} dòng comments)")

        print(
            f"\n🎉 Hoàn thành! Đã xử lý {product_count} products và tạo 1 file Excel")

    except Exception as e:
        # Lưu file hiện tại nếu có lỗi
        if wb is not None and comment_count > 0:
            file_name = output_path / f"{base_file_name}.xlsx"
            wb.save(str(file_name))
            print(f"⚠️ Đã lưu file cuối cùng trước khi có lỗi: {file_name}")
        raise e


# ==================== MAIN FUNCTION ====================
def main():
    """Hàm chính để chạy code"""
    scraper_service = ScraperService()

    links = [
        # "https://www.thegioididong.com/dong-ho-deo-tay-nam",
        # "https://www.thegioididong.com/dong-ho-deo-tay#c=7264&o=8&pi=0"
        # "https://www.thegioididong.com/dong-ho-deo-tay-nu",
        # "https://www.thegioididong.com/dong-ho-deo-tay-casio",
        # "https://www.thegioididong.com/dong-ho-deo-tay-citizen",
        # "https://www.thegioididong.com/dong-ho-deo-tay-orient",
        # "https://www.thegioididong.com/khuyen-mai-dong-ho-chi-ban-online",
        # "https://www.thegioididong.com/dong-ho-deo-tay-MVW",
        # "https://www.thegioididong.com/dong-ho-deo-tay-elio",
        # "https://www.thegioididong.com/dong-ho-deo-tay-tre-em",
        # "https://www.thegioididong.com/camera-giam-sat",
        # "https://www.thegioididong.com/tai-nghe",
        # "https://www.thegioididong.com/sac-dtdd",
        # "https://www.thegioididong.com/phu-kien/apple",
        # "https://www.thegioididong.com/loa-laptop",
        # "https://www.thegioididong.com/chuong-trinh-phu-kien-laptop",
        "https://www.thegioididong.com/sac-cap",
    ]

    driver = get_driver()
    time.sleep(2)

    all_results = []

    for link in links:
        print(f"\n{'='*60}")
        print(f"Đang crawl từ: {link}")
        print(f"{'='*60}")

        driver.get(link)
        time.sleep(1.5)

        for page in range(15):
            print(f"\n--- Trang {page + 1} ---")

            # Click "Xem thêm" để load thêm sản phẩm
            for i in range(20):
                el_view_more = driver.find_elements(
                    By.CSS_SELECTOR, ".view-more")
                if el_view_more and el_view_more[0].is_displayed():
                    el_view_more[0].click()
                    time.sleep(2)
                else:
                    break

            # Tìm và đóng popup nếu có
            popups = driver.find_elements(By.CLASS_NAME, "icon-close-popup")
            if popups:
                try:
                    popups[0].click()
                except Exception as e:
                    pass

            # Tìm tất cả các thẻ a (sản phẩm)
            product_links_elements = driver.find_elements(
                By.CSS_SELECTOR, "li.item > a.main-contain")

            product_links = []
            for link_element in product_links_elements:
                try:
                    product_link = {
                        "name": link_element.get_attribute("data-name"),
                        "link": link_element.get_attribute('href')
                    }
                    if product_link["name"] and product_link["link"]:
                        product_links.append(product_link)
                except:
                    continue

            print(f"Tìm thấy {len(product_links)} sản phẩm")

            # Crawl data từ các sản phẩm
            with ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(
                    scraper_service.crawl_comments, product_links))

            # In kết quả
            for idx, (product, comments) in enumerate(zip(product_links, results)):
                print(f"\n{'─'*60}")
                print(f"Sản phẩm {idx + 1}: {product['name']}")
                print(f"Link: {product['link']}")
                print(f"Số lượng comments: {len(comments)}")
                print(f"{'─'*60}")

                if comments:
                    print("\nComments:")
                    for i, comment in enumerate(comments, 1):
                        print(f"\n  Comment {i}:")
                        print(f"    Tên: {comment.get('name', 'N/A')}")
                        print(f"    Nội dung: {comment.get('content', 'N/A')}")
                        print(
                            f"    Rating: {comment.get('rating', 'N/A')} sao")
                else:
                    print("  Không có comments")

                # Lưu vào all_results để in tổng kết
                all_results.append({
                    "product": product,
                    "comments": comments
                })

            # Tìm nút next để chuyển trang
            try:
                el_pagination = driver.find_elements(
                    By.CSS_SELECTOR, "ul.pagination")
                next_element = el_pagination[0].find_elements(
                    By.XPATH,
                    ".//li[contains(concat(' ', normalize-space(@class), ' '), ' active ')]/following-sibling::li[1][not(@id)]") if el_pagination else None
                if next_element:
                    next_element[0].click()
                    time.sleep(1.5)
                else:
                    break

            except Exception as e:
                print(
                    f"Lỗi khi tìm next element: {type(e).__name__} - {e}")
                traceback.print_exc()
                break

    # In tổng kết
    print(f"\n\n{'='*60}")
    print("TỔNG KẾT")
    print(f"{'='*60}")
    total_products = len(all_results)
    total_comments = sum(len(r["comments"]) for r in all_results)
    print(f"Tổng số sản phẩm đã crawl: {total_products}")
    print(f"Tổng số comments: {total_comments}")
    print(f"\nChi tiết:")
    for result in all_results:
        print(
            f"  - {result['product']['name']}: {len(result['comments'])} comments")

    # In JSON format
    print(f"\n\n{'='*60}")
    print("KẾT QUẢ DẠNG JSON")
    print(f"{'='*60}")
    print(dumps(all_results, ensure_ascii=False, indent=2))

    # Xuất ra Excel
    print(f"\n\n{'='*60}")
    print("XUẤT FILE EXCEL")
    print(f"{'='*60}")
    export_to_excel(all_results, "comments_export", "excel_comment2")

    close_driver()


if __name__ == "__main__":
    main()
