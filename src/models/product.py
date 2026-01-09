"""
Product models
"""
from typing import TypedDict, List


class Comment(TypedDict):
    """Comment model"""
    content: str
    name: str
    rating: int
    date: str


class Product(TypedDict):
    """Product model"""
    name: str
    link: str
    comments: List[dict]
