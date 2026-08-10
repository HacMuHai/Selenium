# Phase 03 — 3 model + base interface + lưu/nạp artifact

## Context links
- [plan.md](./plan.md) · [phase-01-nen-tang.md](./phase-01-nen-tang.md)
- [scout-01-hien-trang.md](./scout/scout-01-hien-trang.md) §"Nguồn model"
- [researcher-01-...md](./research/researcher-01-tieng-viet-va-lech-lop.md) §2,3,5
- [researcher-02-artifact-va-report.md](./research/researcher-02-artifact-va-report.md) §1,3

## Overview
- Date: 2026-07-31
- Description: Port `NaiveBayesModel`/`SVMModel`/`LSTMModel` vào `src/analysis/models/`, thống nhất
  một interface, thay preprocessing tiếng Anh bằng bản tiếng Việt, thêm `predict_batch` và
  lưu/nạp artifact.
- Priority: P0
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; 123 test pass

## Key Insights
- Code gốc **đã có sẵn interface gần đúng** (`train`/`predict`/`evaluate`) → port chứ không viết lại.
  Phần thay đổi thật sự chỉ có 4 chỗ: preprocessing, `class_weight`, `predict_batch`, `save/load`.
- **`evaluate()` gốc phải bỏ**: nó lặp `iterrows()` gọi `predict()` từng dòng và chỉ trả accuracy.
  Vừa chậm vừa dùng sai chỉ số. Thay bằng `predict_batch()` rồi đưa vào `metrics.evaluation_report()`.
- **`predict_batch` không phải tối ưu sớm**: predict 250k dòng bằng vòng lặp `SVC.predict_proba`
  từng câu là bất khả thi về thời gian. Đây là yêu cầu chức năng.
- `max_length` của LSTM lấy `max(len(x))` → 2246 ký tự, pad mọi chuỗi tới đó. Dùng **percentile 95**.
- TensorFlow phải **import lazy** (bên trong hàm/`__init__` của class LSTM), không import ở
  module level: nếu không thì API và CLI cũng phải chờ TF load ~5-10s dù không dùng LSTM.
- Naive Bayes gốc có bug tinh vi: `self.log_likelihood_*.get(token, 0)` → **từ chưa từng thấy được
  điểm 0**, mà `log(p)` luôn âm, nên từ lạ lại "tốt hơn" mọi từ đã biết. Phải trả về log-prob của
  smoothing (một số âm), không phải 0.

## Requirements
1. `SentimentModel` base: `train`, `predict`, `predict_batch`, `save`, `load`, `name`.
2. Ba lớp con dùng preprocessing tiếng Việt từ P1.
3. `class_weight` cho SVM và LSTM; cờ prior cân bằng cho NB.
4. Lưu/nạp artifact kèm `metadata.json` có `PREPROCESSING_VERSION`.
5. `registry`: tên → class; LSTM tự bị loại nếu chưa cài TensorFlow.

## Architecture
```
src/analysis/models/base.py
    class SentimentModel(ABC):
        name: ClassVar[str]
        def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None
        def predict(self, text: str) -> tuple[str, dict[str, float]]
        def predict_batch(self, texts: Sequence[str]) -> list[str]
        def save(self, models_dir: Path) -> None
        @classmethod
        def load(cls, models_dir: Path) -> "SentimentModel"

src/analysis/models/naive_bayes.py   NaiveBayesModel   name="nb"
src/analysis/models/svm.py           SVMModel          name="svm"
src/analysis/models/lstm.py          LSTMModel         name="lstm"    # import tf lazy

src/analysis/registry.py
    AVAILABLE: dict[str, type[SentimentModel]]
    def get_model_class(name) -> type          # raise ValueError neu ten sai
    def available_names() -> list[str]         # bo "lstm" neu import tensorflow that bai
```

## Related code files
- THÊM: `src/analysis/models/{__init__,base,naive_bayes,svm,lstm}.py`, `src/analysis/registry.py`,
  `tests/test_models.py`
- PORT TỪ: `../Sentiment-Analysis-with-Naive-Bayes-Streamlit/models/*.py`
- KHÔNG PORT: `models/text.py` (trùng lặp), `app.py` (thay bằng HTML report ở P4)
- DÙNG LẠI: `src/analysis/preprocessing.py`, `src/analysis/metrics.py` (P1)

## Implementation Steps
1. `base.py`: ABC + `predict_batch` mặc định gọi `predict` trong vòng lặp (lớp con nào làm được
   nhanh hơn thì override — SVM và LSTM đều override).
2. `naive_bayes.py` — port từ bản gốc, sửa 4 điểm:
   - `preprocess` gọi `preprocessing.tokenize()` thay cho PorterStemmer/stopwords tiếng Anh.
   - Thêm **bigram**: `tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]`.
   - Sửa bug từ-chưa-thấy: lưu sẵn `self.default_log_likelihood[label]` =
     `log(1 / (total_words + V))`, dùng thay cho `.get(token, 0)`.
   - `balanced_prior: bool` → khi True dùng `log(1/3)` cho cả 3 lớp.
   - `save/load`: `joblib` một dict gồm 3 log-likelihood + 3 prior + default + version.
