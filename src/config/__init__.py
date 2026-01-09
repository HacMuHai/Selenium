"""
Config module - Cấu hình ứng dụng
"""
from .database import get_collection, close_connection
from .driver import get_driver, close_driver

__all__ = ["get_collection", "close_connection", "get_driver", "close_driver"]
