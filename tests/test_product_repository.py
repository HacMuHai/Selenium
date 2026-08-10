"""
Test ProductRepository trên mongomock. Tập trung vào đúng 3 chỗ bản cũ làm sai:
đọc field ở cấp document, dùng modified_count, và trả cả mảng comments trong danh sách.
"""
import pytest
from bson import ObjectId

from src.repositories.product_repository import ProductRepository, to_object_id

MISSING_ID = "0" * 24


def test_list_products_khong_tra_mang_comments(repository):
    items, total = repository.list_products(page=1, limit=10)

    assert total == 2
    assert len(items) == 2
    for item in items:
        assert "comments" not in item
        assert "total_comments" in item


def test_list_products_phan_trang(repository):
    page1, total = repository.list_products(page=1, limit=1)
    page2, _ = repository.list_products(page=2, limit=1)

    assert total == 2
    assert len(page1) == 1 and len(page2) == 1
    assert page1[0]["_id"] != page2[0]["_id"]


def test_list_products_loc_theo_q(repository):
    items, total = repository.list_products(page=1, limit=10, q="anker")

    assert total == 1
    assert items[0]["name"] == "Sac Anker 20W"


def test_list_products_q_escape_ky_tu_regex(repository):
    # "(" là regex không hợp lệ; nếu không escape thì pymongo/mongomock sẽ ném lỗi.
    items, total = repository.list_products(page=1, limit=10, q="(")

    assert (items, total) == ([], 0)


def test_exists_by_link(repository):
    assert repository.exists_by_link("https://example.com/sac-anker-20w") is True
    assert repository.exists_by_link("https://example.com/khong-co") is False


def test_insert_product(collection):
    repo = ProductRepository(collection)

    product_id = repo.insert_product(
        {
            "name": "X",
            "link": "https://example.com/x",
            "comments": [],
            "total_comments": 0,
            "crawled_at": None,
            "version": "1.0",
        }
    )

    assert repo.count_products() == 1
    assert collection.find_one({"_id": ObjectId(product_id)})["link"] == (
        "https://example.com/x"
    )


def test_get_product_with_comment_page_cat_dung_trang(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])

    page1 = repository.get_product_with_comment_page(pid, skip=0, limit=1)
    page2 = repository.get_product_with_comment_page(pid, skip=1, limit=1)

    assert [c["id"] for c in page1["comments"]] == ["c1"]
    assert [c["id"] for c in page2["comments"]] == ["c2"]


def test_update_comment_sua_dung_phan_tu(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])

    assert repository.update_comment(pid, "c2", {"content": "Đã sửa"}) is True

    comments = seeded_collection.find_one({"_id": ObjectId(pid)})["comments"]
    assert comments[0]["content"] == "Tốt"  # c1 không đổi
    assert comments[1]["content"] == "Đã sửa"


def test_update_comment_gia_tri_y_het_van_tra_true(repository, seeded_collection):
    """Dùng matched_count chứ không phải modified_count - nếu không sẽ 404 sai."""
    pid = str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])

    assert repository.update_comment(pid, "c1", {"content": "Tốt"}) is True


def test_update_comment_khong_ton_tai(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])

    assert repository.update_comment(pid, "khong-co", {"content": "x"}) is False


def test_delete_comment_giam_total_dung_1_va_khong_am(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Sac Anker 20W"})["_id"])

    assert repository.delete_comment(pid, "c1") is True
    doc = seeded_collection.find_one({"_id": ObjectId(pid)})
    assert doc["total_comments"] == 1
    assert [c["id"] for c in doc["comments"]] == ["c2"]

    # Gọi lại: không còn khớp -> không đụng total_comments.
    assert repository.delete_comment(pid, "c1") is False
    assert seeded_collection.find_one({"_id": ObjectId(pid)})["total_comments"] == 1


def test_add_comment_tang_total(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Cap USB-C Baseus"})["_id"])

    comment_id = repository.add_comment(
        pid, {"id": "c9", "name": "D", "content": "Ok", "rating": 3}
    )

    doc = seeded_collection.find_one({"_id": ObjectId(pid)})
    assert comment_id == "c9"
    assert doc["total_comments"] == 2
    assert doc["comments"][-1]["content"] == "Ok"


def test_add_comment_product_khong_ton_tai(repository):
    assert repository.add_comment(MISSING_ID, {"id": "z", "name": "", "content": "", "rating": 0}) is None


def test_delete_product(repository, seeded_collection):
    pid = str(seeded_collection.find_one({"name": "Cap USB-C Baseus"})["_id"])

    assert repository.delete_product(pid) is True
    assert repository.count_products() == 1
    assert repository.delete_product(pid) is False


def test_to_object_id_id_rac_nem_valueerror():
    with pytest.raises(ValueError):
        to_object_id("khong-phai-objectid")


def test_repository_id_rac_nem_valueerror(repository):
    with pytest.raises(ValueError):
        repository.get_product("xxx")


def test_iter_products_ap_dung_projection(repository):
    docs = list(repository.iter_products({"link": 1, "name": 1, "comments": 1}))

    assert len(docs) == 2
    assert "total_comments" not in docs[0]
    assert "comments" in docs[0]
