# Giải thích lỗi ChromeDriver Status Code -9

## Lỗi:
```
Message: Service /Users/hacmuhai/.wdm/drivers/chromedriver/mac64/143.0.7499.169/chromedriver-mac-arm64/chromedriver unexpectedly exited. Status code was: -9
```

## Giải thích:

### Status Code -9 là gì?
- **Status code -9** = `SIGKILL` - Process bị kill bởi hệ thống
- Không phải lỗi từ code của bạn, mà là hệ thống macOS đã kill ChromeDriver

### Tại sao lại xảy ra?

#### 1. **Quyền truy cập (Permissions)**
macOS có thể chặn ChromeDriver vì:
- ChromeDriver không được cấp quyền thực thi
- macOS Gatekeeper chặn ứng dụng không được ký (unsigned)
- Quarantine attribute chưa được xóa

#### 2. **ChromeDriver bị corrupt**
- File ChromeDriver có thể bị hỏng trong quá trình download
- Version không tương thích với Chrome hiện tại

#### 3. **Architecture không khớp**
- Bạn đang dùng Mac ARM64 (Apple Silicon)
- ChromeDriver có thể là version x86_64 thay vì arm64

#### 4. **Chrome version không khớp**
- ChromeDriver version 143.0.7499.169
- Chrome browser có thể đã update lên version khác

## Tại sao trước đây dùng được, giờ lại lỗi?

### Có thể do:
1. **Chrome đã update** → ChromeDriver cũ không tương thích
2. **macOS đã update** → Gatekeeper chặt chẽ hơn
3. **ChromeDriver cache bị corrupt** → Cần download lại
4. **Quyền truy cập thay đổi** → Cần cấp lại quyền

## Cách sửa:

### Cách 1: Xóa cache và download lại ChromeDriver
```bash
# Xóa cache ChromeDriver
rm -rf ~/.wdm/drivers/chromedriver

# Chạy lại code, webdriver_manager sẽ download lại
```

### Cách 2: Cấp quyền thực thi cho ChromeDriver
```bash
# Tìm đường dẫn ChromeDriver
find ~/.wdm -name "chromedriver" -type f

# Cấp quyền thực thi (thay PATH bằng đường dẫn thực tế)
chmod +x ~/.wdm/drivers/chromedriver/mac64/143.0.7499.169/chromedriver-mac-arm64/chromedriver

# Xóa quarantine attribute (nếu có)
xattr -d com.apple.quarantine ~/.wdm/drivers/chromedriver/mac64/143.0.7499.169/chromedriver-mac-arm64/chromedriver
```

### Cách 3: Sử dụng ChromeDriver từ Homebrew (khuyến nghị)
```bash
# Cài đặt ChromeDriver qua Homebrew
brew install chromedriver

# Hoặc cài đặt Chrome for Testing (khuyến nghị)
brew install --cask chromedriver
```

### Cách 4: Force download lại ChromeDriver trong code
```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import shutil

# Xóa cache trước khi download
cache_path = os.path.expanduser("~/.wdm/drivers/chromedriver")
if os.path.exists(cache_path):
    shutil.rmtree(cache_path)
    print("Đã xóa cache ChromeDriver")

# Download lại
driver_path = ChromeDriverManager().install()
print(f"ChromeDriver path: {driver_path}")

# Cấp quyền thực thi
os.chmod(driver_path, 0o755)

# Tạo driver
driver = webdriver.Chrome(service=Service(driver_path))
```

### Cách 5: Kiểm tra và cập nhật Chrome
```bash
# Kiểm tra Chrome version
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Nếu Chrome đã update, ChromeDriver cũ sẽ không tương thích
# webdriver_manager sẽ tự động download version mới
```

## Giải pháp nhanh nhất:

1. **Xóa cache ChromeDriver:**
   ```bash
   rm -rf ~/.wdm/drivers/chromedriver
   ```

2. **Chạy lại code** - webdriver_manager sẽ tự động download lại

3. **Nếu vẫn lỗi**, thử cấp quyền:
   ```bash
   chmod +x ~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver
   xattr -d com.apple.quarantine ~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver
   ```

## Lưu ý:

- **Status code -9** không phải lỗi code, mà là lỗi hệ thống
- Thường xảy ra trên macOS do Gatekeeper
- Có thể xảy ra sau khi update macOS hoặc Chrome
- Giải pháp đơn giản nhất: xóa cache và download lại
