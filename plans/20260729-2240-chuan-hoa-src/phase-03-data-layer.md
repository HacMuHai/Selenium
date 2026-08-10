# Phase 03 — Data layer: models, ProductRepository, database, index

## Context links
- [plan.md](./plan.md) · [phase-01-foundation.md](./phase-01-foundation.md)
- [researcher-02-fastapi-mongo.md](./research/researcher-02-fastapi-mongo.md) §1,2,5
- Scout: 3 lệch schema; bugs #1, #7, #9

## Overview
- Date: 2026-07-29
- Description: Sửa model cho khớp dữ liệu thật, thay `CommentRepository` bằng `ProductRepository`
  đúng schema (nested-array CRUD), bỏ ping mỗi call, tạo index.
- Priority: P0
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- Schema thật (do `scraper_service.save_comments` ghi):
  `{_id, name, link, comments:[{name, content, rating, id}], total_comments, crawled_at, version}`.
- `models/product.py::Comment` thiếu `id`, thừa `date` → sửa MODEL, không sửa DB.
- 4 method repo cũ đọc `product_link/product_name/content/rating` ở **cấp document** → luôn `None`.
  Đó là gốc của mọi bug API.
- `_is_connection_alive()` ping mỗi `get_mongo_client()` = 1 round-trip/request, vô ích —
  pymongo có topology monitor riêng. Ping đúng 1 lần lúc startup.
- `rating` = `""` khi 0 sao (`scraper_service.py:40`) → dữ liệu cũ có thể lẫn `""`. Chuẩn hoá tại
  BIÊN ĐỌC (DTO coerce `"" -> 0`) chứ không migrate DB.

## Requirements
1. `Comment` TypedDict: `{id: str, name: str, content: str, rating: int}`.
2. `ProductRepository` với API đúng schema (danh sách bên dưới).
3. `database.py` bỏ ping-mỗi-call, đọc URI từ `Settings`, giữ `tlsCAFile=certifi.where()`.
4. `ensure_indexes()`: `comments.id` (multikey), `link` unique.
5. Test tối thiểu với `mongomock`.

## Architecture
```
config/database.py
  get_client() -> MongoClient          # 1 instance/process, lru_cache
  get_db() / get_collection(name=None)
  ensure_indexes(col) -> None
  close_client() -> None

repositories/product_repository.py
  class ProductRepository:
      def __init__(self, collection=None)                       # inject được -> test
      # crawler
      def exists_by_link(link: str) -> bool
      def insert_product(product: Product) -> str
      # API - product
      def list_products(page:int, limit:int, q:str|None) -> tuple[list[dict], int]
      def get_product(product_id: str) -> dict | None
      def get_product_with_comment_page(product_id, skip, limit) -> dict | None
      def delete_product(product_id: str) -> bool
      # API - nested comment
      def add_comment(product_id: str, comment: Comment) -> str        # $push + $inc
      def update_comment(product_id, comment_id, data: dict) -> bool   # $ positional
      def delete_comment(product_id, comment_id) -> bool               # $pull + $inc
      # export
      def iter_products(projection=None) -> Iterator[dict]
      def count_products() -> int
```
Không `try/except` + `raise Exception(str)` bọc mọi method như repo cũ — nuốt stack trace và
biến `PyMongoError` thành `Exception` chung khiến API không map được status. Để exception gốc bay lên.

## Related code files
- SỬA: `src/models/product.py`, `src/config/database.py`
- THÊM: `src/repositories/product_repository.py`, `tests/conftest.py`,
  `tests/test_product_repository.py`
- XOÁ: `src/repositories/comment_repository.py`, `src/services/comment_service.py` (P6 thay)

## Implementation Steps
0. **VERIFY DỮ LIỆU TRƯỚC KHI CODE** (bắt buộc, chạy 1 lần, kết quả ghi vào plan):
   ```bash
   python - <<'PY'
   import certifi, os
   from pymongo import MongoClient
   from dotenv import load_dotenv; load_dotenv()
   col = MongoClient(os.environ["MONGO_URI"], tlsCAFile=certifi.where())["selenium_scraper"]["comments"]
   print("total products      :", col.count_documents({}))
   print("comment thiếu id    :", col.count_documents({"comments": {"$elemMatch": {"id": {"$exists": False}}}}))
   print("rating rỗng         :", col.count_documents({"comments.rating": ""}))
   print("total_comments thiếu:", col.count_documents({"total_comments": {"$exists": False}}))
   PY
   ```
   Nếu "comment thiếu id" > 0 → PHẢI thêm 1 bước backfill (`$set` uuid qua pipeline update) trước
   khi khoá API. Nếu = 0 (kỳ vọng) → tiếp tục như plan.
