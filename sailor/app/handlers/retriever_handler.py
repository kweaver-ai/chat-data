# -*- coding: utf-8 -*-
# @Time    : 2025/6/3 10:50
# @Author  : Glen.lv
# @File    : retriever_handler
# @Project : af-sailor
#
from fastapi import APIRouter, Body, Request
from pydantic import BaseModel
from typing import List, Dict, Optional

from starlette.responses import JSONResponse

from app.routers import DatacatalogConnectedSubgraphRetrieverRouter

from app.cores.retriever.graph_retriever import get_datacatalog_connected_subgraph
from app.cores.retriever.models import GraphRetrieverParams
from app.utils.verify_token import verify_token

retriever_router = APIRouter()


@retriever_router.post(DatacatalogConnectedSubgraphRetrieverRouter, include_in_schema=False, summary="数据资源目录关联子图检索接口")
async def datacatalog_connected_subgraph_retriever(request: Request, query_dict=Body(...)):
    print(f"request = {request}")
    if not verify_token(request):  # 验证token
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    query_dict = GraphRetrieverParams(**query_dict)
    print(f"query_dict = {query_dict}")
    # headers = dict(request.headers)
    headers = request.headers
    # print(f"request.headers = {request.headers}")
    print(f"headers = {headers}")
    response = await get_datacatalog_connected_subgraph(headers=headers,inputs=query_dict)
    return {"res": response}
