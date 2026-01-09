"""
Base DTOs dùng chung cho tất cả APIs
"""
import inspect
import os
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """Response model chung cho tất cả API endpoints"""
    data: Optional[T] = None
    success: bool
    message: str
    position: Optional[str] = None  # Format: "filename.function_name" để debug
