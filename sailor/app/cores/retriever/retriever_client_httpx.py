# -*- coding: utf-8 -*-
# @Time    : 2025/6/5 20:29
# @Author  : Glen.lv
# @File    : retriever_client_httpx
# @Project : af-sailor
import httpx
import asyncio
from app.utils.password import get_authorization
from app.handlers.retriever_handler import retriever_router,DatacatalogConnectedSubgraphRetrieverRouter
from app.cores.retriever.inputs import *

if __name__ == '__main__':
    inputs = retriever_inputs_759298

    # 获取授权信息
    Authorization = get_authorization("https://10.4.109.85", "liberly", "")

    # 使用 httpx.AsyncClient
    async def test_post():
        async with httpx.AsyncClient(app=retriever_router, base_url="http://test") as client:
            response = await client.post(
                DatacatalogConnectedSubgraphRetrieverRouter,
                headers={"Authorization": Authorization},
                json=inputs
            )
            print(response.json())

    asyncio.run(test_post())