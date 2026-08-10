# Phase 05 — API `/analyze`: DTO, service, nạp model ở lifespan

## Context links
- [plan.md](./plan.md) · [phase-03-models.md](./phase-03-models.md) · [phase-04-cli-report.md](./phase-04-cli-report.md)
- [researcher-02-artifact-va-report.md](./research/researcher-02-artifact-va-report.md) §1,4
- Khuôn có sẵn: `src/api/products.py`, `src/app.py`, `src/services/errors.py`

## Overview
- Date: 2026-07-31
- Description: Thêm router `/analyze` vào FastAPI đang có: dự đoán 1 đoạn text, xem metrics các
  model, và serve trang HTML so sánh. Model nạp 1 lần, không nạp lại mỗi request.
- Priority: P1
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; 123 test pass

## Key Insights
- **Không đụng gì tới MongoDB** ở phase này. Nhưng `src/app.py` lifespan đang ping Mongo và
  **fail-fast**, nên hiện giờ (cluster chết) cả app không lên được — kéo theo `/analyze` cũng
  không dùng được dù chẳng cần DB. → **Quyết định (user chốt): sửa lifespan để Mongo hỏng chỉ
  log WARNING, không làm app sập.** `/products` sẽ trả 503 khi không có DB; `/analyze` vẫn chạy.
  Sửa ~5 dòng, không dựng server thứ hai.
- Bám đúng khuôn `src/api/products.py`: route `def` (không `async def`) vì predict là CPU-bound
  blocking; `Depends` để test override được; không try/except trong route.
- Model nạp ở **lifespan**, không phải mỗi request: nạp SVM/LSTM mất vài giây, làm trong request
  là hỏng. Nạp lỗi (chưa train) → **không được làm app chết**, chỉ đánh dấu "chưa sẵn sàng"
  và trả 503 khi có người gọi.
- Trang report tái dùng nguyên `report.render_html` của P4 — không viết template thứ hai.

## Requirements
1. `POST /analyze/predict` → `{text, model?}` → nhãn + điểm số.
2. `GET /analyze/models` → danh sách model đã train + metrics + thời điểm train.
3. `GET /analyze/report` → trang HTML so sánh (`text/html`).
4. Chưa train model → **503** với thông điệp "chưa có model, chạy `python -m src.analyze train`".
5. Envelope `{data, success, message}` giữ nguyên cho JSON (riêng `/report` trả HTML thuần).

## Architecture
```
src/services/errors.py
    class ModelNotTrainedError(AppError): status_code = 503     # THEM
    class UnknownModelError(AppError):    status_code = 400     # THEM

src/services/analysis_service.py
    class AnalysisService:
        def __init__(self, predictor: Predictor, metadata: dict | None)
        def predict(self, text: str, model: str | None) -> PredictionResult
        def list_models(self) -> list[ModelInfo]
        def report_html(self) -> str

src/api/analysis.py
    router = APIRouter(prefix="/analyze", tags=["analyze"])
    def get_service() -> AnalysisService          # Depends, override duoc trong test

src/dto/analysis.py
    PredictRequest(text: str = Field(min_length=1, max_length=5000), model: str | None = None)
    PredictionOut(model, sentiment, scores: dict[str, float])
    ModelInfo(name, accuracy, macro_f1, train_seconds, trained_at)
    PredictResponse(BaseResponse[PredictionOut])
    ModelListResponse(BaseResponse[list[ModelInfo]])
```

## Related code files
- THÊM: `src/api/analysis.py`, `src/services/analysis_service.py`, `src/dto/analysis.py`,
  `tests/test_api_analysis.py`
- SỬA: `src/app.py` (include router + nạp model ở lifespan), `src/services/errors.py` (2 lớp lỗi mới)
- DÙNG LẠI: `src/analysis/predictor.py`, `src/analysis/report.py` (P4), `src/dto/base.py`

## Implementation Steps
1. `errors.py` thêm `ModelNotTrainedError` (503) và `UnknownModelError` (400). Handler `AppError`
   ở `app.py` đã có sẵn → **không cần sửa handler**, chỉ thêm lớp con.
2. `analysis_service.py`:
   - `predict`: `model = name or settings.default_model`; tên không có trong registry →
     `UnknownModelError`; chưa có artifact → `ModelNotTrainedError`.
   - `list_models`: đọc `metadata.json`; chưa có → trả list rỗng + `success=True` (không phải lỗi,
     chỉ là chưa train), để FE hiển thị "chưa có model".
   - `report_html`: chưa có metadata → `ModelNotTrainedError`.
3. `api/analysis.py`: 3 route, tất cả là `def`. `/report` trả `HTMLResponse` (không bọc envelope —
   nó là trang web, không phải JSON API).
