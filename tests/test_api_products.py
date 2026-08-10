"""
Test API `/products` với TestClient + mongomock (override dependency `get_service`).

Điểm mấu chốt so với API cũ: status code phải ĐÚNG (400/404/422), envelope
`{data, success, message}` giữ nguyên ở mọi response kể cả lỗi.
"""
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.api.products import get_service
from src.app import app
from src.repositories.product_repository import ProductRepository
from src.services.product_service import ProductService

MISSING_ID = "0" * 24


@pytest.fixture
def client(seeded_collection):
    """App với Mongo thật được thay bằng mongomock; lifespan bị bỏ qua."""
    app.dependency_overrides[get_service] = lambda: ProductService(
        ProductRepository(seeded_collection)
    )
    # Không dùng `with TestClient(...)` để lifespan (ping Mongo thật) không chạy.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def product_id(seeded_collection):
    return str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])


def test_root():
    assert TestClient(app).get("/").json() == {"status": "ok"}


def test_list_products_khong_kem_comments(client):
    response = client.get("/products?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 2
    assert "comments" not in body["data"]["items"][0]
    assert "total_comments" in body["data"]["items"][0]


def test_list_products_loc_q(client):
    body = client.get("/products?q=anker").json()

    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "Sac Anker 20W"


def test_list_products_limit_vuot_tran_tra_422(client):
    response = client.get("/products?limit=1000")

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_get_product_phan_trang_comment(client, product_id):
    body = client.get(f"/products/{product_id}?comment_limit=1").json()

    assert body["data"]["id"] == product_id
    assert [c["id"] for c in body["data"]["comments"]] == ["c1"]


def test_get_product_rating_rong_duoc_ep_ve_0(client, product_id):
    body = client.get(f"/products/{product_id}?comment_page=2&comment_limit=1").json()

    assert body["data"]["comments"][0]["id"] == "c2"
    assert body["data"]["comments"][0]["rating"] == 0


def test_get_product_id_rac_tra_400(client):
    response = client.get("/products/xxx")

    assert response.status_code == 400
    body = response.json()
    assert body["data"] is None
    assert body["success"] is False
    assert set(body) == {"data", "success", "message"}
    assert body["message"]  # có mô tả, không rỗng


def test_get_product_khong_ton_tai_tra_404(client):
    response = client.get(f"/products/{MISSING_ID}")

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_add_comment_201_va_tang_total(client, product_id, seeded_collection):
    response = client.post(
        f"/products/{product_id}/comments",
        json={"name": "Dung", "content": "Rất ổn", "rating": 5},
    )

    assert response.status_code == 201
    comment_id = response.json()["data"]["comment_id"]
    doc = seeded_collection.find_one({"_id": ObjectId(product_id)})
    assert doc["total_comments"] == 3
    assert doc["comments"][-1]["id"] == comment_id
    assert doc["comments"][-1]["content"] == "Rất ổn"


def test_add_comment_rating_ngoai_khoang_tra_422(client, product_id):
    response = client.post(
        f"/products/{product_id}/comments",
        json={"name": "A", "content": "B", "rating": 9},
    )

    assert response.status_code == 422


def test_add_comment_product_khong_ton_tai_tra_404(client):
    response = client.post(
        f"/products/{MISSING_ID}/comments",
        json={"name": "A", "content": "B", "rating": 1},
    )

    assert response.status_code == 404


def test_update_comment(client, product_id, seeded_collection):
    response = client.patch(
        f"/products/{product_id}/comments/c1", json={"content": "Sửa rồi"}
    )

    assert response.status_code == 200
    doc = seeded_collection.find_one({"_id": ObjectId(product_id)})
    assert doc["comments"][0]["content"] == "Sửa rồi"


def test_update_comment_body_rong_tra_422(client, product_id):
    response = client.patch(f"/products/{product_id}/comments/c1", json={})

    assert response.status_code == 422


def test_update_comment_khong_ton_tai_tra_404(client, product_id):
    response = client.patch(
        f"/products/{product_id}/comments/khong-co", json={"content": "x"}
    )

    assert response.status_code == 404


def test_delete_comment_giam_total_va_lan_2_tra_404(
    client, product_id, seeded_collection
):
    first = client.delete(f"/products/{product_id}/comments/c1")
    assert first.status_code == 200
    assert seeded_collection.find_one({"_id": ObjectId(product_id)})["total_comments"] == 1

    second = client.delete(f"/products/{product_id}/comments/c1")
    assert second.status_code == 404
    assert seeded_collection.find_one({"_id": ObjectId(product_id)})["total_comments"] == 1


def test_delete_product(client, product_id):
    assert client.delete(f"/products/{product_id}").status_code == 200
    assert client.delete(f"/products/{product_id}").status_code == 404


def test_route_khong_ton_tai_van_giu_envelope(client):
    response = client.get("/khong-co-route")

    assert response.status_code == 404
    assert set(response.json()) == {"data", "success", "message"}


def test_mongo_hong_tra_503_khong_phai_500(monkeypatch):
    """App không còn fail-fast, nên lỗi kết nối phải lộ ra dưới dạng 503 rõ ràng."""
    from pymongo.errors import ServerSelectionTimeoutError

    import src.api.products as products_api

    def bung(*_args, **_kwargs):
        raise ServerSelectionTimeoutError("no servers")

    monkeypatch.setattr(products_api, "ProductRepository", bung)
    app.dependency_overrides.clear()

    response = TestClient(app).get("/products?limit=1")

    assert response.status_code == 503
    assert "MONGO_URI" in response.json()["message"]
