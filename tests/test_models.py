"""
Test 3 model trên dữ liệu tự tạo (nhỏ, chạy nhanh, không phụ thuộc excel_tag_v2 thật).

Ca quan trọng: round-trip save/load, `predict_batch` khớp `predict`, chặn artifact
lệch phiên bản preprocessing, và bug "token chưa từng thấy" của Naive Bayes.
"""
import importlib.util

import pandas as pd
import pytest

from src.analysis.models.base import ModelVersionMismatch
from src.analysis.models.naive_bayes import NaiveBayesModel
from src.analysis.models.svm import SVMModel
from src.analysis.registry import available_names, get_model_class, parse_model_list

HAS_TF = importlib.util.find_spec("tensorflow") is not None

POSITIVE = ["máy dùng rất tốt", "sản phẩm tuyệt vời", "pin trâu màn đẹp",
            "giao hàng nhanh nhân viên nhiệt tình", "rất hài lòng nên mua"]
NEGATIVE = ["máy quá tệ nhanh hỏng", "pin tụt rất nhanh", "loa bị rè khó nghe",
            "dịch vụ bảo hành tệ", "màn hình lỗi không lên"]
NEUTRAL = ["cho hỏi máy này mấy sim", "bên mình có bán ốp lưng không",
           "giá thay màn hình bao nhiêu", "shop có thu cũ đổi mới không",
           "cách cài đặt tiếng việt thế nào"]


@pytest.fixture
def train_df():
    rows = (
        [{"text": t, "sentiment": "positive"} for t in POSITIVE * 4]
        + [{"text": t, "sentiment": "negative"} for t in NEGATIVE * 4]
        + [{"text": t, "sentiment": "neutral"} for t in NEUTRAL * 4]
    )
    return pd.DataFrame(rows)


# ---------- registry ----------

def test_available_names_co_nb_va_svm():
    names = available_names()
    assert "nb" in names and "svm" in names
    assert ("lstm" in names) is HAS_TF


def test_get_model_class_ten_sai():
    with pytest.raises(ValueError, match="không hợp lệ"):
        get_model_class("khongcomodel")


def test_parse_model_list():
    assert parse_model_list(" nb , svm ") == ["nb", "svm"]
    with pytest.raises(ValueError):
        parse_model_list("nb,bogus")
    with pytest.raises(ValueError):
        parse_model_list("")


# ---------- Naive Bayes ----------

def test_nb_hoc_duoc(train_df):
    model = NaiveBayesModel()
    model.train(train_df)

    assert model.predict("máy rất tốt pin trâu")[0] == "positive"
    assert model.predict("máy tệ pin tụt nhanh")[0] == "negative"


def test_nb_token_la_khong_duoc_uu_ai(train_df):
    """Bug bản gốc: `.get(token, 0)` khiến token lạ (điểm 0) tốt hơn token đã biết (log âm)."""
    model = NaiveBayesModel()
    model.train(train_df)

    _, known = model.predict("máy dùng rất tốt")
    _, unknown = model.predict("xyzzy qwerty asdfgh")

    assert max(known.values()) > max(unknown.values())
    assert all(v < 0 for v in unknown.values()), "token lạ phải nhận log-prob âm, không phải 0"


def test_nb_vocab_toan_cuc_khong_lech_ve_lop_it_du_lieu():
    """Dùng vocab riêng từng lớp làm mẫu số lệch -> lớp ít dữ liệu nuốt hết dự đoán."""
    rows = (
        [{"text": t, "sentiment": "negative"} for t in NEGATIVE * 20]   # nhiều
        + [{"text": t, "sentiment": "neutral"} for t in NEUTRAL[:1]]    # rất ít
        + [{"text": t, "sentiment": "positive"} for t in POSITIVE * 8]
    )
    model = NaiveBayesModel()
    model.train(pd.DataFrame(rows))

    assert model.predict("pin tụt rất nhanh máy tệ")[0] == "negative"


def test_nb_roundtrip(tmp_path, train_df):
    model = NaiveBayesModel()
    model.train(train_df)
    before = model.predict("máy rất tốt")

    model.save(tmp_path)
    after = NaiveBayesModel.load(tmp_path).predict("máy rất tốt")

    assert before == after


def test_nb_chan_artifact_lech_phien_ban(tmp_path, train_df):
    import joblib

    model = NaiveBayesModel()
    model.train(train_df)
    model.save(tmp_path)

    payload = joblib.load(tmp_path / "naive_bayes.joblib")
    payload["version"] = "0.0-cu"
    joblib.dump(payload, tmp_path / "naive_bayes.joblib")

    with pytest.raises(ModelVersionMismatch):
        NaiveBayesModel.load(tmp_path)


# ---------- SVM ----------

def test_svm_hoc_duoc(train_df):
    model = SVMModel()
    model.train(train_df)

    assert model.predict("máy rất tốt pin trâu")[0] == "positive"
    assert model.predict("máy tệ pin tụt nhanh")[0] == "negative"


def test_svm_predict_batch_khop_predict_le(train_df):
    model = SVMModel()
    model.train(train_df)
    texts = ["máy rất tốt", "máy quá tệ", "cho hỏi mấy sim"]

    assert model.predict_batch(texts) == [model.predict(t)[0] for t in texts]


def test_svm_predict_batch_rong(train_df):
    model = SVMModel()
    model.train(train_df)
    assert model.predict_batch([]) == []


def test_svm_scores_du_3_lop(train_df):
    model = SVMModel()
    model.train(train_df)
    _, scores = model.predict("máy rất tốt")

    assert set(scores) == {"negative", "neutral", "positive"}
    assert sum(scores.values()) == pytest.approx(1.0, abs=1e-6)


def test_svm_roundtrip(tmp_path, train_df):
    model = SVMModel()
    model.train(train_df)
    texts = ["máy rất tốt", "máy quá tệ"]
    before = model.predict_batch(texts)

    model.save(tmp_path)
    assert SVMModel.load(tmp_path).predict_batch(texts) == before


# ---------- LSTM ----------

@pytest.mark.skipif(not HAS_TF, reason="chưa cài TensorFlow")
def test_lstm_train_va_predict_batch(tmp_path, train_df):
    from src.analysis.models.lstm import LSTMModel

    model = LSTMModel(epochs=1)
    model.train(train_df)

    labels = model.predict_batch(["máy rất tốt", "máy quá tệ"])
    assert len(labels) == 2
    assert all(l in {"negative", "neutral", "positive"} for l in labels)


@pytest.mark.skipif(not HAS_TF, reason="chưa cài TensorFlow")
def test_lstm_max_length_dung_percentile_khong_dung_max(train_df):
    """Bản gốc dùng max() -> pad mọi chuỗi tới comment dài nhất (2246 ký tự)."""
    from src.analysis.models.lstm import LSTMModel

    frame = pd.concat(
        [train_df, pd.DataFrame([{"text": "từ " * 500, "sentiment": "neutral"}])],
        ignore_index=True,
    )
    model = LSTMModel(epochs=1)
    model.train(frame)

    assert model.max_length < 100, "một comment dài bất thường không được kéo cả tập"


@pytest.mark.skipif(not HAS_TF, reason="chưa cài TensorFlow")
def test_lstm_roundtrip(tmp_path, train_df):
    from src.analysis.models.lstm import LSTMModel

    model = LSTMModel(epochs=1)
    model.train(train_df)
    texts = ["máy rất tốt", "máy quá tệ"]
    before = model.predict_batch(texts)

    model.save(tmp_path)
    assert LSTMModel.load(tmp_path).predict_batch(texts) == before
