"""
@File: code.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

############################################## 标准推荐 Model
class TableFieldParams(BaseModel):
    table_field_id: str = Field(..., description='字段的ID')
    table_field_name: str = Field(..., description='字段的名字')


class CodeQueryParams(BaseModel):
    table_id: str = Field(..., description='表单的ID')
    table_name: str = Field(..., description='表单的名称')
    table_desc: str = Field(..., description='表单的描述')
    department_id: str = Field(default="", description="部门id")
    table_fields: List[TableFieldParams]


class RecommendCodeParams(BaseModel):
    query: CodeQueryParams
    # graph_id: str = Field(..., description='AnyData环境的图谱ID')
    # appid: str = Field(..., description='AnyData环境的appid')
