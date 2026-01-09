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
from json import dumps
from config.driver import get_driver, close_driver
# Import module version, không phải biến version
from config import version as version_module
# import config.version as version_module
import importlib
import sys
import os

# Thêm thư mục src vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Danh sách prefix modules cần reload (kể cả submodule)
MODULE_PREFIXES = (
    'models',
    'repositories',
    'services',
    'utils',
    'main',
)


def reload_modules():
    """Reload tất cả modules đã import"""
    for name in list(sys.modules.keys()):
        if name.startswith(MODULE_PREFIXES):
            try:
                importlib.reload(sys.modules[name])
            except Exception as e:
                print(f"Không thể reload {name}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Driver Service - Giữ driver chạy liên tục")
    print("=" * 60)

    # Khởi tạo driver một lần
    driver = get_driver()
    is_first_run = True
    version_count = 0

    while True:
        try:
            print("\n" + "-" * 60)
            print("Nhấn Enter để chạy lại code từ main.py...")
            print("(Hoặc nhấn Ctrl+C để dừng)")
            # Cập nhật version global
            current_version = version_module.version
            version_module.version = f"{current_version}.{version_count}"
            version_count += 1
            if is_first_run:
                is_first_run = False
            else:
                input()
            print(f"Version: {version_module.version}")

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
            break
