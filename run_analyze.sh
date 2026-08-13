#!/usr/bin/env bash
# Mở trang thử nghiệm phân tích cảm xúc. Chạy từ thư mục gốc repo: ./run_analyze.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=venv/bin/python
[ -x "$PY" ] || { echo "[LỖI] Chưa có venv. Chạy: python3 -m venv venv && venv/bin/pip install -r requirements.txt"; exit 1; }

if [ ! -f models_store/metadata.json ]; then
  echo "[INFO] Chưa có model, đang train (khoảng 30 giây)..."
  # KHÔNG ghi cứng danh sách model: mặc định của lệnh train là available_names(),
  # thêm model mới vào registry là script này tự có. Bản cũ ghi "nb,svm,lstm" nên khi
  # thêm lstm_w2v thì nó âm thầm train thiếu và ghi đè metadata.json.
  "$PY" -m src.analyze train
fi

URL="http://127.0.0.1:8000/analyze/report"
echo "[INFO] Mở $URL — nhấn Ctrl+C để dừng"
( sleep 6; command -v open >/dev/null && open "$URL" ) &
exec "$PY" -m uvicorn src.app:app --port 8000
