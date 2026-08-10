"""
Test ExportService qua InMemoryProductRepository - không cần Mongo, không mock openpyxl.
File sinh ra được đọc lại bằng openpyxl để kiểm nội dung thật.
"""
import pytest
from openpyxl import load_workbook

from src.repositories.memory_repository import InMemoryProductRepository
from src.services.export_service import HEADER, ExportService

from tests.conftest import make_product


def build_repo(product_count: int, comments_per_product: int):
    repo = InMemoryProductRepository()
    for p in range(product_count):
        comments = [
            {
                "id": f"p{p}c{c}",
                "name": f"user{c}",
                "content": f"noi dung {p}-{c}",
                "rating": c % 6,
            }
            for c in range(comments_per_product)
        ]
        repo.insert_product(
            make_product(f"San pham {p}", f"https://example.com/p{p}", comments)
        )
    return repo


def test_chia_file_theo_max_rows(tmp_path):
    repo = build_repo(product_count=3, comments_per_product=2)  # 6 dòng
    service = ExportService(repo, str(tmp_path), max_rows_per_file=2)

    files = service.export()

    assert len(files) == 3
    assert all(path.exists() for path in files)
    assert sorted(p.name for p in files) == [
        "comments_export_1.xlsx",
        "comments_export_2.xlsx",
        "comments_export_3.xlsx",
    ]


def test_header_va_noi_dung(tmp_path):
    repo = build_repo(product_count=1, comments_per_product=2)
    service = ExportService(repo, str(tmp_path), max_rows_per_file=100)

    files = service.export()

    sheet = load_workbook(files[0]).active
    rows = list(sheet.iter_rows(values_only=True))
    assert list(rows[0]) == HEADER
    # Dòng đầu của product có link + tên; dòng sau để trống 2 cột đầu.
    assert rows[1][0] == "https://example.com/p0"
    assert rows[1][3] == "noi dung 0-0"
    assert rows[2][0] is None
    assert rows[2][3] == "noi dung 0-1"


def test_bo_qua_comment_rong(tmp_path):
    repo = InMemoryProductRepository()
    repo.insert_product(
        make_product(
            "P",
            "https://example.com/p",
            [
                {"id": "a", "name": "x", "content": "", "rating": 0},
                {"id": "b", "name": "y", "content": "co noi dung", "rating": 1},
            ],
        )
    )
    service = ExportService(repo, str(tmp_path), max_rows_per_file=100)

    files = service.export()

    sheet = load_workbook(files[0]).active
    rows = list(sheet.iter_rows(values_only=True))
    assert len(rows) == 2  # header + 1 dòng
    assert rows[1][2] == "b"


def test_khong_co_du_lieu_thi_khong_tao_file(tmp_path):
    service = ExportService(InMemoryProductRepository(), str(tmp_path))

    assert service.export() == []
    assert list(tmp_path.glob("*.xlsx")) == []


def test_max_rows_khong_hop_le():
    with pytest.raises(ValueError):
        ExportService(InMemoryProductRepository(), "/tmp/x", max_rows_per_file=0)


def test_memory_repository_khong_dedup_theo_db():
    """--no-db không đọc Mongo nên exists_by_link luôn False (có chủ đích)."""
    repo = build_repo(product_count=1, comments_per_product=1)

    assert repo.exists_by_link("https://example.com/p0") is False
    assert repo.count_products() == 1
