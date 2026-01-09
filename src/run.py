"""
Script để giữ driver chạy và cho phép reload code mà không restart driver.

CÁCH SỬ DỤNG:
1. Chạy script này trong một terminal riêng: python src/run.py
2. Giữ terminal đó chạy
3. Khi sửa code trong main.py, chỉ cần nhấn Enter trong terminal này để reload và chạy lại

Hoặc sử dụng IPython để có trải nghiệm tốt hơn:
- ipython
- %run src/main.py  (chạy lần đầu)
- %run src/main.py  (chạy lại sau khi sửa code, driver sẽ được tái sử dụng)
"""
from config.driver import get_driver, close_driver
import importlib
import sys
import os

# Thêm thư mục src vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Danh sách modules cần reload
MODULES_TO_RELOAD = [
    'models',
    'config',
    'repositories',
    'services',
    'utils',
    'main'
]


def reload_modules():
    """Reload tất cả modules đã import"""
    for module_name in MODULES_TO_RELOAD:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
            except Exception as e:
                print(f"Không thể reload {module_name}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Driver Service - Giữ driver chạy liên tục")
    print("=" * 60)

    # Khởi tạo driver một lần
    driver = get_driver()
    is_first_run = True

    while True:
        try:
            print("\n" + "-" * 60)
            print("Nhấn Enter để chạy lại code từ main.py...")
            print("(Hoặc nhấn Ctrl+C để dừng)")

            if is_first_run:
                is_first_run = False
            else:
                input()

            # Reload tất cả modules
            reload_modules()

            # Chạy main
            if 'main' in sys.modules:
                sys.modules['main'].main()
            else:
                import main
                main.main()

        except KeyboardInterrupt:
            print("\n\nĐang đóng driver...")
            close_driver()
            print("Đã dừng!")
            break
        except Exception as e:
            print(f"\nLỗi: {e}")
            import traceback
            traceback.print_exc()
