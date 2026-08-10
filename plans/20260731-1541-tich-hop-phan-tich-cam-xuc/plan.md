# Plan: Tích hợp phân tích cảm xúc (NB / SVM / LSTM) vào `src/`

Date: 2026-07-31 · Repo: /Volumes/hacmuhai2/Toan/Selenium · Status: **DONE (5/5)** — thực thi 2026-07-31
Cập nhật 2026-07-31: đã audit + gán lại nhãn, xem [scout-02-audit-nhan.md](./scout/scout-02-audit-nhan.md).

## Mục tiêu
Đưa 3 model từ `../Sentiment-Analysis-with-Naive-Bayes-Streamlit/models/` vào `src/`, train
bằng `excel_tag_v2/` (3853 dòng đã làm sạch nhãn), rồi: (a) **entrypoint riêng** `src/analyze.py`
chạy độc lập với crawler, (b) API `/analyze`, (c) trang HTML so sánh 3 model.
Không đụng crawler, không đổi schema Mongo.

## Quyết định đã khoá
- **Nguồn dữ liệu: `excel_tag_v2/`** (44 file, 3853 dòng) — KHÔNG dùng `excel_tag/` gốc nữa.
  Nhãn cũ có 74.7% neutral trong đó ~83% gán sai; đã gán lại 2503 dòng. Phân bố mới:
  negative 45.8% · positive 44.5% · neutral 9.8%.
- **`excel_comment3/` KHÔNG phải tập predict** — nó là nguồn chưa gán nhãn của `excel_tag`
  (87.6% id trùng). Tập predict là `excel_comment/` (~26k dòng) và `excel_comment21/` (~256k).
- **Cả 3 model** NB + SVM + LSTM. Đã chạy thử thật trên Python 3.13 / TF 2.21 / Keras 3.15 →
  OK, không có blocker tương thích.
- **Viết lại preprocessing cho tiếng Việt**, không thêm thư viện NLP; bù từ ghép bằng n-gram (1,2).
- **Chỉ số chính là macro-F1**. Baseline "luôn đoán lớp đa số" giờ là **45.8% accuracy /
  macro-F1 0.209** — mọi báo cáo phải vẽ đường này để biết model có thực sự học hay không.
- **Khử trùng nội dung TRƯỚC khi split** — nếu không, cùng 1 comment nằm ở cả train lẫn test.
- **`src/analyze.py` là entrypoint ĐỘC LẬP** — chạy được khi không có Mongo, không có FastAPI.
  Song song đó vẫn nhúng router `/analyze` vào app chính; sửa lifespan để Mongo chết không
  làm app sập (~5 dòng).
- **HTML self-contained thay cho Streamlit**. Không dựng server thứ 2; chart vẽ bằng SVG thuần.
- **KHÔNG ghi sentiment ngược vào Mongo** ở plan này. Kết quả ra Excel.
- `models/text.py` của repo gốc **không port** — code trùng lặp, không ai import.

## Cây thư mục sau khi làm
    src/analysis/{__init__,dataset,preprocessing,metrics,registry,trainer,predictor,report}.py
    src/analysis/models/{__init__,base,naive_bayes,svm,lstm}.py
    src/analyze.py                      # ENTRYPOINT RIENG: python -m src.analyze
    src/services/analysis_service.py    # cho API
    src/api/analysis.py                 # router /analyze
    src/dto/analysis.py
    models_store/                       # artifact, gitignore
    tests/{test_preprocessing,test_dataset,test_metrics,test_models,test_api_analysis}.py

## Phases
| # | Phase | File | Status | Progress | Depends |
|---|---|---|---|---|---|
| 1 | Nền: settings, deps, preprocessing tiếng Việt, metrics | [phase-01-nen-tang.md](./phase-01-nen-tang.md) | DONE | 100% | — |
| 2 | Dataset: đọc `excel_tag_v2/`, làm sạch, khử trùng, split | [phase-02-dataset.md](./phase-02-dataset.md) | DONE | 100% | P1 |
| 3 | 3 model + base interface + lưu/nạp artifact | [phase-03-models.md](./phase-03-models.md) | DONE | 100% | P1 |
| 4 | Entrypoint riêng `src/analyze.py`: train / evaluate / predict + HTML report | [phase-04-cli-report.md](./phase-04-cli-report.md) | DONE | 100% | P2, P3 |
| 5 | API `/analyze` + DTO + lifespan chịu lỗi Mongo | [phase-05-api.md](./phase-05-api.md) | DONE | 100% | P3 |

