"""
Danh mục thegioididong để crawl. Chọn bằng `--category`, ghi đè bằng `--links`.
"""

CATEGORIES: dict[str, list[str]] = {
    "phu-kien": [
        "https://www.thegioididong.com/sac-cap",
        "https://www.thegioididong.com/chuong-trinh-phu-kien-laptop",
        "https://www.thegioididong.com/sac-dtdd",
        "https://www.thegioididong.com/tai-nghe",
        "https://www.thegioididong.com/loa-laptop",
        "https://www.thegioididong.com/phu-kien/apple",
    ],
    "dtdd": [
        "https://www.thegioididong.com/dtdd",
        "https://www.thegioididong.com/may-tinh-bang",
    ],
    "laptop-pc": [
        "https://www.thegioididong.com/laptop",
        "https://www.thegioididong.com/pc-may-in",
    ],
    "dong-ho": [
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
    "dong-ho-thong-minh": [
        "https://www.thegioididong.com/dong-ho-thong-minh-thoi-trang-sanh-dieu",
        "https://www.thegioididong.com/dong-ho-thong-minh-da-tien-ich",
        "https://www.thegioididong.com/dong-ho-thong-minh-the-thao-chuyen-nghiep",
        "https://www.thegioididong.com/dong-ho-thong-minh-tre-em",
    ],
    "camera": [
        "https://www.thegioididong.com/camera-giam-sat",
    ],
}

DEFAULT_CATEGORY = "phu-kien"
