# Hình cho bài báo — Phân tích cảm xúc bình luận tiếng Việt

Folder này **tự chứa**: zip lại gửi đi vẫn chạy được. Không crawl, không kết nối
MongoDB, không dựng server — chỉ đọc dữ liệu có sẵn và vẽ hình.

## Chạy

```bash
./paper/run.sh                     # macOS / Linux
paper\run.bat                      # Windows
```

Script chạy được từ **bất kỳ thư mục nào** và tự tìm Python (ưu tiên `venv/` của
repo). Lần đầu, nếu báo thiếu thư viện thì cài theo đúng lệnh nó in ra:

```bash
venv/bin/python -m pip install -r paper/requirements.txt
```

Kết quả nằm trong `paper/out/`. Mở `paper/out/index.html` bằng trình duyệt để
xem hết một lượt rồi lấy hình cần dùng.

**`out/` tự chứa** — zip riêng mình nó gửi cho người khác là xem được ngay, không
cần repo, không cần cài gì:

```text
out/
├── index.html      # mở file này
├── bang/           # 9 bảng (.png)
├── bieu-do/        # 8 biểu đồ (.png)
├── csv/            # 9 bảng dạng .csv để mở bằng Excel
└── anh-mau/        # 7 ảnh mẫu từ bài tham khảo, để đối chiếu
```

Trong trang, hình nào có ảnh mẫu tương ứng sẽ xếp **hai cột**: kết quả của bạn
bên trái, ảnh mẫu bên phải. Ảnh mẫu chỉ để đối chiếu **bố cục và cách trình bày** —
số liệu hai bên không so trực tiếp được vì khác tập dữ liệu và khác số lớp.

Mỗi lần chạy, `out/` được **xoá sạch rồi tạo lại**, nên không bao giờ lẫn file cũ.

## Chia sẻ bằng link

Đang chạy tại **<https://hacmuhai.github.io/Selenium/>**

```bash
./paper/run.sh && ./paper/deploy.sh pages     # cập nhật link trên
./paper/deploy.sh tunnel                      # link tạm, chỉ sống khi máy đang chạy
```

`deploy.sh pages` đẩy nội dung `out/` lên nhánh `gh-pages` (ghi đè mỗi lần, không
mang theo lịch sử repo). Không cần domain riêng.

**Ai có link đều xem được** — GitHub Pages không đặt được mật khẩu. Đừng đưa lên
đây thứ gì chưa muốn công khai.

Thêm `--skip-sample` để bỏ bảng mẫu dữ liệu và chạy nhanh hơn (bảng đó là thứ
duy nhất phải đọc 44 file Excel).

### Chạy thẳng bằng Python, không qua script

Phải đứng ở thư mục **cha** của `paper/` thì Python mới nhận `paper` là package,
và trên macOS thường không có lệnh `python` trần — dùng `python3`:

```bash
cd /đường/dẫn/tới/Selenium      # thư mục CHỨA paper/, không phải paper/
venv/bin/python -m paper.figures
```

## Kết quả sinh ra

Mỗi biểu đồ một PNG **300 dpi**; mỗi bảng một PNG **kèm một CSV cùng tên** để tự
định dạng lại trong Excel nếu cần.

Ảnh **không vẽ sẵn tiêu đề** — caption thuộc về Word, in kèm vào ảnh sẽ thành
trùng lặp. Caption gợi ý nằm trong `index.html`, bấm "Copy caption" là lấy được.

**9 bảng** (`bang/`)

