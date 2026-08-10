"""
DTO cho API `/products`.

Dữ liệu cũ có `rating` là chuỗi rỗng khi 0 sao -> chuẩn hoá tại BIÊN ĐỌC bằng
`BeforeValidator` thay vì migrate DB.
"""
import logging
from datetime import datetime
from typing import Annotated, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

from src.dto.base import BaseResponse

logger = logging.getLogger(__name__)


def _coerce_rating(value: object) -> int:
    """`""`/None/giá trị lạ -> 0; số hợp lệ giữ nguyên."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    text = str(value).strip() if value is not None else ""
    if text.isdigit():
        return int(text)
    if text:
        logger.warning("Giá trị rating không hợp lệ: %r -> 0", value)
    return 0


PyObjectId = Annotated[str, BeforeValidator(str)]
RatingInt = Annotated[int, BeforeValidator(_coerce_rating)]


class CommentOut(BaseModel):
    id: str
    name: str = ""
    content: str = ""
    rating: RatingInt = 0


class CommentCreate(BaseModel):
    name: str
    content: str
    rating: int = Field(default=0, ge=0, le=5)


class CommentUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "CommentUpdate":
        if self.name is None and self.content is None and self.rating is None:
            raise ValueError("Cần ít nhất 1 field để cập nhật")
        return self


class ProductSummary(BaseModel):
    """Product KHÔNG kèm mảng comments - dùng cho danh sách."""

    model_config = ConfigDict(populate_by_name=True)

    # validation_alias (không phải alias): FastAPI serialize response với by_alias=True,
    # dùng `alias="_id"` sẽ khiến client nhận key `_id` thay vì `id`.
    id: PyObjectId = Field(validation_alias=AliasChoices("_id", "id"))
    name: str = ""
    link: str = ""
    total_comments: int = 0
    crawled_at: Optional[datetime] = None
    version: Optional[str] = None


class ProductDetail(ProductSummary):
    comments: list[CommentOut] = Field(default_factory=list)


class PaginatedProducts(BaseModel):
    items: list[ProductSummary]
    total: int
    page: int
    limit: int


class CreatedComment(BaseModel):
    comment_id: str


class Acknowledged(BaseModel):
    ok: bool = True


# Response cụ thể cho từng endpoint
class ProductListResponse(BaseResponse[PaginatedProducts]):
    pass


class ProductDetailResponse(BaseResponse[ProductDetail]):
    pass


class CommentCreateResponse(BaseResponse[CreatedComment]):
    pass


class AckResponse(BaseResponse[Acknowledged]):
    pass
