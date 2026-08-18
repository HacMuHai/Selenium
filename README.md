# Selenium Scraper

Crawl comment sản phẩm từ **thegioididong.com, CellphoneS và FPT Shop**, lưu vào MongoDB,
xuất Excel, và phục vụ qua REST API. Một codebase, ba entrypoint.

> **Lệnh đã đổi.** Toàn bộ import dùng prefix `src.`, nên **mọi lệnh chạy từ thư mục gốc
> của repo**: `python -m src.main` (KHÔNG còn `python src/main.py`) và
> `uvicorn src.app:app`. Không cần set `PYTHONPATH`.

## ⚠️ Bảo mật — bắt buộc đọc

Password MongoDB Atlas trước đây được hardcode trong `src/config/database.py` và **đã nằm
trong git history từ commit `874fb1d`**. Xoá khỏi code không xoá khỏi history.

- **PHẢI rotate password** của user Atlas `selenium_db` trên Atlas UI.
- Cân nhắc bật IP allowlist trên cluster.
- URI mới chỉ đặt trong `.env` (đã gitignore), không commit.
- API write (`POST`/`PATCH`/`DELETE`) hiện **không có auth** → không deploy public.

## Cài đặt

Yêu cầu Python **3.13** (code dùng cú pháp type hiện đại).

```bash
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows
pip install -r requirements.txt

cp .env.example .env              # rồi điền MONGO_URI thật
```

Trên Windows có thể double-click `setup.bat`. Xem thêm [SETUP_WINDOWS.md](./SETUP_WINDOWS.md).

ChromeDriver do **Selenium Manager** (tích hợp sẵn trong selenium ≥ 4.15) tự tải về
`~/.cache/selenium` — không cần `webdriver-manager`. Lần chạy đầu cần mạng.

## Cấu hình

Mọi cấu hình đọc từ `.env` qua `src/config/settings.py`. Xem `.env.example` để biết
danh sách đầy đủ.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MONGO_URI` | *(bắt buộc)* | Connection string Atlas |
| `MONGO_DB` | `selenium_scraper` | Tên database |
| `MONGO_COLLECTION` | `comments` | Tên collection (lịch sử; mỗi doc là 1 **product**) |
| `LOG_LEVEL` | `INFO` | |
| `HEADLESS` | `true` | Chrome chạy ẩn |
| `MAX_WORKERS` | `3` | Số thread crawl song song (mỗi thread 1 Chrome ~200–400MB) |
| `WAIT_TIMEOUT` | `15` | Timeout WebDriverWait (giây) |
| `EXPORT_DIR` | `data` | Thư mục xuất Excel |
| `MAX_ROWS_PER_FILE` | `2000` | Số dòng mỗi file `.xlsx` |

## Chạy crawler

```bash
python -m src.main --help                      # xem toàn bộ flag
python -m src.main --category tgdd-phu-kien    # crawl 1 nhóm danh mục
python -m src.main --category dtdd-tat-ca      # điện thoại của cả 3 sàn
python -m src.main --links https://cellphones.com.vn/mobile.html --limit 1 --no-db --export
python -m src.main --export-only               # chỉ xuất Excel từ DB, không mở Chrome
```

Sàn được nhận diện theo hostname của URL, nên `--links` trộn nhiều sàn trong một lần chạy
là hợp lệ. URL không thuộc sàn nào sẽ báo lỗi ngay, **trước khi** mở Chrome.

### Ba sàn được hỗ trợ

| Sàn | Danh sách sản phẩm | Comment lấy từ đâu |
|---|---|---|
| thegioididong.com | Chrome, phân trang `ul.pagination` | đọc DOM trang "xem tất cả đánh giá" |
| cellphones.com.vn | Chrome, nút "Xem thêm N sản phẩm" | GraphQL `reviews` — chính API trang web dùng |
| fptshop.com.vn | Chrome, nút "Xem thêm N kết quả" | REST `bff-before-order/comment/list` |

Với CellphoneS và FPT Shop, khối đánh giá chỉ render sẵn 5 mục rồi lật trang bằng API.
Gọi thẳng API đó lấy được **toàn bộ** đánh giá, nhanh hơn và ít vỡ hơn là bấm nút rồi
đọc DOM — nên hai sàn này không mở Chrome cho từng sản phẩm, chỉ mở ở bước lấy danh sách.
Chi tiết endpoint, header bắt buộc và cách lấy `product_id` / `upc` ghi trong docstring
đầu `src/services/sites/cellphones.py` và `fptshop.py`.

Prefix danh mục theo sàn: `tgdd-*`, `cps-*`, `fpt-*`; các nhóm `*-tat-ca` gộp cả ba sàn.
Xem `src/config/targets.py` để biết danh sách đầy đủ.

| Flag | Ý nghĩa |
|---|---|
| `--links URL [URL ...]` | Ghi đè danh sách link (bỏ qua `--category`) |
| `--category NAME` | Nhóm định nghĩa trong `src/config/targets.py` |
| `--no-db` | Không đọc & không ghi Mongo. Vì không đọc DB nên **sẽ crawl lại** cả sản phẩm đã có |
| `--max-pages N` | Số trang danh mục tối đa mỗi link (mặc định 15). Với CellphoneS/FPT Shop là số lần bấm "Xem thêm" |
| `--workers N` | Số thread song song |
| `--export [DIR]` | Xuất Excel sau khi crawl |
| `--export-only` | Chỉ export từ DB (không dùng chung với `--no-db`) |
| `--limit N` | Chỉ crawl N sản phẩm đầu mỗi danh mục — dùng để smoke test |
| `--headless` / `--no-headless` | |
| `--attach HOST:PORT` | Attach vào Chrome đang mở sẵn (xem dưới) |
| `--version-tag STR` | Ghi đè `config.version.version` cho lần chạy này |
| `--log-level LEVEL` | |

### Giữ browser ấm khi dev

Thay cho `run.py` cũ (đã xoá — `importlib.reload` không cập nhật object đã khởi tạo, sửa
code mà không thấy hiệu lực). Mở Chrome thủ công rồi attach:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

python -m src.main --attach 127.0.0.1:9222 --limit 1 --no-db
```

