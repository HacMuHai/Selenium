# ChromeDriver — lỗi thường gặp

> Tài liệu cũ mô tả lỗi `Status code was: -9` do `webdriver-manager` tải binary về `~/.wdm`
> và bị macOS Gatekeeper cách ly. **Dự án đã bỏ `webdriver-manager`** và dùng
> **Selenium Manager** tích hợp sẵn trong `selenium >= 4.15`, nên lỗi đó không còn xảy ra.
> Nội dung dưới đây phản ánh cách hoạt động hiện tại.

## Selenium Manager hoạt động thế nào

`webdriver.Chrome(options=...)` tự dò phiên bản Chrome đang cài, tải đúng ChromeDriver về
`~/.cache/selenium` và cấp quyền thực thi. Không cần code cấp quyền, không cần
`xattr -d com.apple.quarantine`.

Lần chạy đầu **cần mạng**. Sau đó chạy được offline nhờ cache.

## Lỗi và cách xử lý

### `SessionNotCreatedException: This version of ChromeDriver only supports Chrome version X`

Chrome vừa tự cập nhật còn cache driver thì chưa. Xoá cache rồi chạy lại:

```bash
rm -rf ~/.cache/selenium          # macOS/Linux
rmdir /s %USERPROFILE%\.cache\selenium   # Windows
```

### `WebDriverException: unable to obtain driver` / timeout khi khởi động

Selenium Manager không tải được driver — thường do mất mạng hoặc proxy chặn. Kiểm tra
kết nối, hoặc chạy lại khi đã có mạng để cache được tạo.

### Còn tiến trình chromedriver / Chrome sau khi chạy xong

Driver được quản lý theo thread trong `src/config/driver.py`; `quit_all()` được gọi trong
`finally` của `run_crawl` và đăng ký thêm ở `atexit`. Kiểm tra:

```bash
pgrep -f chromedriver     # phải rỗng sau khi CLI thoát
```

Nếu còn sót, nhiều khả năng process Python bị `kill -9` (bỏ qua `atexit`) — chỉ cần
`pkill -f chromedriver`.

### Chạy `--attach` mà không kết nối được

Chrome phải được mở sẵn với cổng debug **trước khi** chạy CLI:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

Khi attach, `quit_all()` **không** đóng browser của bạn — đó là hành vi có chủ đích.

### Bị chặn ở chế độ headless

Nếu trang trả về nội dung rỗng khi chạy ẩn, thử `--no-headless` để xem thực tế trang hiển thị gì.
