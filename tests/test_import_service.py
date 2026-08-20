"""
Test ImportService: Excel -> product document. Round-trip qua ExportService để chắc
chắn hai chiều khớp nhau, và kiểm cả file 4 cột kiểu cũ.
"""
import pytest
from openpyxl import Workbook

from src.repositories.memory_repository import InMemoryProductRepository
from src.repositories.product_repository import ProductRepository
from src.services.export_service import ExportService
from src.services.import_service import ImportService, read_products

from tests.conftest import make_product


def write_sheet(path, header, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    workbook.save(str(path))


def test_round_trip_export_import(tmp_path):
    """Export rồi import lại phải ra đúng số product / comment / rating / sàn."""
    source = InMemoryProductRepository()
    for index in range(2):
        product = make_product(
            f"San pham {index}",
            f"https://cellphones.com.vn/p{index}.html",
            [
                {"id": f"c{index}{c}", "name": f"user{c}", "content": f"noi dung {index}-{c}",
                 "rating": c + 1}
                for c in range(3)
            ],
        )
        product["site"] = "cellphones"
        source.insert_product(product)
    ExportService(source, str(tmp_path), max_rows_per_file=2).export()

    target = InMemoryProductRepository()
    stats = ImportService(target).import_dir(str(tmp_path))

    assert stats["products"] == 2
    assert stats["inserted"] == 2
    assert stats["comments"] == 6
    docs = sorted(target.iter_products(), key=lambda d: d["link"])
    assert docs[0]["name"] == "San pham 0"
    assert docs[0]["site"] == "cellphones"
    assert docs[0]["total_comments"] == 3
    assert [c["rating"] for c in docs[0]["comments"]] == [1, 2, 3]
    assert [c["name"] for c in docs[0]["comments"]] == ["user0", "user1", "user2"]


def test_quet_ca_thu_muc_con_theo_san(tmp_path):
    """Trỏ vào data/ phải nạp được cả data/<sàn>/."""
    for site, link in (("cellphones", "https://cellphones.com.vn/a.html"),
                       ("fptshop", "https://fptshop.com.vn/b")):
        directory = tmp_path / site
        directory.mkdir()
        write_sheet(
            directory / "comments_export_1.xlsx",
            ["link", "name_item", "comments_id", "comments_content", "site", "user_name", "rating"],
            [[link, "P", "c1", "tot", site, "u", 5]],
        )

    products = read_products(sorted(tmp_path.rglob("*.xlsx")))

    assert len(products) == 2
    assert {p["site"] for p in products.values()} == {"cellphones", "fptshop"}


def test_forward_fill_link_va_ten(tmp_path):
    """Dòng trống 2 cột đầu thuộc về product của dòng trước."""
    write_sheet(
        tmp_path / "a.xlsx",
        ["link", "name_item", "comments_id", "comments_content", "site", "user_name", "rating"],
        [
            ["https://cellphones.com.vn/a.html", "May A", "c1", "cmt 1", "cellphones", "u1", 5],
            ["", "", "c2", "cmt 2", "cellphones", "u2", 4],
            ["https://cellphones.com.vn/b.html", "May B", "c3", "cmt 3", "cellphones", "u3", 3],
        ],
    )

    products = read_products([tmp_path / "a.xlsx"])

    assert len(products) == 2
    assert len(products["https://cellphones.com.vn/a.html"]["comments"]) == 2
    assert products["https://cellphones.com.vn/a.html"]["name"] == "May A"


def test_file_cu_4_cot(tmp_path):
    """File export cũ không có site/user_name/rating: suy sàn từ link, rating = 0."""
    write_sheet(
        tmp_path / "old.xlsx",
        ["link", "name_item", "comments_id", "comments_content"],
        [["https://www.thegioididong.com/dtdd/x", "May X", "c1", "cmt"]],
    )

    products = read_products([tmp_path / "old.xlsx"])

    product = products["https://www.thegioididong.com/dtdd/x"]
    assert product["site"] == "thegioididong"
    assert product["comments"][0]["rating"] == 0
    assert product["comments"][0]["name"] == ""


def test_gom_product_trai_tren_nhieu_file_va_khu_trung_id(tmp_path):
    header = ["link", "name_item", "comments_id", "comments_content", "site", "user_name", "rating"]
    link = "https://fptshop.com.vn/x"
    write_sheet(tmp_path / "1.xlsx", header, [[link, "X", "c1", "a", "fptshop", "u", 5]])
    # File 2 lặp lại c1 (trùng) và thêm c2.
    write_sheet(tmp_path / "2.xlsx", header,
                [[link, "X", "c1", "a", "fptshop", "u", 5],
                 [link, "X", "c2", "b", "fptshop", "u", 4]])

    products = read_products(sorted(tmp_path.rglob("*.xlsx")))

    assert len(products) == 1
    assert [c["id"] for c in products[link]["comments"]] == ["c1", "c2"]


def test_mode_skip_va_replace(tmp_path, collection):
    """Dùng repo Mongo (mongomock) vì in-memory cố tình không dedup theo DB."""
    header = ["link", "name_item", "comments_id", "comments_content", "site", "user_name", "rating"]
    link = "https://fptshop.com.vn/x"
    write_sheet(tmp_path / "1.xlsx", header, [[link, "Ten moi", "c1", "a", "fptshop", "u", 5]])

    repo = ProductRepository(collection)
    repo.insert_product(make_product("Ten cu", link, []))

    assert ImportService(repo, mode="skip").import_dir(str(tmp_path))["skipped"] == 1
    assert collection.find_one({"link": link})["name"] == "Ten cu"

    assert ImportService(repo, mode="replace").import_dir(str(tmp_path))["replaced"] == 1
    assert collection.count_documents({"link": link}) == 1
    document = collection.find_one({"link": link})
    assert document["name"] == "Ten moi"
    assert document["total_comments"] == 1


def test_dry_run_khong_ghi(tmp_path):
    write_sheet(
        tmp_path / "1.xlsx",
        ["link", "name_item", "comments_id", "comments_content"],
        [["https://fptshop.com.vn/x", "X", "c1", "a"]],
    )
    repo = InMemoryProductRepository()

    stats = ImportService(repo).import_dir(str(tmp_path), dry_run=True)

    assert stats["inserted"] == 1
    assert repo.count_products() == 0


def test_thu_muc_khong_ton_tai():
    with pytest.raises(FileNotFoundError):
        ImportService(InMemoryProductRepository()).import_dir("/khong/co/thu/muc")


def test_mode_khong_hop_le():
    with pytest.raises(ValueError):
        ImportService(InMemoryProductRepository(), mode="upsert")
