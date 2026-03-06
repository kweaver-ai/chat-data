"""
@File: explore_rule.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 推荐质量规则：逻辑视图字段级别的探查规则 Model
class TableFieldParams(BaseModel):
    field_id: Optional[str] = Field(..., description='字段的ID')
    field_name: Optional[str] = Field(..., description='字段的名字')
    field_desc: Optional[str] = Field(..., description='字段的描述')
    standard_id: Optional[str] = Field(..., description='字段已经配置的标准ID')

class RecommendExploreRuleQueryParams(BaseModel):
    view_id: Optional[str] = None
    view_name: Optional[str] = None
    view_desc: Optional[str] = None
    fields: List[TableFieldParams] = Field([], description='字段列表')

class RecommendExploreRuleParams(BaseModel):
    query: List[RecommendExploreRuleQueryParams]
    config: Optional[ConfigParams] = ConfigParams()