Mỗi lần sửa code là một process Python mới, nhưng browser vẫn giữ nguyên. Cổng debug chỉ
bind `127.0.0.1`, đừng bind `0.0.0.0`.

## Chạy API

```bash
uvicorn src.app:app --reload
```

Mọi response giữ envelope `{data, success, message}`; HTTP status **đúng nghĩa**
(400 id sai / 404 không tìm thấy / 422 body sai / 500 lỗi hệ thống).

| Method | Endpoint |
|---|---|
| `GET` | `/products?page=&limit=&q=` — danh sách, **không** kèm mảng comments |
| `GET` | `/products/{product_id}?comment_page=&comment_limit=` — chi tiết + comments phân trang |
| `POST` | `/products/{product_id}/comments` → 201 |
| `PATCH` | `/products/{product_id}/comments/{comment_id}` |
| `DELETE` | `/products/{product_id}/comments/{comment_id}` |
| `DELETE` | `/products/{product_id}` |

Router `/comments` cũ đã bị xoá (trả toàn `null` do đọc sai schema).

## Phân tích cảm xúc (Naive Bayes / SVM / LSTM)

Entrypoint **riêng**, chạy độc lập với crawler và không cần MongoDB:

```bash
python -m src.analyze train --report report.html
python -m src.analyze evaluate --report report.html --csv metrics.csv
python -m src.analyze predict --text "Sản phẩm dùng rất tốt"
python -m src.analyze predict --input data --output data_predicted --model svm
```

Dữ liệu huấn luyện: `data_tagged/` (3853 dòng đã gán nhãn, xem `plans/*/scout/scout-02-audit-nhan.md`
để biết vì sao không dùng `excel_tag/` gốc — nay ở `outdated/`). Artifact lưu ở `models_store/` (đã gitignore).

**Kết quả trên tập test 626 dòng:**

| Model | macro-F1 | accuracy | train |
|---|---|---|---|
| **SVM** | **0.833** | 0.875 | 3.2s |
| Naive Bayes | 0.782 | 0.850 | 0.1s |
| LSTM | 0.751 | 0.792 | 9.4s |
| *baseline (luôn đoán negative)* | *0.229* | *0.524* | — |

**macro-F1 là chỉ số chính**, không phải accuracy: dữ liệu lệch lớp nên một model chỉ đoán
lớp đa số vẫn đạt 52% accuracy mà vô dụng. LSTM thua cả Naive Bayes vì 2502 mẫu là quá ít cho
deep learning — đây là kết quả hợp lệ, không phải lỗi.

`report.html` là trang tự chứa (SVG thuần, không tải gì từ mạng), mở trực tiếp bằng trình duyệt
hoặc xem qua `GET /analyze/report`.

### Thử nhanh bằng trình duyệt

