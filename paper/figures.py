"""
ENTRYPOINT. Sinh toàn bộ hình + bảng cho bài báo:

    python -m paper.figures

Kết quả nằm trong `paper/out/`, chia thư mục `bang/` `bieu-do/` `csv/` `anh-mau/`
kèm `index.html` để xem hết một lượt. Folder `out/` tự chứa, gửi riêng nó là đủ.

Không train lại model: mọi con số đọc từ `paper/data/metadata.json` (kết quả đã
huấn luyện sẵn). Chỉ bảng mẫu dữ liệu là đọc thẳng từ Excel đã gán nhãn.
"""
import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from paper import charts, gallery, style, tables
from paper.analysis.metrics import LABELS

logger = logging.getLogger("paper")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def _fmt_int(value) -> str:
    """Định dạng số nguyên kiểu Việt Nam: 3.128 chứ không phải 3,128."""
    return f"{int(value):,}".replace(",", ".")


def _fmt_num(value, digits: int = 3) -> str:
    """Số thập phân kiểu Việt Nam: 0,833. Dùng cho MỌI số trong bảng."""
    return f"{value:.{digits}f}".replace(".", ",")


def _fmt_pct(part, whole, digits: int = 2) -> str:
    return _fmt_num(part / whole * 100, digits) + "%" if whole else "–"


def _fmt_ratio(value, digits: int = 1) -> str:
    """Tỉ lệ 0–1 -> phần trăm: 0.861 -> 86,1%."""
    return _fmt_num(value * 100, digits) + "%"


# ---------------------------------------------------------------- bảng

def bang_mau_du_lieu(frame, per_label: int = 7) -> Path:
    """Bảng mẫu dữ liệu - dựng theo đúng layout ảnh Hình 4.3 (header vàng, chữ đỏ).

    Chọn câu NGẮN có chủ đích: bảng minh hoạ trong báo cáo phải đọc được ở một
    liếc mắt, không phải để chứng minh dữ liệu dài cỡ nào.
    """
    rows: list[list[str]] = []
    for label in ("positive", "neutral", "negative"):
        subset = frame[frame["sentiment"] == label]
        short = subset[subset["text"].str.len().between(6, 46)]
        picked = (short if len(short) >= per_label else subset).head(per_label)
        for text in picked["text"]:
            rows.append([style.LABEL_TAG[label], " ".join(str(text).split())])

    return tables.render_table(
        "bang-mau-du-lieu",
        ["category", "text"],
        rows,
        col_widths=[1.0, 3.4],
        align=["left", "left"],
        total_width=6.4,
    )


def bang_comment_theo_lop(frame, rows_n: int = 12) -> Path:
    """Danh sách bình luận tách theo lớp - thay cho ảnh chụp Notepad ở Hình 4.4.

    Hai lớp cạnh nhau trong cùng một bảng thay vì hai ảnh rời: người đọc thấy ngay
    sự khác biệt về từ ngữ giữa tích cực và tiêu cực, đó mới là điều hình này cần nói.
    """
    def pick(label: str) -> list[str]:
        subset = frame[frame["sentiment"] == label]
        short = subset[subset["text"].str.len().between(6, 52)]
        source = short if len(short) >= rows_n else subset
        return [" ".join(str(t).split()) for t in source["text"].head(rows_n)]

    pos, neg = pick("positive"), pick("negative")
    rows = [[p, n] for p, n in zip(pos, neg)]
    return tables.render_table(
        "bang-comment-theo-lop",
        ["Bình luận tích cực", "Bình luận tiêu cực"],
        rows,
        col_widths=[1.0, 1.0],
        align=["left", "left"],
        total_width=7.0,
    )


def bang_tien_xu_ly(frame, rows_n: int = 10) -> Path:
    """Ba bước tiền xử lý đặt cạnh nhau - thay cho ảnh chụp Notepad ở Hình 4.6.

    Ảnh mẫu chỉ liệt kê kết quả cuối, nhìn vào không biết bước đó LÀM GÌ. Tách
    thành ba cột thì tự nó giải thích, và cho thấy rõ tiền xử lý gồm HAI bước
    riêng biệt: chuẩn hoá (`normalize_text`) rồi mới tách từ + bỏ stopword
    (`tokenize`).
    """
    from paper.analysis.preprocessing import tokenize

    subset = frame[frame["text"].str.len().between(20, 62)]
    source = subset if len(subset) >= rows_n else frame
    rows = [
        [
            " ".join(str(r.text).split()),
            str(r.norm_text),
            " ".join(tokenize(r.text)),
        ]
        for r in source.head(rows_n).itertuples()
    ]
    return tables.render_table(
        "bang-tien-xu-ly",
        ["Bình luận gốc", "Sau chuẩn hoá\n(bỏ dấu câu, hạ chữ thường)",
         "Sau tách từ\n(bỏ stopword)"],
        rows,
        col_widths=[1.0, 1.0, 1.0],
        align=["left", "left", "left"],
        total_width=7.4,
    )