4. `app.py` lifespan: bọc **cả phần Mongo** trong try/except (đây là thay đổi so với hiện tại —
   bản cũ fail-fast), rồi mới tới phần model, cũng bọc riêng:
   ```python
   try:
       get_client(); ensure_indexes()
   except Exception:
       logger.warning("Không kết nối được MongoDB — /products sẽ trả 503", exc_info=True)
   ```
   `ProductRepository()` khi không có DB → ném lỗi → handler `Exception` trả 500; thêm
   `DatabaseUnavailableError(AppError, status_code=503)` để thông điệp rõ ràng hơn.
   ```python
   try:
       app.state.predictor = Predictor(settings.models_dir)
       app.state.metadata = load_metadata(settings.models_dir)   # None neu chua train
       logger.info("Đã nạp %d model", len(app.state.metadata["models"]))
   except Exception:
       app.state.predictor, app.state.metadata = None, None
       logger.warning("Chưa có model đã train — /analyze sẽ trả 503", exc_info=True)
   ```
   **Không để lỗi nạp model làm chết app** — crawler/API sản phẩm vẫn phải chạy được.
5. Nạp model thật sự là **lazy trong `Predictor.load(name)` + cache**, lifespan chỉ dựng đối tượng
   và đọc metadata. Lý do: nạp cả 3 model (có TF) làm uvicorn khởi động chậm 10-20s dù có thể
   không ai gọi `/analyze`.
6. `tests/test_api_analysis.py` — theo đúng khuôn `tests/test_api_products.py`:
   - Override `get_service` bằng service gắn `Predictor` trỏ vào `tmp_path` đã train sẵn model
     `nb` nhỏ (nhanh, không cần TF).
   - Assert: predict trả 200 + envelope đủ 3 khoá; `model` lạ → 400; chưa train → 503;
     `text` rỗng → 422; `/analyze/report` trả 200 `text/html` và **không chứa `http://`**.
   - Assert report đã escape HTML: đưa comment chứa `<script>` vào ví dụ đoán sai →
     output phải có `&lt;script&gt;`.

## Todo list
- [x] errors.py: ModelNotTrainedError (503) + UnknownModelError (400)
- [x] dto/analysis.py
- [x] services/analysis_service.py
- [x] api/analysis.py (3 route, /report trả HTMLResponse)
- [x] app.py: include router + lifespan nạp predictor (không fail-fast)
- [x] tests/test_api_analysis.py (gồm ca XSS escape)

## Success Criteria
- `curl -s -X POST localhost:8000/analyze/predict -H 'content-type: application/json'
  -d '{"text":"Sản phẩm rất tốt"}'` → 200, `data.sentiment` ∈ {negative, neutral, positive}.
- `curl -i localhost:8000/analyze/predict -d '{"text":"x","model":"khongco"}'` → **400**.
- Xoá `models_store/` rồi restart → `POST /analyze/predict` trả **503** với thông điệp hướng dẫn
  chạy `train`, và **app vẫn khởi động bình thường** (không crash).
- `curl -s localhost:8000/analyze/models` → 200, list có `macro_f1` từng model.
- `curl -s localhost:8000/analyze/report | grep -c "https\?://"` → 0.
- `python -m pytest -q` → toàn bộ pass.

## Risk Assessment
- **Bỏ fail-fast của Mongo là thay đổi hành vi** — trước đây app không lên nếu DB sai, giờ nó
  lên và chỉ hỏng ở `/products`. Đánh đổi có chủ đích: lỗi cấu hình DB phát hiện muộn hơn
  (lúc gọi API thay vì lúc khởi động), đổi lại `/analyze` không bị DB kéo sập. Log WARNING
  lúc startup phải rõ ràng để không ai bỏ sót.
- **Người dùng vẫn có đường chạy hoàn toàn không cần web**: `python -m src.analyze` (P4).
- **Predict blocking event loop**: route là `def` nên FastAPI chạy trong threadpool — an toàn.
  Nhưng text 5000 ký tự × nhiều request đồng thời vẫn ăn CPU; đã clamp `max_length=5000`.
- **TensorFlow nạp trong worker của uvicorn** tốn vài trăm MB RAM khi có người gọi model `lstm`.
  Chấp nhận cho môi trường dev; nếu deploy thì nên tách riêng.
- **Không có auth** — giống `/products`, vẫn là vấn đề tồn đọng chung, không giải ở phase này.

## Security Considerations
- `/analyze/report` trả HTML có nhúng nội dung comment → **bắt buộc `html.escape`** (đã yêu cầu ở
  P4, phase này có test chặn hồi quy). Đây là đường XSS thật vì nội dung do người ngoài viết.
- `PredictRequest.text` clamp `max_length=5000` chống payload khổng lồ.
- `model` chỉ nhận tên trong registry (whitelist), **không bao giờ ghép vào đường dẫn file** —
  tránh path traversal tới `joblib.load`.
- Không trả thông tin đường dẫn hệ thống trong thông điệp lỗi 503.

## Next steps
→ Chạy verify toàn cục ở [plan.md](./plan.md); cập nhật README (mục "Phân tích cảm xúc");
  cân nhắc ghi sentiment ngược vào Mongo ở plan sau.
