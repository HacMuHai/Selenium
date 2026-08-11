#!/usr/bin/env bash
# Sinh toàn bộ hình cho bài báo. Chạy được từ BẤT KỲ thư mục nào:
#     ./paper/run.sh          hoặc      cd paper && ./run.sh
set -euo pipefail

# `python -m paper.figures` cần đứng ở thư mục CHA của paper/ thì Python mới thấy
# `paper` là một package. Tự chuyển vào đó thay vì bắt người dùng nhớ.
cd "$(dirname "$0")/.."

# Ưu tiên venv của repo; không có thì dùng python3 hệ thống ("python" trần
# thường không tồn tại trên macOS).
if [ -x venv/bin/python ]; then
  PY=venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "[LỖI] Không tìm thấy Python. Cài Python 3 rồi chạy lại." >&2
  exit 1
fi

if ! "$PY" -c "import matplotlib" 2>/dev/null; then
  echo "[LỖI] Thiếu thư viện. Chạy trước:" >&2
  echo "       $PY -m pip install -r paper/requirements.txt" >&2
  exit 1
fi

exec "$PY" -m paper.figures "$@"
