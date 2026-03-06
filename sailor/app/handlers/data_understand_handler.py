# -*- coding: utf-8 -*-

"""
@Time ：2024/1/15 17:28
@Auth ：Danny.gao
@File ：data_understand_handler.py
@Desc ：
@Motto：ABC(Always Be Coding)
"""

from fastapi import APIRouter, Request, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field

from app.routers import TableCompletionRouter, TableCompletionOnlyRouter, TableCompletionTaskRouter
from app.cores.understand.understand import tableCompletion, tableCompletion_by_task_id


data_understand_router = APIRouter()


class FieldParams(BaseModel):
    id: str = Field(..., description='字段的ID')
    technical_name: str = Field(..., description='字段的技术名称')
    business_name: str = Field(..., description='字段的业务名称')
    data_type: str = Field(..., description='字段的数据类型')
    comment: str = Field(..., description='字段的注释')


class QueryParams(BaseModel):
    id: str = Field(..., description='ID')
    technical_name: str = Field(..., description='技术名称')
    business_name: str = Field(..., description='业务名称')
    desc: str = Field(..., description='描述')
    database: str = Field(..., description='数据库名称')
    columns: Optional[List[FieldParams]] = None
    # 所属主题域
    subject: Optional[str] = None
    # 补全类型
    request_type: Optional[int] = None
    # 需要生成描述的字段ID列表，为空时默认全部字段都声称
    gen_field_ids: Optional[List[str]] = None
    # 视图所属的数据源
    view_source_catalog_name: Optional[str] = None


class TableCompletionParams(BaseModel):
    query: QueryParams
    user_id: str = Field(..., description='用户id')


@data_understand_router.post(TableCompletionRouter, include_in_schema=False)
async def table_completion(request: Request, background_tasks: BackgroundTasks, params: TableCompletionParams):
    af_auth = request.headers.get('Authorization', '')
    res = await tableCompletion(background_tasks=background_tasks,
                                query=params.query,
                                user_id=params.user_id,
                                af_auth=af_auth)
    return {'res': res}


@data_understand_router.post(TableCompletionOnlyRouter, include_in_schema=False)
async def table_completion_only_for_table(request: Request, background_tasks: BackgroundTasks, params: TableCompletionParams):
    af_auth = request.headers.get('Authorization', '')
    res = await tableCompletion(background_tasks=background_tasks,
                                query=params.query,
                                user_id=params.user_id,
                                af_auth=af_auth,
                                only_for_table=True)
    return {'res': res}


@data_understand_router.get(TableCompletionTaskRouter, include_in_schema=False)
async def table_completion_by_task(task_id):
    return {'res': await tableCompletion_by_task_id(task_id=task_id)}

