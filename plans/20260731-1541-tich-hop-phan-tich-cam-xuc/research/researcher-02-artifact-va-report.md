# Research — Lưu artifact model & phương án hiển thị so sánh

## 1. Lưu và nạp lại model

Yêu cầu: train 1 lần (chậm), predict nhiều lần (CLI + API) phải nạp lại nhanh, không train lại.

| Model | Cần lưu gì | Định dạng |
|---|---|---|
| NaiveBayes | 3 dict log-likelihood + 3 log prior | `joblib` (dict thuần Python) |
| SVM | `SVC` đã fit + `TfidfVectorizer` đã fit | `joblib` (chuẩn của sklearn) |
| LSTM | model Keras + tokenizer + `max_length` | `.keras` (native Keras 3) + `joblib` cho tokenizer |

Bố cục thư mục:

```
models_store/
├── metadata.json          # version schema, thời điểm train, seed, số mẫu, phân bố lớp,
│                          # metrics từng model, phiên bản preprocessing
├── naive_bayes.joblib
├── svm.joblib
├── lstm.keras
└── lstm_tokenizer.joblib
```

`models_store/` phải **gitignore** (file `.keras` vài chục MB, `joblib` chứa vectorizer lớn).

**`preprocessing_version`** trong metadata là bắt buộc: nếu sau này sửa hàm chuẩn hoá text mà
vẫn nạp model cũ, predict sẽ sai âm thầm. Nạp model có version lệch → từ chối, báo train lại.

**Rủi ro bảo mật**: `joblib.load` dùng pickle → nạp file lạ = chạy code tuỳ ý. Chỉ nạp từ
`models_store/` do chính mình sinh ra, không nhận đường dẫn từ input người dùng qua API.

## 2. Phương án hiển thị so sánh model

Yêu cầu người dùng: "1 web hay 1 cái chart để hiển thị việc so sánh model, không nhất thiết Streamlit".

| Phương án | Ưu | Nhược |
|---|---|---|
| Streamlit (như app.py gốc) | Có sẵn code | Thêm dependency nặng, **server thứ 2** chạy song song uvicorn, port riêng, train lại mỗi lần khởi động |
| Jupyter notebook | Quen thuộc khi làm đồ án | Không phải "web", phải cài jupyter, khó chia sẻ |
| **HTML tự sinh, self-contained** | Không thêm dependency, xem offline, gửi file được, nhúng luôn vào FastAPI đang có | Phải tự viết phần render (~150 dòng) |

**Chọn: HTML tự sinh.** Lý do thẳng: đã có sẵn FastAPI, thêm Streamlit là dựng server thứ hai
cho đúng một trang so sánh — vi phạm YAGNI. HTML sinh ra vừa mở trực tiếp bằng trình duyệt
(`open report.html`), vừa serve được ở `GET /analyze/report`.

**Cách vẽ chart không cần thư viện JS ngoài**: CSP/offline nên không dùng CDN. Vẽ bằng
**SVG thuần + CSS** — bar chart so sánh macro-F1/accuracy là hình chữ nhật, confusion matrix là
bảng HTML tô màu theo giá trị. Không cần Chart.js/plotly.

Nội dung report:
1. Bảng tổng hợp: model × (accuracy, macro-F1, thời gian train, thời gian predict/1000 dòng)
2. Bar chart SVG so sánh macro-F1, **có vẽ đường baseline "luôn đoán neutral"** để thấy model
   có thực sự học hay không
3. Confusion matrix 3×3 mỗi model
4. Bảng precision/recall/F1 từng lớp
5. Thông tin tập dữ liệu: tổng dòng, sau khử trùng, số dòng bỏ do mâu thuẫn nhãn, phân bố lớp
6. Vài ví dụ dự đoán sai của model tốt nhất — hữu ích để biết model yếu ở đâu

## 3. Predict hàng loạt trên 250k dòng

`excel_comment21/` ~256.600 dòng. Ràng buộc:

- **NaiveBayes/SVM**: predict từng dòng một là chậm. `SVC.predict_proba` với vòng lặp Python
  cho 250k dòng sẽ rất lâu → phải **predict theo batch** (`vectorizer.transform(list_texts)`
  rồi `model.predict(X)` một lần cho cả batch).
  Interface gốc chỉ có `predict(text)` đơn lẻ → **thêm `predict_batch(texts)`** vào base class.
- **LSTM**: `model.predict()` vốn đã nhận batch, chỉ cần gom.
- Ghi kết quả theo từng file Excel đầu vào → từng file đầu ra, dùng cursor/generator, không
  nạp 250k dòng vào RAM cùng lúc.
- `SVC` (kernel linear, không phải `LinearSVC`) với `probability=True` chậm đáng kể.
  Nếu tốc độ không đạt, phương án B: `LinearSVC` + `CalibratedClassifierCV`. Ghi vào rủi ro,
  đo trước khi đổi.

## 4. Tái sử dụng hạ tầng sẵn có trong `src/`

Không dựng song song thứ gì đã có:

| Cần | Dùng lại cái đã có |
|---|---|
| Config | `src/config/settings.py` — thêm field `models_dir`, `tag_dir`, `default_model` |
| Log | `src/config/logging_config.py` |
| Envelope API | `src/dto/base.py::BaseResponse` |
| Lỗi → HTTP status | `src/services/errors.py::AppError` (thêm `ModelNotTrainedError` = 503) |
| Đọc/ghi Excel | `openpyxl` đã có; phần đọc thư mục Excel là **mới**, nhưng ghi thì theo cùng
  quy ước đặt tên của `src/services/export_service.py` |
| Test | `pytest` + fixture kiểu `tests/conftest.py` |
