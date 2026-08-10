# Scout 01 — Inventory `src/` + root (đã đọc 100% code)

Repo: `/Users/hacmuhai/Desktop/Toan/Selenium` · branch `main` · 24 file .py, ~1482 dòng.

## Sơ đồ phụ thuộc hiện tại

```
app.py ──> api/comments.py ──> services/comment_service.py ──┐
                                                              ├─> repositories/comment_repository.py ─> config/database.py
main.py ──> services/scraper_service.py ─────────────────────┘                                          (MongoClient trong sys.modules)
   │              │
   │              └─> config/driver.py (singleton global _driver) , config/version.py , utils/helpers.py , models/product.py
   └─> repositories/comment_repository.py (cho export_to_excel)
run.py ──> config/driver.py + importlib.reload(main) ──> main.main()
final.py ── standalone, KHÔNG import gì trong src (bản copy của driver+scraper+export)
_setup_path.py ── không được file nào import (dead code)
```

## Bảng inventory

| File | Dòng | Vai trò | Phán quyết |
|---|---|---|---|
| `app.py` | 12 | FastAPI app, mount router | SỬA (thêm lifespan, exception handler, mount /products) |
| `api/comments.py` | 139 | 5 endpoint CRUD, luôn trả HTTP 200 | THAY bằng `api/products.py` |
| `services/comment_service.py` | 39 | passthrough repo + `_to_out` map `_id`→`id` | SỬA → `product_service.py` |
| `services/scraper_service.py` | 137 | crawl; **tạo Chrome mới + install() mỗi sản phẩm**; leak driver ở `return None` (L115) | SỬA nặng |
| `repositories/comment_repository.py` | 130 | 7 method; **4 method đọc sai schema** | SỬA → `product_repository.py` |
| `config/database.py` | 87 | Mongo client + **URI hardcode L12** | SỬA |
| `config/driver.py` | 72 | singleton global driver, `_fix_chromedriver_permissions` (dead, đã comment) | VIẾT LẠI (thread-local) |
| `config/version.py` | 5 | `version = "..."` gắn vào doc | GIỮ |
| `models/product.py` | 23 | TypedDict Product/Comment | SỬA (xem lệch bên dưới) |
| `dto/base.py` | 17 | `BaseResponse[T]` generic | GIỮ (bỏ import `inspect`,`os`) |
| `dto/comment.py` | 54 | DTO pydantic | THAY → `dto/product.py` |
| `utils/helpers.py` | 17 | `go_back` | GIỮ / gộp |
| `main.py` | 226 | crawler + export_to_excel; link hardcode; `__main__` gọi export chứ không gọi main() | VIẾT LẠI (argparse) |
| `final.py` | 389 | bản standalone no-DB, trùng ~90% logic | **XOÁ** |
| `run.py` | 90 | dev-loop giữ driver + reload module | SỬA (xem rủi ro) |
| `_setup_path.py` | 10 | chèn src vào sys.path, không ai import | **XOÁ** |

## 3 lệch schema đã xác nhận (nguồn gốc mọi bug API)

DB thực tế ghi bởi `scraper_service.save_comments` (`scraper_service.py:124-130`):
```python
{ "name":…, "link":…, "comments":[{name,content,rating,id}], "total_comments":int, "crawled_at":datetime, "version":str }
```

1. `comment_repository.find_all()` / `find_comment_by_id()` (L43-107) đọc `product_link`, `product_name`, `content`, `rating` **ở cấp document** → luôn trả `None`. `GET /comments/` hiện trả list toàn null.
2. `find_comment_by_id`/`update_comment`/`delete_comment` dùng `ObjectId(comment_id)` khớp `_id` của **product**, không phải comment trong mảng → API "sửa comment" thực chất ghi đè field cấp product.
3. `models/product.py` `Comment` khai `{content,name,rating,date}` — **thiếu `id`**, **thừa `date`**. Nhưng runtime `get_content()` (`scraper_service.py:37-42`) luôn ghi `id=str(ObjectId())` và không ghi `date` → **dữ liệu Atlas đã có sẵn `id` cho mọi comment, KHÔNG cần migrate**, chỉ cần sửa lại model. (Cần verify bằng 1 query trước khi code.)

## Lỗi cụ thể còn lại (file:dòng)

| # | Vị trí | Lỗi |
|---|---|---|
| 1 | `config/database.py:12` | Mongo URI + password hardcode, đã commit → **lộ trong git history, phải rotate** |
| 2 | `scraper_service.py:115` | `return None` không `driver.quit()` → leak Chrome; cả hàm không có try/finally |
| 3 | `scraper_service.py:62-63` | `ChromeDriverManager().install()` gọi lại **mỗi sản phẩm** |
| 4 | `main.py:57` vs `main.py:85` | cùng tên biến `link` → vòng lặp ngoài bị ghi đè, link thứ 2 crawl sai trang |
| 5 | `main.py:61,63` | `for i in range(15)` lồng `for i in range(20)` cùng tên `i` |
| 6 | `main.py:224-226` | `__main__` gọi `export_to_excel`, `main()` bị comment |
| 7 | `scraper_service.py:40` | `rating` = `""` khi 0 sao, model khai `int` |
| 8 | `api/comments.py` | `HTTPException` import không dùng; mọi lỗi trả HTTP 200 + `success:false` |
| 9 | `database.py:37,51` | ping Atlas mỗi lần `get_mongo_client()` → tốn 1 round-trip/request |
| 10 | toàn bộ | `print` thay vì `logging`; `time.sleep` cố định (2s×20 lần view-more = tới 40s/trang) |
| 11 | import thừa | `main.py`: os, dumps, bson_dumps, load_workbook, get_collection, get_database, Product · `database.py`: ssl, Optional · `dto/base.py`: inspect, os · `scraper_service.py`: dumps, get_driver |

## Root files

- `requirements.txt`: thiếu `certifi` (code đã import!), `python-dotenv`/`pydantic-settings`, `openpyxl` không xuống dòng cuối. `pymongo` nên → `pymongo[srv]` (URI dùng `mongodb+srv://`).
- `run.bat` → `python src\main.py` · `run_dev.bat` → `python src\run.py` · `setup.bat` (tạo venv + pip install). Cần cập nhật help text sau khi thêm CLI args.
- `.env` chỉ có `PYTHONPATH=./src`, đã gitignore. `.gitignore` đã chặn `excel_comment/`, `excel_comment2/`, `*.xlsx` — **nhưng `excel_comment3/` và `excel_comment21/` chưa bị chặn**.
- Không có test nào. Không có `docs/`. Không có linter config ngoài `pyrightconfig.json`.
- `text.json` (5KB, gitignored), 4 thư mục excel output ~600 file.

## Unresolved questions

- Có document nào trong Atlas thiếu field `comments[].id` không? (query `{"comments.id": {"$exists": false}}` trước khi khoá thiết kế API).
- `config/version.py` version bump thủ công qua `run.py` — còn dùng thật không?
- `excel_comment21/`, `excel_comment3/` có nên add vào .gitignore / xoá?
