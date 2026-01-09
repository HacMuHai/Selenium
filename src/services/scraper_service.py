"""
Scraper Service - Business logic cho web scraping
"""
from typing import List, Dict, Optional
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from json import dumps
import traceback

from config.driver import get_driver
from models.product import Product
from repositories.comment_repository import CommentRepository
from utils.helpers import go_back


class ScraperService:
    """Service để crawl và lưu comments"""

    def __init__(self):
        self.comment_repository = CommentRepository()

    def crawl_comments(self, product_link: Product) -> Optional[List[Dict]]:
        """
        Crawl comments từ trang web

        Args:
            product_link: Thông tin sản phẩm (name, link)

        Returns:
            Danh sách comments nếu thành công, None nếu lỗi
        """
        driver = get_driver()
        time.sleep(1)

        # btn_view_more_cmt = driver.find_element(
        #     By.CSS_SELECTOR, ".box-flex > a.c-btn-rate.btn-view-all")
        # if btn_view_more_cmt:
        #     driver.get(btn_view_more_cmt.get_attribute("href"))
        #     time.sleep(1.5)

        #     while True:
        #         ul = driver.find_element(By.CSS_SELECTOR, ".comment-list")
        #         lis = ul.find_elements(By.TAG_NAME, "li")

        #         container = driver.find_element(By.CSS_SELECTOR, ".pagcomment")
        #         next_element = container.find_element(
        #             By.XPATH,
        #             "./* [preceding-sibling::span[@class='active']]"
        #         )
        #         if next_element:
        #             try:
        #                 next_element.click()
        #                 time.sleep(1)
        #             except:
        #                 driver.quit()
        #                 break
        #         else:
        #             break
        # else:
        #     ul = driver.find_element(By.CSS_SELECTOR, "ul.comment-list")
        #     lis = ul.find_elements(By.TAG_NAME, "li")

        # =================Crawl data=================
        comments = []
        try:
            while True:
                ul = driver.find_elements(By.CSS_SELECTOR, ".comment-list")
                lis = ul[0].find_elements(By.TAG_NAME, "li") if ul else []

                # name: p.cmt-top-name
                # content: p.cmt-txt
                # Extract comments từ mỗi li
                for li in lis:
                    names = li.find_elements(By.CSS_SELECTOR, "p.cmt-top-name")
                    contents = li.find_elements(By.CSS_SELECTOR, "p.cmt-txt")
                    comments.append({
                        "name": names[0].text if names else "",
                        "content": contents[0].text if contents else ""
                    })

                # Tìm và click nút next
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
                        time.sleep(1)
                    else:
                        break
                except Exception as e:
                    print(
                        f"Lỗi khi tìm next element: {type(e).__name__} - {e}")
                    traceback.print_exc()
                    break

            # In kết quả
            print(dumps(comments, ensure_ascii=False, indent=4))

            # Lưu vào MongoDB
            self.comment_repository.save_comments(product_link, comments)

            # Go back
            go_back(driver)

            return comments

        except Exception as e:
            print(f"Lỗi khi crawl: {type(e).__name__} - {e}")
            traceback.print_exc()

            # Xử lý lỗi - cố gắng go back
            if driver.current_url != product_link["link"]:
                try:
                    pagcomment_new = driver.find_elements(
                        By.CSS_SELECTOR, ".pagcomment")
                    el_a = pagcomment_new[0].find_elements(
                        By.XPATH, "./*") if pagcomment_new else None
                    if el_a and len(el_a) > 0:
                        el_a[1].click()
                except:
                    pass

            return None


# # chạy song song 5 threads
# with ThreadPoolExecutor(max_workers=3) as executor:
#     executor.map(crawl, [p["link"] for p in product_names])
