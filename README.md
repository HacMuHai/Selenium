# Selenium Scraper

Web scraper sử dụng Selenium để crawl comments từ thegioididong.com và lưu vào MongoDB.

## Cấu trúc dự án

```
Selenium/
├── src/
│   ├── models/          # Data models
│   │   ├── __init__.py
│   │   └── product.py   # Product, Comment models
│   │
│   ├── config/          # Configuration
│   │   ├── __init__.py
│   │   ├── database.py  # MongoDB configuration
│   │   └── driver.py     # Selenium WebDriver configuration
│   │
│   ├── repositories/    # Data access layer
│   │   ├── __init__.py
│   │   └── comment_repository.py  # MongoDB operations
│   │
│   ├── services/        # Business logic layer
│   │   ├── __init__.py
│   │   └── scraper_service.py     # Scraping logic
│   │
│   ├── utils/           # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py   # Helper functions
│   │
│   ├── main.py          # Entry point
│   └── run.py           # Development runner (hot reload)
│
├── requirements.txt
└── README.md
```

## Design Pattern

Dự án sử dụng **Repository Pattern** và **Service Layer Pattern**:

- **Models**: Định nghĩa data structures
- **Config**: Quản lý cấu hình (database, driver)
- **Repositories**: Data access layer - tách biệt logic truy cập database
- **Services**: Business logic layer - xử lý nghiệp vụ
- **Utils**: Helper functions

## Cài đặt

### 🪟 Cài đặt trên Windows (Máy mới)

**Xem hướng dẫn chi tiết:** [SETUP_WINDOWS.md](./SETUP_WINDOWS.md)

**Hoặc sử dụng script tự động:**
1. Double-click file `setup.bat` để tự động cài đặt
2. Sau đó double-click `run.bat` để chạy dự án

### Cách 1: Sử dụng virtual environment (khuyến nghị)

```bash
# Kích hoạt virtual environment
source venv/bin/activate  # Trên macOS/Linux
# hoặc
venv\Scripts\activate     # Trên Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### Cách 2: Tạo virtual environment mới

Nếu chưa có venv:

```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate  # Trên macOS/Linux
# hoặc
venv\Scripts\activate     # Trên Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### Lưu ý

- Trên macOS, Python có thể yêu cầu sử dụng virtual environment
- Luôn activate venv trước khi chạy code hoặc cài đặt packages

## Sử dụng

### Trên Windows (dễ dàng):

- **Chạy scraping:** Double-click `run.bat`
- **Development mode:** Double-click `run_dev.bat`

### Trên macOS/Linux:

### Chạy development mode (hot reload):

```bash
python src/run.py
```

Sau đó nhấn Enter để reload code mà không cần restart driver.

### Chạy trực tiếp:

```bash
python src/main.py
```

## Cấu hình MongoDB

Mặc định: `mongodb://localhost:27017/`

Sửa trong `src/config/database.py` nếu cần thay đổi.

## Lưu ý

- Đảm bảo MongoDB đang chạy trước khi chạy scraper
- Driver sẽ tự động được quản lý và tái sử dụng trong development mode
