# Scout — Hiện trạng (khảo sát trực tiếp 2026-07-31)

## Nguồn model: `../Sentiment-Analysis-with-Naive-Bayes-Streamlit/`

| File | Dòng | Nội dung |
|---|---|---|
| `models/naive_bayes_model.py` | 106 | `NaiveBayesModel` tự cài đặt: đếm từ, Laplace smoothing, log prior/likelihood |
| `models/svm_model.py` | 29 | `SVMModel`: `TfidfVectorizer(max_features=5000)` + `SVC(kernel='linear', probability=True)` |
| `models/lstm_model.py` | 53 | `LSTMModel`: Embedding(100) → LSTM(64) → LSTM(32) → Dense(64) → Dropout(.5) → Dense(3, softmax) |
| `models/text.py` | 56 | **Trùng lặp** — bản hàm rời của svm/lstm, không ai import. Bỏ. |
| `app.py` | 91 | Streamlit: train 3 model → bảng accuracy → biểu đồ → ô nhập text |

Interface chung đã có sẵn: `train(train_df)` / `predict(text) -> (label, scores)` / `evaluate(test_df) -> float`.
`train_df` là DataFrame 2 cột `text`, `sentiment`.

`../sentiment-analysis/` — chỉ `main.py` (MultinomialNB, tiếng Anh) + `dataset.csv` 1201 dòng tiếng Anh.
**Không tái sử dụng gì**, prototype cũ.

## Dữ liệu đã gán nhãn: `excel_tag/` (46 file)

Header: `link, name_item, comments_id, comments_content, tag`

- **4600 dòng**, nhãn `neutral` 3495 (76.0%) · `negative` 723 (15.7%) · `positive` 381 (8.3%)
- `comments_id` duy nhất: **4400** → 200 dòng trùng (file chồng nhau)
- Nội dung duy nhất: **3160** → nhiều comment lặp
- **62 nội dung bị gán 2 nhãn khác nhau** → nhiễu nhãn
- 1 file header hỏng: `(link, name_item, comments_id, comments_content, tag, tag, tag)`
- 1 dòng nhãn `None`
- Độ dài text: min 1 · trung bình 105 · **max 2246** ký tự

`comments_id` khớp với `comments[].id` (ObjectId hex) trong Mongo → nối lại được nếu cần.

## Dữ liệu chưa gán nhãn (đầu vào cho predict hàng loạt)

| Thư mục | File | Ước tính dòng |
|---|---|---|
| `excel_comment/` | 266 | ~26.600 |
| `excel_comment21/` | 267 | ~256.600 |
| `excel_comment3/` | 11 | ~20.400 |

Cùng header 4 cột (không có `tag`).

## Môi trường — đã kiểm chứng bằng cách chạy thật

```
Python 3.13.14 · tensorflow 2.21.0 · keras 3.15.1 · scikit-learn 1.9.0 · pandas 3.0.5 · nltk (mới cài)
```

Chạy cả 3 model trên 376 dòng tag thật: **NaiveBayes OK · SVM OK · LSTM OK**.
Keras 3.15 VẪN còn `Tokenizer`, `pad_sequences`, chấp nhận `Embedding(input_length=)`
→ **không có blocker tương thích**, code gốc port sang được gần như nguyên vẹn.

## Bằng chứng vấn đề lệch lớp

Khi train LSTM trên mẫu thử, `val_accuracy` đứng yên **0.8684 suốt 5 epoch** → model chỉ đoán lớp
đa số. Accuracy trần của "luôn đoán neutral" trên toàn bộ tập là **76%**.
`app.py` gốc chỉ đo accuracy nên sẽ báo con số đẹp cho một model vô dụng.

## Codebase `src/` hiện tại (sau plan 20260729)

- Entry: `src/main.py` (CLI crawl), `src/app.py` (FastAPI), `python -m` từ repo root
- `src/config/settings.py` — pydantic-settings, nguồn config duy nhất
- `src/config/logging_config.py` — `setup_logging()` gọi ở entrypoint
- `src/repositories/product_repository.py` + `memory_repository.py` (cùng interface)
- `src/services/{scraper,export,product}_service.py`, `src/services/errors.py` (AppError + status_code)
- `src/dto/base.py` — `BaseResponse[T]` = `{data, success, message}`
- `tests/` — 40 test, mongomock, chạy offline
- **MongoDB Atlas hiện KHÔNG kết nối được** (cluster NXDOMAIN) → mọi thứ liên quan DB chưa verify được
