import json
from urllib.parse import urljoin

from app.cores.cognitive_search.graph_func import get_connected_subgraph_catalog, get_md5
# from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.utils.password import get_authorization
from app.cores.retriever.models import GraphRetrieverParams
from app.dependencies.dependent_apis import DependentAPIs
from app.cores.data_comprehension.dc_api import DataComprehensionAPI
# from config import settings


# async def get_ad_kn_params(headers:dict):
#     apis=DependentAPIs()
#     print(f"apis={apis}")
#     url = urljoin(
#         apis.af_sailor_service_url,
#         apis.endpoint_get_ad_kn_params)
#     print(f"url={url}")
#     api = API(
#         url=url,
#         headers=headers,
#         method=HTTPMethod.GET
#     )
#     try:
#         res = await api.call_async()
#         print("response = ", json.dumps(res, ensure_ascii=False, indent=4))
#         return (res.get("app_id", ""),
#                 res.get("cognitive_search_data_catalog_graph_id", ""))
#         # return (res.get("app_id", ""),
#         #         res.get("cognitive_search_data_catalog_graph_id", ""),
#         #         res.get("cognitive_search_data_resource_graph_id", ""),
#         #         res.get("cognitive_search_synonyms_id", ""),
#         #         res.get("cognitive_search_stopwords_id", ""))
#     except Exception as e:
#         print(e)
#         # return ("","","","","")
#         return ("", "")

# def get_ad_kn_params(headers:dict):
#     # apis=DependentAPIs()
#     apis=DataComprehensionAPI
#     print(f"apis={apis}")
#     url = urljoin(
#         apis.af_sailor_service_url,
#         apis.endpoint_get_ad_kn_params)
#     print(f"url={url}")
#     api = API(
#         url=url,
#         headers=headers,
#         method=HTTPMethod.GET
#     )
#     try:
#         res = api.call()
#         # res={}
#         print("response = ", json.dumps(res, ensure_ascii=False, indent=4))
#         return (res.get("app_id", ""),
#                         res.get("cognitive_search_data_catalog_graph_id", ""))
#         # return (res.get("app_id", ""),
#         #         res.get("cognitive_search_data_catalog_graph_id", ""),
#         #         res.get("cognitive_search_data_resource_graph_id", ""),
#         #         res.get("cognitive_search_synonyms_id", ""),
#         #         res.get("cognitive_search_stopwords_id", ""))
#     except Exception as e:
#         print(e)
#         # return ("","","","","")
#         return ("", "")

async def get_ad_kn_params(headers:dict):

    apis=DataComprehensionAPI()
    res = await apis.get_ad_ids()
    # print(f"res={res}")
    return (res.get("app_id", ""),
            res.get("cognitive_search_data_catalog_graph_id", ""))

    # print(f"apis={apis}")
    # url = urljoin(
    #     apis.af_sailor_service_url,
    #     apis.endpoint_get_ad_kn_params)
    # print(f"url={url}")
    # api = API(
    #     url=url,
    #     headers=headers,
    #     method=HTTPMethod.GET
    # )
    # try:
    #     res = api.call()
    #     # res={}
    #     print("response = ", json.dumps(res, ensure_ascii=False, indent=4))
    #     return (res.get("app_id", ""),
    #                     res.get("cognitive_search_data_catalog_graph_id", ""))
    #     # return (res.get("app_id", ""),
    #     #         res.get("cognitive_search_data_catalog_graph_id", ""),
    #     #         res.get("cognitive_search_data_resource_graph_id", ""),
    #     #         res.get("cognitive_search_synonyms_id", ""),
    #     #         res.get("cognitive_search_stopwords_id", ""))
    # except Exception as e:
    #     print(e)
    #     # return ("","","","","")
    #     return ("", "")

async def get_datacatalog_connected_subgraph(headers,inputs):
    # ad_appid, cognitive_search_data_catalog_graph_id,_,_,_ = await get_ad_kn_params(headers=headers)
    ad_appid, cognitive_search_data_catalog_graph_id = await get_ad_kn_params(headers=headers)
    # (ad_appid, cognitive_search_data_catalog_graph_id, _, _, _) = get_ad_kn_params(headers=headers)
    # ad_appid, cognitive_search_data_catalog_graph_id = get_ad_kn_params(headers=headers)
    print(f"ad_appid = {ad_appid}")
    print(f"cognitive_search_data_catalog_graph_id = {cognitive_search_data_catalog_graph_id}")
    print(f"inputs.datacatalog_ids= {inputs.datacatalog_ids}")

    connected_subgraphs = []
    # 根据数据目录id,查找vid, 可以直接用AD的md5函数, 根据融合属性值生成vid
    datacatalog_graph_vids = []
    # 要改为读取图谱中数据资源目录的类名, 或者通过配置环境变量
    class_name = 'datacatalog'
    # 校验入参不能为空, 防止程序崩溃
    # if inputs.ad_appid is None or inputs.kg_id ,

    if len(inputs.datacatalog_ids) == 0 or inputs.datacatalog_ids is None:
        return connected_subgraphs
    else:
        for datacatalog_id in inputs.datacatalog_ids:
            print(f"datacatalog_id = {datacatalog_id}")
            fusion_property_str = class_name + f'_{datacatalog_id}_'
            datacatalog_graph_vid = get_md5(fusion_property_str)
            print(f"datacatalog_graph_vid = {datacatalog_graph_vid}")
            connected_subgraph = await get_connected_subgraph_catalog(
                ad_appid=ad_appid,
                kg_id=cognitive_search_data_catalog_graph_id,
                datacatalog_graph_vid=datacatalog_graph_vid
            )

            connected_subgraphs.append({
                "datacatalog_id": datacatalog_id,
                "datacatalog_graph_vid": datacatalog_graph_vid,
                "connected_subgraph": connected_subgraph,
            })
    return connected_subgraphs

async def main_func():
    # pass
    Authorization = get_authorization("https://10.4.109.85", "liberly", "")
    headers = {"Authorization": Authorization}
    # ad = PromptServices()
    # ad_appid = ad.get_appid()
    # print(f"ad_appid = {ad_appid}")
    # (app_id, cognitive_search_data_catalog_graph_id, cognitive_search_data_resource_graph_id,
    #  cognitive_search_synonyms_id, cognitive_search_stopwords_id) =  get_ad_kn_params(
    #     headers=headers)

    # (app_id, cognitive_search_data_catalog_graph_id, cognitive_search_data_resource_graph_id,
    #  cognitive_search_synonyms_id, cognitive_search_stopwords_id) = await get_ad_kn_params(
    #     headers=headers)
    # print(app_id, cognitive_search_data_catalog_graph_id, cognitive_search_data_resource_graph_id,
    #       cognitive_search_synonyms_id, cognitive_search_stopwords_id)
    from app.cores.retriever.inputs import retriever_inputs_759298
    # inputs = json.loads(retriever_inputs_759298)
    inputs = retriever_inputs_759298
    inputs = GraphRetrieverParams(**inputs)
    response = await get_datacatalog_connected_subgraph(headers=headers, inputs=inputs)
    print(json.dumps(response, ensure_ascii=False, indent=4))

if __name__ == '__main__':
    import asyncio
    # # asyncio.run(new_main_func())
    asyncio.run(main_func())
    # get_ad_kg_id()
