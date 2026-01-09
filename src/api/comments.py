"""
API endpoints cho comments (FastAPI)
"""
from fastapi import APIRouter, HTTPException
from typing import List
from models.product import Product
from services.comment_service import CommentService
from dto.comment import (
    CommentCreate, CommentUpdate, CommentOut,
    CommentListResponse, CommentDetailResponse,
    CommentCreateResponse, CommentUpdateResponse, CommentDeleteResponse
)

router = APIRouter(prefix="/comments", tags=["comments"])
service = CommentService()


@router.get("/", response_model=CommentListResponse)
def list_comments():
    """Lấy danh sách tất cả comments"""
    try:
        data = service.get_all()
        return CommentListResponse(
            data=data,
            success=True,
            message="Thành công",
        )
    except Exception as e:
        error_msg = str(e)
        return CommentListResponse(
            data=None,
            success=False,
            message=error_msg,
        )


@router.get("/{comment_id}", response_model=CommentDetailResponse)
def get_comment(comment_id: str):
    """Lấy comment theo ID"""
    try:
        doc = service.get_by_id(comment_id)
        if not doc:
            return CommentDetailResponse(
                data=None,
                success=False,
                message=f"Comment với ID {comment_id} không tìm thấy",
            )
        return CommentDetailResponse(
            data=doc,
            success=True,
            message="Thành công",
        )
    except Exception as e:
        error_msg = str(e)
        return CommentDetailResponse(
            data=None,
            success=False,
            message=error_msg,
        )


@router.post("/", response_model=CommentCreateResponse)
def create_comments(product_link: str, payload: list[CommentCreate]):
    """Tạo nhiều comments mới"""
    try:
        comments = [c.model_dump() for c in payload]
        ids = service.create_many(
            Product(link=product_link, name="",
                    comments=comments),  # name optional
        )
        return CommentCreateResponse(
            data=ids,
            success=True,
            message="Thành công",
        )
    except Exception as e:
        error_msg = str(e)
        return CommentCreateResponse(
            data=None,
            success=False,
            message=error_msg,
        )


@router.patch("/{comment_id}", response_model=CommentUpdateResponse)
def update_comment(comment_id: str, payload: CommentUpdate):
    """Cập nhật comment"""
    try:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not data:
            return CommentUpdateResponse(
                data=None,
                success=False,
                message="Không có dữ liệu để cập nhật",
            )
        ok = service.update(comment_id, data)
        if not ok:
            return CommentUpdateResponse(
                data=None,
                success=False,
                message=f"Comment với ID {comment_id} không tìm thấy",
            )
        return CommentUpdateResponse(
            data={"updated": True},
            success=True,
            message="Thành công",
        )
    except Exception as e:
        error_msg = str(e)
        return CommentUpdateResponse(
            data=None,
            success=False,
            message=error_msg,
        )


@router.delete("/{comment_id}", response_model=CommentDeleteResponse)
def delete_comment(comment_id: str):
    """Xóa comment"""
    try:
        ok = service.delete(comment_id)
        if not ok:
            return CommentDeleteResponse(
                data=None,
                success=False,
                message=f"Comment với ID {comment_id} không tìm thấy",
            )
        return CommentDeleteResponse(
            data={"deleted": True},
            success=True,
            message="Thành công",
        )
    except Exception as e:
        error_msg = str(e)
        return CommentDeleteResponse(
            data=None,
            success=False,
            message=error_msg,
        )