3. `svm.py` — port, sửa:
   - `TfidfVectorizer(max_features=5000, ngram_range=(1, 2), preprocessor=normalize_text,
     tokenizer=..., token_pattern=None)` — hoặc đơn giản hơn: `preprocessor=normalize_text` và để
     tokenizer mặc định (đã chuẩn hoá thì tách khoảng trắng là đủ).
   - `SVC(kernel="linear", probability=True, class_weight="balanced" if class_weight else None,
     random_state=seed)`.
   - `predict_batch`: `self.model.predict(self.vectorizer.transform(list(texts)))` — 1 lần cho cả batch.
   - `save/load`: `joblib.dump({"model":…, "vectorizer":…, "version":…})`.
4. `lstm.py` — port, sửa:
   - `import tensorflow as tf` **bên trong** `_ensure_tf()`, gọi ở `train`/`load`.
   - `max_length = int(np.percentile([len(x) for x in sequences], 95))`, tối thiểu 10.
   - `class_weight` tính từ tần suất, truyền vào `model.fit(..., class_weight=cw)`.
   - `model.fit(..., verbose=0)` — không đổ progress bar vào log (đã thấy nó làm bẩn output).
   - `predict_batch`: gom hết `texts` → `pad_sequences` → `model.predict(X, verbose=0)` 1 lần.
   - `save`: `model.save(dir/"lstm.keras")` + `joblib.dump({tokenizer, max_length, version})`.
5. `registry.py`: `available_names()` thử `importlib.util.find_spec("tensorflow")`; không có thì
   bỏ `lstm` khỏi danh sách và log INFO một lần (không phải WARNING — đây là lựa chọn hợp lệ).
6. `tests/test_models.py`: dùng DataFrame nhỏ tự tạo (~60 dòng, 3 lớp) — **KHÔNG** dùng
   `excel_tag/` thật (test phải chạy nhanh và không phụ thuộc dữ liệu ngoài).
   - NB và SVM: bắt buộc test.
   - LSTM: `@pytest.mark.skipif(not tensorflow_installed)` + `epochs=1` để test nhanh.
   - Test `save` → `load` → `predict` cho ra **cùng kết quả** với model gốc (round-trip).
   - Test `predict_batch(texts)` khớp `[predict(t)[0] for t in texts]`.
   - Test nạp artifact có `version` lệch → ném lỗi rõ ràng, không predict sai âm thầm.

## Todo list
- [x] base.py SentimentModel ABC + predict_batch mặc định
- [x] naive_bayes.py (preprocessing VI + bigram + sửa bug từ chưa thấy + balanced_prior)
- [x] svm.py (ngram 1-2, class_weight balanced, predict_batch theo lô)
- [x] lstm.py (lazy import TF, percentile-95 max_length, class_weight, verbose=0)
- [x] save/load + kiểm tra PREPROCESSING_VERSION cho cả 3
- [x] registry.py (bỏ lstm khi thiếu TensorFlow)
- [x] tests/test_models.py (round-trip, batch khớp đơn lẻ, version lệch)

## Success Criteria
- `python -c "from src.analysis.registry import available_names; print(available_names())"`
  → `['nb', 'svm', 'lstm']` (hoặc bỏ `lstm` nếu chưa cài TF), và **không mất 5-10s chờ TF**.
- Round-trip: train → save → load → `predict("sản phẩm rất tốt")` cho ra label và scores
  y hệt trước khi save.
- `predict_batch(["a","b","c"])` khớp từng phần tử với `predict()` gọi lẻ.
- NB sau khi sửa bug: một câu toàn từ chưa từng thấy KHÔNG cho ra điểm cao hơn câu toàn từ đã biết.
- Nạp artifact có `version` khác `PREPROCESSING_VERSION` → ném exception với thông điệp
  "model cũ, cần train lại", không predict.
- `python -m pytest tests/test_models.py -q` → pass, chạy < 60s (LSTM 1 epoch).

## Risk Assessment
- **LSTM thua NB/SVM** → khả năng cao với 3100 mẫu. **Đây là kết quả hợp lệ để báo cáo**,
  không phải bug cần "chỉnh cho LSTM thắng". Ghi rõ trong report.
- **`SVC(probability=True)` chậm**: dùng Platt scaling với cross-validation nội bộ → train lâu
  hơn nhiều lần. Nếu train quá 10 phút, phương án B: `LinearSVC` + `CalibratedClassifierCV`,
  hoặc bỏ `probability=True` và dùng `decision_function` làm score.
- **Bigram làm nổ chiều vector** → đã chặn bằng `max_features=5000`.
- **`joblib`/pickle không tương thích giữa các phiên bản sklearn** → metadata phải lưu cả
  `sklearn.__version__`; nạp mà lệch major thì cảnh báo.
- **Sửa Naive Bayes làm lệch kết quả so với bản gốc của đồ án** → nếu cần đối chiếu với bản cũ,
  giữ cờ `legacy_unknown_token=False` để bật lại hành vi cũ. (Chỉ thêm nếu thực sự cần — YAGNI.)

## Security Considerations
- `joblib.load` = pickle = **thực thi code tuỳ ý**. Chỉ nạp từ `settings.models_dir`; không bao giờ
  nhận đường dẫn artifact từ HTTP request hay CLI của người dùng khác.
- Không nhúng dữ liệu train (nội dung comment) vào artifact ngoài phần từ vựng đã tokenize.
- `models_store/` đã gitignore (P1) — artifact chứa vốn từ trích từ dữ liệu crawl, không commit.

## Next steps
→ Phase 04 (CLI train/evaluate/predict + report), Phase 05 (API) — cả hai đều nạp model qua registry.
