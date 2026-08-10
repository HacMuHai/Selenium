"""
MongoDB connection - một client duy nhất cho mỗi process (dùng chung cho CLI lẫn API).

KHÔNG ping ở mỗi lần lấy collection: pymongo đã có topology monitor riêng, ping mỗi call
chỉ thêm một round-trip vô ích. Ping đúng 1 lần lúc tạo client để fail fast.
"""
import logging
from functools import lru_cache
from typing import Optional

import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> MongoClient:
    """MongoClient singleton. Ping 1 lần để fail fast khi URI/mạng sai."""
    settings = get_settings()
    client = MongoClient(
        settings.mongo_uri,
        server_api=ServerApi("1"),
        tlsCAFile=certifi.where(),
    )
    client.admin.command("ping")
    # KHÔNG log mongo_uri - chứa password.
    logger.info("Đã kết nối MongoDB (db=%s)", settings.mongo_db)
    return client


def get_db() -> Database:
    """Database mặc định theo `settings.mongo_db`."""
    return get_client()[get_settings().mongo_db]


def get_collection(name: Optional[str] = None) -> Collection:
    """Collection theo tên; mặc định `settings.mongo_collection`."""
    return get_db()[name or get_settings().mongo_collection]


def ensure_indexes(collection: Optional[Collection] = None) -> None:
    """Tạo index cần cho API/crawler. Không chặn startup nếu tạo lỗi."""
    col = collection if collection is not None else get_collection()
    try:
        col.create_index([("comments.id", 1)], name="comments_id_idx")
    except PyMongoError:
        logger.warning("Không tạo được index comments.id", exc_info=True)
    try:
        col.create_index([("link", 1)], unique=True, name="link_unique_idx")
    except PyMongoError:
        # Dữ liệu cũ có thể đang có link trùng -> chỉ cảnh báo, không crash.
        logger.warning(
            "Không tạo được unique index trên `link` (có thể do dữ liệu trùng)",
            exc_info=True,
        )


def close_client() -> None:
    """Đóng client và xoá cache để lần sau tạo lại."""
    if get_client.cache_info().currsize == 0:
        return
    client = get_client()
    client.close()
    get_client.cache_clear()
    logger.info("Đã đóng kết nối MongoDB")
