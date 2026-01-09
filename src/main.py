"""
Main entry point
"""
from selenium.webdriver.common.by import By
from config.driver import get_driver
from services.scraper_service import ScraperService
from models.product import Product
import time
# from concurrent.futures import ThreadPoolExecutor
# from json import dumps
# from openpyxl import Workbook


def main():
    """Hàm chính để chạy code"""
    # Lấy driver đã được khởi tạo (chỉ khởi tạo lần đầu tiên)
    driver = get_driver()
    time.sleep(1)

    # Tìm và đóng popup nếu có
    popups = driver.find_elements(By.CLASS_NAME, "icon-close-popup")
    if popups:
        try:
            popups[0].click()
        except Exception as e:
            pass

    #  ====================== Tìm tất cả các thẻ a ======================
    # product_links = driver.find_elements(
    #     By.CSS_SELECTOR, "li.item > a.main-contain")

    # product_names = []
    # for link in product_links:
    #     try:
    #         product_name = {
    #             "name": link.get_attribute("data-name"),
    #             "link":  link.get_attribute('href')
    #         }
    #         if product_name:  # Chỉ thêm nếu có text
    #             product_names.append(product_name)
    #     except:
    #         continue

    # ================In ra danh sách tên sản phẩm ================
    # print(f"\nTìm thấy {len(product_names)} sản phẩm:")
    # for i, item in enumerate(product_names, 1):
    #     prefix = f"{i}."
    #     indent = " " * len(prefix)

    #     print(f"{prefix} {item['name']}")
    #     print(f"{indent} {item['link']}\n")

    # ================Crawl data ======================
    # with ThreadPoolExecutor(max_workers=3) as executor:
    #     results = list(executor.map(crawl, product_names[:2]))
    # print(dumps(results, ensure_ascii=False, indent=4))

    # ================Export to excel ======================
    # def export_to_excel(data, file_name="comments_export.xlsx"):
        # wb = Workbook()
        # ws = wb.active
        # ws.title = "Comments"

        # # Header
        # ws.append(["link", "name_item", "comments_content", "comments_name"])

        # for item in data:
        #     link = item["link"]
        #     name_item = item["name_item"]
        #     comments = item.get("comments", [])

        # # Nếu không có comment → ghi 1 dòng trống
        # if not comments:
        #     ws.append([link, name_item, "", ""])

        # # Ghi comment đầu tiên cùng link + name_item
        # first = True
        # for c in comments:
        #     if first:
        #         ws.append([link, name_item, c["content"], c["name"]])
        #         first = False
        #     else:
        #         # Các dòng sau để trống 2 cột đầu
        #         ws.append(["", "", c["content"], c["name"]])

        # wb.save(file_name)
        # print("Đã xuất file:", file_name)

    # Khởi tạo scraper service
    scraper_service = ScraperService()

    # Crawl comments
    product: Product = {
        "name": "iPhone 16 Pro Max",
        "link": "https://www.thegioididong.com/dtdd/iphone-16-pro-max/danh-gia",
        "comments": []
    }

    comments = scraper_service.crawl_comments(product)
    # print(dumps(data, ensure_ascii=False, indent=4))

    if comments:
        print(f"\n✅ Đã crawl thành công {len(comments)} comments")
    else:
        print("\n❌ Crawl thất bại")

    print("\n=====Close popup successfully=======")


if __name__ == "__main__":
    main()
