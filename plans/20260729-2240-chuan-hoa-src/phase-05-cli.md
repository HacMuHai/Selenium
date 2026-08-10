# Phase 05 — CLI `main.py` (argparse + targets.py), gỡ `run.py`, cập nhật `.bat`

## Context links
- [plan.md](./plan.md) · [phase-04-scraper-export.md](./phase-04-scraper-export.md)
- Scout bugs #4, #5, #6; Root files (`run.bat`, `run_dev.bat`, `setup.bat`)

## Overview
- Date: 2026-07-29
- Description: `main.py` thành CLI argparse duy nhất (crawl / export / no-db), link ra
  `config/targets.py`, xoá `run.py` và thay bằng cơ chế attach Chrome debug.
- Priority: P1
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- `main.py:224-226`: `__main__` gọi `export_to_excel(...)` còn `main()` bị comment → chạy
  `python src/main.py` KHÔNG crawl. argparse xoá hẳn class bug này.
- **`run.py` có còn cần không? KHÔNG.** Lý do thẳng:
  1. `MODULE_PREFIXES` là danh sách chuỗi hardcode — P3/P4 đổi tên module (`comment_repository` →
     `product_repository`) là nó reload nhầm/thiếu, im lặng.
  2. `importlib.reload` KHÔNG cập nhật object đã instantiate: `ScraperService()` cũ vẫn giữ class
     repository cũ → sửa code mà không thấy hiệu lực, debug mất hàng giờ.
  3. Nó tồn tại chỉ để tránh khởi động lại Chrome. Sau P2, `webdriver.Chrome()` không còn
     `ChromeDriverManager().install()` → khởi động ~1–2s, không đáng đánh đổi.
  4. Nó cũng là lý do duy nhất tồn tại hack `_get_storage()` trong `database.py`.
  → **XOÁ**. Thay bằng: chạy Chrome thủ công với `--remote-debugging-port=9222` rồi
  `python -m src.main --attach 127.0.0.1:9222 ...`. Mỗi lần sửa code là 1 process Python mới
  (không reload gì cả) nhưng attach vào cùng browser đang mở → giữ đúng lợi ích, bỏ hết rủi ro.
  Nếu user không cần giữ browser: chạy thẳng `--limit 1 --no-db` là đủ nhanh.
- `--version-tag` thay chỗ của việc `run.py` bump `config/version.py`.

## Requirements
1. `src/config/targets.py`: dict `CATEGORIES: dict[str, list[str]]` + `DEFAULT_CATEGORY`.
2. Flags: `--links`, `--category`, `--no-db`, `--max-pages`, `--workers`, `--export`,
   `--headless/--no-headless`, `--limit`, (+ `--attach`, `--version-tag`, `--log-level`).
3. Mọi giá trị mặc định lấy từ `Settings`; CLI arg override.
4. `.bat` cập nhật sang `python -m src.main`; `run_dev.bat` không còn gọi `run.py`.

