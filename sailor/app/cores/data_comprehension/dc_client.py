from app.logs.logger import logger

from app.cores.cognitive_search.inputs import *

if __name__ == '__main__':
    from starlette.testclient import TestClient
    from app.utils.password import get_authorization
    from app.handlers.data_comprehension_handler import data_comprehension_router,ComprehensionRouter

    # inputs = {
    #     "catalog_id": "540157492294855302",
    #     "dimension": "all"
    # }
    # catalog_id='555633979462576600'  # 没有探查结果
    # catalog_id = '555633151808956888'  # 有日期型和空间型探查结果
    # inputs = {
    #     "catalog_id": "555633151808956888",
    #     "dimension": "时间范围"
    # }
    #
    # 数据资源目录-E6 593206861969243549 有时间字段
    # 实耗人工时宽表..., code ='SJZYMU20250715/000005', 575526257211489687，字段比较多
    inputs = {
        "catalog_id": "599833586656394296",
        "dimension": "时间范围"
        # "dimension": "时间字段理解"
        # "dimension": "空间字段理解"
        # "dimension": "空间范围"
        # "dimension": "业务维度"
        # "dimension": "复合表达"
        # "dimension": "服务范围"
        # "dimension": "服务领域"
        # "dimension": "正面支撑"
        # "dimension": "负面支撑"
        # "dimension": "保护控制"
        # "dimension": "促进推动"


    }


    authorization = get_authorization("https://10.4.175.238", "zyy", "")

    client = TestClient(data_comprehension_router)
    # print('Authorization',Authorization)
    response = client.get(
        ComprehensionRouter,
        headers={"Authorization": authorization},
        params=inputs
    )
    # print("response",response)
    # assert response.status_code == 200
    # print(response.status_code)
    # print(f'response.json() = {response.json()}')
    # print(f'response.text = {response.text}')
