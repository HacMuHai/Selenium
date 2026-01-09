"""
DTOs cho Comment APIs
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from dto.base import BaseResponse
from models.product import Comment, Product


class CommentCreate(BaseModel):
    name: str
    content: str
    rating: Optional[int] = Field(default=None, ge=0, le=5)


class CommentUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)


class CommentOut(BaseModel):
    id: str
    product_link: Optional[str] = None
    product_name: Optional[str] = None
    name: str
    content: Optional[str] = None
    rating: Optional[int] = None


# Response models cụ thể cho từng endpoint
class CommentListResponse(BaseResponse[List[CommentOut]]):
    """Response cho GET /comments/"""
    pass


class CommentDetailResponse(BaseResponse[Product]):
    """Response cho GET /comments/{comment_id}"""
    pass


class CommentCreateResponse(BaseResponse[List[str]]):
    """Response cho POST /comments/"""
    pass


class CommentUpdateResponse(BaseResponse[dict]):
    """Response cho PATCH /comments/{comment_id}"""
    pass


class CommentDeleteResponse(BaseResponse[dict]):
    """Response cho DELETE /comments/{comment_id}"""
    pass
