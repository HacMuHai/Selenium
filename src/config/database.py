"""
Database configuration - MongoDB connection
"""
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from typing import Optional
import sys

# Cấu hình MongoDB
MONGO_URI = "mongodb+srv://selenium_db:selenium_pw123@cluster0.1cqkft2.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "selenium_scraper"
# COLLECTION_NAME = "comments"

# Lưu connection vào sys.modules để không bị mất khi reload module
_MODULE_NAME = __name__


def _get_storage():
    """Lấy storage để lưu connections (không bị reset khi reload)"""
    if not hasattr(sys.modules[_MODULE_NAME], '_storage'):
        sys.modules[_MODULE_NAME]._storage = {
            '_client': None,
            '_database': None,
            '_collection': None
        }
    return sys.modules[_MODULE_NAME]._storage


def get_mongo_client() -> MongoClient:
    """Lấy MongoDB client, tạo mới nếu chưa có hoặc connection đã đóng"""
    storage = _get_storage()
    _client = storage['_client']

    # Kiểm tra connection có tồn tại và còn sống không
    if _client is None or not _is_connection_alive(_client):
        _client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        print("MongoClient", _is_connection_alive(_client))
        storage['_client'] = _client
        print(f"Đã kết nối MongoDB tại {MONGO_URI}")
    else:
        print("- Sử dụng client đã kết nối!")
    return _client


def _is_connection_alive(client: MongoClient) -> bool:
    """Kiểm tra xem MongoDB connection có còn sống không"""
    try:
        # Ping server để kiểm tra connection
        client.admin.command('ping')
        return True
    except Exception:
        return False


def get_database():
    """Lấy database, tạo mới nếu chưa có"""
    storage = _get_storage()
    _database = storage['_database']

    if _database is None:
        client = get_mongo_client()
        _database = client[DATABASE_NAME]
        storage['_database'] = _database
    else:
        print("- Sử dụng database đã kết nối!")
    return _database


def get_collection(collection_name: str):
    """Lấy collection theo collection_name"""
    db = get_database()
    return db[collection_name]


def close_connection():
    """Đóng kết nối MongoDB"""
    storage = _get_storage()
    _client = storage.get('_client')

    if _client:
        _client.close()
        storage['_client'] = None
        storage['_database'] = None
        storage['_collection'] = None
        print("Đã đóng kết nối MongoDB")
