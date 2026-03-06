"""
@File: table.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc:
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.business import BusinessDomainParams, DepartmentParams, InfomationSystemParams


############################################## 表单推荐 Model
class TableParams(BaseModel):
    name: str = Field(..., description='表单的名字')
    description: str = Field(..., description='表单的描述信息')


class FieldParams(BaseModel):
    id: str = Field(..., description='字段的ID')
    name: str = Field(..., description='字段的名字')
    description: str = Field(..., description='字段的描述信息')


class TableQueryParams(BaseModel):
    business_model_id: str = Field(..., description='业务模型的ID')
    business_model_name: str = Field(..., description='业务模型的名称')
    domain: BusinessDomainParams = None
    dept: DepartmentParams = None
    info_system: List[InfomationSystemParams] = None
    table: TableParams
    fields: Optional[List[FieldParams]] = None
    key: str = Field('', description='搜索关键词，有key就是根据搜索文本进行推荐，没key就是推荐表单', max_length=100)


class RecommendTableParams(BaseModel):
    af_query: TableQueryParams
    graph_id: str = Field(..., description='AnyData环境的图谱ID')
    appid: str = Field(..., description='AnyData环境的appid')
