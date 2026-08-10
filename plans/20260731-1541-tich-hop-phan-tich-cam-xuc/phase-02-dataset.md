# Phase 02 — Dataset: đọc `excel_tag_v2/`, làm sạch, khử trùng, split

## Context links
- [plan.md](./plan.md) · [phase-01-nen-tang.md](./phase-01-nen-tang.md)
- [scout-01-hien-trang.md](./scout/scout-01-hien-trang.md) §"Dữ liệu đã gán nhãn"
- [researcher-01-tieng-viet-va-lech-lop.md](./research/researcher-01-tieng-viet-va-lech-lop.md) §4

## Overview
- Date: 2026-07-31
- Description: Gom 44 file Excel trong `excel_tag_v2/` thành 1 DataFrame sạch, khử trùng, chia
  train/test có phân tầng. Kèm module đọc thư mục Excel chưa gán nhãn cho phần predict hàng loạt.
- Priority: P0
- Implementation status: DONE (2026-07-31)
- Review status: SELF-REVIEWED; 123 test pass

## Key Insights
- **Rò rỉ dữ liệu là rủi ro số 1 của phase này.** 3853 dòng, số nội dung duy nhất ít hơn đáng kể.
  Split trước khi khử trùng → cùng câu comment nằm ở cả train lẫn test → điểm số ảo cao,
  toàn bộ so sánh 3 model trở nên vô nghĩa. **Khử trùng TRƯỚC, split SAU.**
- Khử trùng phải theo **nội dung đã chuẩn hoá** (`normalize_text`), không phải chuỗi thô —
  "Tốt!!!" và "tốt" là cùng một câu.
- Nội dung bị gán 2 nhãn khác nhau: **bỏ hẳn cả nhóm**, không chọn bừa nhãn nào. Ghi log số lượng.
  (`excel_tag_v2` đã sạch hơn nhiều so với `excel_tag` gốc vì phần gán lại dùng chung hàm chuẩn hoá,
  nhưng phần `nguon_tag=giu-nguyen` của user vẫn có thể còn vài cặp mâu thuẫn.)
- `excel_tag_v2` có header 7 cột: `link, name_item, comments_id, comments_content, tag, tag_cu,
  nguon_tag`. Chỉ đọc `tag`; `tag_cu`/`nguon_tag` là cột truy vết, KHÔNG dùng để train.
  Đọc theo **tên cột từ header**, không hardcode vị trí.
- Nhãn có thể lẫn khoảng trắng/hoa thường → chuẩn hoá nhãn rồi mới lọc.
- Thư mục chưa gán nhãn có tới ~256k dòng → hàm đọc phải là **generator theo file**, không nạp hết.

## Requirements
1. `load_tagged_dataset(tag_dir)` → DataFrame `[comment_id, text, sentiment]` đã làm sạch.
2. Thống kê quá trình làm sạch trả kèm (bao nhiêu dòng vào, bỏ vì lý do gì, còn lại bao nhiêu).
3. `split_dataset(df, test_size, seed)` → `(train_df, test_df)` có `stratify`.
4. `iter_untagged_rows(input_dir)` → generator theo từng file, không nạp hết vào RAM.
5. Test với file Excel tạo tại chỗ trong `tmp_path` (không phụ thuộc `excel_tag_v2/` thật).

## Architecture
```
src/analysis/dataset.py
    LABELS = ("negative", "neutral", "positive")

    @dataclass
    class CleaningStats:
        total_rows, dropped_empty, dropped_bad_label,
        dropped_duplicate, dropped_conflict, final_rows,
        label_counts: dict[str, int]

    load_tagged_dataset(tag_dir: str) -> tuple[pd.DataFrame, CleaningStats]
    split_dataset(df, test_size=0.2, seed=42) -> tuple[pd.DataFrame, pd.DataFrame]
    iter_untagged_files(input_dir: str) -> Iterator[tuple[Path, list[dict]]]
```
Cột chuẩn của DataFrame: `comment_id`, `text` (thô), `norm_text` (đã chuẩn hoá), `sentiment`.
Giữ cả `text` thô vì LSTM/TF-IDF sẽ tự chuẩn hoá theo cách riêng ở P3.

## Related code files
- THÊM: `src/analysis/dataset.py`, `tests/test_dataset.py`
- ĐỌC (không sửa): `excel_tag_v2/*.xlsx` (44 file). Predict: `excel_comment/`, `excel_comment21/`
  — **KHÔNG dùng `excel_comment3/`**, đó là nguồn của `excel_tag` (87.6% id trùng).
- DÙNG LẠI: `src/analysis/preprocessing.py::normalize_text` (P1)

## Implementation Steps
1. Đọc từng file bằng `openpyxl.load_workbook(fp, read_only=True)` — 44 file × ~88 dòng nên
   nhanh, nhưng `read_only=True` là bắt buộc để không ngốn RAM khi mở rộng.
