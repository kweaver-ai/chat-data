"""
@File: rule.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 推荐业务规则：字段值域的编码规则 Model
class TableFieldParams(BaseModel):
    field_id: Optional[str] = Field(default="", description='字段的ID')
    field_name: Optional[str] = Field(..., description='字段的名字')
    field_desc: Optional[str] = Field(default="", description='字段的描述')
    standard_id: Optional[str] = Field(default="", description='字段已经配置的标准ID')

class TableParams(BaseModel):
    table_id: Optional[str] = Field(default="", description='表单的ID')
    table_name: Optional[str] = Field(..., description='表单的名称')
    table_desc: Optional[str] = Field(default="", description='表单的描述')
    department_id: Optional[str] = Field(default="", description='本部门')
    fields: List[TableFieldParams] = Field([], description='字段列表')

class RecommendFieldRuleParams(BaseModel):
    query: List[TableParams]
    config: Optional[ConfigParams] = ConfigParams()
