# Phase 02 — Driver layer: thread-local, Selenium Manager, WebDriverWait

## Context links
- [plan.md](./plan.md) · [phase-01-foundation.md](./phase-01-foundation.md)
- [researcher-01-selenium-concurrency.md](./research/researcher-01-selenium-concurrency.md) §1,2,3,4,6
- Scout bugs #2 (leak), #3 (install() mỗi sản phẩm), #10 (time.sleep)

## Overview
- Date: 2026-07-29
- Description: Viết lại `config/driver.py` thành thread-local pool + `quit_all()` + `atexit`,
  bỏ webdriver-manager, thêm helper wait/click trong `utils/helpers.py`.
- Priority: P0
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; chua co code review nguoi that

## Key Insights
- `scraper_service.py:62` tạo Chrome MỚI + `ChromeDriverManager().install()` cho **từng sản phẩm**
  → mỗi product tốn 1 round-trip mạng + 1 lần spawn Chrome. Với `max_workers=3` và vài trăm
  product, đây là chi phí lớn nhất của cả pipeline.
- `scraper_service.py:115` `return None` mà không `quit()` → mỗi lỗi để lại 1 chromedriver +
  1 Chrome zombie. try/finally là bắt buộc.
- `ThreadPoolExecutor` không có finalizer → phải `quit_all()` thủ công trong `finally` của caller.
- Selenium 4.38 đã cài sẵn → Selenium Manager có sẵn, `webdriver.Chrome(options=...)` là đủ.
  Trade-off khi bỏ webdriver-manager: mất khả năng pin version driver thủ công và cần mạng lần đầu
  để Selenium Manager tải về `~/.cache/selenium`. Đổi lại: hết lỗi macOS `Status code -9`
  (quarantine trên binary do Python tải), hết race khi nhiều thread ghi `~/.wdm`, bớt 1 dependency.
  → Chấp nhận bỏ.
- KHÔNG trộn implicit wait với explicit wait (`implicitly_wait(0)`).

## Requirements
1. `get_driver()` trả driver riêng cho từng thread, tạo lazy.
2. `quit_all()` đóng mọi driver đã tạo; đăng ký `atexit`.
3. Chrome options build từ `Settings` (headless bật/tắt, window-size, eager page load).
4. Helper `wait_for`, `click_safe`, `wait_count_grows`, `go_back` trong `utils/helpers.py`.
5. Không còn `time.sleep` cố định trong driver/helpers (chỉ backoff khi retry stale).

## Architecture
```
config/driver.py
  _tls = threading.local(); _drivers: list; _lock = Lock()
  build_options(headless: bool) -> ChromeOptions
  get_driver() -> WebDriver          # lazy, per-thread
  get_wait(driver, timeout=None) -> WebDriverWait
  quit_current()                     # đóng driver của thread hiện tại
  quit_all()                         # atexit + finally của CLI
```
Không còn `close_driver()` global singleton. `main.py` gọi `quit_all()` trong `finally`.
FastAPI KHÔNG đụng driver (BE chỉ đọc DB).

## Related code files
- VIẾT LẠI: `src/config/driver.py` (72 dòng → ~90)
- SỬA: `src/utils/helpers.py`
- Ảnh hưởng: `src/services/scraper_service.py` (P4), `src/main.py` (P5)

## Implementation Steps
1. `build_options(headless: bool) -> webdriver.ChromeOptions`:
   `--headless=new` (khi headless), `--disable-gpu`, `--disable-dev-shm-usage`,
   `--window-size=1920,1080`, `--disable-extensions`, `--disable-notifications`,
   real UA macOS, prefs tắt notification, `page_load_strategy = "eager"`.
   KHÔNG `--no-sandbox` (dev macOS không cần).
   **Ghi chú**: không tắt ảnh vội — TGDĐ lazy-load comment; verify bằng smoke-test P4 rồi mới bật
   `--blink-settings=imagesEnabled=false` nếu vẫn ra comment.
2. Thread-local registry theo researcher-01 §1 (`_tls`, `_drivers`, `_lock`, `atexit.register`).
   `get_driver()` set `driver.implicitly_wait(0)` ngay sau khi tạo, log `logger.info("driver mới cho thread %s", threading.current_thread().name)`.
3. `get_wait(driver, timeout=None)` dùng `get_settings().wait_timeout`, `poll_frequency=0.3`.
4. XOÁ `_fix_chromedriver_permissions` (dead), xoá block print hướng dẫn `-9` (không còn xảy ra
   với Selenium Manager), xoá mọi `_driver.get(...)` bị comment.
5. `utils/helpers.py` thêm:
   ```python
   def wait_for(driver, locator, timeout=None, condition=EC.presence_of_element_located)
   def click_safe(driver, element) -> bool        # fallback JS click, log warning
   def wait_count_grows(driver, locator, before: int, timeout=None) -> bool  # trả False khi timeout
   def go_back(driver) -> None                    # giữ, đổi print -> logger
   ```
   `wait_count_grows` nuốt `TimeoutException` trả `False` — caller dùng nó để thoát vòng "view-more".

## Todo list
- [x] build_options() từ Settings
- [x] thread-local get_driver / quit_current / quit_all / atexit
- [x] get_wait()
- [x] Xoá webdriver-manager + code chết trong driver.py
- [x] helpers: wait_for / click_safe / wait_count_grows / go_back dùng logger

## Success Criteria
- `python -c "from src.config.driver import get_driver, quit_all; d=get_driver(); d.get('https://example.com'); print(d.title); quit_all()"`
  → in `Example Domain`, và `pgrep -f chromedriver` sau đó KHÔNG còn process.
- Test 2 thread: mỗi thread `get_driver()` trả object khác nhau; gọi `get_driver()` 2 lần cùng
  thread trả cùng object.
- `grep -rn "webdriver_manager" src/` → rỗng.

## Risk Assessment
- **Selenium Manager cần mạng lần đầu** → offline sẽ fail. Mitigation: cache `~/.cache/selenium`
  đã có sau lần chạy đầu; ghi vào README.
- **`page_load_strategy="eager"`** có thể trả DOM chưa đủ với SPA → mọi truy cập element PHẢI qua
  `wait_for`, không `find_elements` trần. Nếu smoke-test P4 thiếu comment → hạ về `"normal"`.
- **Headless bị chặn bởi anti-bot TGDĐ** → chưa verify. `--headless` là flag CLI, mặc định có thể
  đặt `false` nếu smoke-test P4 thấy bị chặn.
- **RAM**: mỗi Chrome 200–400MB; `max_workers` mặc định 3, trần khuyến nghị 8.

## Security Considerations
- Không `--no-sandbox` trên máy dev.
- Không log full HTML/cookie.
- UA giả lập là để tránh bị chặn, không dùng để vượt paywall/auth.

## Next steps
→ Phase 04 dùng driver mới trong ScraperService.