def bang_lam_sach(metadata: dict) -> Path:
    """Phễu làm sạch: từ dòng thô đến dòng dùng được, mất ở đâu và mất bao nhiêu."""
    d = metadata["dataset"]
    total = d["total_rows"]

    def pct(v):
        return _fmt_pct(v, total)

    rows = [
        ["Tổng số dòng thu thập được", _fmt_int(total), "100,00%"],
        ["Loại bỏ: nội dung rỗng sau chuẩn hoá", _fmt_int(d["dropped_empty"]), pct(d["dropped_empty"])],
        ["Loại bỏ: nhãn không hợp lệ", _fmt_int(d["dropped_bad_label"]), pct(d["dropped_bad_label"])],
        ["Loại bỏ: cùng nội dung nhưng mâu thuẫn nhãn", _fmt_int(d["dropped_conflict"]), pct(d["dropped_conflict"])],
        ["Loại bỏ: trùng lặp nội dung", _fmt_int(d["dropped_duplicate"]), pct(d["dropped_duplicate"])],
        ["Còn lại đưa vào huấn luyện", _fmt_int(d["final_rows"]), pct(d["final_rows"])],
    ]
    return tables.render_table(
        "bang-lam-sach",
        ["Bước xử lý", "Số dòng", "Tỉ lệ"],
        rows,
        col_widths=[3.0, 1.0, 1.0],
        align=["left", "right", "right"],
        total_width=6.2,
        highlight_rows=[len(rows) - 1],
    )


def bang_phan_bo_nhan(metadata: dict) -> Path:
    split, counts = metadata["split"], metadata["dataset"]["label_counts"]
    total = sum(counts.values())
    rows = []
    for label in LABELS:
        n = counts.get(label, 0)
        rows.append([
            style.LABEL_VI[label],
            style.LABEL_TAG[label],
            _fmt_int(split["train_labels"].get(label, 0)),
            _fmt_int(split["test_labels"].get(label, 0)),
            _fmt_int(n),
            _fmt_pct(n, total),
        ])
    rows.append(["Tổng cộng", "", _fmt_int(split["train"]), _fmt_int(split["test"]),
                 _fmt_int(total), "100,00%"])
    return tables.render_table(
        "bang-phan-bo-nhan",
        ["Lớp cảm xúc", "Ký hiệu", "Train", "Test", "Tổng", "Tỉ lệ"],
        rows,
        col_widths=[1.4, 1.0, 0.8, 0.8, 0.8, 0.9],
        align=["left", "left", "right", "right", "right", "right"],
        total_width=6.6,
        highlight_rows=[len(rows) - 1],
    )


def _per_class_line(metadata: dict, model: str, key: str) -> str:
    """Ba giá trị của ba lớp gộp trong một ô, ngăn bằng `|` - đúng kiểu ảnh mẫu.

    Dạng phần trăm, khớp ảnh mẫu (Bảng 5.2 ghi "77% | 87%").
    """
    per = metadata["models"][model]["metrics"]["per_class"]
    return " | ".join(_fmt_ratio(per.get(l, {}).get(key, 0.0)) for l in LABELS)


def bang_precision_recall(metadata: dict) -> Path:
    """Precision / Recall theo lớp + thời gian huấn luyện.

    Dựng theo đúng bố cục Bảng 5.2 của bài mẫu (mỗi ô gộp giá trị của các lớp),
    chỉ khác là ba lớp thay vì hai.
    """
    order = " | ".join(style.LABEL_VI[l] for l in LABELS)
    rows = []
    for n in charts._models(metadata):
        rows.append([
            style.MODEL_VI[n],
            _per_class_line(metadata, n, "precision"),
            _per_class_line(metadata, n, "recall"),
            _fmt_num(metadata["models"][n]["train_seconds"], 2) + " s",
        ])
    return tables.render_table(
        "bang-precision-recall",
        ["Thuật toán", f"Precision\n{order}", f"Recall\n{order}",
         "Thời gian\nhuấn luyện"],
        rows,
        col_widths=[1.3, 2.0, 2.0, 1.1],
        align=["left", "center", "center", "center"],
        total_width=7.2,
    )


