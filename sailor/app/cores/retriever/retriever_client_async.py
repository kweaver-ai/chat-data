import asyncio
from fastapi.testclient import TestClient
import json
from starlette.testclient import TestClient
from app.utils.password import get_authorization
from app.handlers.retriever_handler import retriever_router,DatacatalogConnectedSubgraphRetrieverRouter
from app.cores.retriever.inputs import *

if __name__ == '__main__':
    inputs = retriever_inputs_759298

    # 获取授权信息
    Authorization = get_authorization("https://10.4.109.85", "liberly", "")
    client = TestClient(retriever_router)


    # 使用 asyncio 运行异步任务
    async def test_post():
        response = await client.post(
            DatacatalogConnectedSubgraphRetrieverRouter,
            headers={"Authorization": Authorization},
            json=inputs
        )
        print(response.json())


    asyncio.run(test_post())
# -*- coding: utf-8 -*-
# @Time    : 2025/6/5 20:20
# @Author  : Glen.lv
# @File    : retriever_client_async
# @Project : af-sailor
