# Phase 04 — CLI `src/analyze.py`: train / evaluate / predict + HTML report

## Context links
- [plan.md](./plan.md) · [phase-02-dataset.md](./phase-02-dataset.md) · [phase-03-models.md](./phase-03-models.md)
- [researcher-02-artifact-va-report.md](./research/researcher-02-artifact-va-report.md) §2,3

## Overview
- Date: 2026-07-31
- Description: **Entrypoint RIÊNG cho phân tích** — `python -m src.analyze` với 3 lệnh con
  `train` / `evaluate` / `predict`, cộng trang HTML so sánh 3 model (thay Streamlit).
  Chạy được hoàn toàn độc lập với crawler và với MongoDB.
- Priority: P1
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; 123 test pass

## Key Insights
- **`src/analyze.py` là FILE RIÊNG, chạy độc lập** — không import `src/main.py`, không cần Mongo,
  không cần FastAPI. Crawl và phân tích là hai công việc khác hẳn nhau; gộp vào một CLI sẽ ra
  25 flag rối rắm. Dùng **subcommand** (`argparse` `add_subparsers`).
- Bám đúng khuôn của `src/main.py` đã có: `build_parser()` / `main(argv) -> int` /
  `sys.exit(main())`, `setup_logging` ở đầu, trả exit code.
- **HTML report là sản phẩm chính để so sánh model**, không phải phụ. Nó phải trả lời được
  một câu hỏi: *"model này có thực sự học được gì, hay chỉ đoán lớp đa số?"* → bắt buộc vẽ
  đường baseline lên cùng biểu đồ.
- Report tự chứa (inline CSS + SVG), mở bằng `open report.html` là xem được, không cần server.
- Predict hàng loạt: mỗi file Excel vào → một file Excel ra, thêm cột `sentiment` +
  `sentiment_model`. Xử lý theo từng file để không ôm 250k dòng trong RAM.

## Requirements
1. `python -m src.analyze train [--models nb,svm,lstm] [--no-class-weight]`
2. `python -m src.analyze evaluate [--report FILE] [--csv FILE]`
3. `python -m src.analyze predict (--input DIR --output DIR | --text "...") [--model NAME]`
4. HTML report có: bảng metrics, bar chart macro-F1 + baseline, confusion matrix, ví dụ đoán sai.
5. Xuất thêm CSV metrics để đưa vào báo cáo đồ án.

## Architecture
```
src/analyze.py
    build_parser() -> ArgumentParser            # 3 subcommand
    cmd_train(args) -> int
    cmd_evaluate(args) -> int
    cmd_predict(args) -> int
    main(argv=None) -> int

src/analysis/trainer.py
    class Trainer:
        def __init__(self, models_dir, seed)
        def train(self, names, train_df, class_weight=True) -> dict[str, TrainResult]
        def evaluate(self, names, test_df) -> dict[str, dict]     # goi metrics.evaluation_report
        def write_metadata(self, stats, results) -> None          # metadata.json

src/analysis/predictor.py
    class Predictor:
        def __init__(self, models_dir)
        def load(self, name) -> SentimentModel        # cache theo ten
        def predict_text(self, text, name) -> dict
        def predict_dir(self, input_dir, output_dir, name) -> list[Path]

src/analysis/report.py
    render_html(metadata: dict) -> str        # self-contained, SVG thuan, khong CDN
    render_csv(metadata: dict) -> str
```

## Related code files
- THÊM: `src/analyze.py`, `src/analysis/{trainer,predictor,report}.py`,
  `tests/test_trainer.py`, `tests/test_report.py`
- DÙNG LẠI: `dataset.py` (P2), `registry.py` + models (P3), `metrics.py` (P1),
  `src/config/logging_config.py`, `src/config/settings.py`
- THAM CHIẾU khuôn: `src/main.py` (CLI có sẵn), `src/services/export_service.py` (quy ước ghi Excel)
- THAY THẾ: `../Sentiment-Analysis-with-Naive-Bayes-Streamlit/app.py`

## Implementation Steps
1. `trainer.py::train`: với mỗi tên model → `get_model_class(name)()` → `.train(train_df)` →
   đo thời gian → `.save(models_dir)`. Trả `TrainResult(name, seconds, n_samples)`.
2. `trainer.py::evaluate`: `y_pred = model.predict_batch(test_df.text)` (1 lần, không vòng lặp) →
   `metrics.evaluation_report(y_true, y_pred)` → gom thêm `majority_baseline(y_true)`.
   Lưu kèm **tối đa 10 ví dụ đoán sai** của mỗi model (text rút gọn, nhãn thật, nhãn đoán).
3. `write_metadata`: ghi `models_store/metadata.json`:
   ```json
   {"schema": 1, "trained_at": "...", "seed": 42, "preprocessing_version": "1.0",
    "sklearn_version": "...", "dataset": {CleaningStats + phan bo lop},
    "split": {"train": N, "test": M, "test_size": 0.2},
    "models": {"svm": {"train_seconds": .., "metrics": {...}, "errors_sample": [...]}, ...},
    "baseline": {"label": "negative", "accuracy": 0.458, "macro_f1": 0.209}}
   ```
   **`trained_at` lấy bằng `datetime.now()` ở thời điểm chạy**, không hardcode.
