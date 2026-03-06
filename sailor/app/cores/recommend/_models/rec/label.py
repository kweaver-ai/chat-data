"""
@File: label.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 标签推荐 Model
class LabelQueryParams(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description='标签名称，或者是一段自然语言文本')
    desc: Optional[str] = None
    range_type: Optional[str] = None
    category_id: Optional[str] = None

class RecommendLabelParams(BaseModel):
    query_items: List[LabelQueryParams]
    config: Optional[ConfigParams] = ConfigParams()