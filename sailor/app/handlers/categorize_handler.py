# -*- coding: utf-8 -*-

"""
@Time ：2024/5/11 10:12
@Auth ：Danny.gao
@File ：recommend_handler.py
@Desc ：
@Motto：ABC(Always Be Coding)
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from app.routers import DataCategorizeRouter
# from app.cores.categorize.categorize import dataCategorize
from app.cores.categorize.categorize_v2 import data_categorize_func

data_categorize_router = APIRouter()


############################################## 数据分类分级 Model
class FieldParams(BaseModel):
    view_field_id: str = Field(..., description='逻辑视图字段的ID')
    view_field_technical_name: str = Field(..., description='逻辑视图字段的技术名称')
    view_field_business_name: str = Field(..., description='逻辑视图字段的业务名称')
    standard_code: str = Field(..., description='逻辑视图字段关联的标准ID')

class AFQueryParams(BaseModel):
    view_id: str = Field(..., description='逻辑视图ID')
    view_technical_name: str = Field(..., description='逻辑视图技术名称')
    view_business_name: str = Field(..., description='逻辑视图业务名称')
    view_desc: str = Field(..., description='逻辑视图描述')
    subject_id: str = Field(..., description='逻辑视图所属主题域ID')
    view_fields: List[FieldParams]
    explore_subject_ids: Optional[list] = None # 探查的识别范围
    view_source_catalog_name: Optional[str] = None # 逻辑视图所属的catalog信息


class DataCategorizeParams(BaseModel):
    query: AFQueryParams
    # graph_id: str = Field(..., description='AnyData环境的图谱ID')
    # appid: str = Field(..., description='AnyData环境的appid')


############################################## 数据分类分级接口
@data_categorize_router.post(DataCategorizeRouter, include_in_schema=False)
async def data_categorize(request: Request, params: DataCategorizeParams):
    af_auth = request.headers.get('Authorization', '')
    return {"res": await data_categorize_func(params.query)}