| File | Nội dung | Ảnh mẫu |
|---|---|---|
| `bang-mau-du-lieu` | 21 dòng mẫu, 2 cột `category \| text` | Hình 4.3 |
| `bang-comment-theo-lop` | Bình luận tích cực / tiêu cực đặt cạnh nhau | Hình 4.4 |
| `bang-tien-xu-ly` | Gốc → sau chuẩn hoá → sau tách từ (bỏ stopword) | Hình 4.6 |
| `bang-lam-sach` | Phễu làm sạch: 3.853 dòng thô → 3.128 dòng dùng được | |
| `bang-phan-bo-nhan` | Số lượng và tỉ lệ từng lớp, tách train / test | |
| `bang-precision-recall` | Precision / Recall theo lớp + thời gian huấn luyện | Bảng 5.2 |
| `bang-fscore` | F-score từng lớp + trung bình + baseline | Bảng 5.5 |
| `bang-metrics-chi-tiet` | Precision / Recall / F1 / Support theo từng lớp | |
| `bang-vi-du-doan-sai` | 8 trường hợp mô hình tốt nhất dự đoán sai | |

**8 biểu đồ** (`bieu-do/`)

| File | Nội dung |
|---|---|
| `bd-phan-bo-nhan` | Phân bố nhãn — cho thấy dữ liệu lệch lớp |
| `bd-phan-bo-train-test` | Kiểm chứng split có phân tầng |
| `bd-so-sanh-model` | macro-F1 + accuracy của 3 mô hình, có đường baseline |
| `bd-f1-tung-lop` | F1 từng lớp × từng mô hình + cột trung bình (khớp Biểu đồ 5.1/5.3) |
| `bd-confusion-{nb,svm,lstm}` | Ma trận nhầm lẫn của từng mô hình |
| `bd-thoi-gian-train` | Chi phí huấn luyện (thang log) |

## Dữ liệu đầu vào

- `data/metadata.json` — kết quả huấn luyện đã lưu. **Mọi con số trên hình đọc từ
  đây**, không train lại, nên chạy bao nhiêu lần cũng ra kết quả giống hệt.
- `data/tagged/` — 44 file Excel đã gán nhãn, chỉ dùng cho bảng mẫu dữ liệu.

## Số liệu tóm tắt

3.853 dòng thô → **3.128** dòng sau làm sạch (bỏ 722 dòng trùng nội dung).
Phân bố: tiêu cực 1.637 / tích cực 1.169 / trung lập 322 — lệch lớp rõ, nên
**macro-F1 mới là chỉ số chính**, không phải accuracy. Split 2.502 / 626.

| Mô hình | macro-F1 | accuracy | train |
|---|---|---|---|
| SVM | **0,833** | **0,875** | 3,22 s |
| Naive Bayes | 0,782 | 0,850 | 0,06 s |
| LSTM | 0,751 | 0,792 | 9,40 s |
| *Baseline (luôn đoán "tiêu cực")* | *0,229* | *0,524* | – |

## Ghi chú khi viết bài

- Số thứ tự hình trong `index.html` chỉ để tham chiếu nhanh. Đánh số lại theo
  bố cục chương của bạn khi chèn vào Word.
- Hình dùng font **Times New Roman** để khớp body text của báo cáo. Nếu máy
  không có font này, `style.py` tự chọn font khác còn đủ dấu tiếng Việt.
- Số thập phân dùng **dấu phẩy** (0,833) theo chuẩn tiếng Việt.
- Ba lớp gọi là **Tiêu cực / Trung lập / Tích cực**. Dùng "trung lập" thay vì
  "trung tính" vì đây là bình luận không nghiêng về bên nào (thường là câu hỏi),
  không phải "không có cảm xúc".
- Trong `index.html`, **bấm vào ảnh** để phóng to, bấm tiếp để xem đúng cỡ 300 dpi.

## Cấu trúc

```text
paper/
├── run.sh / run.bat  # chạy được từ bất kỳ thư mục nào
├── figures.py        # entrypoint + định nghĩa các bảng
├── charts.py         # các biểu đồ
├── tables.py         # bộ render bảng -> PNG + CSV
├── style.py          # font / màu / dpi dùng chung
├── gallery.py        # sinh trang preview
├── analysis/         # bản sao module phân tích (không phụ thuộc crawler)
├── data/             # metadata.json + Excel đã gán nhãn
├── samples/          # ảnh mẫu gốc từ bài tham khảo
└── out/              # kết quả (gửi riêng folder này là đủ)
```
