# Chỉ mục `data_tagged/`

Dữ liệu đã gán nhãn, **4.762 dòng**, mỗi danh mục sản phẩm một file.

Sinh tự động: `python -m src.tag_index`. Sửa Excel xong chạy lại để cập nhật bảng.

File này nằm cùng thư mục với dữ liệu để đọc là biết ngay có gì, không cần mở Excel.

## Cấu trúc file

Mỗi file có đúng 5 cột, không có cột nào khác:

| Cột | Nội dung |
|---|---|
| `link` | URL sản phẩm trên thegioididong.com |
| `name_item` | Tên sản phẩm |
| `comments_id` | Mã bình luận, duy nhất trong toàn bộ dữ liệu |
| `comments_content` | Nội dung bình luận, nguyên văn |
| `tag` | `negative` · `neutral` · `positive` |

Hàng 1 là tiêu đề, dữ liệu từ hàng 2 — cột **Hàng** dưới đây là số hàng trong Excel.

## Danh mục

| # | Danh mục | File | Hàng | Dòng | Sản phẩm | negative | neutral | positive |
|---|---|---|---|---|---|---|---|---|
| 01 | [dtdd](https://www.thegioididong.com/dtdd) | `01-dtdd.xlsx` | 2–2064 | 2.063 | 113 | 1.115 | 233 | 715 |
| 02 | [loa-laptop](https://www.thegioididong.com/loa-laptop) | `02-loa-laptop.xlsx` | 2–910 | 909 | 90 | 321 | 55 | 533 |
| 03 | [may-in](https://www.thegioididong.com/may-in) | `03-may-in.xlsx` | 2–796 | 795 | 27 | 216 | 28 | 551 |
| 04 | [laptop](https://www.thegioididong.com/laptop) | `04-laptop.xlsx` | 2–449 | 448 | 92 | 229 | 48 | 171 |
| 05 | [dong-ho-thong-minh](https://www.thegioididong.com/dong-ho-thong-minh) | `05-dong-ho-thong-minh.xlsx` | 2–186 | 185 | 21 | 108 | 33 | 44 |
| 06 | [muc-in](https://www.thegioididong.com/muc-in) | `06-muc-in.xlsx` | 2–145 | 144 | 15 | 17 | 3 | 124 |
| 07 | [may-tinh-bang](https://www.thegioididong.com/may-tinh-bang) | `07-may-tinh-bang.xlsx` | 2–128 | 127 | 21 | 40 | 19 | 68 |
| 08 | [man-hinh-may-tinh](https://www.thegioididong.com/man-hinh-may-tinh) | `08-man-hinh-may-tinh.xlsx` | 2–79 | 78 | 20 | 30 | 11 | 37 |
| 09 | [may-tinh-de-ban](https://www.thegioididong.com/may-tinh-de-ban) | `09-may-tinh-de-ban.xlsx` | 2–6 | 5 | 5 | 4 | 1 | 0 |
| 10 | [may-choi-game-cam-tay](https://www.thegioididong.com/may-choi-game-cam-tay) | `10-may-choi-game-cam-tay.xlsx` | 2–5 | 4 | 3 | 1 | 0 | 3 |
| 11 | [gia-treo-man-hinh](https://www.thegioididong.com/gia-treo-man-hinh) | `11-gia-treo-man-hinh.xlsx` | 2–5 | 4 | 1 | 4 | 0 | 0 |
| | **Tổng** | | | **4.762** | | **2.085** | **431** | **2.246** |

## Số thực sự vào huấn luyện

`load_tagged_dataset()` bỏ dòng rỗng, dòng mâu thuẫn nhãn và **trùng nội dung**, nên
thấp hơn tổng ở trên:

| Bước | Dòng |
|---|---|
| Tổng thu thập | 4.762 |
| Bỏ: nội dung rỗng sau chuẩn hoá | 3 |
| Bỏ: nhãn không hợp lệ | 0 |
| Bỏ: cùng nội dung nhưng mâu thuẫn nhãn | 0 |
| Bỏ: trùng lặp nội dung | 722 |
| **Còn lại để huấn luyện** | **4.037** |

Phân bố sau làm sạch: negative 1.958 · neutral 377 · positive 1.702

## Lưu ý khi sửa tay

- **Tên file và số lượng file không quan trọng.** Loader đọc mọi `*.xlsx` trong thư mục
  theo TÊN CỘT, không theo tên file hay vị trí cột. Gộp thêm hay tách nhỏ đều chạy.
- **Thứ tự dòng thì quan trọng.** Đảo thứ tự làm phép chia train/test khác đi và mọi chỉ
  số trong báo cáo đổi theo. Sửa nội dung tại chỗ thì không ảnh hưởng.
- File thiếu một trong ba cột `comments_id` / `comments_content` / `tag` bị **bỏ qua cả
  file**, chỉ ghi WARNING chứ không dừng. Sau khi sửa, chạy `python -m src.analyze train`
  rồi xem `skipped_files` trong log có rỗng không.
- File `.xlsx` bị `.gitignore` chặn nên không nằm trong repo; riêng `README.md` này
  thì có, để người clone repo về vẫn biết dữ liệu gồm những gì.
