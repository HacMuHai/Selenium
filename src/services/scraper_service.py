"""
Scraper Service - Business logic cho web scraping
"""
from datetime import datetime
from typing import List, Dict, Optional
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from json import dumps
from bson import ObjectId
import traceback

from config.driver import get_driver
from config import version as version_module
from models.product import Comment, Product
from repositories.comment_repository import CommentRepository
from utils.helpers import go_back


class ScraperService:
    """Service để crawl và lưu comments"""

    def __init__(self):
        self.comment_repository = CommentRepository()

    def get_content(self, li: WebElement) -> Comment:
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

    def crawl_comments(self, product_link: Product) -> Optional[List[Dict]]:
        """
        Crawl comments từ trang web

        Args:
            product_link: Thông tin sản phẩm (name, link)

        Returns:
            Danh sách comments nếu thành công, None nếu lỗi, [] nếu đã có trong DB
        """
        # Kiểm tra xem đã có product với link này chưa
        existing_product = self.comment_repository.find_by_product_link(
            product_link["link"])
        if existing_product:
            print(
                f"⚠️ Product với link {product_link['link']} đã tồn tại trong database. Bỏ qua crawl.")
            return []

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

                    # count += 1
                    # if count > 1:
                    #     break

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

                return None
        else:
            ul = driver.find_elements(By.CSS_SELECTOR, "ul.comment-list")
            lis = ul[0].find_elements(By.TAG_NAME, "li") if ul else []
            for li in lis:
                comments.append(self.get_content(li))

        # In kết quả
        # print(dumps(comments, ensure_ascii=False, indent=4))
        self.comment_repository.save_comments({
            **product_link,
            "comments": comments,
            "total_comments": len(comments),
            "crawled_at": datetime.now(),
            "version": version_module.version
        })

        driver.quit()
        return comments

# # chạy song song 5 threads
# with ThreadPoolExecutor(max_workers=3) as executor:
#     executor.map(crawl, [p["link"] for p in product_names])
