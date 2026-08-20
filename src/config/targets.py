"""
Danh mục để crawl. Chọn bằng `--category`, ghi đè bằng `--links`.

Tên nhóm có tiền tố sàn (`tgdd-`, `cps-`, `fpt-`) vì cùng một mặt hàng ba sàn đặt URL
khác nhau. Nhóm `*-tat-ca` gộp cả ba sàn cho tiện gom dữ liệu huấn luyện. Sàn được nhận
diện theo hostname nên trộn URL nhiều sàn trong một nhóm là hợp lệ.
"""

TGDD = {
    "tgdd-phu-kien": [
        "https://www.thegioididong.com/sac-cap",
        "https://www.thegioididong.com/chuong-trinh-phu-kien-laptop",
        "https://www.thegioididong.com/sac-dtdd",
        "https://www.thegioididong.com/tai-nghe",
        "https://www.thegioididong.com/loa-laptop",
        "https://www.thegioididong.com/phu-kien/apple",
    ],
    "tgdd-dtdd": [
        "https://www.thegioididong.com/dtdd",
        "https://www.thegioididong.com/may-tinh-bang",
    ],
    "tgdd-laptop-pc": [
        "https://www.thegioididong.com/laptop",
        "https://www.thegioididong.com/pc-may-in",
    ],
    "tgdd-dong-ho": [
        "https://www.thegioididong.com/dong-ho-deo-tay-nam",
        "https://www.thegioididong.com/dong-ho-deo-tay-nu",
        "https://www.thegioididong.com/dong-ho-deo-tay-casio",
        "https://www.thegioididong.com/dong-ho-deo-tay-citizen",
        "https://www.thegioididong.com/dong-ho-deo-tay-orient",
        "https://www.thegioididong.com/dong-ho-deo-tay-MVW",
        "https://www.thegioididong.com/dong-ho-deo-tay-elio",
        "https://www.thegioididong.com/dong-ho-deo-tay-tre-em",
        "https://www.thegioididong.com/khuyen-mai-dong-ho-chi-ban-online",
        "https://www.thegioididong.com/day-dong-ho",
    ],
    "tgdd-dong-ho-thong-minh": [
        "https://www.thegioididong.com/dong-ho-thong-minh-thoi-trang-sanh-dieu",
        "https://www.thegioididong.com/dong-ho-thong-minh-da-tien-ich",
        "https://www.thegioididong.com/dong-ho-thong-minh-the-thao-chuyen-nghiep",
        "https://www.thegioididong.com/dong-ho-thong-minh-tre-em",
    ],
    "tgdd-camera": [
        "https://www.thegioididong.com/camera-giam-sat",
    ],
}

