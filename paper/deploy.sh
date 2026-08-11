#!/usr/bin/env bash
# Đưa `paper/out/` lên web để người khác xem bằng link, không phải gửi file.
#
#   ./paper/deploy.sh pages     # GitHub Pages - link vĩnh viễn, tắt máy vẫn xem được
#   ./paper/deploy.sh tunnel    # Cloudflare Tunnel - link tạm, chỉ sống khi máy đang chạy
#
# Cả hai đều KHÔNG cần domain riêng.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=paper/out
MODE="${1:-}"

[ -f "$OUT/index.html" ] || { echo "[LỖI] Chưa có $OUT/index.html. Chạy ./paper/run.sh trước." >&2; exit 1; }

case "$MODE" in
pages)
  command -v gh >/dev/null || { echo "[LỖI] Cần GitHub CLI: brew install gh" >&2; exit 1; }
  gh auth status >/dev/null 2>&1 || { echo "[LỖI] Chưa đăng nhập: gh auth login" >&2; exit 1; }

  REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
  OWNER=${REPO%%/*}; NAME=${REPO##*/}

  if [ "$(gh repo view --json isPrivate -q .isPrivate)" = "true" ]; then
    echo "[CẢNH BÁO] Repo đang PRIVATE. GitHub Pages với repo private cần tài khoản trả phí."
    echo "           Nếu định chuyển sang public, nhớ repo này từng commit mật khẩu MongoDB"
    echo "           vào lịch sử git - phải rotate mật khẩu trước."
    exit 1
  fi

  # Đẩy NGUYÊN nội dung out/ lên nhánh gh-pages, không mang theo lịch sử repo.
  # Nhánh này bị ghi đè mỗi lần deploy - nó là output, không phải nơi lưu trữ.
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT
  cp -R "$OUT"/. "$TMP"/
  touch "$TMP/.nojekyll"   # Jekyll bỏ qua file/thư mục bắt đầu bằng "_"; tắt hẳn cho chắc

  git -C "$TMP" init -q
  git -C "$TMP" checkout -qb gh-pages
  git -C "$TMP" add -A
  git -C "$TMP" -c user.email="$(git config user.email)" \
      -c user.name="$(git config user.name)" \
      commit -qm "Hình cho bài báo"
  git -C "$TMP" push -qf "https://github.com/$REPO.git" gh-pages

  # Bật Pages nếu chưa bật (lần sau gọi lại sẽ báo đã tồn tại - bỏ qua).
  gh api -X POST "repos/$REPO/pages" -f "source[branch]=gh-pages" -f "source[path]=/" \
    >/dev/null 2>&1 || true

  echo
  echo "  Đã đẩy lên nhánh gh-pages."
  # `tr` chứ không phải ${VAR,,}: bash mặc định của macOS là 3.2, không có cú pháp đó.
  echo "  Link: https://$(printf %s "$OWNER" | tr '[:upper:]' '[:lower:]').github.io/$NAME/"
  echo "  Lần đầu GitHub cần 1-2 phút build. Kiểm tra: gh browse --settings"
  echo
  ;;

tunnel)
  command -v cloudflared >/dev/null || { echo "[LỖI] Cần cloudflared: brew install cloudflared" >&2; exit 1; }
  PY=venv/bin/python; [ -x "$PY" ] || PY=python3

  # Server tĩnh phục vụ out/, tunnel trỏ vào nó. Cả hai chết khi Ctrl+C.
  "$PY" -m http.server 8899 --directory "$OUT" >/dev/null 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null || true' EXIT

  echo "[INFO] Link tạm sẽ hiện bên dưới. Giữ cửa sổ này mở, Ctrl+C để dừng."
  cloudflared tunnel --url "http://127.0.0.1:8899"
  ;;

*)
  cat <<'EOF'
Cách dùng:

  ./paper/deploy.sh pages     Đẩy lên GitHub Pages.
                              Link vĩnh viễn, tắt máy vẫn xem được, ai có link đều xem được.

  ./paper/deploy.sh tunnel    Mở Cloudflare Tunnel.
                              Link tạm (*.trycloudflare.com), chỉ sống khi cửa sổ này còn chạy.
                              Hợp cho lúc cần cho ai đó xem ngay trong vài phút.
EOF
  exit 1
  ;;
esac