1. `models/product.py`: `Comment = {id, name, content, rating:int}`; `Product` giữ nguyên,
   `total: NotRequired` không cần. Bỏ import `datetime` thừa nếu không dùng.
2. `database.py` viết lại (~45 dòng): bỏ `_get_storage()` sys.modules hack (chỉ tồn tại để sống sót
   `importlib.reload` của `run.py` — mà `run.py` bị xoá), dùng `@lru_cache def get_client()`.
   Ping 1 lần trong `get_client()` (fail fast), KHÔNG ping trong `get_collection`. Log
   "Đã kết nối MongoDB (db=%s)" — **không log URI**.
3. `ensure_indexes(col)`: `create_index([("comments.id",1)])`,
   `create_index([("link",1)], unique=True)`.
   *Rủi ro*: nếu DB đang có link trùng, unique index tạo fail → bọc try/except, log warning,
   không chặn startup; ghi vào "Câu hỏi chưa giải quyết".
4. `list_products` dùng aggregation theo researcher-02 §2:
   `$match` (regex `name` khi có `q`) → `$sort {_id:-1}` → `$skip` → `$limit` →
   `$project {name,link,crawled_at,version,total_comments}` (KHÔNG project `comments`).
   `total` = `count_documents(filter)` khi có `q`, `estimated_document_count()` khi không.
5. `update_comment`: filter `{"_id":oid, "comments.id":cid}`, `$set` dotted `comments.$.{k}`.
   Trả `matched_count > 0` (KHÔNG `modified_count` — set giá trị y hệt sẽ trả 0 → 404 sai).
6. `delete_comment`: `{"$pull": {"comments": {"id": cid}}, "$inc": {"total_comments": -1}}`
   với filter chứa `"comments.id": cid` (chặn `total_comments` âm).
7. `add_comment`: sinh `id = str(ObjectId())`, filter `{"_id":oid, "comments.id": {"$ne": id}}`,
   `$push` + `$inc: +1`. Trả id.
8. Helper module-level `def to_object_id(value: str) -> ObjectId` raise `ValueError` khi sai định
   dạng → API map 400 (P6).
9. Tests (`mongomock`): fixture collection in-memory nạp 2 product mẫu; assert
   `list_products` không trả field `comments`; `update_comment` sửa đúng phần tử;
   `delete_comment` giảm `total_comments` đúng 1 và không âm khi gọi lại.

## Todo list
- [ ] **CHƯA LÀM ĐƯỢC** — Chạy query verify Atlas (bước 0). Cluster
  `cluster0.1cqkft2.mongodb.net` trả NXDOMAIN (kiểm bằng DNS-over-HTTPS tới authoritative
  của AWS) → cluster không còn tồn tại. Code viết theo schema suy ra từ `scraper_service`
  cũ, test bằng mongomock. **Phải chạy lại query này khi có cluster sống**; nếu
  "comment thiếu id" > 0 thì cần backfill trước khi dùng API sửa/xoá comment.
- [x] models/product.py
- [x] database.py (lru_cache client, bỏ ping/call, không log URI)
- [x] ensure_indexes
- [x] product_repository.py đủ 11 method
- [x] tests/test_product_repository.py (mongomock)
- [x] Xoá comment_repository.py + comment_service.py

## Success Criteria
- Query bước 0 chạy được, "comment thiếu id" = 0.
- `python -m pytest tests/test_product_repository.py -q` → pass.
- `python -c "from src.repositories.product_repository import ProductRepository as R; r=R(); print(r.count_products()); print(r.list_products(1,2,None)[0][0].keys())"`
  → keys KHÔNG chứa `comments`.
- `grep -rn "comment_repository\|CommentRepository" src/` → rỗng.

## Risk Assessment
- **Unique index trên `link` fail** nếu có duplicate trong Atlas → xử lý bằng warning, không crash.
- **`$pull` xoá mọi phần tử trùng id** → an toàn vì id là ObjectId hex duy nhất, nhưng nếu bước 0
  phát hiện thiếu id thì giả định này gãy.
- **Đổi tên repo class** làm gãy `main.py`/`scraper_service.py` tạm thời cho tới P4 — chấp nhận,
  P3 và P4 merge cùng branch.
- **estimated_document_count()** có thể lệch nhẹ khi đang crawl — chấp nhận cho admin UI.

## Security Considerations
- Không log connection string / password (bug hiện tại `database.py:41`).
- `q` đưa vào `$regex` → escape bằng `re.escape()` để tránh ReDoS/regex injection.
- `to_object_id` validate trước khi query → tránh `bson.errors.InvalidId` thành 500.

## Next steps
→ Phase 04 (scraper dùng repository mới), Phase 06 (API dùng repository mới).
