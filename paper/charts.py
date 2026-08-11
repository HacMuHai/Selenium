"""
Biểu đồ cho bài báo. Mỗi hàm nhận `metadata` (đọc từ metadata.json) và trả về đường dẫn PNG.

NGUYÊN TẮC BẤT BIẾN: mọi biểu đồ so sánh model PHẢI vẽ đường baseline. Không có nó,
người đọc không biết macro-F1 = 0.833 là giỏi hay chỉ đang đoán lớp đa số.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paper import style
from paper.analysis.metrics import LABELS

# Thứ tự cố định để mọi hình xếp model giống nhau; người đọc không phải học lại từng hình.
MODEL_ORDER = ("nb", "svm", "lstm")

# Thư mục con trong `out/`.
DIR_BIEU_DO = "bieu-do"


def _models(metadata: dict) -> list[str]:
    present = metadata.get("models", {})
    return [m for m in MODEL_ORDER if m in present]


def _vn(text: str) -> str:
    """Dấu thập phân kiểu Việt Nam: 0,833. Giữ thống nhất với các bảng."""
    return text.replace(".", ",")


def _vn_int(value) -> str:
    """Phân cách nghìn kiểu Việt Nam: 2.502."""
    return f"{int(value):,}".replace(",", ".")


def _vn_ticks(ax, axis: str = "y", digits: int = 1) -> None:
    """Nhãn trục cũng phải dùng dấu phẩy.

    Nếu bỏ qua bước này thì trục ghi `0.6` còn nhãn trên cột ghi `52,3%` - hai
    quy ước số trong cùng một hình, người chấm sẽ nhìn ra ngay.
    """
    from matplotlib.ticker import FuncFormatter

    fmt = FuncFormatter(lambda v, _: _vn(f"{v:.{digits}f}"))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def _annotate(ax, bars, fmt="{:.3f}", *, dy=0.008, fontsize=9):
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + dy, _vn(fmt.format(h)),
                ha="center", va="bottom", fontsize=fontsize, color=style.TEXT)


def phan_bo_nhan(metadata: dict) -> Path:
    """Phân bố nhãn của tập đã làm sạch - cho thấy dữ liệu LỆCH LỚP."""
    counts = metadata["dataset"]["label_counts"]
    total = sum(counts.values())
    labels = [l for l in LABELS if l in counts]
    values = [counts[l] for l in labels]

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    ypos = np.arange(len(labels))
    bars = ax.barh(ypos, values, height=0.6,
                   color=[style.COLORS[l] for l in labels])
    ax.set_yticks(ypos, [style.LABEL_VI[l] for l in labels])
    ax.invert_yaxis()
    ax.set_xlabel("Số lượng bình luận")
    ax.set_xlim(0, max(values) * 1.16)
    for bar, v in zip(bars, values):
        ax.text(v + max(values) * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{v:,}".replace(",", ".") + _vn(f"  ({v / total:.1%})"),
                va="center", fontsize=10, color=style.TEXT)
    style.clean_axes(ax, grid_axis="x")
    _vn_ticks(ax, axis="x", digits=0)
    return style.save(fig, "bd-phan-bo-nhan", DIR_BIEU_DO)


def phan_bo_train_test(metadata: dict) -> Path:
    """Tỉ lệ nhãn ở train vs test - kiểm chứng split có phân tầng."""
    split = metadata["split"]
    train, test = split["train_labels"], split["test_labels"]
    labels = [l for l in LABELS if l in train]
    n_train, n_test = split["train"], split["test"]
    train_pct = [train.get(l, 0) / n_train for l in labels]
    test_pct = [test.get(l, 0) / n_test for l in labels]

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    x = np.arange(len(labels))
    w = 0.36
    b1 = ax.bar(x - w / 2, train_pct, w, label=f"Train (n = {_vn_int(n_train)})",
                color="#34495e")
    b2 = ax.bar(x + w / 2, test_pct, w, label=f"Test (n = {_vn_int(n_test)})",
                color="#95a5a6")
    ax.set_xticks(x, [style.LABEL_VI[l] for l in labels])
    ax.set_ylabel("Tỉ lệ trong tập")
    ax.set_ylim(0, max(train_pct + test_pct) * 1.25)
    _annotate(ax, b1, "{:.1%}", dy=0.008)
    _annotate(ax, b2, "{:.1%}", dy=0.008)
    ax.legend(frameon=False, loc="upper right")
    style.clean_axes(ax)
    _vn_ticks(ax)
    return style.save(fig, "bd-phan-bo-train-test", DIR_BIEU_DO)


def so_sanh_model(metadata: dict) -> Path:
    """HÌNH QUAN TRỌNG NHẤT: macro-F1 và accuracy của 3 model, so với baseline."""
    names = _models(metadata)
    base = metadata["baseline"]
    f1 = [metadata["models"][n]["metrics"]["macro_f1"] for n in names]
    acc = [metadata["models"][n]["metrics"]["accuracy"] for n in names]

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    x = np.arange(len(names))
    w = 0.36
    b1 = ax.bar(x - w / 2, f1, w, label="macro-F1", color="#2471a3")
    b2 = ax.bar(x + w / 2, acc, w, label="Accuracy", color="#a9cce3")
    _annotate(ax, b1)
    _annotate(ax, b2)

    # Chú thích baseline nằm trong legend, KHÔNG viết đè lên vùng cột: ở thang 0-1
    # các cột chiếm gần hết chiều cao nên mọi nhãn đặt trong khung đều bị đè.
    l1 = ax.axhline(base["macro_f1"], color=style.BASELINE_COLOR,
                    linestyle="--", linewidth=1.4,
                    label=_vn(f"baseline macro-F1 = {base['macro_f1']:.3f}"))
    l2 = ax.axhline(base["accuracy"], color=style.BASELINE_COLOR,
                    linestyle=":", linewidth=1.6,
                    label=_vn(f"baseline accuracy = {base['accuracy']:.3f}"))

    ax.set_xticks(x, [style.MODEL_VI[n] for n in names])
    # Thang cố định 0-1: để auto-scale sẽ phóng đại chênh lệch giữa các model.
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Điểm")
    ax.legend([b1, b2, l1, l2], [t.get_label() for t in (b1, b2, l1, l2)],
              frameon=False, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), handlelength=2.2)
    style.clean_axes(ax)
    _vn_ticks(ax)
    return style.save(fig, "bd-so-sanh-model", DIR_BIEU_DO)


def f1_tung_lop(metadata: dict) -> Path:
    """F1 từng lớp × từng model, kèm cột trung bình.

    Nhóm "Trung bình (macro)" ở cuối là để khớp bố cục ảnh mẫu (Biểu đồ 5.1/5.3
    có cột "F-score trung bình"), và cũng vì đó mới là con số kết luận.
    """
    names = _models(metadata)
    labels = list(LABELS)
    groups = [style.LABEL_VI[l] for l in labels] + ["Trung bình\n(macro-F1)"]

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(groups))
    w = 0.8 / len(names)
    for i, n in enumerate(names):
        m = metadata["models"][n]["metrics"]
        per = m["per_class"]
        vals = [per.get(l, {}).get("f1", 0.0) for l in labels] + [m["macro_f1"]]
        bars = ax.bar(x + (i - (len(names) - 1) / 2) * w, vals, w * 0.9,
                      label=style.MODEL_VI[n], color=style.MODEL_COLORS[n])
        _annotate(ax, bars, "{:.2f}", dy=0.01, fontsize=8)

    # Vạch ngăn tách nhóm trung bình khỏi ba lớp - nó là số tổng hợp, không cùng loại.
    ax.axvline(len(labels) - 0.5, color=style.GRID, linewidth=1.0, linestyle="-")
    ax.set_xticks(x, groups)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("F1")
    # -0.15: nhãn nhóm cuối chiếm hai dòng, legend đặt cao hơn sẽ chen ngang nó.
    ax.legend(frameon=False, ncol=len(names), loc="upper center",
              bbox_to_anchor=(0.5, -0.15))
    style.clean_axes(ax)
    _vn_ticks(ax)
    return style.save(fig, "bd-f1-tung-lop", DIR_BIEU_DO)


def confusion(metadata: dict, model: str) -> Path:
    """Ma trận nhầm lẫn: số tuyệt đối + % theo HÀNG (tức theo nhãn thật)."""
    matrix = metadata["models"][model]["metrics"]["confusion"]
    labels = list(LABELS)
    counts = np.array([[matrix[a][b] for b in labels] for a in labels], dtype=float)
    row_sum = counts.sum(axis=1, keepdims=True)
    pct = np.divide(counts, row_sum, out=np.zeros_like(counts), where=row_sum > 0)

    fig, ax = plt.subplots(figsize=(5.0, 4.3))
    im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), [style.LABEL_VI[l] for l in labels])
    ax.set_yticks(range(len(labels)), [style.LABEL_VI[l] for l in labels])
    ax.set_xlabel("Nhãn mô hình dự đoán")
    ax.set_ylabel("Nhãn thực tế")
    for i in range(len(labels)):
        for j in range(len(labels)):
            # Ô đậm thì chữ trắng, ô nhạt thì chữ đen - nếu không sẽ có ô không đọc được.
            color = "white" if pct[i, j] > 0.55 else style.TEXT
            ax.text(j, i, f"{int(counts[i, j])}\n{pct[i, j]:.0%}",
                    ha="center", va="center", fontsize=10, color=color)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.045, pad=0.04).set_label(
        "Tỉ lệ theo nhãn thực tế", fontsize=9
    )
    return style.save(fig, f"bd-confusion-{model}", DIR_BIEU_DO)


def thoi_gian_train(metadata: dict) -> Path:
    """Chi phí huấn luyện - đánh đổi giữa độ chính xác và thời gian."""
    names = _models(metadata)
    secs = [metadata["models"][n]["train_seconds"] for n in names]

    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    bars = ax.bar(range(len(names)), secs, 0.5,
                  color=[style.MODEL_COLORS[n] for n in names])
    ax.set_xticks(range(len(names)), [style.MODEL_VI[n] for n in names])
    # Log scale: 0.06s và 9.4s chênh hơn 150 lần, thang thường sẽ làm cột NB biến mất.
    ax.set_yscale("log")
    ax.set_ylabel("Thời gian huấn luyện (giây, thang log)")
    for bar, v in zip(bars, secs):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.12, _vn(f"{v:.2f}s"),
                ha="center", va="bottom", fontsize=10, color=style.TEXT)
    ax.set_ylim(min(secs) * 0.4, max(secs) * 3)
    style.clean_axes(ax)
    return style.save(fig, "bd-thoi-gian-train", DIR_BIEU_DO)