# CellphoneS. MỌI URL dưới đây đã kiểm tay: mở trang, đếm lưới sản phẩm, đọc nhãn nút
# "Xem thêm" (số trong ngoặc là số sản phẩm nút báo lúc kiểm, 19/08/2026).
#
# Hai cạm bẫy đã vấp:
# - `phu-kien.html`, `do-gia-dung.html`, `do-choi-cong-nghe.html` là TRANG TỔNG, không có
#   lưới sản phẩm nào. Config cũ trỏ vào `phu-kien.html` nên nhóm đó luôn ra 0 sản phẩm.
#   Phải dùng danh mục con.
# - Danh mục con của trang tổng phần lớn là LỌC THEO HÃNG (`do-gia-dung/xiaomi`,
#   `do-gia-dung/lg`...) chồng lấn nhau. Ở đây chỉ lấy nhóm theo LOẠI sản phẩm.
CELLPHONES = {
    "cps-dtdd": [
        "https://cellphones.com.vn/mobile.html",              # ~939
    ],
    "cps-may-tinh-bang": [
        "https://cellphones.com.vn/tablet.html",              # ~211
    ],
    "cps-laptop": [
        "https://cellphones.com.vn/laptop.html",              # ~897
    ],
    "cps-man-hinh": [
        "https://cellphones.com.vn/man-hinh.html",            # ~587
    ],
    "cps-may-in": [
        "https://cellphones.com.vn/may-in.html",              # ~130
    ],
    "cps-may-tinh-de-ban": [
        "https://cellphones.com.vn/may-tinh-de-ban.html",     # ~116
    ],
    "cps-phu-kien": [
        "https://cellphones.com.vn/phu-kien/bao-da-op-lung.html",           # ~1518
        "https://cellphones.com.vn/phu-kien/chuot-ban-phim-may-tinh.html",  # ~675
        "https://cellphones.com.vn/phu-kien/sac-dien-thoai.html",           # ~628
        "https://cellphones.com.vn/phu-kien/balo-tui-chong-soc-laptop.html",# ~358
        "https://cellphones.com.vn/phu-kien/camera.html",                   # ~349
        "https://cellphones.com.vn/phu-kien/pin-du-phong.html",             # ~286
        "https://cellphones.com.vn/phu-kien/may-tinh-laptop.html",          # ~216
        "https://cellphones.com.vn/phu-kien/dien-thoai.html",               # ~115
        "https://cellphones.com.vn/phu-kien/gaming-gear.html",              # ~67
        "https://cellphones.com.vn/phu-kien/decor-setup.html",              # ~27
        "https://cellphones.com.vn/phu-kien/kinh-thong-minh.html",          # 18, không có nút
        "https://cellphones.com.vn/phu-kien/but-cam-ung.html",              # 15, không có nút
        "https://cellphones.com.vn/phu-kien/pin-tieu.html",                 # 14, không có nút
        "https://cellphones.com.vn/phu-kien/den-pin.html",                  # 6,  không có nút
    ],
    # Điện máy. `dien-may.html` chỉ là trang tổng; các danh mục con nằm ở CẤP 1
    # (`/may-giat.html`) chứ KHÔNG lồng dưới `/dien-may/`, trừ vài cái dưới `/may-giat/`.
    # Suy slug từ cây menu là sai - mọi URL dưới đây đều mở thử rồi mới ghi vào.
    "cps-dien-may": [
        "https://cellphones.com.vn/tivi.html",                          # ~538
        "https://cellphones.com.vn/may-giat.html",                      # ~227
        "https://cellphones.com.vn/tu-lanh.html",                       # ~218
        "https://cellphones.com.vn/may-lanh.html",                      # ~162
        "https://cellphones.com.vn/may-giat/may-giat-say.html",         # ~41
        "https://cellphones.com.vn/may-say-quan-ao.html",               # ~35
        "https://cellphones.com.vn/may-rua-chen-bat.html",              # ~30
        "https://cellphones.com.vn/may-giat/tu-cham-soc-quan-ao.html",  # 9,  không có nút
        "https://cellphones.com.vn/may-giat/thap-giat-say.html",        # 4,  không có nút
    ],
    "cps-gia-dung": [
        "https://cellphones.com.vn/do-gia-dung/quat.html",                  # ~245
        "https://cellphones.com.vn/do-gia-dung/noi-chien-khong-dau.html",   # ~93
        "https://cellphones.com.vn/do-gia-dung/ban-ui.html",                # ~88
        "https://cellphones.com.vn/do-gia-dung/may-cao-rau.html",           # ~64
    ],
}

FPTSHOP = {
    "fpt-dtdd": [
        "https://fptshop.com.vn/dien-thoai",
    ],
    "fpt-may-tinh-bang": [
        "https://fptshop.com.vn/may-tinh-bang",
    ],
    "fpt-laptop": [
        "https://fptshop.com.vn/may-tinh-xach-tay",
    ],
    "fpt-phu-kien": [
        "https://fptshop.com.vn/phu-kien",
        "https://fptshop.com.vn/phu-kien/tai-nghe",
    ],
}

CATEGORIES: dict[str, list[str]] = {
    **TGDD,
    **CELLPHONES,
    **FPTSHOP,
    "dtdd-tat-ca": TGDD["tgdd-dtdd"] + CELLPHONES["cps-dtdd"] + FPTSHOP["fpt-dtdd"],
    "phu-kien-tat-ca": (
        TGDD["tgdd-phu-kien"] + CELLPHONES["cps-phu-kien"] + FPTSHOP["fpt-phu-kien"]
    ),
    "laptop-tat-ca": (
        TGDD["tgdd-laptop-pc"] + CELLPHONES["cps-laptop"] + FPTSHOP["fpt-laptop"]
    ),
    # Gom cả sàn - dùng khi muốn crawl trọn một sàn trong một lần chạy.
    "cps-tat-ca": [url for urls in CELLPHONES.values() for url in urls],
    "fpt-tat-ca": [url for urls in FPTSHOP.values() for url in urls],
    "tgdd-tat-ca": [url for urls in TGDD.values() for url in urls],
}

DEFAULT_CATEGORY = "tgdd-phu-kien"