def bang_hai_lop(metadata: dict) -> Path:
    """Bảng phụ: cùng dữ liệu, cùng model, nhưng BỎ lớp neutral.

    Lý do có bảng này: phần lớn bài báo tiếng Việt cùng chủ đề chỉ phân tích cực/tiêu
    cực. So thẳng bảng 3 lớp của ta với số của họ là so nhầm bài toán. Bảng này cho
    người đọc thấy cùng bộ dữ liệu đặt về 2 lớp thì đạt mức nào.
    """
    binary = metadata.get("binary")
    if not binary:
        raise ValueError("metadata chưa có mục 'binary' - train lại với --binary")

    ordered = sorted(binary["models"], key=lambda n: -binary["models"][n]["macro_f1"])
    rows = [
        [style.MODEL_VI.get(n, n),
         _fmt_ratio(binary["models"][n]["accuracy"]),
         _fmt_ratio(binary["models"][n]["macro_f1"])]
        for n in ordered
    ]
    base = binary["baseline"]
    rows.append([f"Baseline (luôn đoán \"{style.LABEL_VI.get(base['label'], base['label'])}\")",
                 _fmt_ratio(base["accuracy"]), _fmt_ratio(base["macro_f1"])])
    return tables.render_table(
        "bang-2-lop",
        ["Thuật toán", "Accuracy", "macro-F1"],
        rows,
        col_widths=[3.0, 1.2, 1.2],
        align=["left", "center", "center"],
        highlight_rows=[len(rows) - 1],
    )


def bang_fscore(metadata: dict) -> Path:
    """F-score từng lớp + trung bình - bố cục Bảng 5.5 của bài mẫu.

    Có thêm dòng baseline: bài mẫu không có, nhưng thiếu nó thì không ai biết
    các con số kia là giỏi hay chỉ bằng đoán bừa.
    """
    names = charts._models(metadata)
    ordered = sorted(names, key=lambda n: -metadata["models"][n]["metrics"]["macro_f1"])
    rows = []
    for n in ordered:
        m = metadata["models"][n]["metrics"]
        per = m["per_class"]
        rows.append(
            [style.MODEL_VI[n]]
            + [_fmt_ratio(per.get(l, {}).get("f1", 0.0)) for l in LABELS]
            + [_fmt_ratio(m["macro_f1"]), _fmt_ratio(m["accuracy"])]
        )
    base = metadata["baseline"]
    rows.append(
        [f"Baseline (luôn đoán \"{style.LABEL_VI.get(base['label'], base['label'])}\")"]
        + ["–"] * len(LABELS)
        + [_fmt_ratio(base["macro_f1"]), _fmt_ratio(base["accuracy"])]
    )
    return tables.render_table(
        "bang-fscore",
        ["Thuật toán"] + [f"F-score\n{style.LABEL_VI[l]}" for l in LABELS]
        + ["F-score\ntrung bình", "Accuracy"],
        rows,
        col_widths=[2.0, 1.0, 1.0, 1.0, 1.15, 1.0],
        align=["left", "center", "center", "center", "center", "center"],
        total_width=7.2,
        highlight_rows=[0],  # model tốt nhất đứng đầu sau khi sắp xếp
    )


def bang_metrics_chi_tiet(metadata: dict) -> Path:
    rows = []
    for n in charts._models(metadata):
        per = metadata["models"][n]["metrics"]["per_class"]
        for i, label in enumerate(LABELS):
            s = per.get(label, {})
            rows.append([
                style.MODEL_VI[n] if i == 0 else "",
                style.LABEL_VI[label],
                _fmt_num(s.get("precision", 0)),
                _fmt_num(s.get("recall", 0)),
                _fmt_num(s.get("f1", 0)),
                _fmt_int(s.get("support", 0)),
            ])
    return tables.render_table(
        "bang-metrics-chi-tiet",
        ["Mô hình", "Lớp", "Precision", "Recall", "F1", "Support"],
        rows,
        col_widths=[1.3, 1.1, 1.0, 1.0, 1.0, 0.9],
        align=["left", "left", "right", "right", "right", "right"],
        total_width=6.8,
    )


def bang_vi_du_doan_sai(metadata: dict, limit: int = 8) -> Path:
    """Ví dụ đoán sai của model tốt nhất - phần định tính của chương kết quả."""
    names = charts._models(metadata)
    if not names:
        raise ValueError("metadata không có model nào")
    best = max(names, key=lambda n: metadata["models"][n]["metrics"]["macro_f1"])
    samples = metadata["models"][best]["metrics"].get("errors_sample", [])[:limit]
    if not samples:
        raise ValueError(f"model {best} không lưu errors_sample")

    rows = [
        [" ".join(str(s["text"]).split()),
         style.LABEL_VI.get(s["true"], s["true"]),
         style.LABEL_VI.get(s["pred"], s["pred"])]
        for s in samples
    ]
    return tables.render_table(
        "bang-vi-du-doan-sai",
        ["Nội dung bình luận", "Nhãn thực tế", "Nhãn dự đoán"],
        rows,
        col_widths=[3.6, 1.0, 1.0],
        align=["left", "center", "center"],
        total_width=7.0,
    )


