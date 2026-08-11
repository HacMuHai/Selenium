"""
Style dùng chung cho MỌI hình trong bài báo.

Một chỗ duy nhất định nghĩa font / màu / dpi. Cả bộ figure phải nhìn như một hệ
thống - đó là thứ người đọc cảm nhận trước khi kịp đọc con số.

RỦI RO SỐ 1: font thiếu glyph tiếng Việt -> chữ "Tiêu cực" render thành ô vuông ▯
mà matplotlib KHÔNG báo lỗi, chỉ log warning dễ bị bỏ qua. `_pick_font()` kiểm
tra thật sự từng ký tự có dấu trước khi chọn.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # không cần cửa sổ GUI, chạy được cả trên máy không màn hình

import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT_DIR = Path(__file__).resolve().parent / "out"
DPI = 300

# Chuỗi thử: đủ mọi loại dấu tiếng Việt (mũ, móc, thanh điệu, đ).
_PROBE = "Tiêu cực Trung lập Tích cực Phân bố nhãn Độ chính xác ữ ượ ỹ đ"

# Ưu tiên Times New Roman: khớp với body text của luận văn/báo cáo tiếng Việt.
_FONT_PREFERENCE = ("Times New Roman", "DejaVu Serif", "Arial Unicode MS", "DejaVu Sans")

# Bảng màu 3 lớp. Đỏ/xám/xanh là quy ước ai cũng đọc được ngay, không cần chú giải.
COLORS = {
    "negative": "#c0392b",
    "neutral": "#7f8c8d",
    "positive": "#1e8449",
}
LABEL_VI = {
    "negative": "Tiêu cực",
    "neutral": "Trung lập",
    "positive": "Tích cực",
}
# Nhãn dùng trong bảng mẫu dữ liệu - viết liền, khớp đúng kiểu ảnh Hình 4.3.
LABEL_TAG = {
    "negative": "TieuCuc",
    "neutral": "TrungLap",
    "positive": "TichCuc",
}

MODEL_VI = {"nb": "Naive Bayes", "svm": "SVM", "lstm": "LSTM"}
# Màu theo model - khác hẳn bảng màu lớp, để không ai nhầm hai chiều thông tin này.
MODEL_COLORS = {"nb": "#2980b9", "svm": "#8e44ad", "lstm": "#d68910"}
BASELINE_COLOR = "#c0392b"

GRID = "#d5d8dc"
TEXT = "#1a1a1a"
MUTED = "#5d6d7e"

# Màu bảng - lấy đúng tinh thần ảnh mẫu: header vàng, chữ header đỏ.
TABLE_HEADER_BG = "#ffd966"
TABLE_HEADER_FG = "#c00000"
TABLE_ROW_BG = "#ffffff"
TABLE_ROW_ALT = "#f4f6f7"
TABLE_LINE = "#b7b7b7"


def _pick_font() -> str:
    """Chọn font ĐẦU TIÊN render được đầy đủ dấu tiếng Việt.

    Không tin vào tên font: một số bản Times New Roman cũ thiếu ký tự như 'ữ'.
    Nạp thẳng file .ttf và hỏi bảng mã ký tự.
    """
    for name in _FONT_PREFERENCE:
        try:
            path = font_manager.findfont(
                font_manager.FontProperties(family=name), fallback_to_default=False
            )
            charmap = font_manager.get_font(path).get_charmap()
        except Exception:
            continue
        if all(ord(ch) in charmap for ch in _PROBE if ch != " "):
            return name
    # Không font nào đủ dấu: DejaVu Sans luôn có sẵn cùng matplotlib và đủ tiếng Việt.
    return "DejaVu Sans"


FONT = _pick_font()


def apply() -> None:
    """Nạp style toàn cục. Gọi MỘT lần ở đầu chương trình."""
    plt.rcParams.update(
        {
            "font.family": FONT,
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.dpi": 110,
            "savefig.dpi": DPI,
            "text.color": TEXT,
            "axes.labelcolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": GRID,
            "axes.linewidth": 0.9,
            "axes.grid": True,
            "axes.axisbelow": True,  # lưới nằm DƯỚI cột, không vạch ngang qua dữ liệu
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "grid.alpha": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            # Nền trắng đặc: transparent=True sẽ ra nền đen khi in Word.
            "savefig.facecolor": "white",
            "savefig.transparent": False,
        }
    )


def clean_axes(ax, *, grid_axis: str = "y") -> None:
    """Bỏ viền trên + phải, chỉ giữ lưới theo một trục. Ít mực hơn, dễ đọc hơn."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis=grid_axis, linestyle="-")
    ax.set_axisbelow(True)
    if grid_axis == "y":
        ax.xaxis.grid(False)
    else:
        ax.yaxis.grid(False)


def save(fig, name: str, subdir: str = "") -> Path:
    """Ghi PNG 300dpi vào `out/<subdir>/`, trả về đường dẫn."""
    folder = OUT_DIR / subdir if subdir else OUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.18, facecolor="white")
    plt.close(fig)
    return path


def rel(path: Path) -> str:
    """Đường dẫn tương đối so với `out/`, dùng cho link trong trang HTML."""
    return path.resolve().relative_to(OUT_DIR.resolve()).as_posix()
