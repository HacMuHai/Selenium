"""
Test API `/analyze` bằng model Naive Bayes train thật trong tmp_path (không mock model).

Ca bảo mật bắt buộc: `/analyze/report` nhúng nội dung comment do người ngoài viết,
phải escape HTML - nếu không là lỗ XSS thật.
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.analysis import metrics
from src.analysis.dataset import describe_split
from src.analysis.predictor import Predictor
from src.analysis.trainer import Trainer
from src.api.analysis import get_service
from src.app import app
from src.services.analysis_service import AnalysisService

POSITIVE = ["máy dùng rất tốt", "sản phẩm tuyệt vời", "pin trâu màn đẹp",
            "giao hàng nhanh nhiệt tình", "rất hài lòng nên mua"]
NEGATIVE = ["máy quá tệ nhanh hỏng", "pin tụt rất nhanh", "loa bị rè khó nghe",
            "dịch vụ bảo hành tệ", "màn hình lỗi không lên"]
NEUTRAL = ["cho hỏi máy này mấy sim", "bên mình có bán ốp lưng không",
           "giá thay màn hình bao nhiêu", "shop có thu cũ không",
           "cách cài tiếng việt thế nào"]


@pytest.fixture
def models_dir(tmp_path):
    """Train thật model `nb` (nhanh, không cần TensorFlow) rồi ghi metadata."""
    rows = (
        [{"text": t, "sentiment": "positive"} for t in POSITIVE * 4]
        + [{"text": t, "sentiment": "negative"} for t in NEGATIVE * 4]
        + [{"text": t, "sentiment": "neutral"} for t in NEUTRAL * 4]
    )
    frame = pd.DataFrame(rows)

    from src.analysis.dataset import CleaningStats

    stats = CleaningStats()
    stats.total_rows = stats.final_rows = len(frame)
    stats.label_counts = {k: int(v) for k, v in frame["sentiment"].value_counts().items()}

    directory = tmp_path / "models"
    trainer = Trainer(directory, seed=42)
    results = trainer.train(["nb"], frame)
    evaluations = trainer.evaluate(["nb"], frame)
    baseline = metrics.majority_baseline(list(frame["sentiment"]))
    trainer.write_metadata(stats, describe_split(frame, frame), results, evaluations, baseline, 0.2)
    return directory


@pytest.fixture
def client(models_dir):
    app.dependency_overrides[get_service] = lambda: AnalysisService(
        Predictor(models_dir), default_model="nb"
    )
    yield TestClient(app)   # không dùng `with`: tránh chạy lifespan (ping Mongo thật)
    app.dependency_overrides.clear()


@pytest.fixture
def client_chua_train(tmp_path):
    app.dependency_overrides[get_service] = lambda: AnalysisService(
        Predictor(tmp_path / "trong"), default_model="nb"
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_predict_tra_ve_envelope_dung(client):
    response = client.post("/analyze/predict", json={"text": "máy dùng rất tốt"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "success", "message"}
    assert body["success"] is True
    assert body["data"]["sentiment"] in {"negative", "neutral", "positive"}
    assert body["data"]["model"] == "nb"
    assert set(body["data"]["scores"]) == {"negative", "neutral", "positive"}


def test_predict_phan_loai_dung_chieu(client):
    tot = client.post("/analyze/predict", json={"text": "máy rất tốt pin trâu"}).json()
    te = client.post("/analyze/predict", json={"text": "máy quá tệ nhanh hỏng"}).json()

    assert tot["data"]["sentiment"] == "positive"
    assert te["data"]["sentiment"] == "negative"


def test_predict_model_khong_ton_tai_tra_400(client):
    response = client.post(
        "/analyze/predict", json={"text": "abc", "model": "khongcomodel"}
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


def test_predict_text_rong_tra_422(client):
    assert client.post("/analyze/predict", json={"text": ""}).status_code == 422


def test_predict_text_qua_dai_tra_422(client):
    response = client.post("/analyze/predict", json={"text": "a" * 5001})
    assert response.status_code == 422


def test_predict_chua_train_tra_503(client_chua_train):
    response = client_chua_train.post("/analyze/predict", json={"text": "máy tốt"})

    assert response.status_code == 503
    assert "train" in response.json()["message"]


def test_list_models(client):
    body = client.get("/analyze/models").json()

    assert body["success"] is True
    assert [m["name"] for m in body["data"]["models"]] == ["nb"]
    assert body["data"]["models"][0]["macro_f1"] is not None
    assert body["data"]["baseline"]["label"] in {"negative", "neutral", "positive"}


def test_list_models_chua_train_khong_phai_loi(client_chua_train):
    response = client_chua_train.get("/analyze/models")

    assert response.status_code == 200
    assert response.json()["data"]["models"] == []


def test_report_tra_html_tu_chua(client):
    response = client.get("/analyze/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "http://" not in response.text and "https://" not in response.text
    assert "<svg" in response.text


def test_report_escape_html_chong_xss(client, models_dir):
    """Nội dung comment do người ngoài viết -> bắt buộc escape."""
    import json

    path = models_dir / "metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["models"]["nb"]["metrics"]["errors_sample"] = [
        {"text": "<img src=x onerror=alert(1)>", "true": "positive", "pred": "negative"}
    ]
    path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    text = client.get("/analyze/report").text

    assert "<img src=x onerror=alert(1)>" not in text
    assert "&lt;img" in text


def test_report_chua_train_tra_503(client_chua_train):
    assert client_chua_train.get("/analyze/report").status_code == 503


def test_app_van_khoi_dong_khi_khong_co_mongo():
    """Bỏ fail-fast: DB hỏng thì `/analyze` vẫn phải dùng được."""
    assert TestClient(app).get("/").json() == {"status": "ok"}


def test_compare_tra_ve_moi_model_da_train(client):
    response = client.post("/analyze/compare", json={"text": "máy dùng rất tốt"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert [d["model"] for d in body["data"]] == ["nb"]   # chỉ nb được train trong fixture
    assert body["data"][0]["sentiment"] in {"negative", "neutral", "positive"}


def test_compare_chua_train_tra_503(client_chua_train):
    response = client_chua_train.post("/analyze/compare", json={"text": "máy tốt"})
    assert response.status_code == 503


def test_compare_text_rong_tra_422(client):
    assert client.post("/analyze/compare", json={"text": ""}).status_code == 422


def test_report_co_o_thu_nghiem_va_van_tu_chua(client):
    text = client.get("/analyze/report").text

    assert 'id="inp"' in text and 'id="go"' in text
    assert "analyze/compare" in text or "'compare'" in text
    assert "http://" not in text and "https://" not in text   # JS inline, không CDN
