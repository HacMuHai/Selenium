"""
Chỉ số đánh giá, cài tay - KHÔNG import sklearn.

Lý do không dùng `sklearn.metrics`: module này phải nạp được ở tiến trình chỉ hiển thị
kết quả đã lưu (API, render HTML) mà không kéo theo cả sklearn.

**macro-F1 là chỉ số chính**, không phải accuracy. Với dữ liệu lệch lớp, một model chỉ
đoán lớp đa số vẫn có accuracy cao nhưng vô dụng - `majority_baseline()` cho biết ngưỡng đó.
"""
from collections import Counter
from typing import Sequence

LABELS: tuple[str, ...] = ("negative", "neutral", "positive")


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if not y_true:
        return 0.0
    hit = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    return hit / len(y_true)


def confusion_matrix(
    y_true: Sequence[str], y_pred: Sequence[str]
) -> dict[str, dict[str, int]]:
    """`matrix[nhãn_thật][nhãn_đoán] = số lượng`."""
    matrix = {a: {b: 0 for b in LABELS} for a in LABELS}
    for true, pred in zip(y_true, y_pred):
        if true in matrix and pred in matrix[true]:
            matrix[true][pred] += 1
    return matrix


def per_class_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] = LABELS
) -> dict[str, dict[str, float]]:
    """precision / recall / f1 / support cho TỪNG lớp trong `labels`.

    `labels` truyền vào được để đánh giá bài toán 2 lớp: giữ nguyên 3 lớp thì `neutral`
    có support 0, f1 0, và macro-F1 bị chia cho 3 -> thấp giả tạo.
    """
    truth, pred = Counter(y_true), Counter(y_pred)
    hit = Counter(a for a, b in zip(y_true, y_pred) if a == b)

    out: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = hit[label]
        precision = tp / pred[label] if pred[label] else 0.0
        recall = tp / truth[label] if truth[label] else 0.0
        # f1 = 0 khi cả hai bằng 0 - không để chia cho 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": truth[label],
        }
    return out


def macro_f1(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] = LABELS
) -> float:
    """Trung bình F1 trên CẢ các lớp trong `labels`, kể cả lớp model không đoán tới."""
    scores = per_class_metrics(y_true, y_pred, labels)
    return sum(scores[label]["f1"] for label in labels) / len(labels)


def majority_baseline(y_true: Sequence[str]) -> dict:
    """Điểm của model ngu nhất: luôn đoán lớp đa số. Mọi kết quả phải so với con số này."""
    if not y_true:
        return {"label": None, "accuracy": 0.0, "macro_f1": 0.0}
    label = Counter(y_true).most_common(1)[0][0]
    y_pred = [label] * len(y_true)
    return {
        "label": label,
        "accuracy": accuracy(y_true, y_pred),
        "macro_f1": macro_f1(y_true, y_pred),
    }


def evaluation_report(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] = LABELS
) -> dict:
    """Gom tất cả chỉ số vào 1 dict JSON-serializable, dùng cho metadata + HTML."""
    return {
        "n": len(y_true),
        "accuracy": accuracy(y_true, y_pred),
        "macro_f1": macro_f1(y_true, y_pred, labels),
        "per_class": per_class_metrics(y_true, y_pred, labels),
        "confusion": confusion_matrix(y_true, y_pred),
    }
