"""
Gom `data_tagged/` theo danh mục sản phẩm và sinh `data_tagged/README.md`.

    python -m src.tag_index                 # gom lại + ghi tài liệu
    python -m src.tag_index --chi-doc       # chỉ ghi lại tài liệu, không đụng Excel

Vì sao gom theo danh mục: 54 file `tagged_*.xlsx` đánh số tuần tự không nói lên điều gì,
muốn biết bình luận máy in nằm đâu phải mở từng file. Một danh mục một file thì nhìn tên
là biết, và `README.md` đặt ngay trong thư mục cho biết mỗi danh mục có bao nhiêu dòng,
bao nhiêu nhãn mỗi loại - khỏi phải đọc lại toàn bộ dữ liệu mỗi lần cần con số.

CẢNH BÁO: gom lại làm ĐỔI THỨ TỰ DÒNG, kéo theo phép chia train/test khác đi và mọi chỉ
số trong báo cáo đổi theo. Chạy xong phải train lại. Không phải lỗi - chỉ là số khác.
"""
import argparse
import glob
import json
import logging
import re
from pathlib import Path

import pandas as pd

from src.analysis.dataset import load_tagged_dataset

logger = logging.getLogger(__name__)

TAG_DIR = Path("data_tagged")
DATA_DIR = Path("data")
# Tài liệu nằm NGAY TRONG thư mục dữ liệu, không phải docs/: mở thư mục ra là
# thấy luôn nó chứa gì, khỏi phải mở Excel lên đọc mới biết.
DOC = TAG_DIR / "README.md"

# 5 cột này là toàn bộ những gì loader cần + đủ để truy ngược về sản phẩm. Các cột
# `tag_cu` / `nguon_tag` của bản cũ đã bỏ: nhãn hiện tại là nhãn chốt, giữ lại nhãn
# nháp chỉ làm người đọc phân vân không biết cột nào mới là thật.
COLS = ["link", "name_item", "comments_id", "comments_content", "tag"]
LABELS = ("negative", "neutral", "positive")
BASE_URL = "https://www.thegioididong.com"


def _so(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _danh_muc() -> dict[str, str]:
    """comments_id -> danh mục, tra từ `link` trong `data/`."""
    ra: dict[str, str] = {}
    for path in sorted(DATA_DIR.glob("*.xlsx")):
        frame = pd.read_excel(path)
        cat = frame["link"].astype(str).str.extract(rf"{re.escape('thegioididong.com')}/([^/]+)/")[0]
        ra.update(zip(frame["comments_id"].astype(str), cat))
    return ra


def gom() -> list[dict]:
    """Đọc mọi Excel trong `data_tagged/`, ghi lại thành mỗi danh mục một file."""
    files = sorted(TAG_DIR.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"Không thấy file nào trong {TAG_DIR}")
    frame = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)

    thieu = [c for c in COLS if c not in frame.columns]
    if thieu:
        raise ValueError(f"Thiếu cột {thieu} - dừng để khỏi ghi đè dữ liệu bằng bản hỏng")

    frame["_cat"] = frame["comments_id"].astype(str).map(_danh_muc())
    la = frame["_cat"].isna().sum()
    if la:
        # Không đoán bừa: dòng không tra được danh mục là dấu hiệu data_tagged và data
        # đã lệch nhau, gom tiếp chỉ giấu vấn đề đi.
        raise ValueError(f"{la} dòng không tra được danh mục từ data/ - kiểm tra lại")

    for f in files:
        f.unlink()

    ra: list[dict] = []
    for i, cat in enumerate(frame["_cat"].value_counts().index, start=1):
        sub = frame[frame["_cat"] == cat][COLS].reset_index(drop=True)
        ten = f"{i:02d}-{cat}.xlsx"
        sub.to_excel(TAG_DIR / ten, index=False)
        dem = sub["tag"].value_counts()
        ra.append({
            "stt": i, "cat": cat, "file": ten, "n": len(sub),
            "sp": int(sub["name_item"].nunique()),
            **{l: int(dem.get(l, 0)) for l in LABELS},
        })
        logger.info("%s: %d dòng", ten, len(sub))
    return ra


def doc_hien_co() -> list[dict]:
    """Đọc lại thống kê từ các file đã gom, không ghi gì."""
    ra = []
    for i, path in enumerate(sorted(TAG_DIR.glob("*.xlsx")), start=1):
        sub = pd.read_excel(path)
        dem = sub["tag"].value_counts()
        ra.append({
            "stt": i, "cat": path.stem.split("-", 1)[-1], "file": path.name, "n": len(sub),
            "sp": int(sub["name_item"].nunique()),
            **{l: int(dem.get(l, 0)) for l in LABELS},
        })
    return ra


def viet_doc(muc: list[dict]) -> Path:
    tong = {k: sum(m[k] for m in muc) for k in ("n", *LABELS)}
    _, st = load_tagged_dataset(str(TAG_DIR))

    hang = "\n".join(
        f"| {m['stt']:02d} | [{m['cat']}]({BASE_URL}/{m['cat']}) | `{m['file']}` | "
        f"2–{m['n'] + 1} | {_so(m['n'])} | {_so(m['sp'])} | "
        f"{_so(m['negative'])} | {_so(m['neutral'])} | {_so(m['positive'])} |"
        for m in muc
    )
    phan_bo = " · ".join(f"{k} {_so(v)}" for k, v in sorted(st.label_counts.items()))

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(f"""# Chỉ mục `data_tagged/`

Dữ liệu đã gán nhãn, **{_so(tong['n'])} dòng**, mỗi danh mục sản phẩm một file.

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
{hang}
| | **Tổng** | | | **{_so(tong['n'])}** | | **{_so(tong['negative'])}** | \
**{_so(tong['neutral'])}** | **{_so(tong['positive'])}** |

## Số thực sự vào huấn luyện

`load_tagged_dataset()` bỏ dòng rỗng, dòng mâu thuẫn nhãn và **trùng nội dung**, nên
thấp hơn tổng ở trên:

| Bước | Dòng |
|---|---|
| Tổng thu thập | {_so(st.total_rows)} |
| Bỏ: nội dung rỗng sau chuẩn hoá | {_so(st.dropped_empty)} |
| Bỏ: nhãn không hợp lệ | {_so(st.dropped_bad_label)} |
| Bỏ: cùng nội dung nhưng mâu thuẫn nhãn | {_so(st.dropped_conflict)} |
| Bỏ: trùng lặp nội dung | {_so(st.dropped_duplicate)} |
| **Còn lại để huấn luyện** | **{_so(st.final_rows)}** |

Phân bố sau làm sạch: {phan_bo}

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
""", encoding="utf-8")
    return DOC


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(prog="python -m src.tag_index")
    p.add_argument("--chi-doc", action="store_true",
                   help="Chỉ ghi lại tài liệu, không gom lại Excel")
    args = p.parse_args()

    muc = doc_hien_co() if args.chi_doc else gom()
    path = viet_doc(muc)
    print(f"{len(muc)} danh mục · {_so(sum(m['n'] for m in muc))} dòng -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