2. Map cột **theo tên trong header**, không theo vị trí:
   ```python
   header = [str(c).strip().lower() if c else "" for c in next(rows)]
   idx_id      = header.index("comments_id")
   idx_text    = header.index("comments_content")
   idx_tag     = header.index("tag")        # KHONG lay tag_cu / nguon_tag
   ```
   File nào thiếu cột bắt buộc → log WARNING, bỏ qua cả file, đếm vào stats.
3. Chuẩn hoá nhãn: `str(tag).strip().lower()`; không thuộc `LABELS` (kể cả `None`) → `dropped_bad_label`.
4. Bỏ dòng `text` rỗng/chỉ khoảng trắng sau `normalize_text` → `dropped_empty`.
5. **Khử trùng theo `norm_text`** (không phải `comment_id` — id trùng chỉ là hệ quả của file
   chồng nhau, còn nội dung trùng mới là thứ gây rò rỉ):
   ```python
   grouped = df.groupby("norm_text")["sentiment"].nunique()
   conflict = set(grouped[grouped > 1].index)      # 1 noi dung, >1 nhan -> bo ca nhom
   df = df[~df["norm_text"].isin(conflict)]
   df = df.drop_duplicates(subset="norm_text", keep="first")
   ```
   Đếm `dropped_conflict` và `dropped_duplicate` riêng biệt.
6. `split_dataset`: `sklearn.model_selection.train_test_split(df, test_size=..., random_state=seed,
   stratify=df["sentiment"])`. **`stratify` là bắt buộc** — lớp `neutral` chỉ ~9.8%, split ngẫu
   nhiên có thể cho tập test lệch nặng.
7. `iter_untagged_files`: yield `(path, rows)` theo từng file. Mỗi `rows` là list dict
   `{link, name_item, comments_id, comments_content}`. Bỏ dòng nội dung rỗng.
8. Log ở mức INFO một dòng tổng kết:
   `"Dataset: 3853 dòng -> N sau khử trùng (bỏ K mâu thuẫn nhãn, ...); phân bố: ..."`.
9. Test dùng `openpyxl.Workbook()` tạo 3-4 file Excel giả trong `tmp_path`, cố tình cài sẵn:
   1 dòng trùng nội dung khác cách viết hoa, 1 cặp mâu thuẫn nhãn, 1 nhãn rác, 1 dòng rỗng,
   1 file có thêm cột `tag_cu`/`nguon_tag`.

## Todo list
- [x] dataset.py: load_tagged_dataset + CleaningStats
- [x] Map cột theo tên header (xử lý file 3 cột `tag`)
- [x] Khử trùng theo norm_text + loại nhóm mâu thuẫn nhãn
- [x] split_dataset có stratify
- [x] iter_untagged_files (generator theo file)
- [x] tests/test_dataset.py với Excel giả trong tmp_path

## Success Criteria
- Chạy thật trên `excel_tag_v2/`: `total_rows == 3853`, `label_counts` giữ đúng 3 nhãn với
  phân bố xấp xỉ negative 1764 / positive 1713 / neutral 376.
- **Không rò rỉ**: `set(train_df.norm_text) & set(test_df.norm_text) == set()` — assert trong test.
- `stratify` hoạt động: tỷ lệ từng lớp ở train và test lệch nhau < 2 điểm phần trăm.
- Đọc đúng cột `tag`, KHÔNG nhầm sang `tag_cu`.
- `iter_untagged_files("excel_comment")` yield đúng 266 tuple, không nạp hết vào RAM.
- `python -m pytest tests/test_dataset.py -q` → pass.

## Risk Assessment
- **Rò rỉ dữ liệu nếu split trước khử trùng** → HIGH. Có assert riêng trong test để chặn.
- **Khử trùng làm mất dữ liệu** → ghi rõ con số ra log và HTML report để người đọc biết.
- **`groupby` trên 3853 dòng** không vấn đề, nhưng nếu sau này tag nhiều hơn thì vẫn ổn (O(n)).
- **pandas 3.0.5 là bản rất mới** → tránh API mới lạ, dùng những thứ ổn định lâu năm
  (`groupby`, `drop_duplicates`, `isin`).
- **File Excel hỏng giữa chừng** → bọc try/except quanh từng file, log WARNING, tiếp tục file khác;
  không để 1 file hỏng giết cả pipeline.

## Security Considerations
- `input_dir` từ CLI arg → resolve về đường dẫn tuyệt đối và kiểm tra là thư mục tồn tại;
  không nối chuỗi đường dẫn thô.
- Chỉ đọc `*.xlsx`, bỏ qua file khác trong thư mục.
- Không log nội dung comment, chỉ log số lượng.

## Next steps
→ Phase 04 dùng `load_tagged_dataset` + `iter_untagged_files`.
