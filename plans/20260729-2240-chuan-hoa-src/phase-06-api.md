# Phase 06 — API `/products`: DTO, HTTPException, lifespan

## Context links
- [plan.md](./plan.md) · [phase-03-data-layer.md](./phase-03-data-layer.md)
- [researcher-02-fastapi-mongo.md](./research/researcher-02-fastapi-mongo.md) §1,2,3,5,6
- Scout: 3 lệch schema, bug #8, #9

## Overview
- Date: 2026-07-29
- Description: Thay router `/comments` (đang trả toàn `null`) bằng `/products` + nested comment
  CRUD, trả đúng HTTP status qua `HTTPException` nhưng giữ nguyên envelope `{data,success,message}`.
- Priority: P1
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- API cũ trả HTTP 200 cho mọi lỗi kể cả not-found → client không phân biệt được. Sửa bằng
  `raise HTTPException` + global handler render lại envelope cũ ⇒ **shape response không đổi**,
  chỉ status code đổi. Breaking change chấp nhận được vì dữ liệu cũ vốn là `null`.
- pymongo là **blocking** → route định nghĩa bằng `def`, KHÔNG `async def` (nếu không sẽ chặn
  event loop).
- `service = CommentService()` ở module level (`api/comments.py:15`) tạo Mongo client lúc import →
  import module là kết nối DB, test không cô lập được. Chuyển sang `Depends(get_product_service)`.
- `rating` cũ có thể là `""` → DTO dùng `BeforeValidator` ép về `int` (0).

## Requirements
1. Endpoints:
   - `GET /products?page=&limit=&q=` → list, KHÔNG kèm mảng comments, có `total_comments`.
   - `GET /products/{product_id}?comment_page=&comment_limit=` → detail + comments phân trang.
   - `POST /products/{product_id}/comments` → 201, trả `comment_id`.
   - `PATCH /products/{product_id}/comments/{comment_id}` → 200.
   - `DELETE /products/{product_id}/comments/{comment_id}` → 200.
   - `DELETE /products/{product_id}` → 200.
2. Status map: 400 ObjectId sai / payload rỗng · 404 product|comment không có · 409 trùng id ·
   422 validation body · 500 còn lại.
3. Envelope `{data, success, message}` giữ nguyên ở MỌI response, kể cả lỗi.
4. Lifespan mở/đóng Mongo client, ping 1 lần, `ensure_indexes()`.

## Architecture
```
app.py
  lifespan: setup_logging -> get_client() ping -> ensure_indexes -> yield -> close_client()
  exception_handler(StarletteHTTPException | RequestValidationError | Exception)
  include_router(products.router)

api/products.py       router = APIRouter(prefix="/products", tags=["products"])
  get_service() -> ProductService                       # Depends
services/product_service.py
  class ProductService:
      def __init__(self, repository)
      list_products(page, limit, q) -> tuple[list[ProductSummary], int]
      get_product(pid, comment_page, comment_limit) -> ProductDetail
      add_comment(pid, payload) -> str
      update_comment(pid, cid, payload) -> None         # raise NotFoundError
      delete_comment(pid, cid) -> None
      delete_product(pid) -> None
dto/product.py
  ProductSummary, ProductDetail, CommentOut, CommentCreate, CommentUpdate,
  PaginatedProducts(items, total, page, limit)
  ProductListResponse / ProductDetailResponse / ... (kế thừa BaseResponse[T])
```
Service ném exception domain (`NotFoundError`, `InvalidIdError`, `DuplicateError` — định nghĩa trong
`services/errors.py`), router map sang `HTTPException`. Repository không biết HTTP.

## Related code files
- SỬA: `src/app.py` (12 → ~55 dòng), `src/dto/base.py`
- THÊM: `src/api/products.py`, `src/services/product_service.py`, `src/services/errors.py`,
  `src/dto/product.py`, `tests/test_api_products.py`
- XOÁ: `src/api/comments.py`, `src/dto/comment.py`, `src/services/comment_service.py`

## Implementation Steps
1. `services/errors.py`: `class AppError(Exception)`, `NotFoundError`, `InvalidIdError`,
   `DuplicateError`, `EmptyPayloadError` — mỗi cái có `message` tiếng Việt.
2. `dto/product.py`:
   ```python
   PyObjectId = Annotated[str, BeforeValidator(str)]
   RatingInt  = Annotated[int, BeforeValidator(lambda v: int(v) if str(v).strip().isdigit() else 0)]
   class CommentOut(BaseModel):  id: str; name: str = ""; content: str = ""; rating: RatingInt = 0
   class ProductSummary(BaseModel):
       model_config = ConfigDict(populate_by_name=True)
       id: PyObjectId = Field(alias="_id"); name: str = ""; link: str = ""
       total_comments: int = 0; crawled_at: datetime | None = None; version: str | None = None
   class ProductDetail(ProductSummary): comments: list[CommentOut] = []
   class PaginatedProducts(BaseModel): items: list[ProductSummary]; total: int; page: int; limit: int
   ```
   `CommentCreate(name, content, rating: int = Field(0, ge=0, le=5))`,
   `CommentUpdate` các field `Optional` + validator "ít nhất 1 field".
