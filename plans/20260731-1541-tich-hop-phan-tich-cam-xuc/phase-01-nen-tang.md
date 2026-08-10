# Phase 01 — Nền tảng: settings, dependencies, preprocessing tiếng Việt, metrics

## Context links
- [plan.md](./plan.md)
- [scout-01-hien-trang.md](./scout/scout-01-hien-trang.md) §"Môi trường", §"Bằng chứng lệch lớp"
- [researcher-01-tieng-viet-va-lech-lop.md](./research/researcher-01-tieng-viet-va-lech-lop.md) §1,2,3

## Overview
- Date: 2026-07-31
- Description: Dựng 2 module thuần tính toán, không phụ thuộc gì khác: chuẩn hoá text tiếng Việt
  và tính chỉ số đánh giá. Cộng thêm cấu hình + dependencies cho toàn bộ tính năng.
- Priority: P0 (chặn mọi phase khác)
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; 123 test pass

## Key Insights
- Đây là 2 module **dễ test nhất và quan trọng nhất**: sai chuẩn hoá text thì mọi model sai theo,
  sai metrics thì không biết model nào tốt. Làm trước, test kỹ, rồi mới tới model.
- Tiếng Việt có 2 cách gõ dấu (tổ hợp `e` + `◌́` vs dựng sẵn `é`). Không `unicodedata.normalize("NFC")`
  thì "tốt" gõ 2 kiểu thành 2 token khác nhau — lỗi âm thầm, rất khó phát hiện.
- **Không được lọc** `không, chẳng, chưa, rất, quá, lắm` khỏi stopword: đó là tín hiệu cảm xúc.
  "không tốt" mà bỏ "không" thì thành "tốt" — đảo ngược nhãn.
- `PorterStemmer`/`stopwords` gốc còn được khởi tạo lại **mỗi lần gọi hàm** → chậm khi chạy 250k dòng.
  Bản mới đặt stopword set ở module level, tính 1 lần.

## Requirements
1. `src/analysis/preprocessing.py`: `normalize_text`, `tokenize`, `VI_STOPWORDS`, `PREPROCESSING_VERSION`.
2. `src/analysis/metrics.py`: macro-F1, per-class P/R/F1, confusion matrix, baseline lớp đa số.
3. `requirements.txt` bổ sung: `scikit-learn`, `pandas`, `joblib`, `tensorflow`, `nltk` **(bỏ)**.
4. `Settings` thêm field cho đường dẫn model/tag/report.
5. `.gitignore` chặn `models_store/`.

## Architecture
```
src/analysis/preprocessing.py       # thuần Python + unicodedata, KHÔNG import sklearn/tf
    PREPROCESSING_VERSION = "1.0"   # đổi khi sửa logic -> model cũ bị từ chối nạp
    VI_STOPWORDS: frozenset[str]    # ~200 từ, KHÔNG chứa từ phủ định/mức độ
    normalize_text(s: str) -> str
    tokenize(s: str, remove_stopwords: bool = True) -> list[str]

src/analysis/metrics.py             # thuần Python, KHÔNG import sklearn (dễ test, nhẹ)
    LABELS = ("negative", "neutral", "positive")
    confusion_matrix(y_true, y_pred) -> dict[tuple[str,str], int]
    per_class_metrics(y_true, y_pred) -> dict[str, dict]   # precision/recall/f1/support
    macro_f1(y_true, y_pred) -> float
    accuracy(y_true, y_pred) -> float
    majority_baseline(y_true) -> dict   # accuracy + macro_f1 cua "luon doan lop da so"
    evaluation_report(y_true, y_pred) -> dict   # gom tat ca, dung cho JSON + HTML
```
`nltk` **bị loại** khỏi dependencies: sau khi bỏ PorterStemmer + stopwords tiếng Anh thì không
còn chỗ nào dùng. (Đã cài lúc khảo sát, phải gỡ khỏi requirements.)

## Related code files
- THÊM: `src/analysis/__init__.py`, `src/analysis/preprocessing.py`, `src/analysis/metrics.py`,
  `tests/test_preprocessing.py`, `tests/test_metrics.py`
- SỬA: `requirements.txt`, `.gitignore`, `.env.example`, `src/config/settings.py`

## Implementation Steps
1. `requirements.txt` thêm 4 dòng: `scikit-learn`, `pandas`, `joblib`, `tensorflow`.
   **Không thêm `nltk`.** Ghi chú trong README: `tensorflow` ~600MB, chỉ cần khi dùng LSTM.
2. `src/config/settings.py` thêm:
   ```python
   models_dir: str = "models_store"
   tag_dir: str = "excel_tag_v2"           # nguồn nhãn ĐÃ LÀM SẠCH (không dùng excel_tag/)
   default_model: str = "svm"              # model dùng khi API không chỉ định
   test_size: float = 0.2
   random_seed: int = 42
   ```
   Cập nhật `.env.example` tương ứng.
