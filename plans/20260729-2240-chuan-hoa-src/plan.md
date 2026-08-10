# Plan: Chuẩn hoá `src/` — 1 codebase, 3 entrypoint

Date: 2026-07-29 · Repo: /Volumes/hacmuhai2/Toan/Selenium · Status: **DONE (6/6)** — thực thi 2026-07-31

## Mục tiêu
Một codebase phục vụ: (a) BE FastAPI `src.app:app`, (b) crawler CLI `python -m src.main`,
(c) dev loop. Không trùng logic. Giữ nguyên schema Atlas (1 doc = 1 product + mảng comments),
KHÔNG migrate dữ liệu.

## Quyết định đã khoá
- Import tuyệt đối prefix `src.` cho toàn bộ code → bỏ `PYTHONPATH` hack, `uvicorn src.app:app`
  và `python -m src.main` chạy từ repo root. Kéo theo: `.bat` đổi sang `python -m src.main`.
- `final.py` XOÁ → thay bằng `--no-db`, dùng chung `ScraperService` qua **repository injection**
  (`InMemoryProductRepository` null-object), không copy logic.
- `run.py` XOÁ (importlib.reload quá dễ vỡ, xem P5). Thay bằng `--attach` vào Chrome
  remote-debugging → giữ browser ấm mà không reload module.
- `_setup_path.py` XOÁ (không file nào import).
- Bỏ `webdriver-manager`, dùng Selenium Manager built-in (selenium>=4.15, đang có 4.38).
- API reshape sang `/products`; router `/comments` cũ XOÁ (đang trả toàn `null`, không ai dùng được).

## Cây `src/` sau refactor
    src/app.py  main.py
    src/api/products.py
    src/config/{settings,logging_config,database,driver,targets,version}.py
    src/dto/{base,product}.py
    src/models/product.py
    src/repositories/product_repository.py
    src/services/{scraper_service,product_service,export_service}.py
    src/utils/helpers.py
    tests/{conftest,test_product_repository,test_export_service,test_api_products}.py
XOÁ: `src/final.py` `src/run.py` `src/_setup_path.py` `src/api/comments.py` `src/dto/comment.py`
`src/repositories/comment_repository.py` `src/services/comment_service.py`

## Phases
| # | Phase | File | Status | Progress | Depends |
|---|---|---|---|---|---|
| 1 | Nền tảng: settings/.env, logging, requirements, xoá dead code, chuẩn import | [phase-01-foundation.md](./phase-01-foundation.md) | DONE | 100% | — |
| 2 | Driver layer: thread-local + WebDriverWait + options + teardown | [phase-02-driver-layer.md](./phase-02-driver-layer.md) | DONE | 100% | P1 |
| 3 | Data layer: models + product_repository + database + index | [phase-03-data-layer.md](./phase-03-data-layer.md) | DONE | 100% | P1 |
| 4 | Scraper + export service + chế độ no-db | [phase-04-scraper-export.md](./phase-04-scraper-export.md) | DONE | 100% | P2, P3 |
| 5 | CLI `main.py` (argparse + targets.py) + `.bat` + gỡ `run.py` | [phase-05-cli.md](./phase-05-cli.md) | DONE | 100% | P4 |
| 6 | API `/products` + DTO + exception handler + lifespan | [phase-06-api.md](./phase-06-api.md) | DONE | 100% | P3 |

## Verify toàn cục (sau P6)
    python -m compileall src
    python -m pytest -q
    uvicorn src.app:app --reload   # curl /products?limit=1 -> 200; /products/deadbeef -> 400/404
    python -m src.main --links https://www.thegioididong.com/sac-cap --limit 1 --no-db --export

## Rủi ro xuyên suốt
- **Selector TGDĐ đổi bất cứ lúc nào** → mọi test crawl phải là smoke-test thủ công, không CI.
- **ZERO test hiện tại** → refactor mù. P3/P4/P6 mỗi phase kèm 1–2 test tối thiểu (mongomock).
- **Dữ liệu Atlas** số lượng chưa rõ (`count_documents` ở P3 bước 0). Không migrate, chỉ đọc.
- **`.bat` là Windows, dev đang macOS** → không test được tại chỗ; chỉ sửa text, giữ tương thích.
- **Password Atlas đã lộ trong git history** (`config/database.py:12`, commit `874fb1d`+) →
  PHẢI rotate trên Atlas. Xoá file không xoá history.

## Kết quả verify (2026-07-31)
- `python -m compileall src tests` → OK.
- `python -m pytest -q` → **40 passed** (mongomock, không đụng Atlas).
- Driver thread-local: cùng thread trả cùng object, khác thread trả object khác;
  `quit_all()` xong `pgrep -f chromedriver` rỗng. ✅
- CLI end-to-end thật: `--links .../sac-cap --limit 1 --no-db --export`
  → 1 sản phẩm, **600 comment**, ghi 1 file `.xlsx` (421 dòng, 311 nội dung duy nhất —
  phần lặp đều là comment ngắn kiểu "Tốt"/"Ok", không phải lỗi phân trang). ✅
- `uvicorn src.app:app` → **KHÔNG lên được**: lifespan ping Mongo thất bại (cluster chết).
  Đây là fail-fast đúng thiết kế, nhưng ĐƯỜNG DẪN DỮ LIỆU THẬT CỦA API CHƯA ĐƯỢC VERIFY.
- Môi trường: venv cũ trỏ về `/Users/hacmuhai/Desktop/...` đã hỏng → dựng lại bằng
  Python 3.13.14 (cài qua `brew install python@3.13`).

## Câu hỏi chưa giải quyết
1. **CHẶN** — Cluster `cluster0.1cqkft2.mongodb.net` trả NXDOMAIN → không còn tồn tại.
   Cần URI Atlas sống để: (a) chạy query verify ở P3 bước 0, (b) verify API với dữ liệu thật,
   (c) xác nhận `ensure_indexes` tạo được unique index trên `link`.
2. Có doc nào thiếu `comments[].id` không? Chưa trả lời được (xem #1). Nếu > 0 thì
   `update_comment`/`delete_comment` sẽ không khớp phần tử → cần backfill uuid trước.
3. `total_comments` có khớp `len(comments)` không? Chưa trả lời được (xem #1).
4. API write (POST/PATCH/DELETE) vẫn **không auth** — chưa làm, ngoài scope plan này.
   Tối thiểu nên thêm `X-API-Key` so với `settings.api_key` trước khi deploy.
5. CORS chưa cấu hình — cần thêm `CORSMiddleware` với allowlist nếu FE khác origin.
6. `.bat` sửa text nhưng **chưa chạy thử** (dev đang macOS) — nhờ user verify trên Windows.
7. `excel_comment/`, `excel_comment3/`, `excel_comment21/`, `excel_tag/` vẫn còn trong repo,
   đã gitignore bằng `excel_*/`. Xoá hay giữ tuỳ user.
