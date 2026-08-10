"""
Fixture dùng chung. Mongo được thay bằng `mongomock` - test chạy hoàn toàn offline.
"""
import os
from datetime import datetime

import mongomock
import pytest

# Settings đọc .env lúc import; đảm bảo có giá trị kể cả trên máy CI chưa có file .env.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

from src.repositories.product_repository import ProductRepository  # noqa: E402


def make_product(name: str, link: str, comments: list[dict]) -> dict:
    return {
        "name": name,
        "link": link,
        "comments": comments,
        "total_comments": len(comments),
        "crawled_at": datetime(2026, 1, 1, 12, 0, 0),
        "version": "1.0",
    }


@pytest.fixture
def collection():
    """Collection mongomock trống."""
    return mongomock.MongoClient()["selenium_scraper"]["comments"]


@pytest.fixture
def seeded_collection(collection):
    """2 product mẫu; product đầu có 1 comment `rating` rỗng như dữ liệu cũ."""
    collection.insert_many(
        [
            make_product(
                "Sac Anker 20W",
                "https://example.com/sac-anker-20w",
                [
                    {"id": "c1", "name": "An", "content": "Tốt", "rating": 5},
                    {"id": "c2", "name": "Binh", "content": "Tạm", "rating": ""},
                ],
            ),
            make_product(
                "Cap USB-C Baseus",
                "https://example.com/cap-usb-c-baseus",
                [{"id": "c3", "name": "Chi", "content": "Bền", "rating": 4}],
            ),
        ]
    )
    return collection


@pytest.fixture
def repository(seeded_collection):
    return ProductRepository(seeded_collection)
