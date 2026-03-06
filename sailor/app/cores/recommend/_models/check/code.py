"""
@File: check_code.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams


############################################## 标准一致性校验 Model
class TableFieldParams(BaseModel):
    field_id: Optional[str] = None  # 字段的ID
    field_name: Optional[str] = None    # 字段的名字
    field_desc: Optional[str] = None    # 字段的描述
    standard_id: Optional[str] = None   # 字段已经配置的标准ID
    standard_name: Optional[str] = None # 字段已经配置的标准名称
    standard_type: Optional[str] = None # 字段已经配置的标准的类型，如国家标准

class TableParams(BaseModel):
    table_id: Optional[str] = None  # 表单的ID
    table_name: Optional[str] = None    # 表单的名称
    table_desc: Optional[str] = None    # 表单的描述
    fields: List[TableFieldParams]    # 字段列表


class CheckCodeParams(BaseModel):
    query: List[TableParams]
    config: Optional[ConfigParams] = ConfigParams()