3. `preprocessing.py::normalize_text` theo thứ tự:
   ```python
   s = unicodedata.normalize("NFC", str(s))
   s = s.lower()
   s = EMOJI_RE.sub(r" \g<0> ", s)          # tach emoji thanh token rieng, KHONG xoa
   s = re.sub(r"(.)\1{2,}", r"\1\1", s)     # "tottttt" -> "tott"
   s = PUNCT_RE.sub(" ", s)                 # bo dau cau, GIU chu co dau tieng Viet
   s = re.sub(r"\s+", " ", s).strip()
   ```
   Chú ý: regex bỏ dấu câu phải dùng `\w` với `re.UNICODE` hoặc whitelist ký tự tiếng Việt —
   **không** dùng `string.punctuation` + `[^a-z0-9]` vì sẽ xoá sạch chữ có dấu.
4. `VI_STOPWORDS`: ~200 từ. Bắt buộc **loại trừ** khỏi danh sách:
   `không, chẳng, chưa, đừng, rất, quá, hơi, lắm, nhất, hơn, kém, tệ, tốt`.
5. `tokenize(s, remove_stopwords=True)`: `normalize_text` → tách khoảng trắng → lọc stopword →
   bỏ token rỗng. Trả `list[str]`.
6. `metrics.py`: cài tay, không dùng `sklearn.metrics` — module này phải import được mà không
   kéo theo sklearn (API chỉ hiển thị metrics đã lưu, không cần sklearn trong tiến trình đó).
   Công thức: `precision = TP/(TP+FP)`, `recall = TP/(TP+FN)`, `f1 = 2PR/(P+R)`,
   **`f1 = 0.0` khi P+R = 0** (không để chia 0), `macro_f1 = mean(f1 mỗi lớp)` — trung bình trên
   CẢ 3 lớp kể cả lớp không xuất hiện trong dự đoán.
7. `majority_baseline(y_true)`: giả lập dự đoán toàn bộ = lớp đa số, trả `{accuracy, macro_f1, label}`.
   Đây là con số phải in cạnh mọi kết quả.
8. `.gitignore` thêm `models_store/` và `*.keras`.

## Todo list
- [x] requirements.txt + ghi chú TensorFlow trong README
- [x] Settings: models_dir, tag_dir, default_model, test_size, random_seed + .env.example
- [x] preprocessing.py: normalize_text / tokenize / VI_STOPWORDS / PREPROCESSING_VERSION
- [x] metrics.py: confusion / per_class / macro_f1 / accuracy / majority_baseline
- [x] tests/test_preprocessing.py
- [x] tests/test_metrics.py
- [x] .gitignore: models_store/

## Success Criteria
- `normalize_text` giữ nguyên chữ có dấu: `normalize_text("Sản phẩm TỐT!!!")` → `"sản phẩm tốt"`.
- 2 cách gõ dấu cho ra cùng kết quả:
  `normalize_text("tốt") == normalize_text(unicodedata.normalize("NFD", "tốt"))` → True.
- `tokenize("sản phẩm này không tốt")` → còn `"không"` và `"tốt"` (không bị lọc mất).
- `majority_baseline` trên phân bố thật của `excel_tag_v2` (45.8/44.5/9.8) trả
  `accuracy ≈ 0.458`, `macro_f1 ≈ 0.209` (lớp đa số là `negative`).

- `python -c "import src.analysis.metrics"` chạy được **khi chưa cài sklearn/tensorflow**.
- `python -m pytest tests/test_preprocessing.py tests/test_metrics.py -q` → pass.

## Risk Assessment
- **Regex bỏ dấu câu xoá luôn chữ tiếng Việt** → medium, đây là lỗi kinh điển. Test bắt buộc
  phải có ca chữ có dấu đầy đủ (`ă â ê ô ơ ư đ` + 5 thanh).
- **Danh sách stopword tự viết thiếu/thừa** → low, ảnh hưởng nhẹ chất lượng. Có thể tinh chỉnh sau.
- **`PREPROCESSING_VERSION` quên bump** khi sửa logic → model cũ vẫn nạp, predict sai âm thầm.
  Ghi chú rõ ngay đầu file.
- **TensorFlow 600MB** → cài lâu, chiếm đĩa. Đã cài sẵn lúc khảo sát nên không phát sinh thêm.

## Security Considerations
- `normalize_text` nhận text từ Excel/API → phải `str()` phòng `None`/số, không để ném exception.
- Không log nội dung comment ở mức INFO (dữ liệu người dùng công khai nhưng không cần đổ vào log).
- Regex phải tránh backtracking mũ (`(.)\1{2,}` an toàn, nhưng không thêm pattern lồng nhau).

## Next steps
→ Phase 02 (dataset) và Phase 03 (models) — chạy song song được, cả hai chỉ phụ thuộc P1.
