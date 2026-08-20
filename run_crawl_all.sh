#!/usr/bin/env bash
#
# Crawl trọn CellphoneS + FPT Shop vào MongoDB, rồi xuất Excel ra data/<sàn>/.
#
# KHÔNG crawl thegioididong: dữ liệu TGDD đã có sẵn trong Mongo (3.196 sản phẩm) và
# không cần làm lại. Muốn crawl thì thêm nhóm tgdd-* vào CRAWL_GROUPS.
#
# Chạy lại được nhiều lần: đang nối Mongo nên `exists_by_link` bỏ qua sản phẩm đã có.
# Bị chặn giữa chừng cứ chạy lại, nó tiếp từ chỗ dở chứ không làm lại từ đầu.
#
#   ./run_crawl_all.sh              # crawl rồi export
#   ./run_crawl_all.sh --export     # chỉ export lại từ Mongo, không mở Chrome
#
set -uo pipefail
cd "$(dirname "$0")"

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$LOG_DIR/crawl-$STAMP.log"

# --workers ở đây là số LUỒNG GỌI API, không phải số Chrome: với CellphoneS và FPT Shop
# chỉ có đúng 1 Chrome cho bước lấy danh sách, comment lấy qua HTTP.
WORKERS_FAST=2      # mặc định
WORKERS_SAFE=1      # dùng lại khi bị chặn
MAX_PAGES=60        # số lần bấm "Xem thêm" tối đa mỗi URL danh mục
PAUSE=60            # nghỉ giữa hai nhóm (giây)
COOLDOWN=900        # nghỉ khi bị chặn, trước khi chạy lại 1 luồng (giây)

# KHÔNG đặt tên mảng này là GROUPS: trong bash, GROUPS là biến đặc biệt chứa danh sách
# GID của user, gán đè vào nó KHÔNG có tác dụng và cũng KHÔNG báo lỗi. Script sẽ lặp qua
# 16 GID rồi gọi `--category 20`, tức chạy rỗng mà nhìn vẫn như đang chạy thật.
CRAWL_GROUPS=(
  # CellphoneS - 33 URL, ~9.500 sản phẩm
  cps-dtdd cps-may-tinh-bang cps-laptop cps-man-hinh cps-may-in
  cps-may-tinh-de-ban cps-dien-may cps-gia-dung cps-phu-kien
  # FPT Shop - hai nhóm này lần trước chạm trần 15 lần bấm nên còn sót sản phẩm
  fpt-laptop fpt-phu-kien
)

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

run_group() {                      # $1 = tên nhóm, $2 = số luồng
  local group=$1 workers=$2
  local tmp="$LOG_DIR/.$group.tmp"
  log "--- $group (workers=$workers) ---"
  python -m src.main --category "$group" --workers "$workers" --max-pages "$MAX_PAGES" \
      > "$tmp" 2>&1
  local code=$?
  cat "$tmp" >> "$LOG"
  # Dòng tổng kết là thứ duy nhất đáng nhìn khi theo dõi bằng mắt.
  grep -E "Thu được|Tổng kết|Bị chặn" "$tmp" | tee -a "$LOG" >/dev/null
  grep -E "Tổng kết" "$tmp" | tail -1
  if grep -q "Bị chặn bot" "$tmp"; then
    rm -f "$tmp"
    return 10                      # mã riêng: bị chặn, không phải lỗi chương trình
  fi
  rm -f "$tmp"
  return $code
}

export_excel() {
  log "=== Xuất Excel ra data/<sàn>/ ==="
  python -m src.main --export-only --export data --export-name "comments_$(date +%y%m%d)" 2>&1 | tee -a "$LOG"
}

if [[ "${1:-}" == "--export" ]]; then
  export_excel
  exit $?
fi

log "=== BẮT ĐẦU: ${#CRAWL_GROUPS[@]} nhóm, log $LOG ==="
BLOCKED=()
for group in "${CRAWL_GROUPS[@]}"; do
  run_group "$group" "$WORKERS_FAST"
  if [[ $? -eq 10 ]]; then
    log "$group BỊ CHẶN -> nghỉ ${COOLDOWN}s rồi chạy lại với $WORKERS_SAFE luồng"
    sleep "$COOLDOWN"
    run_group "$group" "$WORKERS_SAFE"
    if [[ $? -eq 10 ]]; then
      log "$group VẪN BỊ CHẶN - bỏ qua, chạy lại script sau là tiếp được"
      BLOCKED+=("$group")
    fi
  fi
  sleep "$PAUSE"
done

log "=== CRAWL XONG ==="
if [[ ${#BLOCKED[@]} -gt 0 ]]; then
  log "Nhóm còn dở (chạy lại script để tiếp): ${BLOCKED[*]}"
fi

python - <<'PY' 2>&1 | tee -a "$LOG"
from src.config.database import get_collection
col = get_collection()
print("--- MongoDB ---")
for r in col.aggregate([{"$group": {"_id": "$site", "sp": {"$sum": 1},
                                    "cmt": {"$sum": "$total_comments"}}},
                        {"$sort": {"sp": -1}}]):
    print(f"  {r['_id']:15s} {r['sp']:6d} sản phẩm  {r['cmt']:7d} comment")
PY

export_excel
log "=== HOÀN TẤT - log đầy đủ: $LOG ==="
