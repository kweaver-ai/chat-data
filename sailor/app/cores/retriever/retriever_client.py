# -*- coding: utf-8 -*-
# @Time    : 2025/5/24 12:40
# @Author  : Glen.lv
# @File    : retriever_client
# @Project : af-sailor
import json
from starlette.testclient import TestClient
from app.utils.password import get_authorization
from app.handlers.retriever_handler import retriever_router,DatacatalogConnectedSubgraphRetrieverRouter
from app.cores.retriever.inputs import *

if __name__ == '__main__':
    inputs = retriever_inputs_759298


    Authorization = get_authorization("https://10.4.109.85", "liberly", "")
    client = TestClient(retriever_router)
    print(Authorization)
    try:
        response = client.post(
            DatacatalogConnectedSubgraphRetrieverRouter,
            headers={"Authorization": Authorization},
            json=inputs
        )
        print(json.dumps(response.json(),ensure_ascii=False, indent=4))
    except Exception as e:
        print(e)
    # assert response.status_code == 200
    # print(response.status_code)