## Architecture
```
main.py
  build_parser() -> argparse.ArgumentParser
  resolve_links(args) -> list[str]        # --links > --category > DEFAULT_CATEGORY
  build_repository(no_db) -> repository   # ProductRepository | InMemoryProductRepository
  run_crawl(args, repo) -> None
  main(argv=None) -> int
  if __name__ == "__main__": sys.exit(main())
```
`main()` là hàm THẬT được gọi từ `__main__` (sửa bug #6).

## Related code files
- VIẾT LẠI: `src/main.py` (226 → ~120 dòng; phần export & thu link đã chuyển sang P4)
- THÊM: `src/config/targets.py`
- SỬA: `run.bat`, `run_dev.bat`, `setup.bat`, `README.md`, `SETUP_WINDOWS.md`
- XOÁ (đã làm ở P1): `src/run.py`

## Implementation Steps
1. `config/targets.py`:
   ```python
   CATEGORIES: dict[str, list[str]] = {
       "phu-kien": ["https://www.thegioididong.com/sac-cap",
                    "https://www.thegioididong.com/chuong-trinh-phu-kien-laptop"],
       "dong-ho": [...],          # bê từ block comment main.py:27-50, gom theo nhóm
       "dtdd": ["https://www.thegioididong.com/dtdd", ...],
   }
   DEFAULT_CATEGORY = "phu-kien"
   ```
   Toàn bộ link bị comment-out trong `main.py` chuyển vào đây thành entry thật; XOÁ hết comment.
2. `build_parser()` — mô tả `--help` phải nói rõ `--no-db` = không đọc & không ghi Mongo
   (nên sẽ crawl lại cả product đã có trong DB).
   ```
   --links URL [URL ...]        Ghi đè danh sách link (bỏ qua --category)
   --category NAME              Khoá trong targets.CATEGORIES (mặc định phu-kien)
   --no-db                      Không dùng Mongo: in kết quả + (tuỳ chọn) xuất Excel
   --max-pages N                Số trang danh mục tối đa (mặc định 15)
   --workers N                  Số thread crawl song song (mặc định settings.max_workers=3)
   --export [DIR]               Xuất Excel sau khi crawl (mặc định settings.export_dir)
   --export-only                Chỉ export từ DB, không crawl
   --limit N                    Chỉ crawl N sản phẩm đầu (smoke-test)
   --headless / --no-headless   (mặc định settings.headless)
   --attach HOST:PORT           Attach vào Chrome remote-debugging đang chạy
   --version-tag STR            Ghi đè config.version.version cho lần chạy này
   --log-level LEVEL
   ```
3. `run_crawl`: `setup_logging` → `repo = build_repository(args.no_db)` →
   `ensure_indexes()` (chỉ khi có DB) → `scraper = ScraperService(repo, headless=...)` →
   với mỗi category link: `driver = get_driver()`, `links = scraper.collect_product_links(...)` →
   `with ThreadPoolExecutor(max_workers=args.workers) as ex: results = list(ex.map(scraper.crawl_product, links))`
   → **`finally: quit_all()`** (bọc toàn bộ `run_crawl`).
4. Chế độ `--no-db`: sau crawl, log bảng tổng kết (số product, tổng comment, product 0 comment) và
   nếu `--export` thì `ExportService(repo, dir).export()` — repo ở đây là in-memory. Không có
   nhánh code riêng nào khác cho no-db.
5. `--attach`: `build_options()` nhận thêm `debugger_address` → khi có, bỏ qua headless/window-size.
   `quit_all()` với driver attach chỉ nên `close()` phiên, không giết browser của user → thêm cờ
   `_attached` để `quit_all()` bỏ qua. (Giữ đơn giản: log warning "driver attach — không quit".)
6. `.bat`:
   - `run.bat`: `python -m src.main --category phu-kien`
   - `run_dev.bat`: `python -m src.main --limit 2 --no-db --no-headless --log-level DEBUG`
     (đổi tiêu đề, bỏ dòng "Nhan Enter de reload code")
   - `setup.bat`: sửa help cuối file: `python -m src.main --help`, `uvicorn src.app:app --reload`;
     thêm nhắc "Sao chép .env.example thành .env rồi điền MONGO_URI".
7. README/SETUP_WINDOWS: bảng flags + ví dụ; ghi chú macOS dùng `source venv/bin/activate`.

## Todo list
- [x] config/targets.py (gom link, xoá comment-out)
- [x] build_parser + main() trả exit code
- [x] run_crawl với try/finally quit_all
- [x] Nhánh --no-db qua InMemoryProductRepository
- [x] --export / --export-only dùng ExportService
- [x] --attach
- [x] run.bat / run_dev.bat / setup.bat / README / SETUP_WINDOWS

## Success Criteria
- `python -m src.main --help` in đủ 11 flag.
- `python -m src.main --links https://www.thegioididong.com/sac-cap --limit 1 --no-db --export`
  → log ra ≥1 product + tạo file `.xlsx`, exit code 0, `pgrep -f chromedriver` rỗng.
- `python -m src.main --export-only --export excel_test` → chạy được không mở Chrome.
- `python -m src.main --limit 1` (có DB) → doc mới xuất hiện trong Atlas với đủ
  `comments[].id` + `total_comments`.
- `grep -rn "run.py\|_setup_path" . --include=*.bat --include=*.md --include=*.json` → rỗng.

## Risk Assessment
- **Xoá `run.py` là quyết định gây tranh cãi nhất trong plan** — nếu user phản đối, phương án tối
  thiểu: giữ `run.py` nhưng chỉ `subprocess.run([sys.executable,"-m","src.main",*argv])` trong
  vòng lặp `input()` (không `importlib.reload`), kết hợp `--attach`. Đơn giản, không dễ vỡ.
- **`.bat` không test được trên macOS** → chỉ sửa text, không đổi cấu trúc; nhờ user chạy thử.
- **`python -m src.main` khác `python src/main.py`** → user quen lệnh cũ sẽ gặp `ModuleNotFoundError`.
  Ghi rõ ở đầu README.
- **`--limit` chỉ cắt sau khi đã load trang danh mục** → smoke-test vẫn tốn ~10s, chấp nhận.

## Security Considerations
- `--attach` mở cổng debug 9222 trên localhost → không bind 0.0.0.0, ghi cảnh báo trong `--help`.
- CLI không nhận `MONGO_URI` qua argv (tránh lộ trong `ps`/shell history) — chỉ qua `.env`.

## Next steps
→ Phase 06: API.
