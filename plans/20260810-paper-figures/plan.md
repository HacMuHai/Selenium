# Plan: Tách folder `paper/` sinh figure cho bài báo

## Mục tiêu

Từ codebase hiện tại, dựng một folder **`paper/` tự chứa** sinh ra toàn bộ hình
(biểu đồ + bảng) dạng **PNG 300dpi** để chèn thẳng vào Word, kèm một trang
**`gallery.html`** để preview tất cả hình trong một lần cuộn.

## Quyết định đã chốt

| Hạng mục | Chốt |
|---|---|
| Số lớp | **3 lớp** (negative / neutral / positive) — dùng lại `models_store/metadata.json` đã có, **không train lại** |
| Định dạng | PNG 300dpi, matplotlib |
| Bảng | Xuất **hết**: bảng mẫu dữ liệu, bảng metrics, bảng làm sạch — mỗi bảng vừa PNG vừa CSV |
| Preview | Một trang HTML gallery nhúng toàn bộ PNG |

## Phát hiện quan trọng

`src/analysis/` **đã tự chứa hoàn toàn** — không import `src.config`,
`src.services`, `src.repositories`, không đụng MongoDB / Selenium / FastAPI
(đã verify bằng grep toàn bộ import). Chỉ `src/analyze.py` (CLI) mới kéo
`src.config`. Nên việc tách folder chỉ là **copy + đổi prefix import**, không
phải viết lại logic.

Phần **không** mang sang `paper/`: `src/main.py`, `src/app.py`, `src/api/`,
`src/services/`, `src/repositories/`, `src/models/`, `src/dto/`, `src/config/`,
`tests/`, và các dependency `selenium` / `pymongo` / `fastapi` / `uvicorn`.

## Số liệu sẽ lên hình (từ `models_store/metadata.json`, trained 2026-07-31)

- Dataset: 3853 dòng thô → 3128 sau làm sạch (rỗng 3, trùng nội dung 722)
- Phân bố: negative 1637 / positive 1169 / neutral 322
- Split: train 2502 / test 626
- Baseline (luôn đoán `negative`): acc 0.524, macro-F1 0.229

| Model | macro-F1 | accuracy | train (s) |
|---|---|---|---|
| svm | 0.833 | 0.875 | 3.22 |
| nb | 0.782 | 0.850 | 0.06 |
| lstm | 0.751 | 0.792 | 9.40 |

---

## Phase 1 — Dựng khung `paper/`

```
paper/
├── README.md               # 2 lệnh: cài + chạy
├── requirements.txt        # pandas, scikit-learn, matplotlib, openpyxl, joblib, tensorflow
├── analysis/               # copy nguyên từ src/analysis/, đổi prefix import
│   ├── dataset.py  metrics.py  preprocessing.py  registry.py
│   ├── trainer.py  predictor.py
│   └── models/{base,naive_bayes,svm,lstm}.py
├── figures.py              # entrypoint: python -m paper.figures
├── style.py                # style matplotlib dùng chung
├── tables.py               # render bảng -> PNG + CSV
├── charts.py               # render biểu đồ -> PNG
├── gallery.py              # sinh gallery.html
├── data/                   # copy excel_tag_v2/ (44 file) + metadata.json
└── out/                    # kết quả: *.png, *.csv, gallery.html
```

Việc cần làm:
1. `cp -r src/analysis paper/analysis`, đổi `src.analysis` → `paper.analysis` trong mọi import.
2. Copy `excel_tag_v2/` → `paper/data/tagged/` và `models_store/metadata.json` → `paper/data/metadata.json`.
   Lý do copy chứ không trỏ đường dẫn ra ngoài: folder phải zip gửi đi được.
3. `paper/requirements.txt` chỉ giữ deps thật sự cần. **Thêm `matplotlib`** (repo chưa có).
4. Bỏ `report.py` khỏi bản copy — gallery HTML thay thế nó.

**Rủi ro**: font tiếng Việt trong matplotlib. Mặc định DejaVu Sans có đủ dấu
tiếng Việt nên OK, nhưng phải verify bằng một hình có chữ "Tiêu cực / Phân bố"
trước khi render cả loạt — nếu thấy ô vuông ▯ thì fallback sang font hệ thống.

## Phase 2 — `style.py`: style dùng chung

Một chỗ duy nhất định nghĩa: `dpi=300`, figsize, font size, bảng màu 3 lớp
(negative đỏ / neutral xám / positive xanh), màu baseline (đỏ đứt nét), grid mờ,
bỏ viền trên+phải. Mọi hình gọi qua đây để cả bộ figure nhìn như một hệ thống —
đây là thứ giám khảo nhìn thấy đầu tiên.

Hàm `save(fig, name)` ghi `out/<name>.png` ở 300dpi, `bbox_inches="tight"`,
nền trắng (không dùng transparent — Word sẽ ra nền đen khi in).

## Phase 3 — Bảng (`tables.py`)

