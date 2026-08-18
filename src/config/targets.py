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

CELLPHONES = {
    "cps-dtdd": [
        "https://cellphones.com.vn/mobile.html",
    ],
    "cps-may-tinh-bang": [
        "https://cellphones.com.vn/tablet.html",
    ],
    "cps-laptop": [
        "https://cellphones.com.vn/laptop.html",
    ],
    "cps-phu-kien": [
        "https://cellphones.com.vn/phu-kien.html",
        "https://cellphones.com.vn/phu-kien/camera.html",
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
}

DEFAULT_CATEGORY = "tgdd-phu-kien"
