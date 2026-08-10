"""
Product models - khớp ĐÚNG schema đang có trong MongoDB.

Mỗi document = 1 product, comments là mảng lồng bên trong:
    {_id, name, link, comments: [{id, name, content, rating}], total_comments,
     crawled_at, version}
"""
from datetime import datetime
from typing import List, TypedDict


class Comment(TypedDict):
    """Một comment nằm trong mảng `comments` của product."""
    id: str
    name: str
    content: str
    rating: int


class Product(TypedDict):
    """Một document trong collection."""
    name: str
    link: str
    comments: List[Comment]
    total_comments: int
    crawled_at: datetime
    version: str
