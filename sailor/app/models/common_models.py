from pydantic import BaseModel
from typing import Generic, TypeVar, List

# 泛型类型变量
T = TypeVar('T')


class PaginationReqBody(BaseModel):
    """通用分页请求模型"""
    size: int = 0
    pagination_marker_str: str = ""


class PaginationResp(BaseModel, Generic[T]):
    """通用分页响应模型"""
    entries: List[T] = []
    pagination_marker_str: str = ""
    is_last_page: bool = False