```bash
./run_analyze.sh          # macOS/Linux
run_analyze.bat           # Windows (double-click)
```

Script tự train nếu chưa có model, bật server rồi mở `/analyze/report`. Trang này có **ô nhập
text**: gõ một comment, bấm "Phân loại" là thấy cả 3 model cùng đoán, kèm điểm số. Có sẵn 3 nút
mẫu tích cực / tiêu cực / trung tính để bấm thử ngay.

### API phân tích

| Method | Endpoint |
|---|---|
| `POST` | `/analyze/predict` — `{text, model?}` → nhãn + điểm số của 1 model |
| `POST` | `/analyze/compare` — `{text}` → cả 3 model cùng đoán |
| `GET` | `/analyze/models` — model đã train + metrics |
| `GET` | `/analyze/report` — trang HTML so sánh + ô thử nghiệm |

MongoDB hỏng **không** làm app sập: `/products` trả 503, `/analyze` vẫn chạy bình thường.

## Test

```bash
python -m pytest -q
```

Test chạy hoàn toàn offline bằng `mongomock` — không đụng Atlas. `tests/test_sites.py` phủ
phần chọn sàn theo URL và phần parse JSON của CellphoneS / FPT Shop. Riêng selector DOM và
API thật thì phụ thuộc trang đích nên chỉ smoke-test thủ công, không đưa vào CI:

```bash
python -m src.main --links https://www.thegioididong.com/sac-cap --limit 2 --no-db
python -m src.main --links https://cellphones.com.vn/mobile.html --limit 2 --no-db
python -m src.main --links https://fptshop.com.vn/dien-thoai --limit 2 --no-db
```

## Cấu trúc

```
src/
├── app.py                        # FastAPI app + lifespan + exception handler
├── main.py                       # CLI argparse
├── api/products.py               # Router /products (route sync — pymongo blocking)
├── config/
│   ├── settings.py               # Nguồn cấu hình DUY NHẤT (pydantic-settings)
│   ├── logging_config.py
│   ├── database.py               # MongoClient singleton + ensure_indexes
│   ├── driver.py                 # WebDriver thread-local + quit_all
│   ├── targets.py                # Danh mục để crawl
│   └── version.py
├── dto/{base,product}.py
├── models/product.py             # TypedDict khớp schema DB
├── repositories/
│   ├── product_repository.py     # Mongo
│   └── memory_repository.py      # In-memory cho --no-db (cùng interface)
├── services/
│   ├── scraper_service.py        # Điều phối: chọn sàn theo URL, nhận repository qua DI
│   ├── sites/
│   │   ├── __init__.py           # get_site(url) - registry theo hostname
│   │   ├── base.py               # SiteScraper + helper "Xem thêm" + client httpx dùng chung
│   │   ├── tgdd.py               # đọc DOM
│   │   ├── cellphones.py         # GraphQL reviews
│   │   └── fptshop.py            # REST comment/list
│   ├── export_service.py
│   ├── product_service.py
│   └── errors.py                 # AppError + status_code
└── utils/helpers.py              # wait_for / click_safe / wait_count_grows
tests/                            # mongomock, không cần Mongo thật
```

**Schema MongoDB** (giữ nguyên, không migrate): 1 document = 1 product, comments lồng bên trong.

```json
{ "_id": "…", "name": "…", "link": "…", "site": "cellphones",
  "comments": [{ "id": "…", "name": "…", "content": "…", "rating": 5 }],
  "total_comments": 1, "crawled_at": "…", "version": "1.0" }
```

`site` là field **mới**, thêm khi crawl 3 sàn; document crawl trước đó không có field này.

## Lưu ý vận hành

- Selector và API của cả ba sàn có thể đổi bất cứ lúc nào → crawl trả 0 comment sẽ được
  log ở mức `WARNING` kèm tổng kết cuối run.
- **FPT Shop trả nhiều câu hỏi giá hơn là nhận xét sản phẩm.** Galaxy S25 Ultra: 163 mục
  nhưng chỉ 12 mục có sao. Bộ lọc `commentType: ["RATING"]` của chính trang web không tách
  được, nên crawler giữ lại tất cả (`rating` = 0 khi không chấm sao) và việc lọc để dành
  cho tầng phân tích. CellphoneS thì ngược lại: mọi review đều có sao.
- `--workers` mặc định 3; đừng nâng cao quá (lịch sự với site đích, và mỗi Chrome tốn RAM).
- File Excel sinh ra nằm trong `excel_*/` và đã được gitignore — chứa dữ liệu crawl.
