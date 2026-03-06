"""
@File: field_subject.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 业务对象识别 Model

class TableFieldParams(BaseModel):
    field_id: Optional[str] = Field(..., description='字段的ID')
    field_name: Optional[str] = Field(..., description='字段的名字')
    field_desc: Optional[str] = Field(..., description='字段的描述')
    standard_id: Optional[str] = Field(..., description='字段已经配置的标准ID')


class SubjectParams(BaseModel):
    subject_id: Optional[str] = Field(..., description='主题域ID')
    subject_name: Optional[str] = Field(..., description='主题域名称-逻辑实体属性')
    subject_path: Optional[str] = Field(..., description='主题域路径')

class RecommendFieldSubjectQueryParams(BaseModel):
    table_id: Optional[str] = None
    table_name: Optional[str] = None
    table_desc: Optional[str] = None
    fields: List[TableFieldParams] = Field([], description='字段列表')
    subjects: List[SubjectParams] = Field([], description='逻辑实体属性列表')

class RecommendFieldSubjectParams(BaseModel):
    query: List[RecommendFieldSubjectQueryParams]
    config: Optional[ConfigParams] = ConfigParams()
