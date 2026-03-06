"""
@File: view.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List


############################################## 视图推荐 Model
class FieldParams(BaseModel):
    id: str = Field(..., description='字段的ID')
    name: str = Field(..., description='字段的名字')
    description: str = Field(..., description='字段的描述信息')

class TableParams(BaseModel):
    name: str = Field(..., description='表单的名字')
    description: str = Field(..., description='表单的描述信息')


class TableQueryParams(BaseModel):
    # 想要推荐的视图类型，1=元数据视图、2=逻辑实体视图、3=自定义视图，默认只有1
    recommend_view_types: Optional[List[int]] = None
    table: TableParams
    fields: Optional[List[FieldParams]] = None


class RecommendViewParams(BaseModel):
    query: TableQueryParams
    # graph_id: str = Field(..., description='AnyData环境的图谱ID')
    # appid: str = Field(..., description='AnyData环境的appid')