# ---------------------------------------------------------------- chạy

def build(metadata: dict, *, tag_dir: Path, skip_sample: bool) -> list[tuple[str, str, str]]:
    """Sinh mọi hình. Trả về [(nhóm, tên file, caption)] để gallery dựng trang."""
    items: list[tuple[str, str, str]] = []

    def run(group: str, caption: str, fn, *args):
        try:
            path = fn(*args)
        except Exception:
            # Một hình lỗi không được kéo sập cả bộ - còn 12 hình kia vẫn dùng được.
            logger.exception("Bỏ qua hình lỗi: %s", caption)
            return
        items.append((group, style.rel(path), caption))
        logger.info("✓ %s", path.name)

    if not skip_sample:
        from paper.analysis.dataset import load_tagged_dataset

        logger.info("Đọc dữ liệu đã gán nhãn từ %s ...", tag_dir)
        frame, _ = load_tagged_dataset(str(tag_dir))
        run("Bảng", "Dữ liệu sau khi thu thập và gán nhãn", bang_mau_du_lieu, frame)
        run("Bảng", "Bình luận tách theo lớp cảm xúc", bang_comment_theo_lop, frame)
        run("Bảng", "Dữ liệu trước và sau tiền xử lý", bang_tien_xu_ly, frame)

    run("Bảng", "Thống kê quá trình làm sạch dữ liệu", bang_lam_sach, metadata)
    run("Bảng", "Phân bố nhãn trên tập huấn luyện và kiểm tra", bang_phan_bo_nhan, metadata)
    run("Bảng", "Precision và Recall của các mô hình", bang_precision_recall, metadata)
    run("Bảng", "Kết quả F-score của các mô hình", bang_fscore, metadata)
    run("Bảng", "Precision / Recall / F1 theo từng lớp", bang_metrics_chi_tiet, metadata)
    run("Bảng", "Một số trường hợp dự đoán sai", bang_vi_du_doan_sai, metadata)
    run("Bảng", "Kết quả trên bài toán 2 lớp (bỏ trung lập)", bang_hai_lop, metadata)

    run("Biểu đồ", "Phân bố nhãn sau khi làm sạch", charts.phan_bo_nhan, metadata)
    run("Biểu đồ", "Phân bố nhãn ở tập train và test", charts.phan_bo_train_test, metadata)
    run("Biểu đồ", "So sánh các mô hình với baseline", charts.so_sanh_model, metadata)
    run("Biểu đồ", "Điểm F1 theo từng lớp cảm xúc", charts.f1_tung_lop, metadata)
    for name in charts._models(metadata):
        run("Biểu đồ", f"Ma trận nhầm lẫn – {style.MODEL_VI[name]}",
            charts.confusion, metadata, name)
    run("Biểu đồ", "Thời gian huấn luyện của các mô hình", charts.thoi_gian_train, metadata)
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m paper.figures",
        description="Sinh hình và bảng cho bài báo (PNG 300dpi + CSV + index.html).",
    )
    parser.add_argument("--metadata", default=str(DATA / "metadata.json"),
                        help="File kết quả huấn luyện")
    parser.add_argument("--tag-dir", default=str(DATA / "tagged"),
                        help="Thư mục Excel đã gán nhãn (chỉ dùng cho bảng mẫu dữ liệu)")
    parser.add_argument("--skip-sample", action="store_true",
                        help="Bỏ bảng mẫu dữ liệu để chạy nhanh (không cần đọc Excel)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    style.apply()
    logger.info("Font dùng cho hình: %s", style.FONT)

    meta_path = Path(args.metadata)
    if not meta_path.is_file():
        logger.error("Không thấy %s. Chạy `python -m src.analyze train` rồi copy "
                     "models_store/metadata.json vào paper/data/.", meta_path)
        return 2
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    # Dọn sạch out/ trước: đổi tên hình hoặc đổi cấu trúc thư mục sẽ để lại file cũ,
    # và folder này được gửi đi nguyên cụm nên không được lẫn rác của lần chạy trước.
    if style.OUT_DIR.exists():
        shutil.rmtree(style.OUT_DIR)
    style.OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = build(metadata, tag_dir=Path(args.tag_dir), skip_sample=args.skip_sample)
    if not items:
        logger.error("Không sinh được hình nào")
        return 1

    page = gallery.render(items, metadata)
    logger.info("\nĐã sinh %d hình vào %s", len(items), style.OUT_DIR)
    logger.info("Mở để xem: %s", page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
