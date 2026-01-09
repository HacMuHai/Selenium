"""
Database configuration - MongoDB connection
"""
from pymongo import MongoClient
from typing import Optional

# Cấu hình MongoDB
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "selenium_scraper"
COLLECTION_NAME = "comments"

# Biến global để lưu client và database
_client: Optional[MongoClient] = None
_database = None
_collection = None


def get_mongo_client() -> MongoClient:
    """Lấy MongoDB client, tạo mới nếu chưa có"""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
        print(f"Đã kết nối MongoDB tại {MONGO_URI}")
    return _client


def get_database():
    """Lấy database, tạo mới nếu chưa có"""
    global _database
    if _database is None:
        client = get_mongo_client()
        _database = client[DATABASE_NAME]
    return _database


def get_collection():
    """Lấy collection, tạo mới nếu chưa có"""
    global _collection
    if _collection is None:
        db = get_database()
        _collection = db[COLLECTION_NAME]
    return _collection


def close_connection():
    """Đóng kết nối MongoDB"""
    global _client, _database, _collection
    if _client:
        _client.close()
        _client = None
        _database = None
        _collection = None
        print("Đã đóng kết nối MongoDB")
