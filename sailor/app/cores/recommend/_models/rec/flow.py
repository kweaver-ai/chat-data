"""
@File: flow.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List


############################################## 流程推荐 Model
class FCNodeParams(BaseModel):
    id: str = Field(..., description='数据库中流程节点ID,即uuid')
    mxcell_id: str = Field(..., description='前端节点ID')
    name: str = Field(..., description='节点的名称')
    description: str = Field(..., description='节点的描述')


class ParentNodeParams(BaseModel):
    id: str = Field(..., description='数据库中流程节点ID,即uuid')
    mxcell_id: str = Field(..., description='前端节点ID')
    name: str = Field(..., description='节点的名称')
    description: str = Field(..., description='节点的描述')
    flowchart_id: Optional[str] = Field('', description='所属流程图的ID')
    tables: List[str] = Field([], description='关联的表单列表')


class FCParams(BaseModel):
    id: str = Field(..., description='当前需要推荐流程的节点所在流程图ID')
    name: str = Field(..., description='流程图名称')
    description: str = Field(..., description='流程图描述')
    business_model_id: str = Field(..., description='流程图所在业务模型,当前理解为主干业务id,后期做调整')
    nodes: List[FCNodeParams] = Field([], description='节点列表')


class FlowQueryParams(BaseModel):
    business_model_id: str = Field(..., description='业务模型的ID')
    node: FCNodeParams
    parent_node: Optional[ParentNodeParams] = None
    flowchart: Optional[FCParams] = None


class RecommendFlowParams(BaseModel):
    af_query: FlowQueryParams
    graph_id: str = Field(..., description='AnyData环境的图谱ID')
    appid: str = Field(..., description='AnyData环境的appid')