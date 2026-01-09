"""
Main entry point
"""
from concurrent.futures import ThreadPoolExecutor
from json import dumps
import traceback
import os
from pathlib import Path
from bson.json_util import dumps as bson_dumps
from openpyxl import Workbook, load_workbook
from selenium.webdriver.common.by import By
from config.database import get_collection, get_database
from config.driver import get_driver
from services.scraper_service import ScraperService
from models.product import Product
from repositories.comment_repository import CommentRepository
import time
# from concurrent.futures import ThreadPoolExecutor
# from json import dumps
# from openpyxl import Workbook


def main():
    """Hàm chính để chạy code"""
    # Lấy driver đã được khởi tạo (chỉ khởi tạo lần đầu tiên)
    scraper_service = ScraperService()
    # links = ["https://www.thegioididong.com/dtdd", "https://www.thegioididong.com/laptop",
    #          "https://www.thegioididong.com/may-tinh-bang", "https://www.thegioididong.com/pc-may-in",
    #          "https://www.thegioididong.com/dong-ho-thong-minh-thoi-trang-sanh-dieu",
    #          "https://www.thegioididong.com/dong-ho-thong-minh-da-tien-ich",
    #          "https://www.thegioididong.com/dong-ho-thong-minh-the-thao-chuyen-nghiep",
    #          "https://www.thegioididong.com/dong-ho-thong-minh-tre-em",
    #          "https://www.thegioididong.com/day-dong-ho"
    #          ]
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
        "https://www.thegioididong.com/sac-cap",
        "https://www.thegioididong.com/chuong-trinh-phu-kien-laptop",
    ]

    driver = get_driver()
    time.sleep(2)
    for link in links:

        driver.get(link)
        time.sleep(1.5)
        for i in range(15):

            for i in range(20):
                el_view_more = driver.find_elements(
                    By.CSS_SELECTOR, ".view-more")
                if el_view_more and el_view_more[0].is_displayed():
                    el_view_more[0].click()
                    time.sleep(2)
                else:
                    break

            # # # Tìm và đóng popup nếu có
            popups = driver.find_elements(By.CLASS_NAME, "icon-close-popup")
            if popups:
                try:
                    popups[0].click()
                except Exception as e:
                    pass

            # # #  ====================== Tìm tất cả các thẻ a ======================
            product_links_elements = driver.find_elements(
                By.CSS_SELECTOR, "li.item > a.main-contain")

            product_links = []
            for link in product_links_elements:
                try:
                    product_link = {
                        "name": link.get_attribute("data-name"),
                        "link":  link.get_attribute('href')
                    }
                    if product_link:  # Chỉ thêm nếu có text
                        product_links.append(product_link)
                except:
                    continue

            # # ================Crawl data ======================
            with ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(
                    scraper_service.crawl_comments, product_links))
            # print(dumps(results, ensure_ascii=False, indent=4))

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


def export_to_excel(base_file_name="comments_export", output_dir="excel_comment2"):
    """
    Export products với comments ra nhiều file Excel, mỗi file tối đa 100 comments
    Tối ưu memory bằng cách sử dụng cursor để xử lý từng product thay vì load tất cả vào memory

    Args:
        base_file_name: str - Tên file cơ bản (sẽ thêm số thứ tự vào)
        output_dir: str - Thư mục để lưu các file Excel
    """
    comment_repository = CommentRepository()

    # Tạo thư mục output nếu chưa tồn tại
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"📁 Lưu file vào thư mục: {output_path.absolute()}")

    # Đếm tổng số products để hiển thị progress
    total_products = comment_repository.count_products()
    print(f"Tổng số products trong collection: {total_products}")
    print("Bắt đầu export (sử dụng cursor để tối ưu memory)...")

    # Sử dụng cursor thay vì load tất cả vào memory
    products_cursor = comment_repository.find_all_products_cursor()

    MAX_COMMENTS_PER_FILE = 100
    file_index = 1
    comment_count = 0
    product_count = 0
    wb = None
    ws = None

    try:
        for product in products_cursor:
            product_count += 1

            # Hiển thị progress mỗi 100 products
            if product_count % 100 == 0:
                print(
                    f"Đang xử lý product {product_count}/{total_products}...")

            link = product.get("link", "")
            name_item = product.get("name", "")
            comments = product.get("comments", [])

            if comments:
                first = True
                for idx, comment in enumerate(comments):
                    if wb is None:
                        wb = Workbook()
                        ws = wb.active
                        ws.title = "Comments"
                        ws.append(
                            ["link", "name_item", "comments_id", "comments_content"])

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

                    # Kiểm tra nếu đủ 100 comments thì lưu file và tạo file mới
                    if comment_count >= MAX_COMMENTS_PER_FILE:
                        file_name = output_path / \
                            f"{base_file_name}_{file_index}.xlsx"
                        wb.save(str(file_name))
                        print(
                            f"✅ Đã xuất file: {file_name} ({comment_count} dòng comments)")
                        wb = None
                        ws = None
                        comment_count = 0
                        file_index += 1
                        first = True  # Reset first flag cho product tiếp theo

        # Lưu file cuối cùng nếu còn dữ liệu
        if wb is not None and comment_count > 0:
            file_name = output_path / f"{base_file_name}_{file_index}.xlsx"
            wb.save(str(file_name))
            print(
                f"✅ Đã xuất file: {file_name} ({comment_count} dòng comments)")

        print(
            f"\n🎉 Hoàn thành! Đã xử lý {product_count} products và tạo {file_index} file(s) Excel")

    except Exception as e:
        # Lưu file hiện tại nếu có lỗi
        if wb is not None and comment_count > 0:
            file_name = output_path / f"{base_file_name}_{file_index}.xlsx"
            wb.save(str(file_name))
            print(f"⚠️ Đã lưu file cuối cùng trước khi có lỗi: {file_name}")
        raise e


if __name__ == "__main__":
    # main()
    export_to_excel("comments_export", "excel_comment2")
