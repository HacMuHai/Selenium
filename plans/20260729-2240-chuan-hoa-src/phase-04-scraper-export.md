# Phase 04 — ScraperService + ExportService + chế độ `--no-db`

## Context links
- [plan.md](./plan.md) · [phase-02-driver-layer.md](./phase-02-driver-layer.md)
- [phase-03-data-layer.md](./phase-03-data-layer.md)
- [researcher-01-selenium-concurrency.md](./research/researcher-01-selenium-concurrency.md) §1,3,6
- Scout bugs #2, #3, #7, #10

## Overview
- Date: 2026-07-29
- Description: ScraperService dùng driver thread-local + WebDriverWait + try/finally; tách
  `export_service.py` khỏi `main.py`; chế độ no-db dùng chung service qua repository injection.
- Priority: P0
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- **Cách làm no-db (đã cân nhắc 2 phương án)**:
  - `persist: bool` → phải rắc `if persist:` ở 2 chỗ (dedup + save), và `--export` khi no-db lại
    không có nguồn dữ liệu để đọc.
  - **Chọn: repository injection + `InMemoryProductRepository`** (null-object có state). Cùng
    interface → `ScraperService` KHÔNG có một dòng `if` nào về DB; `ExportService` nhận repository
    nên export chạy y hệt cho cả 2 chế độ. Bonus: test không cần mongomock cho service layer.
- `export_to_excel` hiện nằm trong `main.py` và tự `new CommentRepository()` → phải tách ra và
  nhận repository từ ngoài (DRY + testable).
- Vòng crawl comment hiện dùng `time.sleep(1.5)` sau mỗi lần click phân trang → thay bằng
  `staleness_of` phần tử `.comment-list` cũ + chờ item xuất hiện.
- `rating` phải luôn là `int`: `len(ratings)` (0 khi không có sao), bỏ `if ratings else ""`.

## Requirements
1. `ScraperService(repository, headless, wait_timeout)` — không tự tạo repository.
2. `crawl_product(product_link) -> list[Comment]` có try/finally, không leak driver, không tự quit
   driver thread-local (dùng lại).
3. Không `time.sleep` cố định trong luồng crawl (trừ backoff retry stale).
4. `ExportService(repository, output_dir, max_rows_per_file)` với `export()`.
5. `InMemoryProductRepository` cùng interface với `ProductRepository`.

## Architecture
```
repositories/product_repository.py     # Mongo (P3)
repositories/memory_repository.py      # InMemoryProductRepository (THÊM)
   -> cùng bộ method: exists_by_link, insert_product, iter_products, count_products, ...

services/scraper_service.py
   class ScraperService:
       def __init__(self, repository, headless=True, wait_timeout=15.0)
       def crawl_product(self, product_link: dict) -> list[Comment]
       def collect_product_links(self, driver, category_url, max_pages, limit) -> list[dict]
       def _parse_comment(self, li: WebElement) -> Comment
       def _crawl_comment_pages(self, driver) -> list[Comment]

services/export_service.py
   class ExportService:
       def __init__(self, repository, output_dir: str, max_rows_per_file: int = 2000)
       def export(self, base_file_name="comments_export") -> list[Path]
```
`main.py` (P5) quyết định inject repo nào; service không biết chế độ nào đang chạy.

## Related code files
- SỬA nặng: `src/services/scraper_service.py` (137 → ~170 dòng)
- THÊM: `src/services/export_service.py`, `src/repositories/memory_repository.py`,
  `tests/test_export_service.py`
- Lấy logic từ (rồi xoá): `src/main.py:121-221` (export), `src/main.py:55-118` (thu link/phân trang)
- Đã xoá ở P1: `src/final.py` — mọi hành vi "in ra + xuất Excel, không DB" nằm ở đây.

## Implementation Steps
1. `memory_repository.py`: giữ `self._docs: list[dict]`, `exists_by_link` luôn trả `False`
   (no-db thì không dedup theo DB — mong muốn), `insert_product` append + sinh `_id` giả,
   `iter_products` yield từ list, `count_products` len. Method API-only (`update_comment`…)
   raise `NotImplementedError` — chấp nhận, CLI không gọi.
