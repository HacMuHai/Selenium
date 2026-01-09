# Hướng dẫn cài đặt và chạy dự án trên Windows

## Yêu cầu hệ thống

- Windows 10/11
- VSCode đã cài đặt
- Source code của dự án

## Các bước cài đặt

### Bước 1: Cài đặt Python

1. **Tải Python:**
   - Truy cập: https://www.python.org/downloads/
   - Tải phiên bản Python 3.11 hoặc 3.12 (khuyến nghị 3.11)
   - Chọn file `.exe` cho Windows (64-bit)

2. **Cài đặt Python:**
   - Chạy file `.exe` vừa tải
   - ✅ **QUAN TRỌNG:** Tích chọn "Add Python to PATH" ở màn hình đầu tiên
   - Chọn "Install Now" hoặc "Customize installation"
   - Nếu chọn Customize, đảm bảo tích chọn "pip" và "tcl/tk and IDLE"
   - Nhấn "Install" và chờ hoàn tất

3. **Kiểm tra cài đặt:**
   - Mở Command Prompt (cmd) hoặc PowerShell
   - Chạy lệnh:
     ```bash
     python --version
     ```
   - Nếu hiển thị version (ví dụ: Python 3.11.5) là thành công
   - Kiểm tra pip:
     ```bash
     pip --version
     ```

### Bước 2: Cài đặt Google Chrome

Selenium cần Chrome browser để chạy:

1. **Tải Chrome:**
   - Truy cập: https://www.google.com/chrome/
   - Tải và cài đặt Google Chrome

2. **Kiểm tra:**
   - Mở Chrome để đảm bảo đã cài đặt thành công

### Bước 3: Mở dự án trong VSCode

1. Mở VSCode
2. File → Open Folder
3. Chọn thư mục chứa source code (thư mục có file `requirements.txt`)

### Bước 4: Tạo Virtual Environment