Mỗi bảng xuất **cả PNG lẫn CSV** cùng tên. PNG để chèn Word ngay, CSV để bạn tự
chỉnh lại trong Excel nếu muốn format khác.

| File | Nội dung |
|---|---|
| `bang-mau-du-lieu` | 20 dòng mẫu, 2 cột `category \| text` — **đúng layout ảnh Hình 4.3 bạn gửi** (header vàng, chữ đỏ), nhưng 3 lớp: TieuCuc / TrungTinh / TichCuc |
| `bang-lam-sach` | Tổng dòng → bỏ rỗng → bỏ nhãn rác → bỏ mâu thuẫn → bỏ trùng → còn lại. Kèm cột % |
| `bang-phan-bo-nhan` | Số lượng + tỉ lệ từng lớp, cột train / test / tổng |
| `bang-metrics-tong-hop` | 3 model + baseline × (macro-F1, accuracy, thời gian train) |
| `bang-metrics-chi-tiet` | precision / recall / F1 / support cho từng lớp × từng model (bảng bắt buộc của bài báo ML) |
| `bang-vi-du-doan-sai` | 8 ví dụ model tốt nhất đoán sai, kèm nhãn thật / nhãn đoán — lấy từ `errors_sample` có sẵn trong metadata |

Render bằng `matplotlib.table` chứ không screenshot HTML, để chữ sắc nét ở 300dpi.

**Lưu ý**: cột `text` chứa comment dài (có dòng >200 ký tự). Phải wrap text và
cắt ở ~80 ký tự, nếu không bảng tràn ngang thành một dải mỏng vô dụng.

## Phase 4 — Biểu đồ (`charts.py`)

| File | Loại | Nội dung |
|---|---|---|
| `bd-phan-bo-nhan` | bar ngang | 1637 / 1169 / 322 — cho thấy dữ liệu **lệch lớp**, lý giải vì sao dùng macro-F1 |
| `bd-phan-bo-train-test` | bar nhóm | Kiểm chứng split có phân tầng: tỉ lệ train ≈ tỉ lệ test |
| `bd-so-sanh-model` | bar nhóm | macro-F1 + accuracy của 3 model, **kèm đường ngang đứt nét = baseline 0.229**. Đây là hình quan trọng nhất của bài |
| `bd-f1-tung-lop` | bar nhóm | F1 của từng lớp × từng model — lộ rõ `neutral` là lớp yếu nhất (NB chỉ 0.598) |
| `bd-confusion-nb`<br>`bd-confusion-svm`<br>`bd-confusion-lstm` | heatmap 3×3 | Ma trận nhầm lẫn, annotate số tuyệt đối + % theo hàng |
| `bd-thoi-gian-train` | bar (log scale) | 0.06s / 3.22s / 9.40s — đánh đổi độ chính xác vs chi phí |

Mọi biểu đồ so sánh model **phải vẽ đường baseline**. Không có nó, người đọc
không biết 0.833 là giỏi hay chỉ là đoán bừa.

Trục % dùng thang 0–1 nhất quán (không auto-scale), nếu không mắt sẽ đọc sai
mức chênh giữa các cột.

## Phase 5 — `gallery.html`

Trang tĩnh tự sinh, mở bằng double-click, **không cần server**:
- Mỗi hình một khối: ảnh + tên file + caption gợi ý (`Hình 4.x: ...`)
- Nút "Copy tên file" để bạn biết lấy file nào trong `out/`
- Nhóm theo 2 mục: **Bảng** và **Biểu đồ**
- Nhúng PNG bằng đường dẫn tương đối (`out/*.png`), không base64 → mở nhanh,
  và bạn kéo thả ảnh từ folder vào Word được luôn

Không đụng vào `src/analysis/report.py` — trang đó vẫn phục vụ API như cũ.

## Phase 6 — Đóng gói + kiểm chứng

1. `paper/README.md`: đúng 2 lệnh — `pip install -r paper/requirements.txt` và
   `python -m paper.figures`.
2. Chạy thật, verify: đủ 13 PNG + 6 CSV trong `out/`, mở `gallery.html` xem
   tiếng Việt không lỗi font, không hình nào bị cắt chữ.
3. Verify `paper/` chạy được khi tách rời: `cd /tmp && cp -r paper . && python -m paper.figures`
   — nếu còn import nào trỏ về `src.` thì bước này sẽ lộ ra.

## Câu hỏi để lại cho lúc chạy

- Caption `Hình 4.x` đánh số theo thứ tự nào là do bố cục bài báo của bạn —
  mình sẽ để caption gợi ý trong gallery, bạn tự đổi số khi chèn Word.
- Nếu sau khi xem gallery bạn thấy thiếu hình nào (ví dụ: top từ đặc trưng theo
  lớp, đường học của LSTM), nói mình bổ sung — cả hai đều lấy được từ dữ liệu
  hiện có mà không cần train lại.
