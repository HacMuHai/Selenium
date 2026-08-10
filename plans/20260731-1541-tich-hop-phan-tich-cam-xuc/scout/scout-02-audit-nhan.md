# Scout 02 — Audit chất lượng nhãn `excel_tag/` và kết quả gán lại (2026-07-31)

## Cách audit

Trích **mẫu mù 120 dòng** (phân tầng theo nhóm file early/mid/late, seed cố định), gán nhãn
độc lập **không nhìn nhãn của user**, rồi mới đối chiếu. Tiêu chí: `positive` = khen/hài lòng ·
`negative` = chê/phàn nàn/báo lỗi · `neutral` = câu hỏi thuần tuý, thông tin, không đánh giá.

## Kết quả: 35.8% đồng thuận tổng thể — nhưng lỗi tập trung ở đúng một chỗ

| User gán | Tôi đồng ý | Tỷ lệ |
|---|---|---|
| `negative` (21) | 19 | **90%** |
| `positive` (9) | 9 | **100%** |
| `neutral` (90) | 15 | **17%** |

Ma trận (hàng = user, cột = tôi):

```
              negative   neutral  positive
negative            19         0         2
neutral             33        15        42
positive             0         0         9
```

**Kết luận: nhãn `positive`/`negative` của user đáng tin. `neutral` là thùng rác.**
83% những gì được gán neutral thực ra là positive hoặc negative rõ ràng — không phải ca ranh giới:
`"Tốt"`, `"Sản phẩm tốt, chất lượng, giao hàng nhanh."`, `"Dùng rất tệ"`,
`"Máy in mơi mà chua được 100 trang đã hết mực rồi."` đều đang là neutral.

15 dòng neutral tôi ĐỒNG Ý thì đúng là trung tính thật (`"Chuyển tắt đài FM khỏi màn hình bằng
cách nào vậy"`, `"E muốn hỏi giá thay màn hình"`) → user *có* khái niệm neutral đúng, chỉ là
phần lớn thời gian không áp dụng.

## Nhãn trôi theo thứ tự file (mệt mỏi khi gán nhãn)

| Nhóm file | Đồng thuận | Tỷ lệ neutral |
|---|---|---|
| early (1–12) | 50.0% | 65% |
| mid (13–28) | 32.5% | 78% |
| late (29–44) | 25.0% | 83% |

File 21 và 37 đạt **97% neutral**. Càng về sau càng gán neutral cho xong.

## File #1 có 3 phiên bản mâu thuẫn

`comments_export_1_tagged.xlsx` / `_v2` / `_v3` — **cùng đúng 100 `comments_id`**, nhãn lệch nặng:

| Bản | neutral | negative | positive | Ghi chú |
|---|---|---|---|---|
| `_tagged` | 43 | 34 | 22 | +1 nhãn rỗng; header hỏng 7 cột (`tag` ×3) |
| `_v2` | 26 | 50 | 24 | lệch v1 **24/100** |
| `_v3` | 53 | 30 | 17 | lệch v2 **37/100** |

Ví dụ cùng comment: `negative → neutral`, `positive → negative`, `negative → positive`.
→ **Quyết định (user chốt): chỉ dùng `_v3`**, bỏ `_tagged` và `_v2`.

## Truy nguồn: `excel_tag` đến từ `excel_comment3`, KHÔNG phải `excel_comment`

Đối chiếu theo `comments_id`:

| Thư mục | Số id duy nhất | Giao với `excel_tag` |
|---|---|---|
| `excel_tag/` | 4400 | — |
| `excel_comment3/` | 21264 | **3853 (87.6%)** |
| `excel_comment/` | 13207 | **0** |

→ `excel_comment3/` là **nguồn chưa gán nhãn** của `excel_tag`, không phải tập để predict.
Loại khỏi danh sách predict (user xác nhận).

## Gán lại toàn bộ (user chốt phương án)

Giữ nguyên 974 dòng `positive`/`negative` của user (đã chứng minh đúng 90–100%).
Gán lại toàn bộ 2879 dòng `neutral` → khử trùng còn **2236 text duy nhất** để gán.

**Độ tin cậy lặp lại của người gán (tôi)**: đối chiếu 90 dòng trùng giữa mẫu audit ban đầu và
lượt gán lại (hai lượt độc lập, cách nhau nhiều lô) → **90/90 = 100%**.

### Kết quả: `excel_tag_v2/` (44 file)

| | Trước (`excel_tag`) | Sau (`excel_tag_v2`) |
|---|---|---|
| Tổng dòng | 3853 | 3853 |
| `negative` | 639 (16.6%) | **1764 (45.8%)** |
| `positive` | 335 (8.7%) | **1713 (44.5%)** |
| `neutral` | 2879 (74.7%) | **376 (9.8%)** |

**2503 dòng đã đổi nhãn.**

Schema output giữ 4 cột gốc + 3 cột mới để truy vết:
`link, name_item, comments_id, comments_content, tag, tag_cu, nguon_tag`
(`nguon_tag` ∈ `giu-nguyen` | `gan-lai`).

## Ảnh hưởng tới thiết kế

- **Baseline đổi hẳn**: "luôn đoán lớp đa số" giờ chỉ đạt **45.8% accuracy** (trước là 76%),
  macro-F1 baseline ≈ **0.209**. Model bây giờ *phải* thực sự học mới vượt được.
- Lệch lớp gần như biến mất giữa pos/neg; chỉ còn `neutral` là lớp thiểu số (9.8%) →
  vẫn cần `class_weight` và macro-F1, nhưng rủi ro "sụp về lớp đa số" giảm mạnh.
- Số nội dung mâu thuẫn nhãn còn rất ít (chỉ trong phần `giu-nguyen` của user) vì phần gán lại
  dùng cùng một hàm chuẩn hoá → cùng text luôn cùng nhãn.