1. **Mở Terminal trong VSCode:**
   - Nhấn `Ctrl + `` (backtick) hoặc
   - Menu: Terminal → New Terminal

2. **Tạo virtual environment:**
   ```bash
   python -m venv venv
   ```
   - Lệnh này sẽ tạo thư mục `venv` trong dự án

3. **Kích hoạt virtual environment:**
   ```bash
   venv\Scripts\activate
   ```
   - Sau khi kích hoạt, bạn sẽ thấy `(venv)` ở đầu dòng lệnh
   - **Lưu ý:** Mỗi lần mở terminal mới, cần chạy lại lệnh này

### Bước 5: Cài đặt Dependencies

1. **Đảm bảo virtual environment đã được kích hoạt** (thấy `(venv)` ở đầu dòng)

2. **Cài đặt các package:**
   ```bash
   pip install -r requirements.txt
   ```
   - Lệnh này sẽ cài đặt tất cả các thư viện cần thiết:
     - selenium
     - webdriver-manager
     - pymongo
     - fastapi
     - uvicorn
     - pydantic
     - openpyxl (để xử lý Excel)

3. **Chờ quá trình cài đặt hoàn tất** (có thể mất vài phút)

### Bước 6: Kiểm tra cài đặt

1. **Kiểm tra các package đã cài:**
   ```bash
   pip list
   ```
   - Bạn sẽ thấy danh sách các package đã cài

2. **Test import Python:**
   ```bash
   python -c "import selenium; print('Selenium OK')"
   python -c "import pymongo; print('MongoDB OK')"
   ```

## Chạy dự án

### Cách 1: Chạy trực tiếp (Scraping)

1. **Đảm bảo virtual environment đã kích hoạt:**
   ```bash
   venv\Scripts\activate
   ```

2. **Chạy script chính:**
   ```bash
   python src\main.py
   ```
   - Script sẽ bắt đầu scrape dữ liệu từ thegioididong.com
   - Dữ liệu sẽ được lưu vào MongoDB (đã cấu hình sẵn connection string)

### Cách 2: Chạy Development Mode (Hot Reload)

1. **Kích hoạt virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

2. **Chạy development server:**
   ```bash
   python src\run.py
   ```
   - Driver sẽ được giữ chạy
   - Khi sửa code, chỉ cần nhấn Enter để reload và chạy lại
   - Nhấn `Ctrl+C` để dừng

### Cách 3: Export dữ liệu ra Excel

1. **Kích hoạt virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

2. **Chạy export:**
   ```bash
   python src\main.py
   ```
   - Trong file `main.py`, hàm `export_to_excel()` sẽ export dữ liệu từ MongoDB ra file Excel
   - File Excel sẽ được lưu trong thư mục `excel_comment2/`

### Cách 4: Chạy FastAPI Server (nếu cần)

1. **Kích hoạt virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

2. **Chạy server:**
   ```bash
   uvicorn src.app:app --reload
   ```
   - Server sẽ chạy tại: http://127.0.0.1:8000
   - Truy cập http://127.0.0.1:8000 để xem API

## Xử lý lỗi thường gặp

### Lỗi: "python is not recognized"

**Nguyên nhân:** Python chưa được thêm vào PATH

**Giải pháp:**
1. Gỡ cài đặt Python
2. Cài lại và **tích chọn "Add Python to PATH"**
3. Hoặc thêm Python vào PATH thủ công:
   - Tìm đường dẫn Python (thường là `C:\Users\YourName\AppData\Local\Programs\Python\Python311`)
   - Thêm vào System Environment Variables

### Lỗi: "pip is not recognized"

**Giải pháp:**
```bash
python -m pip install -r requirements.txt
```

### Lỗi: ChromeDriver không chạy được

**Nguyên nhân:** ChromeDriver không tương thích với phiên bản Chrome

**Giải pháp:**
- `webdriver-manager` sẽ tự động tải ChromeDriver phù hợp
- Đảm bảo Chrome đã được cập nhật lên phiên bản mới nhất
- Nếu vẫn lỗi, xóa cache:
  ```bash
  rmdir /s %USERPROFILE%\.wdm
  ```
  Sau đó chạy lại script

### Lỗi: "ModuleNotFoundError"

**Nguyên nhân:** Chưa cài đặt package hoặc virtual environment chưa kích hoạt

**Giải pháp:**
1. Đảm bảo virtual environment đã kích hoạt (thấy `(venv)`)
2. Cài lại dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Lỗi: Kết nối MongoDB

**Nguyên nhân:** Connection string không đúng hoặc không có internet

**Giải pháp:**
- Kiểm tra kết nối internet
- Kiểm tra connection string trong `src/config/database.py`
- Đảm bảo MongoDB Atlas (nếu dùng cloud) đã cho phép IP của bạn

## Lưu ý quan trọng

1. **Luôn kích hoạt virtual environment trước khi chạy:**
   ```bash
   venv\Scripts\activate
   ```

2. **Mỗi terminal mới cần kích hoạt lại venv**

3. **Không commit thư mục `venv/` vào git** (đã có trong .gitignore)

4. **File Excel được tạo tự động** trong các thư mục `excel_comment/`, `excel_comment2/`, `excel_tag/`

5. **MongoDB connection string** đã được cấu hình sẵn trong code, không cần cài MongoDB local

## Tóm tắt các lệnh cần nhớ

```bash
# 1. Tạo virtual environment (chỉ cần làm 1 lần)
python -m venv venv

# 2. Kích hoạt virtual environment (mỗi lần mở terminal mới)
venv\Scripts\activate

# 3. Cài đặt dependencies (chỉ cần làm 1 lần sau khi tạo venv)
pip install -r requirements.txt

# 4. Chạy dự án
python src\main.py

# 5. Chạy development mode
python src\run.py

# 6. Chạy FastAPI server
uvicorn src.app:app --reload
```

## Kiểm tra nhanh

Sau khi cài đặt, chạy lệnh này để kiểm tra mọi thứ đã sẵn sàng:

```bash
python -c "import selenium, pymongo, fastapi, openpyxl; print('✅ Tất cả dependencies đã sẵn sàng!')"
```

Nếu không có lỗi, bạn đã sẵn sàng chạy dự án!
