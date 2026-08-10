"""
Base DTO dùng chung cho tất cả API. Mọi response - kể cả lỗi - đều giữ envelope này.
"""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Envelope chung: `{data, success, message}`."""

    data: Optional[T] = None
    success: bool
    message: str
