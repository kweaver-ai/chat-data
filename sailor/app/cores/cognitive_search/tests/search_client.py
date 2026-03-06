from starlette.testclient import TestClient
from app.handlers.cognitive_search_handler import (cognitive_search_router, ResourceAnalysisRouter,ResourceSearchRouter,
                                                   TestAssetRouter,TestRouter)
from app.cores.cognitive_search.tests.inputs import *
from app.cores.cognitive_search.re_analysis_search import  *
from app.cores.cognitive_search.graph_func import  *
from app.cores.cognitive_search.search_model import AssetSearchParams, AnalysisSearchParams
# from app.routers.cognitive_search_router import TestAssetRouter


def test_resource_analysis_search():
    inputs = resource_inputs_761173
    search_params = AnalysisSearchParams(**inputs)
    logger.debug(f'search_params = {search_params}')
    Authorization = get_authorization("https://10.4.134.68", "", "")
    logger.debug(f'Authorization = {Authorization}')
    client = TestClient(cognitive_search_router)
    response = client.post(
        # CatalogAnalysisRouter,
        ResourceAnalysisRouter,
        # TestRouter,
        headers={"Authorization": Authorization},
        json=inputs
    )
    # 获取请求对象
    request = response.request
    # 打印请求对象的信息
    logger.debug("\nRequest Method:", request.method)
    logger.debug("Request URL:", request.url)
    logger.debug("Request Headers:", request.headers)
    logger.debug("Request Body:", request.content.decode())
    response_dict = response.json()
    logger.debug(f"type of response = {type(response)}")
    logger.debug(f"type of response_dict = {type(response_dict)}")
    json_string = json.dumps(response_dict, indent=4, ensure_ascii=False)
    logger.debug(f"\nresponse_json = \n{json_string}")
    # # with open("catalog_analysis_output_1.json", "w", encoding="utf-8") as json_file:
    # with open("resource_analysis_output_1.json", "w", encoding="utf-8") as json_file:
    #     json_file.write(json_string)
    # assert response.status_code == 200
    logger.debug(f"response.status_code = {response.status_code}")

def test_resource_asset_search():
    inputs_json = resource_inputs_761173
    inputs = AssetSearchParams(**inputs_json)
    logger.debug(f'inputs = {inputs}')
    logger.debug(f'json inputs = \n{json.dumps(inputs.model_dump(), indent=4, ensure_ascii=False)}')
    Authorization = get_authorization("https://10.4.134.68", "", "")
    logger.debug(f'Authorization = {Authorization}')
    client = TestClient(cognitive_search_router)
    response = client.post(
        # ResourceSearchRouter,
        # TestRouter,
        TestAssetRouter,
        headers={"Authorization": Authorization},
        json=inputs_json
    )
    # 获取请求对象
    request = response.request
    # 打印请求对象的信息
    logger.debug("\nRequest Method:\n", request.method)
    logger.debug("Request URL\n:", request.url)
    logger.debug("Request Headers:\n", request.headers)
    logger.debug("Request Body:\n", request.content.decode())
    response_dict = response.json()
    logger.debug(f"type of response = \n{type(response)}")
    logger.debug(f"type of response_dict = \n{type(response_dict)}")
    json_string = json.dumps(response_dict, indent=4, ensure_ascii=False)
    logger.debug(f"\nresponse_json = \n{json_string}")
    # # with open("catalog_analysis_output_1.json", "w", encoding="utf-8") as json_file:
    # with open("resource_analysis_output_1.json", "w", encoding="utf-8") as json_file:
    #     json_file.write(json_string)
    # assert response.status_code == 200
    logger.debug(f"response.status_code = {response.status_code}")



if __name__ == '__main__':
    # test_resource_asset_search()
    test_resource_analysis_search()

