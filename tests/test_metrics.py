"""
Test chỉ số đánh giá. Trọng tâm: macro-F1 tính trên CẢ 3 lớp và baseline lớp đa số -
đây là hai thứ quyết định việc đọc kết quả có đúng hay không.
"""
import pytest

from src.analysis.metrics import (
    LABELS,
    accuracy,
    confusion_matrix,
    evaluation_report,
    macro_f1,
    majority_baseline,
    per_class_metrics,
)


def test_accuracy_hoan_hao():
    y = ["negative", "neutral", "positive"]
    assert accuracy(y, y) == 1.0


def test_accuracy_rong():
    assert accuracy([], []) == 0.0


def test_accuracy_mot_nua():
    assert accuracy(["negative", "positive"], ["negative", "neutral"]) == 0.5


def test_confusion_matrix():
    y_true = ["negative", "negative", "positive"]
    y_pred = ["negative", "neutral", "positive"]
    matrix = confusion_matrix(y_true, y_pred)

    assert matrix["negative"]["negative"] == 1
    assert matrix["negative"]["neutral"] == 1
    assert matrix["positive"]["positive"] == 1
    assert matrix["neutral"]["neutral"] == 0


def test_per_class_tinh_dung_tay():
    # negative: TP=2, FP=1 -> P=2/3 ; FN=1 -> R=2/3 -> F1=2/3
    y_true = ["negative", "negative", "negative", "positive"]
    y_pred = ["negative", "negative", "positive", "negative"]
    scores = per_class_metrics(y_true, y_pred)

    assert scores["negative"]["precision"] == pytest.approx(2 / 3)
    assert scores["negative"]["recall"] == pytest.approx(2 / 3)
    assert scores["negative"]["f1"] == pytest.approx(2 / 3)
    assert scores["negative"]["support"] == 3


def test_f1_bang_0_khong_chia_cho_0():
    """Lớp không xuất hiện ở cả nhãn thật lẫn dự đoán -> F1 = 0, không ZeroDivisionError."""
    scores = per_class_metrics(["negative"], ["negative"])
    assert scores["neutral"]["f1"] == 0.0
    assert scores["positive"]["f1"] == 0.0


def test_macro_f1_trung_binh_tren_ca_3_lop():
    """Model chỉ đoán 1 lớp bị phạt vì 2 lớp còn lại F1 = 0."""
    y_true = ["negative"] * 8 + ["positive"] * 2
    y_pred = ["negative"] * 10

    assert accuracy(y_true, y_pred) == pytest.approx(0.8)
    # F1(negative) = 2*0.8*1/(1.8) ; F1(neutral) = F1(positive) = 0
    assert macro_f1(y_true, y_pred) == pytest.approx((2 * 0.8 / 1.8) / 3)
    assert macro_f1(y_true, y_pred) < 0.3, "macro-F1 phải phơi bày model chỉ đoán 1 lớp"


def test_majority_baseline_tren_phan_bo_that():
    """Phân bố xấp xỉ excel_tag_v2 sau làm sạch: negative đa số."""
    y_true = ["negative"] * 1637 + ["positive"] * 1169 + ["neutral"] * 322
    baseline = majority_baseline(y_true)

    assert baseline["label"] == "negative"
    assert baseline["accuracy"] == pytest.approx(1637 / 3128, abs=1e-4)
    assert baseline["macro_f1"] < 0.25


def test_majority_baseline_rong():
    assert majority_baseline([])["label"] is None


def test_evaluation_report_du_khoa():
    report = evaluation_report(["negative", "positive"], ["negative", "negative"])

    assert set(report) == {"n", "accuracy", "macro_f1", "per_class", "confusion"}
    assert report["n"] == 2
    assert set(report["per_class"]) == set(LABELS)