4. `cmd_train`: `load_tagged_dataset` → log `CleaningStats` → `split_dataset` → `Trainer.train`
   → `Trainer.evaluate` → `write_metadata` → in bảng tóm tắt ra terminal (model | accuracy |
   macro-F1 | thời gian), **kèm dòng baseline ở cuối bảng để đối chiếu ngay**.
5. `cmd_evaluate`: đọc `metadata.json` (không train lại) → `report.render_html` → ghi file;
   `--csv` thì ghi thêm CSV. Nếu chưa có `metadata.json` → lỗi rõ ràng "chạy `train` trước", exit 2.
6. `cmd_predict`:
   - `--text`: nạp 1 model, in `{model, sentiment, scores}`.
   - `--input DIR --output DIR`: `iter_untagged_files` → với mỗi file, gom `comments_content`
     → `predict_batch` một lần → ghi Excel mới cùng tên + `_pred`, header cũ + `sentiment`,
     `sentiment_model`. Log tiến độ mỗi 20 file.
   - Hai nhánh loại trừ nhau; thiếu cả hai → lỗi tham số.
7. `report.py::render_html` — không dùng thư viện ngoài:
   - CSS inline, hỗ trợ cả nền sáng/tối bằng `@media (prefers-color-scheme: dark)`.
   - Bar chart macro-F1: các `<rect>` SVG, thang 0→1, kèm `<line>` đứt nét màu đỏ ở mức
     baseline macro-F1 + nhãn "baseline: luôn đoán lớp đa số (negative)".
   - Confusion matrix: `<table>` 3×3, ô tô nền theo cường độ (`background: rgba(...)` tỷ lệ giá trị).
   - Bảng per-class precision/recall/F1/support cho từng model.
   - Khối thông tin dataset: tổng dòng → sau khử trùng, số bỏ do mâu thuẫn nhãn, phân bố lớp.
   - Danh sách ví dụ đoán sai của model có macro-F1 cao nhất.
8. Test:
   - `test_trainer.py`: DataFrame nhỏ tự tạo, train `nb` + `svm`, assert `metadata.json` có đủ
     khoá, assert `evaluate` không train lại, assert baseline được tính.
   - `test_report.py`: đưa metadata giả → `render_html` trả chuỗi chứa tên cả 3 model, chứa
     `<svg`, chứa từ "baseline"; **không có `http://` hay `https://` nào** (tự chứa hoàn toàn).

## Todo list
- [x] trainer.py (train + evaluate theo batch + write_metadata)
- [x] predictor.py (cache model, predict_text, predict_dir theo từng file)
- [x] report.py render_html (SVG thuần, có baseline) + render_csv
- [x] analyze.py với 3 subcommand + bảng tóm tắt terminal
- [x] tests/test_trainer.py, tests/test_report.py

## Success Criteria
- `python -m src.analyze train --models nb,svm,lstm` chạy xong, sinh đủ artifact trong
  `models_store/` + `metadata.json`, in bảng có dòng baseline.
- `python -m src.analyze evaluate --report report.html --csv metrics.csv` → mở file HTML thấy
  3 model, biểu đồ có đường baseline, confusion matrix.
- `grep -c "https\?://" report.html` → **0** (self-contained thật sự).
- `python -m src.analyze predict --text "Sản phẩm dùng rất tốt"` → in nhãn + điểm số.
- `python -m src.analyze predict --input excel_comment --output excel_predicted --model svm`
  → sinh 266 file, mở 1 file thấy có cột `sentiment` và `sentiment_model`.
- `python -m src.analyze evaluate` khi chưa train → thông báo rõ ràng, exit code 2 (không traceback).
- `python -m pytest -q` → toàn bộ test cũ (40) + test mới đều pass.

## Risk Assessment
- **Predict 256k dòng (`excel_comment21/`) quá lâu** → chưa đo được cho tới khi chạy thật.
  Giảm rủi ro: chạy `excel_comment/` (~26k) trước để đo tốc độ, ngoại suy rồi mới quyết định.
  Nếu SVM quá chậm → chuyển `LinearSVC` (P3 đã ghi phương án B).
- **Train LSTM lâu** → đặt `epochs` mặc định 5 như bản gốc, cho phép `--epochs` override.
- **HTML tự viết trông xấu** → chấp nhận; ưu tiên đọc được số liệu, không phải đẹp. Nếu cần đẹp
  hơn thì đó là việc riêng, không chặn phase.
- **Ghi đè `models_store/` khi train lại** → mất model cũ. Chấp nhận (train lại rẻ), nhưng log
  WARNING trước khi ghi đè.
- **Ghi Excel đầu ra vào đúng thư mục đầu vào** → chặn bằng kiểm tra `input_dir != output_dir`.

## Security Considerations
- `--input/--output` là đường dẫn từ người dùng → `Path(...).resolve()`, kiểm tra tồn tại,
  từ chối nếu output trùng input.
- HTML report nhúng **nội dung comment thật** (ví dụ đoán sai) → phải escape HTML
  (`html.escape`) nếu không sẽ dính XSS khi serve qua `/analyze/report` ở P5. Bắt buộc.
- Cắt ngắn ví dụ còn ~200 ký tự, không đổ nguyên comment 2246 ký tự vào report.

## Next steps
→ Phase 05: API dùng lại `Predictor` và `report.render_html`.