2. `_parse_comment`: `rating: int = len(ratings)` (bỏ `""`); giữ `id = str(ObjectId())`.
3. `crawl_product`:
   ```python
   def crawl_product(self, product_link: dict) -> list[Comment]:
       if self.repository.exists_by_link(product_link["link"]):
           logger.info("Bỏ qua (đã có trong DB): %s", product_link["link"]); return []
       driver = get_driver()                      # thread-local, KHÔNG tạo mới
       try:
           driver.get(product_link["link"])
           comments = self._crawl_comment_pages(driver)
           self.repository.insert_product({**product_link, "comments": comments,
               "total_comments": len(comments), "crawled_at": datetime.now(),
               "version": version_module.version})
           return comments
       except Exception:
           logger.exception("Lỗi crawl %s", product_link["link"])
           return []                              # không để thread chết ôm driver
       finally:
           pass                                   # driver tái dùng; quit_all() ở CLI
   ```
   Trả `[]` thay vì `None` → caller không phải check None (bug #2 gốc).
4. `_crawl_comment_pages`: chờ `.box-flex > a.c-btn-rate.btn-view-all` bằng `wait_for` ngắn
   (timeout riêng ~5s, không lỗi khi không có); nếu có → `driver.get(href)`; vòng lặp:
   `wait_for(.comment-list)` → parse `li` → tìm next trong `.pagcomment` → `click_safe` →
   `wait.until(EC.staleness_of(old_ul))` → tiếp. Thoát khi không còn next hoặc `TimeoutException`.
   Thêm `max_comment_pages` guard (mặc định 50) chống vòng vô hạn.
5. `collect_product_links(driver, category_url, max_pages, limit)`: chuyển logic từ `main.py:55-118`,
   **sửa bug shadow biến**: vòng ngoài `category_url`, vòng trong `anchor` (bug #4);
   vòng "view-more" dùng `page_idx` / `click_idx` riêng (bug #5). Vòng view-more thay
   `sleep(2)` bằng `wait_count_grows(driver, ITEM_LOCATOR, before)`; dừng khi không tăng.
   `limit` cắt sớm danh sách để smoke-test nhanh.
6. `export_service.py`: bê nguyên thuật toán từ `main.py:121-221` nhưng:
   - `repository.iter_products(projection={"link":1,"name":1,"comments":1})` — giảm băng thông.
   - `print` → `logger.info`; bỏ emoji trong log.
   - Bỏ `except: save rồi raise e` → dùng `try/finally` để flush workbook cuối cùng, `raise` trần.
   - Trả `list[Path]` các file đã ghi (test assert được).
   - Đặt tên biến `max_rows_per_file` (tên cũ `max_comments_per_file` nhưng đếm theo dòng).
7. Test: `test_export_service.py` dùng `InMemoryProductRepository` nạp 3 product × 2 comment,
   `max_rows_per_file=2` → assert số file = 3, đọc lại bằng `openpyxl.load_workbook` kiểm header.

## Todo list
- [x] memory_repository.py
- [x] scraper_service: DI repository, _parse_comment rating int
- [x] crawl_product try/finally, trả []
- [x] _crawl_comment_pages với WebDriverWait + guard max page
- [x] collect_product_links (sửa shadow `link`/`i`)
- [x] export_service.py tách khỏi main.py
- [x] tests/test_export_service.py

## Success Criteria
- `python -m pytest tests/test_export_service.py -q` → pass, sinh file trong tmp_path.
- Smoke-test thật (chạy sau P5, nhưng verify được bằng snippet):
  `python -c "from src.repositories.memory_repository import InMemoryProductRepository as M; from src.services.scraper_service import ScraperService; from src.config.driver import quit_all; s=ScraperService(M(), headless=True); print(len(s.crawl_product({'name':'x','link':'<url 1 sp>'}))); quit_all()"`
  → in số comment > 0, `pgrep -f chromedriver` rỗng sau đó.
- `grep -rn "time.sleep" src/services/` → chỉ còn trong backoff retry (0 hoặc 1 chỗ).
- `grep -rn "print(" src/services/` → rỗng.

## Risk Assessment
- **Selector TGDĐ đổi** → crawl trả 0 comment mà không báo lỗi. Mitigation: log WARNING khi
  `comments == []` cho 1 product, và log tổng kết cuối run (số product 0-comment).
- **`staleness_of` không kích hoạt** nếu site phân trang bằng AJAX in-place → fallback:
  so sánh text comment đầu tiên trước/sau click. Cần smoke-test xác nhận, ghi vào TODO khi chạy.
- **`exists_by_link` luôn False ở chế độ no-db** → crawl lại product đã có trong Mongo. Đúng ý đồ
  (no-db không đụng Mongo), nhưng phải ghi rõ trong `--help`.
- **Vòng lặp vô hạn** nếu next-button luôn tồn tại → guard `max_comment_pages`.

## Security Considerations
- Rate-limit lịch sự: `max_workers` mặc định 3, không nâng mặc định lên cao (tránh DoS site đích).
- Không lưu HTML thô / dữ liệu cá nhân ngoài tên hiển thị + nội dung comment công khai.
- Excel output đã gitignore (`excel_*/` sau P1) — chứa dữ liệu crawl, không commit.

## Next steps
→ Phase 05: CLI ráp ScraperService + ExportService + chọn repository.
