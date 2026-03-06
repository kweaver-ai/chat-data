"""
@File: others.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

############################################## 业务的通用 Model
class InfomationSystemParams(BaseModel):
    info_system_id: str = Field(..., description='信息系统的id')
    info_system_name: str = Field(..., description='信息系统的名称')
    # info_system_desc: str = Field(..., description='信息系统的描述')


class BusinessDomainParams(BaseModel):
    domain_id: str = Field(..., description='业务域分组/业务域/业务流程的ID')
    domain_name: str = Field(..., description='业务域分组/业务域/业务流程的名称')
    domain_path: str = Field(..., description='业务域分组/业务域/业务流程的层级')
    domain_path_id: str = Field(..., description='业务域分组/业务域/业务流程的层级ID')


class DepartmentParams(BaseModel):
    dept_id: str = Field(..., description='组织部门的ID')
    dept_name: str = Field(..., description='组织部门的名称')
    dept_path: str = Field(..., description='组织部门的层级')
    dept_path_id: str = Field(..., description='组织部门的层级ID')