3. `dto/base.py`: giữ `BaseResponse[T]`; bỏ import `inspect`, `os`; giữ hay bỏ field `position`?
   → **bỏ** (không ai set, chỉ là rác debug). Nếu FE đang đọc, giữ lại default `None`.
4. `api/products.py`: mọi route là `def` (sync). `limit: int = Query(20, ge=1, le=100)`,
   `page: int = Query(1, ge=1)`. Không `try/except` trong route (researcher-02 §3) — để handler lo.
   Map lỗi bằng 1 dependency/decorator nhỏ hoặc `except AppError` trong `product_service` → router
   dịch: đơn giản nhất là 1 global handler cho `AppError`:
   ```python
   @app.exception_handler(AppError)
   def app_error_handler(request, exc: AppError):
       return JSONResponse(exc.status_code, {"data": None, "success": False, "message": exc.message})
   ```
   (mỗi subclass khai `status_code = 404/400/409`) → router sạch hoàn toàn.
5. `app.py`: `lifespan` theo researcher-02 §5 nhưng dùng `get_client()` từ `database.py` (đã
   `lru_cache`) thay vì `app.state` riêng — 1 nguồn client cho cả CLI lẫn API. Đăng ký handler cho
   `starlette.exceptions.HTTPException` (bắt cả 404 route), `RequestValidationError`, `AppError`,
   `Exception`. Giữ `GET /` nhưng sửa `{"status": "ook"}` → `{"status": "ok"}`.
6. Tests (`tests/test_api_products.py`): `TestClient` + override dependency `get_service` bằng
   ProductService gắn mongomock collection. Assert: list không có key `comments`;
   `GET /products/{id}` với id rác → 400 + `success=false`; comment không tồn tại → 404;
   DELETE comment → `total_comments` giảm 1.

## Todo list
- [x] services/errors.py
- [x] dto/product.py (+ dọn dto/base.py)
- [x] services/product_service.py
- [x] api/products.py (routes `def`, Depends)
- [x] app.py lifespan + 4 exception handler
- [x] Xoá api/comments.py, dto/comment.py, services/comment_service.py
- [x] tests/test_api_products.py

## Success Criteria
- `uvicorn src.app:app --reload` khởi động, log "Đã kết nối MongoDB (db=selenium_scraper)" 1 lần.
- `curl -s "localhost:8000/products?limit=2" | python -m json.tool` → 200,
  `data.items[0]` có `total_comments`, KHÔNG có `comments`.
- `curl -i localhost:8000/products/xxx` → **400** + body `{"data":null,"success":false,...}`.
- `curl -i localhost:8000/products/000000000000000000000000` → **404**.
- `curl -i -X DELETE localhost:8000/products/<pid>/comments/<cid>` → 200, gọi lại → 404,
  `total_comments` giảm đúng 1.
- `python -m pytest tests/ -q` → pass.
- `grep -rn "CommentService\|api.comments" src/` → rỗng.

## Risk Assessment
- **Breaking API**: `/comments/*` biến mất. Chấp nhận — endpoint cũ trả `null` toàn bộ, không thể
  đang có client thật dùng. Nếu cần, thêm 410 Gone stub (không khuyến nghị, YAGNI).
- **`rating` lẫn `""`** trong dữ liệu cũ → `RatingInt` coerce; nếu gặp giá trị lạ khác → 0, log
  WARNING. Không migrate.
- **`estimated_document_count` không khớp filter** → chỉ dùng khi `q` rỗng (đã xử ở P3).
- **Không có auth**: POST/PATCH/DELETE mở toang. Chưa nằm trong scope; ghi vào câu hỏi mở.

## Security Considerations
- Không auth trên write endpoints → **không deploy public** cho tới khi thêm API key/JWT.
  Khuyến nghị tối thiểu: `X-API-Key` so với `settings.api_key` nếu có giá trị.
- Handler `Exception` không được lộ stack trace ra client — chỉ `logger.exception` + message chung
  "Lỗi hệ thống" (repo cũ trả nguyên `traceback.format_exc()` ra API response — lộ path & schema).
- `q` escape regex (P3), `limit` clamp ≤100 chống DoS.
- CORS chưa cấu hình — nếu FE khác origin, thêm `CORSMiddleware` với allowlist, không `*`.

## Next steps
→ Chạy verify toàn cục ở `plan.md`; cập nhật README; xét thêm auth + CORS ở plan sau.
