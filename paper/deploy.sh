#!/usr/bin/env bash
# Đưa `paper/out/` lên web để người khác xem bằng link, không phải gửi file.
#
#   ./paper/deploy.sh pages v3 "Thêm 800 comment máy in"
#                               # GitHub Pages - link vĩnh viễn, tắt máy vẫn xem được
#   ./paper/deploy.sh tunnel    # Cloudflare Tunnel - link tạm, chỉ sống khi máy đang chạy
#
# Cả hai đều KHÔNG cần domain riêng.
#
# `pages` GIỮ các phiên bản cũ: mỗi lần deploy ghi vào `vN/` riêng và sinh lại trang
# gốc liệt kê. Bản đã gửi kèm bài báo không bị đổi số dưới chân người phản biện.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=paper/out
MODE="${1:-}"
VERSION="${2:-}"
LABEL="${3:-}"

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

  [ -n "$VERSION" ] || { echo "[LỖI] Thiếu mã phiên bản. Ví dụ: $0 pages v3 \"Thêm dữ liệu máy in\"" >&2; exit 1; }
  case "$VERSION" in v[0-9]*) ;; *) echo "[LỖI] Mã phiên bản phải dạng v1, v2, ... (nhận: $VERSION)" >&2; exit 1;; esac

  PY=venv/bin/python; [ -x "$PY" ] || PY=python3

  # Clone nhánh gh-pages hiện có rồi CỘNG THÊM thư mục vN/, không đè cả nhánh.
  # Chưa có nhánh (lần deploy đầu) thì tạo mới.
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT
  if ! git clone -q --branch gh-pages --single-branch "https://github.com/$REPO.git" "$TMP" 2>/dev/null; then
    echo "  Chưa có nhánh gh-pages, tạo mới."
    git -C "$TMP" init -q
    git -C "$TMP" checkout -qb gh-pages
  fi
  touch "$TMP/.nojekyll"   # Jekyll bỏ qua file/thư mục bắt đầu bằng "_"; tắt hẳn cho chắc

  "$PY" -m paper.publish --site "$TMP" --out "$OUT" --version "$VERSION" --label "$LABEL"

  git -C "$TMP" add -A
  git -C "$TMP" -c user.email="$(git config user.email)" \
      -c user.name="$(git config user.name)" \
      commit -qm "Báo cáo $VERSION${LABEL:+ - $LABEL}"
  git -C "$TMP" push -q "https://github.com/$REPO.git" gh-pages

  # Bật Pages nếu chưa bật (lần sau gọi lại sẽ báo đã tồn tại - bỏ qua).
  gh api -X POST "repos/$REPO/pages" -f "source[branch]=gh-pages" -f "source[path]=/" \
    >/dev/null 2>&1 || true

  echo
  echo "  Đã đẩy lên nhánh gh-pages."
  # `tr` chứ không phải ${VAR,,}: bash mặc định của macOS là 3.2, không có cú pháp đó.
  BASE="https://$(printf %s "$OWNER" | tr '[:upper:]' '[:lower:]').github.io/$NAME"
  echo "  Trang chọn phiên bản: $BASE/"
  echo "  Phiên bản vừa đẩy:    $BASE/$VERSION/"
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

  ./paper/deploy.sh pages vN ["mô tả"]
                              Đẩy lên GitHub Pages thành phiên bản vN.
                              Link vĩnh viễn, tắt máy vẫn xem được, ai có link đều xem được.
                              Các phiên bản cũ được giữ nguyên; trang gốc liệt kê tất cả.
                              Deploy lại cùng mã vN = ghi đè đúng phiên bản đó.

  ./paper/deploy.sh tunnel    Mở Cloudflare Tunnel.
                              Link tạm (*.trycloudflare.com), chỉ sống khi cửa sổ này còn chạy.
                              Hợp cho lúc cần cho ai đó xem ngay trong vài phút.
EOF
  exit 1
  ;;
esac
