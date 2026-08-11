"""
Render bảng thành PNG 300dpi (+ CSV cùng tên).

KHÔNG dùng `matplotlib.table`: nó ép mọi hàng cao bằng nhau, nên một comment dài
sẽ hoặc bị cắt cụt hoặc thổi phồng cả bảng. Ở đây tự vẽ bằng rectangle + text để
mỗi hàng cao đúng theo số dòng sau khi wrap.
"""
import csv
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from paper import style

# Chiều cao một dòng chữ và lề trong ô, đều tính bằng inch.
# Lề phải là số tuyệt đối, không phải % bề rộng cột: nếu tính theo %, cột rộng sẽ
# thụt đầu dòng sâu hơn hẳn cột hẹp và bảng nhìn lệch.
_LINE_H = 0.26
_PAD_IN = 0.09
_FONT_SIZE = 10

# Thư mục con trong `out/` - gom cho gọn khi gửi cả folder đi.
DIR_BANG = "bang"
DIR_CSV = "csv"

_measure_fig = None
_width_cache: dict[tuple[str, bool], float] = {}


def _text_width(text: str, *, bold: bool) -> float:
    """Bề rộng THẬT của chuỗi khi render, tính bằng inch.

    Đếm ký tự để đoán chỗ xuống dòng là không đủ: chữ số và chữ hoa rộng hơn hẳn
    chữ thường có dấu, nên cùng một số ký tự lúc vừa lúc tràn đè sang cột bên -
    mà matplotlib cắt chữ trong im lặng, không hề báo lỗi.
    """
    global _measure_fig
    key = (text, bold)
    if key not in _width_cache:
        if _measure_fig is None:
            _measure_fig = plt.figure(figsize=(1, 1))
        artist = _measure_fig.text(0, 0, text, fontsize=_FONT_SIZE,
                                   fontweight="bold" if bold else "normal")
        extent = artist.get_window_extent(renderer=_measure_fig.canvas.get_renderer())
        artist.remove()
        _width_cache[key] = extent.width / _measure_fig.dpi
    return _width_cache[key]


def _wrap(text: str, max_width: float, *, bold: bool = False) -> list[str]:
    """Xuống dòng theo bề rộng inch thật, gom từ theo kiểu greedy."""
    text = "" if text is None else str(text)
    if not text.strip():
        return [""]

    lines: list[str] = []
    for para in text.splitlines() or [""]:
        current = ""
        for word in para.split():
            candidate = f"{current} {word}".strip()
            if current and _text_width(candidate, bold=bold) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
            # Một "từ" dài hơn cả cột (link, chuỗi không dấu cách) - cắt cứng
            # theo ký tự, nếu không nó sẽ thò ra ngoài bảng.
            while _text_width(current, bold=bold) > max_width and len(current) > 1:
                cut = len(current)
                while cut > 1 and _text_width(current[:cut], bold=bold) > max_width:
                    cut -= 1
                lines.append(current[:cut])
                current = current[cut:]
        lines.append(current)
    return [l for l in lines if l != ""] or [""]


def render_table(
    name: str,
    header: Sequence[str],
    rows: Sequence[Sequence[object]],
    *,
    col_widths: Sequence[float],
    align: Sequence[str] | None = None,
    total_width: float = 7.0,
    highlight_rows: Sequence[int] = (),
) -> Path:
    """Vẽ một bảng.

    `col_widths` là tỉ lệ bề ngang các cột (tự chuẩn hoá về tổng = 1). Chỗ xuống
    dòng tự tính từ bề rộng thật của cột, không cần khai báo tay.
    `highlight_rows` là chỉ số hàng cần in đậm (ví dụ: model tốt nhất).
    """
    align = list(align or ["left"] * len(header))
    total = sum(col_widths)
    widths = [w / total for w in col_widths]
    xs = [0.0]
    for w in widths:
        xs.append(xs[-1] + w)

    # Bề rộng dùng được của mỗi cột, đã trừ padding hai bên.
    usable = [max(0.4, w * total_width - 2 * _PAD_IN) for w in widths]

    # Wrap trước, để biết mỗi hàng cần bao nhiêu dòng.
    head_cells = [_wrap(h, usable[i], bold=True) for i, h in enumerate(header)]
    head_lines = max(len(c) for c in head_cells)
    body_cells = [
        [_wrap(c, usable[i], bold=idx in highlight_rows) for i, c in enumerate(row)]
        for idx, row in enumerate(rows)
    ]
    body_lines = [max(len(c) for c in row) for row in body_cells]

    # Không vẽ tiêu đề vào ảnh: caption thuộc về Word, in kèm sẽ thành trùng lặp.
    fig_h = (head_lines + sum(body_lines)) * _LINE_H + 0.24
    fig = plt.figure(figsize=(total_width, fig_h))
    # Trục phải chiếm TRỌN figure. `plt.subplots` để lại lề mặc định ~22% bề ngang,
    # khiến cột hẹp hơn con số dùng để tính chỗ xuống dòng -> chữ tràn sang cột bên.
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, fig_h)

    def draw_row(cells, y_top, height, *, bg, fg, bold, alt_align=None):
        ax.add_patch(
            Rectangle((0, y_top - height), 1, height, facecolor=bg,
                      edgecolor=style.TABLE_LINE, linewidth=0.7, zorder=1)
        )
        for i, lines in enumerate(cells):
            # Kẻ dọc phân cột (bỏ cạnh trái ngoài cùng).
            if i:
                ax.plot([xs[i], xs[i]], [y_top - height, y_top],
                        color=style.TABLE_LINE, linewidth=0.7, zorder=2)
            a = (alt_align or align)[i]
            pad = _PAD_IN / total_width  # inch -> tỉ lệ theo bề ngang figure
            if a == "left":
                x, ha = xs[i] + pad, "left"
            elif a == "right":
                x, ha = xs[i + 1] - pad, "right"
            else:
                x, ha = (xs[i] + xs[i + 1]) / 2, "center"
            # Căn giữa khối chữ theo chiều dọc của ô.
            block = len(lines) * _LINE_H
            y = y_top - (height - block) / 2 - _LINE_H / 2
            for line in lines:
                ax.text(x, y, line, ha=ha, va="center", fontsize=_FONT_SIZE,
                        fontweight="bold" if bold else "normal", color=fg, zorder=3)
                y -= _LINE_H

    y = fig_h - 0.12
    draw_row(head_cells, y, head_lines * _LINE_H,
             bg=style.TABLE_HEADER_BG, fg=style.TABLE_HEADER_FG, bold=True,
             alt_align=["center"] * len(header))
    y -= head_lines * _LINE_H

    for idx, (cells, nlines) in enumerate(zip(body_cells, body_lines)):
        bg = style.TABLE_ROW_ALT if idx % 2 else style.TABLE_ROW_BG
        draw_row(cells, y, nlines * _LINE_H, bg=bg, fg=style.TEXT,
                 bold=idx in highlight_rows)
        y -= nlines * _LINE_H

    path = style.save(fig, name, DIR_BANG)
    _write_csv(name, header, rows)
    return path


def _write_csv(name: str, header: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    """CSV song song với PNG, để bạn tự format lại trong Excel nếu cần."""
    folder = style.OUT_DIR / DIR_CSV
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    # utf-8-sig: Excel trên Windows mở CSV utf-8 thuần sẽ hỏng hết dấu tiếng Việt.
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
