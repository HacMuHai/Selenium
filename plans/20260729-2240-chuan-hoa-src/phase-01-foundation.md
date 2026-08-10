# Phase 01 — Nền tảng: settings, logging, dependencies, dọn dead code

## Context links
- [plan.md](./plan.md)
- [scout-01-codebase-inventory.md](./scout/scout-01-codebase-inventory.md) (bug #1, #11; root files)
- [researcher-02-fastapi-mongo.md](./research/researcher-02-fastapi-mongo.md) §4

## Overview
- Date: 2026-07-29
- Description: Dựng nền chung cho cả 3 entrypoint: config typed qua pydantic-settings + `.env`,
  logging tập trung, requirements đúng, xoá 3 file chết, chuẩn hoá import `src.` toàn repo.
- Priority: P0 (chặn mọi phase khác)
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- Import hiện tại là top-level (`from config.database import ...`) → chỉ chạy khi `src` nằm trong
  `sys.path`. Đó là lý do tồn tại `_setup_path.py`, `.env PYTHONPATH=./src`, `.vscode cwd=src`.
  Đổi sang `src.` prefix xoá cả 3 workaround cùng lúc. Trade-off: `python src/main.py` hết chạy,
  phải dùng `python -m src.main` (sửa `.bat` ở P5).
- `certifi` đang được import nhưng KHÔNG có trong requirements.txt → cài mới là gãy ngay.
- `.env` hiện chỉ có `PYTHONPATH=./src`; sau phase này nó chứa `MONGO_URI` → đã gitignore sẵn.

## Requirements
1. `src/config/settings.py` với `Settings(BaseSettings)` + `get_settings()` cache.
2. `.env.example` commit; `.env` local có `MONGO_URI` thật; README ghi cảnh báo rotate password.
3. `src/config/logging_config.py` — `setup_logging(level)` gọi 1 lần ở entrypoint.
4. `requirements.txt` đúng và đủ.
5. Xoá `src/final.py`, `src/_setup_path.py`, `src/run.py`.
6. Mọi import nội bộ dùng prefix `src.`; bỏ hết import thừa (scout #11).
7. `.gitignore` chặn `excel_*/`.

## Architecture
`settings.py` là nguồn config DUY NHẤT. `database.py`/`driver.py`/`main.py`/`app.py` đọc qua
`get_settings()`, không `os.getenv` rải rác. `logging_config.setup_logging()` chỉ gọi tại
`main.py::main()` và `app.py` lifespan — thư viện/service chỉ `logger = logging.getLogger(__name__)`.

## Related code files
- THÊM: `src/config/settings.py`, `src/config/logging_config.py`, `.env.example`
- SỬA: `.env`, `.gitignore`, `requirements.txt`, `README.md`, `SETUP_WINDOWS.md`,
  `.vscode/launch.json`, `.vscode/settings.json`, `pyrightconfig.json`, `src/dto/base.py`
- XOÁ: `src/final.py` (389 dòng), `src/_setup_path.py` (10), `src/run.py` (90)
- Đụng chạm import: mọi file trong `src/`

## Implementation Steps
1. `src/config/settings.py`:
   ```python
   class Settings(BaseSettings):
       model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
       mongo_uri: str
       mongo_db: str = "selenium_scraper"
       mongo_collection: str = "comments"      # GIỮ tên cũ, không migrate
       log_level: str = "INFO"
       headless: bool = True
       max_workers: int = 3
       wait_timeout: float = 15.0
       export_dir: str = "excel_comment"
   @lru_cache
   def get_settings() -> Settings: ...
   ```
2. `.env.example` (commit):
   `MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Cluster0`
   + `MONGO_DB=selenium_scraper`, `LOG_LEVEL=INFO`, `HEADLESS=true`, `MAX_WORKERS=3`.
   `.env` local: chuyển URI thật vào, XOÁ dòng `PYTHONPATH=./src`.
3. `src/config/logging_config.py`:
   ```python
   def setup_logging(level: str = "INFO") -> None:
       logging.basicConfig(level=level.upper(),
           format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s")
       logging.getLogger("selenium").setLevel(logging.WARNING)
       logging.getLogger("urllib3").setLevel(logging.WARNING)
       logging.getLogger("pymongo").setLevel(logging.WARNING)
   ```
4. `requirements.txt` (thay toàn bộ, có newline cuối):
   `selenium>=4.15` · `pymongo[srv]>=4.9` · `certifi` · `fastapi` · `uvicorn[standard]` ·
   `pydantic>=2` · `pydantic-settings>=2` · `openpyxl` · `pytest` · `mongomock` · `httpx`
   → BỎ `webdriver-manager` (P2 giải thích).
5. `git rm src/final.py src/_setup_path.py src/run.py`.
6. Đổi import toàn bộ: `from config.` → `from src.config.`, tương tự `services/repositories/
   models/dto/utils/api`. Kiểm: `grep -rnE "^from (config|services|repositories|models|dto|utils|api)\." src/`
   phải rỗng.
7. Xoá import thừa: `dto/base.py` (`inspect`, `os`), `config/database.py` (`ssl`, `Optional`),
   `main.py` (`os`, `dumps`, `bson_dumps`, `load_workbook`, `get_collection`, `get_database`,
   `Product`), `scraper_service.py` (`dumps`, `get_driver`), `api/comments.py` (`HTTPException`
   — file này bị xoá ở P6 nên bỏ qua).
8. `.gitignore`: thay 3 dòng `excel_comment/ excel_comment2/ excel_tag/` bằng `excel_*/`;
   sửa dòng `!requirements.xlsx  # Uncomment...` (comment inline trong gitignore là SAI cú pháp,
   pattern thành `!requirements.xlsx  # Uncomment...`) → xoá dòng đó.
9. `.vscode/launch.json`: bỏ `"cwd": "${workspaceFolder}/src"`, args `"src.app:app"`.
   `.vscode/settings.json`: bỏ `python.analysis.extraPaths`.
10. README: thêm section "Cấu hình" + **cảnh báo ROTATE password Atlas** (đã lộ trong git history
    từ commit `874fb1d`; xoá file không xoá history — phải đổi password trên Atlas UI).

## Todo list
- [x] settings.py + .env.example + cập nhật .env
- [x] logging_config.py
- [x] requirements.txt
- [x] Xoá final.py / _setup_path.py / run.py
- [x] Đổi toàn bộ import sang `src.`
- [x] Dọn import thừa
- [x] .gitignore, .vscode, README (mục rotate password)

## Success Criteria
- `pip install -r requirements.txt` sạch trong venv mới.
- `python -m compileall src` → 0 lỗi.
- `python -c "from src.config.settings import get_settings; print(get_settings().mongo_db)"`
  → `selenium_scraper` (chạy từ repo root, KHÔNG set PYTHONPATH).
- `grep -rn "webdriver_manager\|_setup_path\|final.py" src/` → rỗng (sau P2).
- `git status` không còn `.xlsx` untracked.

## Risk Assessment
- **Đổi import hàng loạt sót chỗ** → medium. Giảm bằng `compileall` + grep pattern ở bước 6.
- **Xoá `run.py` khi user vẫn dùng** → xem P5 (có phương án thay thế); nếu user phản đối, revert
  chỉ 1 file, không ảnh hưởng phase khác.
- **`pydantic-settings` chưa cài** → `Settings()` ném `ValidationError` nếu thiếu `MONGO_URI`;
  đó là hành vi mong muốn (fail fast), nhưng phải cài trước khi test.

## Security Considerations
- Secret rời code sang `.env` (đã gitignore). `.env.example` chỉ chứa placeholder.
- **BẮT BUỘC**: rotate password Atlas user `selenium_db`; cân nhắc bật IP allowlist.
- Không log `mongo_uri` (bug hiện tại: `database.py:41` in cả URI kèm password ra stdout) — cấm.

## Next steps
→ Phase 02 (driver layer), Phase 03 (data layer) — chạy song song được.