## Verify toàn cục (sau P5)
    python -m pytest -q
    python -m src.analyze train --models nb,svm,lstm
    python -m src.analyze evaluate --report report.html   # macro-F1 vs baseline 0.209
    python -m src.analyze predict --input excel_comment --output excel_predicted --model svm
    python -m src.analyze predict --text "Sản phẩm dùng rất tốt"
    uvicorn src.app:app --reload   # POST /analyze/predict; GET /analyze/models; GET /analyze/report

## Rủi ro xuyên suốt
- **Nhãn là do 1 người gán** (tôi, sau khi user chốt). Độ tin cậy lặp lại 100% trên 90 dòng
  đối chứng, nhưng vẫn là 1 góc nhìn. Cột `tag_cu` được giữ trong `excel_tag_v2/` để user
  soát lại bất cứ lúc nào.
- **Ranh giới "câu hỏi báo lỗi"**: `"Loa bị rè, khắc phục sao ạ"` được gán `negative`
  (báo hỏng) chứ không `neutral` (câu hỏi). Đây là quy ước, ghi rõ trong report.
- **Dữ liệu ít**: ~3100 mẫu duy nhất sau khử trùng. LSTM nhiều khả năng THUA SVM — kết quả
  hợp lệ để báo cáo, không phải bug cần "sửa cho LSTM thắng".
- **250k dòng khi predict hàng loạt** → phải có `predict_batch`; `SVC(probability=True)` có thể
  quá chậm (phương án B: `LinearSVC` + calibration).
- **Text dài 2246 ký tự** → `max_length` LSTM dùng percentile 95, không dùng `max()`.
- **Artifact dùng pickle** → chỉ nạp file do chính mình sinh, không nhận path từ API.

## Kết quả thực tế (2026-07-31)
Dữ liệu: 3853 dòng → **3128** sau làm sạch (bỏ 3 rỗng, 722 trùng nội dung, 0 mâu thuẫn nhãn).
Phân bố: negative 1637 · positive 1169 · neutral 322. Split train 2502 / test 626.

| Model | macro-F1 | accuracy | train | predict |
|---|---|---|---|---|
| **svm** | **0.833** | 0.875 | 3.2s | 0.1s |
| nb | 0.782 | 0.850 | 0.1s | 0.0s |
| lstm | 0.751 | 0.792 | 9.4s | 0.3s |
| *baseline (luôn đoán negative)* | *0.229* | *0.524* | — | — |

**SVM thắng, LSTM thua cả Naive Bayes** — đúng như dự đoán trong plan: 2502 mẫu là quá ít
cho deep learning. Đây là kết quả hợp lệ để báo cáo, không phải bug.

**Bug đã phát hiện & sửa khi chạy thật**: Naive Bayes ban đầu chỉ đạt macro-F1 0.361 /
accuracy 0.359 (dưới cả baseline), dồn 303/328 negative vào neutral. Nguyên nhân: Laplace
smoothing dùng vocab RIÊNG từng lớp → lớp `neutral` ít dữ liệu có mẫu số nhỏ nhất → token lạ
được điểm cao nhất → mọi thứ trôi về neutral. Sửa sang **vocab toàn cục** → 0.782.

Test: **123 pass**. `report.html` tự chứa (0 URL ngoài).

## Câu hỏi chưa giải quyết
1. `neutral` giờ chỉ còn 9.8% (376 dòng) — đủ để model học lớp này không? Nếu macro-F1 của
   riêng lớp neutral quá thấp, cân nhắc gộp về bài toán 2 lớp pos/neg.
2. Có muốn soát lại phần `nguon_tag = gan-lai` trong `excel_tag_v2/` không? (2503 dòng)
3. Predict cho `excel_comment/` (~26k) hay cả `excel_comment21/` (~256k)? Chưa đo được tốc độ.
4. Sau khi có kết quả, có ghi `sentiment` ngược vào Mongo không? (đang ngoài scope)
5. Đây có phải đồ án cần báo cáo so sánh 3 thuật toán? Nếu có, P4 xuất thêm CSV metrics.
