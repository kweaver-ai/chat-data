# -*- coding: utf-8 -*-
# @Time    : 2024/1/21 9:48
# @Author  : Glen.lv
# @File    : asset_search
# @Project : copilot
import copy
from typing import Any

# from sqlalchemy.engine.result import null_result
# from openai import BaseModel
from pydantic import BaseModel
from fastapi import Request

from app.cores.cognitive_assistant.qa_error import DataCataLogError
from app.cores.cognitive_assistant.qa_model import QueryIntentionName
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.cores.data_comprehension.dc_api import DataComprehensionAPI
from app.retriever.base import RetrieverAPI
# from app.cores.datasource.dimension_reduce import DimensionReduce

from app.cores.cognitive_search.search_func import *
from app.cores.cognitive_search.graph_func import *
from app.cores.cognitive_search.prompts_config import resource_entity
from app.cores.cognitive_search.search_model import (ANALYSIS_SEARCH_EMPTY_RESULT,
                                                     EMPTY_RESULT_LLM_INVOKE_PLUS_RELATED_INFO, EMPTY_RESULT_LLM_INVOKE,
                                                     AnalysisSearchParams,
                                                     RetrieverHistoryQAParams)

from app.cores.cognitive_search.search_config.get_params import get_search_configs, SearchConfigs
from app.utils.password import get_authorization
from app.cores.cognitive_search.utils.utils import safe_str_to_int, safe_str_to_float
from app.cores.cognitive_search.re_asset_search import cognitive_search_resource_for_qa

from config import settings

find_number_api = FindNumberAPI()
retriever_api = RetrieverAPI()

# dimension_reduce_type: str = "default"  # default 默认为向量匹配， opensearch opensearch搜索， llm 大模型
# dimension_reduce_kg_id: str = ""
# dimension_reduce_kg_type: str = "resource"
# dimension_reduce_app_id: str = ""
# field_entity_name: str = ""
# dimension_reduce = DimensionReduce(
#     dimension_reduce_type=dimension_reduce_type,
#     dimension_reduce_kg_id=dimension_reduce_kg_id,
#     dimension_reduce_kg_type=dimension_reduce_kg_type,
#     dimension_reduce_app_id=dimension_reduce_app_id,
#     field_entity_name=field_entity_name
# )  # 字段召回


# 获取认知搜索图谱信息、query向量化、认知搜索图谱的向量搜索
# 向量搜索
async def init_qa(request, search_params):
    headers = {"Authorization": request.headers.get('Authorization')}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    if not search_params.query:
        return output

    total_start_time = time.time()
    # ad的appid，图谱id，用户query，返回结果的数量
    logger.info(
        f'INPUT：kg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\n')
    # entity2service，图谱关系边的权重
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\n')

    # 获取图谱信息和向量化
    try:
        entity_info, query_embedding = await asyncio.gather(
            get_kgotl_qa(search_params),
            query_m3e(search_params.query)
        )
        if isinstance(entity_info, Exception):
            logger.error(f"获取搜索图谱信息失败: {entity_info}")
            raise entity_info

        if isinstance(query_embedding, Exception):
            logger.error(f"查询向量化失败: {query_embedding}")
            raise query_embedding
        entity_types, vector_index_filed, data_params = entity_info
        embeddings, m_status = query_embedding
        # task_get_kgotl_qa = asyncio.create_task(get_kgotl_qa(search_params))
        # task_query_m3e = asyncio.create_task(query_m3e(search_params.query))
        # entity_types 字典{实体类型名：实体本体信息}
        # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        # type2names 字典 是前端传来的停用实体,现在已经废弃
        # data_params['type2names']
        # data_params['space_name']
        # data_params['indextag2tag']
    except Exception as e:
        logger.error(f"获取图谱信息或query向量化失败: {e}")
        raise

    # 分析问答型搜索只做向量搜索
    # 向量搜索
    min_score = 0.5
    # drop_indices是按照停用实体信息应该被过滤掉的实体,现在已经废弃
    all_hits, drop_indices = await vector_search_dip(embeddings, m_status, vector_index_filed, entity_types, data_params, min_score, search_params)
    drop_indices_set = set(drop_indices)  # 避免在循环中重复创建set
    all_hits = [hit for hit in all_hits if hit['_id'] not in drop_indices_set]
    # for hit in all_hits:
    #     if hit['_id'] in set(drop_indices):
    #         all_hits.remove(hit)
    return output, headers, total_start_time, all_hits, drop_indices


async def init_qa_dip(request, search_params, search_configs):
    logger.info(f"init_qa_dip() running : {search_params}")
    headers = {"Authorization": request.headers.get('Authorization')}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    if not search_params.query:
        return output

    total_start_time = time.time()
    # ad的appid，图谱id，用户query，返回结果的数量
    logger.info(
        f'INPUT：kg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\n')
    # entity2service，图谱关系边的权重
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\n')
    # 获取图谱信息
    headers={"Authorization": request.headers.get('Authorization')}
    try:
        entity_types, vector_index_filed, data_params = await get_kgotl_qa_dip_new(
            headers=headers,
            search_params=search_params
        )
    #     # entity_types 字典{实体类型名：实体本体信息}
    #     # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
    #     # type2names 字典 是前端传来的停用实体,现在已经废弃
    #     # data_params['type2names']
    #     # data_params['space_name']
    #     # data_params['indextag2tag']
    except DataCataLogError as e:
        logger.error(f"获取图谱信息或query向量化失败: {e}")
        raise

    # 目录版分析问答型搜索当前版本只做向量搜索
    min_score = safe_str_to_float(search_configs.sailor_vec_min_score_analysis_search)

    # drop_indices是按照停用实体信息应该被过滤掉的实体,现在已经废弃
    all_hits = await vector_search_dip_new(
        headers=headers,
        vector_index_filed=vector_index_filed,
        entity_types=entity_types,
        data_params=data_params,
        min_score=min_score,
        search_params=search_params
    )
    # drop_indices_set = set(drop_indices)
    # all_hits = [hit for hit in all_hits if hit['_id'] not in drop_indices_set]

    return output, headers, total_start_time, all_hits




# # 获取认知搜索图谱信息, 因为部门职责知识增强场景下, 将query向量化提出来,所以要建一个与 init_qa 大部分相同, 但是没有query向量化的函数
# # 向量搜索
# async def graph_vector_retriever_search_qa(request: Request, search_params: AnalysisSearchParams,
#                                            query_embedding: List[str], m_status: int):
#     headers = {"Authorization": request.headers.get('Authorization')}
#     output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
#     total_start_time = None
#     all_hits, drop_indices = [],[]
#     # return output, headers, total_start_time, all_hits, drop_indices
#     if not search_params.query:
#         return output, headers, total_start_time, all_hits, drop_indices
#
#     total_start_time = time.time()
#     # ad的appid，图谱id，用户query，返回结果的数量
#     logger.info(f'''认知搜索图谱 向量搜索 search_params =
# appid: {search_params.ad_appid}\nkg_id: {search_params.kg_id}
# query: {search_params.query}\nlimit: {search_params.limit}\n''')
#     # entity2service，图谱关系边的权重
#     logger.info(
#         f'认知搜索图谱 向量搜索 INPUT：entity2service: {search_params.entity2service}\n')
#
#     # 获取图谱信息和向量化
#     # task_get_kgotl_qa = asyncio.create_task(get_kgotl_qa(search_params))
#     # entity_types 字典{实体类型名：实体本体信息}
#     # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#     # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # data_params['type2names']
#     # data_params['space_name']
#     # data_params['indextag2tag']
#     # entity_types, vector_index_filed, data_params = await task_get_kgotl_qa
#     entity_types, vector_index_filed, data_params = await get_kgotl_qa(search_params)
#     # logger.debug(f'entity_types = \n{entity_types}')
#     # logger.debug(f'vector_index_filed = \n{vector_index_filed}')
#     # logger.debug(f'data_params = \n{data_params}')
#
#     # 分析问答型搜索只做向量搜索
#     # 向量搜索
#     # min_score = settings.VEC_MIN_SCORE_ANALYSIS_SEARCH
#     # vec_knn_k = settings.VEC_KNN_K_ANALYSIS_SEARCH
#     # logger.debug(search_configs.sailor_vec_min_score_analysis_search)
#     # logger.debug(search_configs.sailor_vec_knn_k_analysis_search)
#     search_configs = get_search_configs()
#     min_score = safe_str_to_float(search_configs.sailor_vec_min_score_analysis_search)
#     # logger.debug(f'min_score = {min_score}')
#     if min_score is None:
#         logger.error(f'获取向量检索 分数下限 参数失败!')
#     vec_knn_k = safe_str_to_int(search_configs.sailor_vec_knn_k_analysis_search)
#     # logger.debug(f'vec_knn_k = {vec_knn_k}')
#     if vec_knn_k is None:
#         logger.error(f'获取向量检索 knn-k 参数失败!')
#     # logger.debug(f'search_configs.sailor_vec_min_score_analysis_search = {search_configs.sailor_vec_min_score_analysis_search}')
#     # logger.debug(f'search_configs.sailor_vec_knn_k_analysis_search = {search_configs.sailor_vec_knn_k_analysis_search}')
#     # task_vector_search = asyncio.create_task(
#     #     vector_search(
#     #         embeddings=query_embedding,
#     #         m_status=m_status,
#     #         vector_index_filed=vector_index_filed,
#     #         entity_types=entity_types,
#     #         data_params=data_params,
#     #         search_params=search_params,
#     #         min_score = min_score,
#     #         vec_knn_k = vec_knn_k
#     #     )
#     # )
#
#     # all_hits, drop_indices = await task_vector_search
#     all_hits, drop_indices = await vector_search(
#             embeddings=query_embedding,
#             m_status=m_status,
#             vector_index_filed=vector_index_filed,
#             entity_types=entity_types,
#             data_params=data_params,
#             search_params=search_params,
#             min_score = min_score,
#             vec_knn_k = vec_knn_k
#         )
#     # logger.debug(f'all_hits = {all_hits}')
#     # logger.debug(f'drop_indices = {drop_indices}')
#     # drop_indices_vec是按照前端传参查询出的停用实体信息,应该被过滤掉的向量,现在已经废弃
#     # all_hits是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,示例数据如下
#
#     # 删除停用实体(按照前端传参, 现在已经废弃)
#     if len(drop_indices)>0:
#         drop_indices_set = set(drop_indices)  # 避免在循环中重复创建set
#         all_hits = [hit for hit in all_hits if hit['_id'] not in drop_indices_set]
#     # for hit in all_hits:
#     #     if hit['_id'] in set(drop_indices):
#     #         all_hits.remove(hit)
#     # output原本是给搜索列表用的， 应为这里是转为分析问答型搜索写的函数， output没有用到
#     # 分析问答型搜索 后续流程用 all_hits
#     return output, headers, total_start_time, all_hits, drop_indices


# 获取部门职责知识增强图谱信息(kecc:knowledge enhancement of catalog chain)()
# 向量搜索
async def graph_vector_retriever_kecc(ad_appid, kg_id_kecc, query, query_embedding, m_status=0,
                                      vec_size_kecc=10, vec_min_score_kecc=0.5, vec_knn_k_kecc=10):
    # headers = {"Authorization": request.headers.get('Authorization')}
    total_start_time = time.time()
    # # ad的appid，图谱id，用户query，返回结果的数量
    logger.info(
        f'''部门职责知识增强图谱 向量搜索 INPUT：\nappid: {ad_appid}\tkg_id_kecc: {kg_id_kecc}\tquery: {query}\tm_status: {m_status}
vec_size_kecc={vec_size_kecc}\tvec_min_score_kecc:{vec_min_score_kecc}\tvec_knn_k_kecc: {vec_knn_k_kecc}''')

    # 获取部门职责知识增强图谱信息
    # task_get_kgotl_kecc = asyncio.create_task(
    #     get_kgotl_kecc(
    #         ad_appid=ad_appid,
    #         kg_id_kecc=kg_id_kecc
    #     )
    # )
    entity_types, vector_index_filed, data_params = await get_kgotl_kecc(
        ad_appid=ad_appid,
        kg_id_kecc=kg_id_kecc
    )
    # entity_types 字典{实体类型名：实体本体信息}
    # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
    # type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names']
    # data_params['space_name']
    # data_params['indextag2tag']
    # logger.debug(f"task_get_kgotl_kecc={task_get_kgotl_kecc}")
    # entity_types, vector_index_filed, data_params = await task_get_kgotl_kecc
    # query_m3e返回一个tuple，有两个元素，第一个元素，就是embedding，是一个768个数字组成的列表；第二个元素，是一个数字，代表m3e服务执行状态，0代表成功
    # embeddings, m_status = await task2
    # 分析问答型搜索只做向量搜索
    # 向量搜索
    # logger.debug(f"entity_types_kecc={entity_types}")
    # logger.debug(f"vector_index_filed_kecc={vector_index_filed}")
    # logger.debug(f"data_params_kecc={data_params}")

    # task_vector_search_kecc = asyncio.create_task(
    #     vector_search_kecc(
    #         ad_appid=ad_appid,
    #         kg_id_kecc=kg_id_kecc,
    #         query_embedding=query_embedding,
    #         m_status=m_status,
    #         vector_index_filed=vector_index_filed,
    #         entity_types=entity_types,
    #         data_params=data_params,
    #         vec_size_kecc=vec_size_kecc,
    #         vec_min_score_kecc=vec_min_score_kecc,
    #         vec_knn_k_kecc=vec_knn_k_kecc
    #     )
    # )
    all_hits_entity = await vector_search_kecc(
            ad_appid=ad_appid,
            kg_id_kecc=kg_id_kecc,
            query_embedding=query_embedding,
            m_status=m_status,
            vector_index_filed=vector_index_filed,
            entity_types=entity_types,
            data_params=data_params,
            vec_size_kecc=vec_size_kecc,
            vec_min_score_kecc=vec_min_score_kecc,
            vec_knn_k_kecc=vec_knn_k_kecc
        )
    # all_hits 是搜索命中的相似向量对应的实体id
    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
    # all_hits_entity = await task_vector_search_kecc
    # all_hits, drop_indices = await task4
    # for i in all_hits:
    #     if i['_id'] in set(drop_indices):
    #         all_hits.remove(i)
    # return output, headers, total_start_time, all_hits, drop_indices
    # logger.debug("len(all_hits_entity)=", len(all_hits_entity))
    # all_hits_entity 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,
    all_hits_kecc = []
    for item in all_hits_entity:
        new_item = {
            "信息相关性得分": item["_score"],
            "问题相关信息": {
                "单位": item["_source"]["dept_name_bdsp"],
                "信息系统": item["_source"]["info_system_bdsp"],
                "单位职责": item["_source"]["dept_duty"],
                "单位职责-明细": item["_source"]["sub_dept_duty"],
                "业务事项": item["_source"]["duty_items"],
                "业务事项类型": item["_source"]["duty_items_type"],
                "数据资源": item["_source"]["data_resource"],
                "核心数据项": item["_source"]["core_data_fields"]
            }
        }
        all_hits_kecc.append(new_item)
    total_end_time = time.time()
    total_elapsed_time = total_end_time - total_start_time
    # logger.debug("all_hits_cn=\n", json.dumps(all_hits_cn, indent=4, ensure_ascii=False))
    # logger.debug("len(all_hits_kecc) ", len(all_hits_kecc))
    return total_elapsed_time, all_hits_kecc


# 调用大模型
# pro_data 是大模型提示词中 {{data_dict}} 的部分, 含义可能是processed_data, 是经过处理之后的, 可以直接调用大模型的
# query 是 大模型提示词中 用户的 query
# prompt_name 是提示词模版的名称
# table_name 是前一步查询知识库得到的所有候选表名,调用大模型的时候没有用到, 是在解析大模型返回结果的时候用到的
# 数据资源版中, table_name是形如 'table_name','interface_name','indicator_name'这样的字符串,
# 用于区分不同的数据资源: 逻辑视图/接口服务/指标
# all_hits 是调用大模型之后做校验用的, 用来判断大模型返回的数据资源是否在向量召回结果中, 如果不符,说明存在编造
async def llm_invoke(pro_data, query, ad_appid, prompt_id_table, table_name, all_hits):
    if not pro_data:
        logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
        return [], [], [], '', {}
    else:
        # res_load 是大模型原始返回结果
        # res 是资源名称, 从res_load中拆出来的
        # res_reason 是分析思路话术, 从res_load中拆出来的
        res, res_reason, res_load = await qw_gpt(data=pro_data, query=query, appid=ad_appid,
                                                 prompt_name=prompt_id_table, table_name=table_name)
        res_id = [i.split('|')[0] for i in res]
        # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
        # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
        # 命名中包含graph的含义是从图谱中查出来的
        # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
        #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
        # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
        hits_graph = []
        for i in all_hits:
            if '_selfid' in i and i['_selfid'] in res_id:
                hits_graph.append(i)
        # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
        # 为了后续前端在话术中加上资源序号数字角标
        hits = [i["_selfid"] + '|' + i["_source"]["resourcename"] for i in hits_graph]
        return hits_graph, hits, res, res_reason, res_load


# 因为加入关键词搜索和关联搜索后， all_hits排序有问题，改为使用search返回的entity，数据结构有不同，暂时不做后置校验
# async def llm_invoke_kecc_new(pro_data, query, dept_infosystem_duty, ad_appid, prompt_id_table, table_name,
#                          all_hits):
#     if not pro_data:
#         logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
#         return [], [], [], '', {}
#     else:
#         # res_load 是大模型原始返回结果
#         # res 是资源名称, 从res_load中"推荐实例"拆出来的
#         # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
#         res, res_reason, related_info,res_load = await qw_gpt_kecc(
#             data=pro_data,
#             query=query,
#             appid=ad_appid,
#             prompt_name=prompt_id_table,
#             table_name=table_name,
#             dept_infosystem_duty=dept_infosystem_duty
#         )
#         res_id = [i.split('|')[0] for i in res]
#         # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
#         # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
#         # 命名中包含graph的含义是从图谱中查出来的
#         # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
#         #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
#         # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
#         hits_graph = []
#         for hit in all_hits:
#
#             if '_selfid' in hit and hit['_selfid'] in res_id:
#                 hits_graph.append(hit)
#         # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
#         # 为了后续前端在话术中加上资源序号数字角标
#         hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in hits_graph]
#         # logger.info(f"hits_graph={hits_graph}")
#         # logger.info(f"hits={hits}")
#         # logger.info(f"res={res}")
#         # logger.info(f"res_reason={res_reason}")
#
#         return hits_graph, hits, res, res_reason, related_info,res_load

# 部门职责知识增强算法的大模型调用, 增加入参 dept_infosystem_duty
# 将”相关信息“单独解析出来
async def llm_invoke_kecc(pro_data, query, dept_infosystem_duty, ad_appid, prompt_id_table, table_name,
                         all_hits):
    if not pro_data:
        logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
        return EMPTY_RESULT_LLM_INVOKE_PLUS_RELATED_INFO
    else:
        # res_load 是大模型原始返回结果
        # res 是资源名称, 从res_load中"推荐实例"拆出来的
        # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
        res, res_reason, related_info, res_load = await qw_gpt_kecc(
            data=pro_data,
            query=query,
            appid=ad_appid,
            prompt_name=prompt_id_table,
            table_name=table_name,
            dept_infosystem_duty=dept_infosystem_duty
        )
        res_id = [i.split('|')[0] for i in res]
        # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
        # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
        # 命名中包含graph的含义是从图谱中查出来的
        # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
        #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
        # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
        hits_graph = [hit for hit in all_hits if '_selfid' in hit and hit['_selfid'] in res_id]
        # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
        # 为了后续前端在话术中加上资源序号数字角标
        hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in hits_graph]
        # logger.info(f"hits_graph={hits_graph}")
        # logger.info(f"hits={hits}")
        # logger.info(f"res={res}")
        # logger.info(f"res_reason={res_reason}")

        return hits_graph, hits, res, res_reason, related_info,res_load

# 部门职责知识增强算法的大模型调用, 增加入参 dept_infosystem_duty
# async def llm_invoke_kecc_old(pro_data, query, dept_infosystem_duty, ad_appid, prompt_id_table, table_name,
#                          all_hits):
#     if not pro_data:
#         logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
#         return [], [], [], '', {}
#     else:
#         # res_load 是大模型原始返回结果
#         # res 是资源名称, 从res_load中"推荐实例"拆出来的
#         # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
#         res, res_reason, res_load = await qw_gpt_kecc(
#             data=pro_data,
#             query=query,
#             appid=ad_appid,
#             prompt_name=prompt_id_table,
#             table_name=table_name,
#             dept_infosystem_duty=dept_infosystem_duty
#         )
#         res_id = [i.split('|')[0] for i in res]
#         # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
#         # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
#         # 命名中包含graph的含义是从图谱中查出来的
#         # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
#         #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
#         # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
#         hits_graph = []
#         for hit in all_hits:
#
#             if '_selfid' in hit and hit['_selfid'] in res_id:
#                 hits_graph.append(hit)
#         # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
#         # 为了后续前端在话术中加上资源序号数字角标
#         hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in hits_graph]
#         # logger.info(f"hits_graph={hits_graph}")
#         # logger.info(f"hits={hits}")
#         # logger.info(f"res={res}")
#         # logger.info(f"res_reason={res_reason}")
#
#         return hits_graph, hits, res, res_reason, res_load

# # 不走大模型， 将认知搜索图谱搜索结果直接输出
# async def llm_invoke_kecc_no_llm(pro_data, query, dept_infosystem_duty, ad_appid, prompt_id_table, table_name,
#                          all_hits):
#     if not pro_data:
#         logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
#         return [], [], [], '', {}
#     else:
#
#         # res 是资源名称, 从res_load中"推荐实例"拆出来的
#         # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
#         res = [key for item in pro_data for key,value in item.items() ]
#         res_reason = ''
#         recommend_cases = [{'table_name': table_name} for table_name in res]
#         # related_info_start = res_reason.find("相关负责单位:")
#         # related_info = res_reason[related_info_start:] if related_info_start != -1 else ""
#         # analysis_steps = res_reason[:related_info_start] if related_info_start != -1 else res_reason
#         # res_load 原为大模型原始返回结果，但是因为改为不走大模型， 直接将搜索结果返回
#         # res_load = {
#         #     '推荐实例': recommend_cases,
#         #     '分析步骤': analysis_steps.strip(),
#         #     '相关信息': related_info
#         # }
#         res_load = {
#             '推荐实例': recommend_cases,
#             '分析步骤': '',
#             '相关信息': ''
#         }
#
#         # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
#         #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
#         # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
#         # hits_graph = all_hits
#         # `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
#         # 为了后续前端在话术中加上资源序号数字角标
#         # hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in hits_graph]
#         hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in all_hits]
#         # logger.info(f"hits_graph={hits_graph}")
#         # logger.info(f"hits={hits}")
#         # logger.info(f"res={res}")
#         # logger.info(f"res_reason={res_reason}")
#
#         return all_hits, hits, res, res_reason, res_load


"""分析问答型——数据目录版"""


# search_params,API请求的Body部分
# request,API请求的request部分

async def catalog_analysis_main(request, search_params,search_configs=None):
    '''数据目录版分析问答型搜索算法主函数'''
    # init_qa(request, search_params)完成 (1)获取图谱信息和 query 向量化;(2) 向量搜索
    # all_hits 是搜索命中的相似向量对应的实体id
    # 为了兼容 旧版本
    if search_configs is None:
        search_configs = get_search_configs()

    output, headers, total_start_time, all_hits = await init_qa_dip(
        request=request,
        search_params=search_params,
        search_configs=search_configs
    )
    logger.info(f"OpenSearch召回数量：{len(all_hits)}")
    pro_data = []
    # auth_header = {"Authorization": search_params.auth_header}
    # 当前用的 鉴权函数, 查询出该用户(subject_id)有权限的所有资源id
    # 如果是数据运营和数据开发工程师, 可以针对所有资源进行问答, 不权限
    auth_id = await find_number_api.user_all_auth(
        headers=headers,
        subject_id=search_params.subject_id
    )
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        logger.info('用户是数据开发者和运营工程师')
    else:
        logger.info(f'该用户有权限的id = {auth_id}')
    # 把所有的资源并且由权限的, 名称和描述, 都放入pro_data, 后续加入大模型提示词中
    for num, hit in enumerate(all_hits):
        # 1数据目录2接口服务3逻辑视图
        # hit['_source']是节点所有属性的字典
        if 'datacatalogname' in hit['_source']:
            description = hit['_source']['description_name'] if 'description_name' in hit['_source'] else '暂无描述'
            # hit['_source']['resource_id']是数据资源目录挂接的数据资源uuid
            if (hit.get('_source').get('resource_id') in auth_id or search_configs.sailor_search_if_auth_in_find_data_qa=='0'
                  or "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles):
                # hit['_source']['resource_type']是挂接的数据资源类型1逻辑视图2接口
                if hit.get('_source').get('online_status') in ['online', 'down-auditing', 'down-reject'] and hit.get('_source').get(
                    'resource_type') == '1':
                    hit['_selfid'] = str(num)
                    pro_data.append(
                        {hit['_selfid'] + '|' + hit['_source']['datacatalogname']: description})
    logger.info(f'放入大模型的库表 = {pro_data}')

    task_qw_gpt = asyncio.create_task(
        qw_gpt_dip(
            headers=headers,
            data=pro_data,
            query=search_params.query,
            search_configs=search_configs,
            prompt_name="all_table",
            table_name='table_name'
        )
    )
    res_catalog, res_catalog_reason, res_load = await task_qw_gpt

    logger.info(f'大模型返回结果 = {res_catalog}')
    res = res_catalog
    hits_graph = []
    for i in all_hits:
        if '_selfid' in i and i['_selfid'] in [j.split('|')[0] for j in res]:
            hits_graph.append(i)
    entities = []

    # 组织答案文本
    res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
    hits_all = [i["_selfid"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
    if len(hits_graph) > 0:
        if len(hits_graph) == len(res_catalog):
            explanation_formview, explanation_statu = add_label(
                reason=res_catalog_reason,
                cites=hits_all,
                a=0
            )
            if explanation_statu == '0':
                use_hits = [i["_id"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
                explanation_formview = add_label_easy(
                    reason=res_explain,
                    cites=use_hits
                )
                logger.info(f"话术不可用时，拼接话术 {explanation_formview}, {explanation_statu}")
            res_statu = 1
        else:
            explanation_formview, res_statu, explanation_statu = ' ', '1', '0'
    else:
        explanation_formview, res_statu, explanation_statu = ' ', '1', '0'

    for num, hit in enumerate(hits_graph):
        catalog_entity_copy = copy.deepcopy(prompts_config.catalog_entity)
        catalog_entity_copy["id"] = hit["_id"]
        catalog_entity_copy["default_property"]["value"] = hit["_source"]["datacatalogname"]
        for props in catalog_entity_copy["properties"][0]["props"]:
            if props["name"] in hit["_source"]:
                props['value'] = hit["_source"][props["name"]]
        if search_params.if_display_graph:
        # 查该数据资源目录在搜索图谱中连接的子图
            connected_subgraph = await get_connected_subgraph_catalog_dip(
                x_account_id=search_params.subject_id,
                x_account_type=search_params.subject_type,
                kg_id=search_params.kg_id,
                datacatalog_graph_vid=hit["_id"]
            )

            # logger.debug(f"connected_subgraph={connected_subgraph}")
            entities.append({
                "starts": [],
                "entity": catalog_entity_copy,
                "score": search_params.limit - num,
                "connected_subgraph": connected_subgraph,
            })
        else:
            entities.append({
                "starts": [],
                "entity": catalog_entity_copy,
                "score": search_params.limit - num,
            })

    output['explanation_formview'] = explanation_formview
    output['entities'] = entities
    output['count'] = len(hits_graph)
    output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    logger.info(f"输出的总结语句------------------\n{output['explanation_formview']}")
    logger.info('--------------问答部分最终召回的资源-----------------\n')
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False), res_statu, explanation_statu)
    log_content = "\n".join(
        f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
        for entity in output["entities"]
    )
    logger.info(log_content)
    # for entity in output["entities"]:
    #     logger.debug(entity['entity']["id"], entity['entity']["default_property"]["value"])
    return output, res_statu, explanation_statu

# async def catalog_analysis_main_dip(request, search_params,search_configs=None):
#     '''数据目录版分析问答型搜索算法主函数'''
#     # init_qa(request, search_params)完成 (1)获取图谱信息和 query 向量化;(2) 向量搜索
#     # all_hits 是搜索命中的相似向量对应的实体id
#     # drop_indices 是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
#     # 为了兼容 旧版本
#     if search_configs is None:
#         search_configs = get_search_configs()
#     # output, headers, total_start_time, all_hits, drop_indices = await init_qa_dip(
#     #     request=request,
#     #     search_params=search_params
#     # )
#     output, headers, total_start_time, all_hits = await init_qa_dip(
#         request=request,
#         search_params=search_params
#     )
#     logger.info(f"OpenSearch召回数量：{len(all_hits)}")
#     pro_data = []
#     # auth_header = {"Authorization": search_params.auth_header}
#     # 当前用的 鉴权函数, 查询出该用户(subject_id)有权限的所有资源id
#     # 如果是数据运营和数据开发工程师, 可以针对所有资源进行问答, 不权限
#     auth_id = await find_number_api.user_all_auth(
#         headers=headers,
#         subject_id=search_params.subject_id
#     )
#     if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
#         logger.info('用户是数据开发者和运营工程师')
#     else:
#         logger.info(f'该用户有权限的id = {auth_id}')
#     # 把所有的资源并且由权限的, 名称和描述, 都放入pro_data, 后续加入大模型提示词中
#     for num, hit in enumerate(all_hits):
#         # 1数据目录2接口服务3逻辑视图
#         # hit['_source']是节点所有属性的字典
#         if 'datacatalogname' in hit['_source']:
#             description = hit['_source']['description_name'] if 'description_name' in hit['_source'] else '暂无描述'
#             # hit['_source']['resource_id']是数据资源目录挂接的数据资源uuid
#             if (hit.get('_source').get('resource_id') in auth_id or search_configs.sailor_search_if_auth_in_find_data_qa=='0'
#                   or "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles):
#                 # hit['_source']['resource_type']是挂接的数据资源类型1逻辑视图2接口
#                 if hit.get('_source').get('online_status') in ['online', 'down-auditing', 'down-reject'] and hit.get('_source').get(
#                     'resource_type') == '1':
#                     hit['_selfid'] = str(num)
#                     pro_data.append(
#                         {hit['_selfid'] + '|' + hit['_source']['datacatalogname']: description})
#     logger.info(f'放入大模型的库表 = {pro_data}')
#
#     task_qw_gpt = asyncio.create_task(
#         qw_gpt_dip(
#             data=pro_data,
#             query=search_params.query,
#             x_account_id=search_params.subject_id,
#             search_configs=search_configs,
#             prompt_name="all_table",
#             table_name='table_name'
#         )
#     )
#     res_catalog, res_catalog_reason, res_load = await task_qw_gpt
#
#     logger.info(f'大模型返回结果 = {res_catalog}')
#     res = res_catalog
#     hits_graph = []
#     for i in all_hits:
#         if '_selfid' in i and i['_selfid'] in [j.split('|')[0] for j in res]:
#             hits_graph.append(i)
#     entities = []
#
#     # 组织答案文本
#     res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
#     hits_all = [i["_selfid"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
#     if len(hits_graph) > 0:
#         if len(hits_graph) == len(res_catalog):
#             explanation_formview, explanation_statu = add_label(
#                 reason=res_catalog_reason,
#                 cites=hits_all,
#                 a=0
#             )
#             if explanation_statu == '0':
#                 use_hits = [i["_id"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
#                 explanation_formview = add_label_easy(
#                     reason=res_explain,
#                     cites=use_hits
#                 )
#                 logger.info(f"话术不可用时，拼接话术 {explanation_formview}, {explanation_statu}")
#             res_statu = 1
#         else:
#             explanation_formview, res_statu, explanation_statu = ' ', '1', '0'
#     else:
#         explanation_formview, res_statu, explanation_statu = ' ', '1', '0'
#
#     for num, hit in enumerate(hits_graph):
#         catalog_entity_copy = copy.deepcopy(prompts_config.catalog_entity)
#         catalog_entity_copy["id"] = hit["_id"]
#         catalog_entity_copy["default_property"]["value"] = hit["_source"]["datacatalogname"]
#         for props in catalog_entity_copy["properties"][0]["props"]:
#             if props["name"] in hit["_source"]:
#                 props['value'] = hit["_source"][props["name"]]
#         if search_params.if_display_graph:
#         # 查该数据资源目录在搜索图谱中连接的子图
#             connected_subgraph = await get_connected_subgraph_catalog_dip(
#                 x_account_id=search_params.subject_id,
#                 x_account_type=search_params.subject_type,
#                 kg_id=search_params.kg_id,
#                 datacatalog_graph_vid=hit["_id"]
#             )
#
#             # logger.debug(f"connected_subgraph={connected_subgraph}")
#             entities.append({
#                 "starts": [],
#                 "entity": catalog_entity_copy,
#                 "score": search_params.limit - num,
#                 "connected_subgraph": connected_subgraph,
#             })
#         else:
#             entities.append({
#                 "starts": [],
#                 "entity": catalog_entity_copy,
#                 "score": search_params.limit - num,
#             })
#
#     output['explanation_formview'] = explanation_formview
#     output['entities'] = entities
#     output['count'] = len(hits_graph)
#     output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
#     total_end_time = time.time()
#     total_time_cost = total_end_time - total_start_time
#     logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
#     logger.info(f"输出的总结语句------------------\n{output['explanation_formview']}")
#     logger.info('--------------问答部分最终召回的资源-----------------\n')
#     # logger.debug(json.dumps(output, indent=4, ensure_ascii=False), res_statu, explanation_statu)
#     log_content = "\n".join(
#         f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
#         for entity in output["entities"]
#     )
#     logger.info(log_content)
#     # for entity in output["entities"]:
#     #     logger.debug(entity['entity']["id"], entity['entity']["default_property"]["value"])
#     return output, res_statu, explanation_statu

"""分析问答型——数据资源版"""

# 原名：resource_analysis_main
# 切换为 resource_analysis_main_nokecc
# 2025.05.25 切换回到resource_analysis_main，因为主线没有部门职责知识增强
async def resource_analysis_main(request, search_params):
    '''数据资源版分析问答型搜索算法主函数'''
    # init_qa(request, search_params)完成 (1)获取图谱信息和 query 向量化;(2) 向量搜索
    # all_hits 是搜索命中的相似向量对应的实体id
    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃

    output, headers, total_start_time, all_hits, drop_indices = await init_qa(request, search_params)

    # 删除stop_entity_infos
    logger.info(f"OpenSearch召回数量：{len(all_hits)}")
    logger.debug(f'all_hits = \n{all_hits}')
    # pro_data 是逻辑视图
    pro_data_formview = []
    # resour是接口服务
    # pro_data_svc是接口服务
    pro_data_svc = []
    # indicator是指标
    pro_data_indicator = []

    # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
    # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
    query_filters = search_params.filter
    asset_type = query_filters.get('asset_type', '')
    # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
    # 只有 application-developer 可以搜到接口服务
    if asset_type == [-1]:  # 全部tab
        # 只有应用开发者的角色可以搜到接口服务
        # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
        if "application-developer" in search_params.roles:
            # 恢复分析问答型搜索返回指标
            # catalog = "1"  # 目录
            # api = "2"  # API
            # view = "3"  # 视图
            # metric = "4"  # 指标 ？
            assert_type_v = ['1', '2', '3', '4']
        else:
            assert_type_v = ['1', '3', '4']
    else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
        assert_type_v = asset_type
    # 这里的 subject_id 是用户id

    # 获取用户拥有权限的所有资源id, auth_id
    # search_params.subject_id 实际上是用户id， 因为历史问题，变量名有误
    try:
        auth_id = await find_number_api.user_all_auth(headers=headers, subject_id=search_params.subject_id)
    except Exception as e:
        logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
        return ANALYSIS_SEARCH_EMPTY_RESULT


    # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        logger.info('用户是数据开发工程师和运营工程师')
    else:
        logger.info(f'该用户有权限的id = {auth_id}')

    for num, hit in enumerate(all_hits):
        # 描述和名称拼起来作为提示词的一部分
        # 2025.05.26 需要增加字段信息作为提示词的一部分, 需要把数据资源的字段信息查出来,可以调用AF接口来查, 需要做在的分支上

        description = hit['_source']['description'] if 'description' in hit['_source'] else '暂无描述'
        # 1数据目录 2接口服务 3逻辑视图 4指标
        # 从图谱get的i['_source']['asset_type']为字符型
        # 分析问答型搜索要求必须是已经上线的资源
        # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
        if 'asset_type' in hit['_source'] and hit['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
                hit['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
            # find_number_api.sub_user_auth_state对一个数据资源进行权限校验, 返回字符串"allow"或者"deny"
            res_auth = await find_number_api.sub_user_auth_state(hit['_source'], search_params, headers, auth_id)
            hit['_selfid'] = str(num)
            # logger.debug(hit['_source']['resourcename'], res_auth)
            # 3 逻辑视图
            if hit['_source']['asset_type'] == '3' and res_auth == "allow":
                # 描述和名称拼起来作为提示词的一部分
                pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
            #  2接口服务
            if hit['_source']['asset_type'] == '2' and res_auth == "allow":
                pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
            #  4指标
            if hit['_source']['asset_type'] == '4' and res_auth == "allow":
                pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})

        else:
            pass
    # 保留用户有权限并且已上线的资源    #
    logger.info(f'pro_data_formview = {pro_data_formview}')
    logger.info(f'pro_data_svc = {pro_data_svc}')
    logger.info(f'pro_data_indicator = {pro_data_indicator}')

    # async def skip_model():
    #     logger.info('大模型入参为空，减少此次交互')
    #     return [], [], [], '', {}

    # 根据逻辑视图、接口服务、指标的返回结果，分别并发调用 llm_invoke
    # 如果逻辑视图的召回结果为空
    if not pro_data_formview:
        task5 = asyncio.create_task(skip_model('form_view'))
    # 如果逻辑视图有召回结果，并发调用llm_invoke
    else:
        task5 = asyncio.create_task(
            llm_invoke(pro_data_formview, search_params.query, search_params.ad_appid, "all_table", 'table_name', all_hits))
    # 如果接口服务的召回结果为空
    if not pro_data_svc:
        task6 = asyncio.create_task(skip_model('interface_service'))
    # 如果接口服务有召回结果，并发调用llm_invoke
    else:
        task6 = asyncio.create_task(
            llm_invoke(pro_data_svc, search_params.query, search_params.ad_appid, "all_interface", 'interface_name', all_hits))
    # 如果指标的召回结果为空
    if not pro_data_indicator:
        task7 = asyncio.create_task(skip_model('pro_data_indicator'))
    # 如果指标有召回结果，并发调用llm_invoke
    else:
        task7 = asyncio.create_task(
            llm_invoke(pro_data_indicator, search_params.query, search_params.ad_appid, "all_indicator", 'indicator_name', all_hits))
    # 触发事件循环开始迭代，接收大模型调用的返回结果
    # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
    # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
    # 逻辑视图
    hits_graph_view, hits_view, res_view, res_view_reason, res_load_view = await task5
    # 接口服务
    hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task6
    # 指标
    hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task7
    #
    entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc
    hits_all_name = [i["_source"]["resourcename"] for i in entities_all]
    #
    entities = []
    #
    explanation_service = {}
    # 指标
    res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'
    if len(hits_graph_ind) > 0:
        if len(hits_graph_ind) == len(res_ind):
            explanation_ind, explanation_statu = add_label(res_ind_reason, hits_ind, 0)
            logger.info(f"返回的话术和状态码 = {explanation_ind}, {explanation_statu}")
            if explanation_statu == '0':
                use_hits = [i["_selfid"] + '|' + i["_source"]["resourcename"] for i in hits_graph_ind]
                explanation_formview = add_label_easy(res_explain, use_hits)
                logger.info(f"话术不可用时，拼接话术 = {explanation_formview}, {explanation_statu}")
            res_statu = '1'
            explanation_statu = '1'
        else:
            explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
    else:
        explanation_ind, res_statu, explanation_statu = ' ', '0', '0'

    # 逻辑视图
    if len(hits_graph_view) > 0:
        if len(hits_graph_view) == len(res_view):
            explanation_formview, explanation_st = add_label(res_view_reason, hits_view, len(hits_graph_ind))
            res_statu += '1'
            explanation_statu += explanation_st
        else:
            explanation_formview = ' '
            res_statu += '1'
            explanation_statu += '0'
    else:
        explanation_formview = ' '
        res_statu += '0'
        explanation_statu += '0'

    # 接口服务
    if len(hits_graph_svc) > 0:
        if len(hits_graph_svc) == len(res_svc):
            explanation_service["explanation_params"] = res_load_svc
            for i in res_load_svc['推荐实例']:
                i['interface_name'] = i["interface_name"].split('|')[1]
            explanation_service["explanation_text"], explana_s = add_label(res_svc_reason, hits_svc,
                                                                           len(hits_graph_ind) + len(hits_graph_view))
            res_statu += '1'
            explanation_statu += explana_s
        else:
            c_res = res_load_svc['推荐实例']
            c_res1 = c_res[:]
            for i in c_res1:
                if i["interface_name"].split('|')[1] not in hits_all_name:
                    res_load_svc.remove(i)
            for i in c_res:
                i['interface_name'] = i["interface_name"].split('|')[1]
            res_load_svc['推荐实例'] = c_res
            explanation_service["explanation_params"] = res_load_svc
            explanation_service["explanation_text"] = ''
            res_statu += '1'
            explanation_statu += '0'
    else:
        explanation_service["explanation_params"] = ''
        explanation_service["explanation_text"] = ''
        res_statu += '0'
        explanation_statu += '0'

    # 最终返回
    for num, i in enumerate(entities_all):
        resource_entity_copy = copy.deepcopy(prompts_config.resource_entity)
        resource_entity_copy["id"] = i["_id"]
        resource_entity_copy["default_property"]["value"] = i["_source"]["resourcename"]
        for props in resource_entity_copy["properties"][0]["props"]:
            if props["name"] in i["_source"]:
                props['value'] = i["_source"][props["name"]]
        entities.append({
            "starts": [],
            "entity": resource_entity_copy,
            "score": search_params.limit - num
        })
    output['explanation_ind'] = explanation_ind
    output['explanation_formview'] = explanation_formview
    output['explanation_service'] = explanation_service
    output['entities'] = entities
    output['count'] = len(entities_all)
    output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    logger.info(f"""===================指标返回结果==============\n {output['explanation_ind']}
              \n===================视图返回结果===================\n
              {output['explanation_formview']}\n===================接口返回结果===================\n
              {output['explanation_service']['explanation_text']}""")
    logger.info('--------------问答部分最终召回的资源-----------------\n')
    log_content = "\n".join(
        f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
        for entity in output["entities"]
    )
    logger.info(log_content)
    # for entity in output["entities"]:
    #     logger.debug(entity['entity']["id"], entity['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False),res_statu, explanation_statu)
    return output, res_statu, explanation_statu




async def resource_analysis_search_kecc(request, search_params, search_configs):
    # async def cognitive_analysis_main_kecc(request, search_params):
    """有部门职责知识增强的分析问答型搜索"""
    # 因为认知搜索图谱和部门职责图谱向量搜索都需要用到query的embedding，所以第一步先做query向量化
    # query_embedding, m_status = await query_m3e(search_params.query)

    total_start_time = time.time()
    search_configs = get_search_configs()
    related_info = []
    try:
        query_embedding, embedding_status = await query_m3e(search_params.query)
        # 检查返回值的有效性
        if not query_embedding or embedding_status is None:
            logger.error("查询embedding无效或状态无效")
            return ANALYSIS_SEARCH_EMPTY_RESULT
    except Exception as e:
        logger.error(f'M3E embedding 错误: {settings.ML_EMBEDDING_URL} \nException= ', str(e))
        # raise M3ERequestException(reason=f'{settings.ML_EMBEDDING_URL} Internal Server Error')
        return ANALYSIS_SEARCH_EMPTY_RESULT
        # 可以在这里添加更多的错误处理逻辑


    try:
        # 以下graph_vector_retriever_search_qa()函数
        # 完成 (1)获取认知搜索图谱信息;(2) 认知搜索图谱向量搜索
        # task_search_qa_retriever = asyncio.create_task(
        #     graph_vector_retriever_search_qa(
        #         request=request,
        #         search_params=search_params,
        #         query_embedding=query_embedding,
        #         m_status=embedding_status
        #     )
        # )

        # 以下 替换为 认知搜索列表的算法，向量搜索的阈值要调低，需要一个独立的函数
        # 完成 (1)获取认知搜索图谱信息;(2) 认知搜索图谱向量搜索+关键词搜索+关联搜索（3）排序分
        task_cognitive_search_qa_retriever = asyncio.create_task(
            cognitive_search_resource_for_qa(
                request=request,
                search_params=search_params,
                query_embedding=query_embedding,
                m_status=embedding_status,
                search_configs=search_configs
            )
        )

        # 查询知识增强图谱，获取query对应的部门-信息系统-业务职责-业务事项 all_hits_kecc, 是字典列表
        # 图谱id不能写死在这里, 产品化时需要采用和认知搜索同样的方式, af-sailor-service 程序构建后, 调用 af-sailor-service 接口获取图谱id
        # 先加到config中
        kg_id_kecc = safe_str_to_int(search_configs.kg_id_kecc)
        if kg_id_kecc is None:
            logger.error(f"获取'组织结构-部门职责-信息系统'知识图谱id失败!")
        vec_size_kecc = safe_str_to_int(search_configs.sailor_vec_size_kecc)
        if vec_size_kecc is None:
            logger.error(f'获取向量检索 返回文档数上限 参数失败!')
        vec_min_score_kecc = safe_str_to_float(search_configs.sailor_vec_min_score_kecc)
        if vec_min_score_kecc is None:
            logger.error(f'获取向量检索 分数下限 参数失败!')
        vec_knn_k_kecc = safe_str_to_int(search_configs.sailor_vec_knn_k_kecc)
        if vec_knn_k_kecc is None:
            logger.error(f'获取向量检索 knn-k 参数失败!')

        task_retriever_kecc = asyncio.create_task(
            graph_vector_retriever_kecc(
                ad_appid=search_params.ad_appid,
                kg_id_kecc=kg_id_kecc,
                query=search_params.query,
                query_embedding=query_embedding,
                m_status=embedding_status,
                vec_size_kecc=vec_size_kecc,
                vec_min_score_kecc=vec_min_score_kecc,
                vec_knn_k_kecc=vec_knn_k_kecc
            )
        )

        # all_hits 是认知搜索图谱中与搜索词query向量相似的所有实体（数据资源或数据目录）
        # drop_indices_vec是按照停用实体信息(原页面左栏),应该被过滤掉的向量,现在已经废弃
        # output, headers, total_start_time, all_hits, _ = await task_search_qa_retriever
        # logger.info(f"认知搜索图谱 OpenSearch 召回实体数量：{len(all_hits)}")
        # logger.debug(f'all_hits = \n{all_hits}')

        # all_hits 是认知搜索图谱中与搜索词query向量相似的所有实体（数据资源或数据目录）
        # drop_indices_vec是按照停用实体信息(原页面左栏),应该被过滤掉的向量,现在已经废弃
        # output 是加入关键词搜索和关联搜索后的结果，
        output, headers, total_time_cost, all_hits, _ = await task_cognitive_search_qa_retriever
        logger.info(f"认知搜索图谱 OpenSearch 召回实体数量：all_hits={len(all_hits)}")
        # logger.debug(f'all_hits = \n{all_hits}')

        # all_hits_kecc 是部门职责知识增强图谱中与搜索词query向量相似的所有实体（单位-部门职责-业务事项-信息系统）
        _, all_hits_kecc = await task_retriever_kecc
        # logger.info(f'all_hits of graph_vector_retriever_kecc = \n{all_hits_kecc}')
        logger.info(f"length of all_hits_kecc={len(all_hits_kecc)}")
    # logger.debug("all_hits_kecc=\n", all_hits_kecc)
    except Exception as e:
        logger.error(f"获取图谱信息或向量搜索错误：{e}")
        return ANALYSIS_SEARCH_EMPTY_RESULT
    # len_output = len(output['entities'])
    # 临时处理
    # len_output = 10
    # logger.info(f'cognitive_search_for_qa, 召回数量 = {len_output}')
    # pro_data_formview(旧代码中pro_data） 是逻辑视图
    # pro_data_svc(旧代码中resour）是接口服务
    # indicator是指标
    pro_data_formview, pro_data_svc, pro_data_indicator = [], [], []

    # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
    # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
    query_filters = search_params.filter
    asset_type = query_filters.get('asset_type', '')
    # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
    # 只有 application-developer 可以搜到接口服务
    if asset_type == [-1]:  # 全部tab
        # 只有应用开发者的角色可以搜到接口服务
        # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
        if "application-developer" in search_params.roles:
            # 恢复分析问答型搜索返回指标
            # catalog = "1"  # 目录
            # api = "2"  # API
            # view = "3"  # 视图
            # metric = "4"  # 指标 ？
            allowed_asset_type = ['1', '2', '3', '4']
        else:
            allowed_asset_type = ['1', '3', '4']
    else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
        allowed_asset_type = asset_type
    # 这里的 subject_id 是用户id

    # 获取用户拥有权限的所有资源id, auth_id
    try:
        auth_id = await find_number_api.user_all_auth(
            headers=headers,
            subject_id=search_params.subject_id
        )
    except Exception as e:
        logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
        return ANALYSIS_SEARCH_EMPTY_RESULT

    # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        logger.info('用户是数据开发工程师和运营工程师')
    else:
        logger.info(f'该用户有权限的id = {auth_id}')

    # logger.info(f'before filtered  all_hits = {all_hits} ')
    # # 创建新列表，只保留不满足删除条件的元素
    # all_hits = [hit for hit in all_hits if 'asset_type' in hit['_source']]
    # logger.info(f'length of filtered all_hits = {len(all_hits)}')
    # # logger.info(f'按照entity分数更新前的 all_hits = \n{all_hits}')
    #
    # # 创建id到hit的映射，提高查找效率
    # hit_map = {hit['_id']: hit for hit in all_hits}
    #
    # # 更新_score字段
    # for num, entity in enumerate(output['entities']):
    #     # logger.info(f'num = {num}')
    #     entity_id = entity['entity']['id']
    #     # entity_score = entity['entity']['score'] # 这个内层score只是综合排序的第二优先级， 首先要看关键字命中数量，
    #     entity_score = entity['score'] # 这个外层的score是综合排序后的分数， 8、7、6、。。。1这种形式
    #
    #     # 通过映射直接查找并更新
    #     if entity_id in hit_map:
    #         logger.info(f"entity_id = {entity_id}")
    #         logger.info(f"entity = {entity}")
    #         logger.info(f'hit_map[entity_id] = {hit_map[entity_id]}')
    #         hit_map[entity_id]['_score'] = entity_score
    # # logger.info(f'按照entity分数更新后，排序前的 all_hits = \n{all_hits}')
    # #
    # # 按_score从大到小排序
    # all_hits.sort(key=lambda x: x['_score'], reverse=True)
    # logger.info(f'length of sorted all_hits = \n{len(all_hits)}')
    # logger.info(f'按照entity分数更新后并且排序后的 all_hits = \n{all_hits}')
    # 按照 output 中 entities的资源和排序分， 对all_hits 进行过滤

    all_hits_new=[]
    # 必须按照 entity 来构造 all_hits, 仅构造必须的属性字段
    for num, entity in enumerate(output['entities']):
        # logger.info(f'num = {num}')
        # logger.info(f'entity = {entity}')
        # 从entity的properties中提取属性值
        props_list = entity['entity']['properties'][0]['props']
        props_dict = {prop['name']: prop['value'] for prop in props_list}

        hit = {
            '_id': entity['entity']['id'],
            '_score': entity['entity']['score'],
            '_source': {
                'asset_type': props_dict.get('asset_type'),
                'code': props_dict.get('code'),
                'color': props_dict.get('color'),
                'description': props_dict.get('description'),
                'online_at': props_dict.get('online_at'),
                'online_status': props_dict.get('online_status'),
                'publish_status': props_dict.get('publish_status'),
                'publish_status_category': props_dict.get('publish_status_category'),
                'resourceid': props_dict.get('resourceid'),
                'resourcename': props_dict.get('resourcename'),
                'technical_name': props_dict.get('technical_name'),
                'department': props_dict.get('department'),
                'department_path': props_dict.get('department_path'),
                'department_id': props_dict.get('department_id'),
                'department_path_id': props_dict.get('department_path_id'),
                'owner_id': props_dict.get('owner_id'),
                'owner_name': props_dict.get('owner_name'),
                'info_system_name': props_dict.get('info_system_name'),
                'info_system_uuid': props_dict.get('info_system_uuid'),
                'subject_id': props_dict.get('subject_id'),
                'subject_name': props_dict.get('subject_name'),
                'subject_path': props_dict.get('subject_path'),
                'subject_path_id': props_dict.get('subject_path_id'),
                'published_at': props_dict.get('published_at')
            },
            "relation": "",
            "type": "resource",
            "type_alias": "数据资源",
            "name": props_dict.get('resourcename'),
            "service_weight": 4
        }
        # hit = {
        #     '_id': entity['entity']['id'],
        #     '_score': entity['entity']['score'],
        #     '_source': {
        #         'asset_type': entity['entity']['properties'][0]['props']['asset_type'],
        #         'code': entity['entity']['properties'][0]['props']['code'],
        #         'color': entity['entity']['properties'][0]['props']['color'],
        #         'description': entity['entity']['properties'][0]['props']['description'],
        #         'online_at': entity['entity']['properties'][0]['props']['online_at'],
        #         'online_status': entity['entity']['properties'][0]['props']['online_status'],
        #         'publish_status': entity['entity']['properties'][0]['props']['publish_status'],
        #         'publish_status_category': entity['entity']['properties'][0]['props']['publish_status_category'],
        #         'published_at': entity['entity']['properties'][0]['props']['published_at'],
        #         'resourceid': entity['entity']['properties'][0]['props']['resourceid'],
        #         'resourcename': entity['entity']['properties'][0]['props']['resourcename'],
        #         'technical_name': entity['entity']['properties'][0]['props']['technical_name'],
        #     },
        #     "relation": "",
        #     "type": "resource",
        #     "type_alias": "数据资源",
        #     "name": entity['entity']['properties'][0]['props']['resourcename'],
        #     "service_weight": 4
        #  }
        all_hits_new.append(hit)
        # logger.info(f'all_hits_new={all_hits_new}')
    logger.info(f"按照 output['entities'] 构造的all_hits_new 长度 = {len(all_hits_new)}")
    # logger.info(f"按照 output['entities'] 构造的all_hits_new = \n{all_hits_new}")

    for num, hit in enumerate(all_hits_new):
        # logger.info(f'num = {num}')
        # logger.info(f'resource_analysis_search_kecc, hit = {hit}')
        # hit['_source'] 是图谱实体点的属性数据， hit可能是图谱中各种类型的实体，搜索的最终目标是数据资源
        # 描述和名称拼起来作为提示词的一部分
        description = hit['_source']['description'] if 'description' in hit['_source'] else '暂无描述'
        # 1数据目录 2接口服务 3逻辑视图 4指标
        # 从图谱get的i['_source']['asset_type']为字符型
        # 分析问答型搜索要求必须是已经上线的资源
        # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
        valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
        has_asset_type = 'asset_type' in hit['_source']
        asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}

        online_status_valid = hit['_source'].get('online_status') in valid_online_statuses
        # logger.info(f'valid_online_statuses = {valid_online_statuses}')
        # logger.info(f'has_asset_type = {has_asset_type}')
        # logger.info(f'asset_type_valid = {asset_type_valid}')

        # if 'asset_type' in i['_source'] and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
        #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:

        # if has_asset_type and asset_type_valid and online_status_valid:
        if asset_type_valid and online_status_valid:
            res_auth = ""
            # 取决于配置参数， 是否要对普通用户进行权限校验
            if search_configs.sailor_search_if_auth_in_find_data_qa == '1':
                res_auth = await find_number_api.sub_user_auth_state(
                    assets=hit['_source'],
                    params=search_params,
                    headers=headers,
                    auth_id=auth_id
                )
            # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
            hit['_selfid'] = str(num)
            # logger.debug(i['_source']['resourcename'], res_auth)
            # 3 逻辑视图
            # logger.info(f'resource_analysis_search_kecc, pro_data_formview = {pro_data_formview}')
            if hit['_source']['asset_type'] == '3' and (
                    res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
                # 描述和名称拼起来作为提示词的一部分
                # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
                # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
                pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
                # logger.info(f'resource_analysis_search_kecc, pro_data_formview = {pro_data_formview}')
            #  2接口服务
            if hit['_source']['asset_type'] == '2' and (
                    res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
                pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
            #  4指标
            if hit['_source']['asset_type'] == '4' and (
                    res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
                pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})

        else:
            pass

    # 改用output来做， hit是无序的，导致结果错误, 因为后续处理还有很多地方，依赖all_hits的数据结构， 暂是放弃这种做法
    # for num, entt in enumerate(output['entities']):
    #     logger.info(f'num = {num}')
    #     logger.info(f'resource_analysis_search_kecc, hit = {hit}')
    #     # hit['_source'] 是图谱实体点的属性数据， hit可能是图谱中各种类型的实体，搜索的最终目标是数据资源
    #     # 描述和名称拼起来作为提示词的一部分
    #     description = hit['_source']['description'] if 'description' in hit['_source'] else '暂无描述'
    #     # 1数据目录 2接口服务 3逻辑视图 4指标
    #     # 从图谱get的i['_source']['asset_type']为字符型
    #     # 分析问答型搜索要求必须是已经上线的资源
    #     # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
    #     valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
    #     has_asset_type = 'asset_type' in hit['_source']
    #     asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}
    #
    #     online_status_valid = hit['_source'].get('online_status') in valid_online_statuses
    #     logger.info(f'valid_online_statuses = {valid_online_statuses}')
    #     logger.info(f'has_asset_type = {has_asset_type}')
    #     logger.info(f'asset_type_valid = {asset_type_valid}')
    #
    #     # if 'asset_type' in i['_source'] and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
    #     #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
    #
    #     # if has_asset_type and asset_type_valid and online_status_valid:
    #     if asset_type_valid and online_status_valid:
    #         res_auth = ""
    #         # 取决于配置参数， 是否要对普通用户进行权限校验
    #         if search_configs.sailor_search_if_auth_in_find_data_qa == '1':
    #             res_auth = await find_number_api.sub_user_auth_state(
    #                 assets=hit['_source'],
    #                 params=search_params,
    #                 headers=headers,
    #                 auth_id=auth_id
    #             )
    #         # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
    #         hit['_selfid'] = str(num)
    #         # logger.debug(i['_source']['resourcename'], res_auth)
    #         # 3 逻辑视图
    #         # logger.info(f'resource_analysis_search_kecc, pro_data_formview = {pro_data_formview}')
    #         if hit['_source']['asset_type'] == '3' and (
    #                 res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
    #             # 描述和名称拼起来作为提示词的一部分
    #             # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
    #             # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
    #             pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
    #             logger.info(f'resource_analysis_search_kecc, pro_data_formview = {pro_data_formview}')
    #         #  2接口服务
    #         if hit['_source']['asset_type'] == '2' and (
    #                 res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
    #             pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
    #         #  4指标
    #         if hit['_source']['asset_type'] == '4' and (
    #                 res_auth == "allow" or search_configs.sailor_search_if_auth_in_find_data_qa == '0'):
    #             pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
    #
    #     else:
    #         pass

    # 保留用户有权限并且已上线的资源    #
    # # 实际上这里按照ouput【entity】中的分数进行排序就可以了
    # for num, entity in enumerate(output['entities']):
    #     print(f'num = {num}')
    #     # print(f'entity = {entity}')
    #     # print(f"{entity['entity']['properties'][0]['props']}")
    #     props = entity['entity']['properties'][0]['props']
    #     print(f"id={entity['entity']['id']}")
    #     print(f"score={entity['entity']['score']}")
    logger.info(f'before cutoff : pro_data_formview = {pro_data_formview}')
    all_hits_limit = int(search_configs.sailor_search_qa_cites_num_limit)
    pro_data_formview = pro_data_formview[:all_hits_limit]
    # pro_data_svc = pro_data_svc[:len_output]
    # pro_data_indicator = pro_data_indicator[:len_output]
    logger.info(f'after cutoff : pro_data_formview = {pro_data_formview}')
    logger.info(f'pro_data_svc = {pro_data_svc}')
    logger.info(f'pro_data_indicator = {pro_data_indicator}')

    # 根据逻辑视图、接口服务、指标的返回结果，分别并发调用 llm_invoke
    # 如果逻辑视图的召回结果为空
    if not pro_data_formview:
        task_llm_invoke_kecc = asyncio.create_task(skip_model('form_view'))
    # 如果逻辑视图有召回结果，并发调用llm_invoke
    else:
        task_llm_invoke_kecc = asyncio.create_task(
            llm_invoke_kecc(
                pro_data=pro_data_formview,
                query=search_params.query,
                dept_infosystem_duty=all_hits_kecc,
                ad_appid=search_params.ad_appid,
                prompt_id_table="all_table_kecc",
                table_name='table_name',
                all_hits=all_hits_new
            )
        )
    # 如果接口服务的召回结果为空
    if not pro_data_svc:
        task6 = asyncio.create_task(skip_model('interface_service'))
    # 如果接口服务有召回结果，并发调用llm_invoke
    else:
        task6 = asyncio.create_task(
            llm_invoke(
                pro_data=pro_data_svc,
                query=search_params.query,
                ad_appid=search_params.ad_appid,
                prompt_id_table="all_interface",
                table_name='interface_name',
                all_hits=all_hits_new
            )
        )
    # 如果指标的召回结果为空
    if not pro_data_indicator:
        task7 = asyncio.create_task(skip_model('pro_data_indicator'))
    # 如果指标有召回结果，并发调用llm_invoke
    else:
        task7 = asyncio.create_task(
            llm_invoke(
                pro_data=pro_data_indicator,
                query=search_params.query,
                ad_appid=search_params.ad_appid,
                prompt_id_table="all_indicator",
                table_name='indicator_name',
                all_hits=all_hits_new
            )
        )
    # 触发事件循环开始迭代，接收大模型调用的返回结果
    # hits_graph_view 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
    # hits_view 提供了一个更简洁的形式来表示 `hits_graph_view` 中的项目，仅保留了项目的 ID 和名称信息。
    # res_view 是大模型返回的答案
    # 逻辑视图
    hits_graph_view, hits_view, res_view, res_view_reason, related_info, res_load_view = await task_llm_invoke_kecc
    # 接口服务
    hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task6
    # 指标
    hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task7
    #
    entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc

    hits_all_name = [entity["_source"]["resourcename"] for entity in entities_all]
    #
    entities = []
    #
    explanation_service = {}

    logger.info(f'after task_llm_invoke_kecc, related_info = {related_info} ')

    # 指标
    #    因为业务规则时,如果全部tab的搜索结果有指标,则不走text2sql和text2api，直接给出分析思路解释话术;如果解释话术不可用，则走保底话术
    res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'
    # 只要交集不为空, res_statu = 1
    # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
    if len(hits_graph_ind) > 0:
        # 如果交集(向量搜索结果和大模型返回结果的交集hits_graph_ind)和大模型返回结果res_ind数量相等, 说明大模型没有编造新的搜索结果,否则话术不可用
        if len(hits_graph_ind) == len(res_ind):
            explanation_ind, explanation_statu = add_label(
                reason=res_ind_reason,
                cites=hits_ind,
                a=0
            )
            logger.info(f"返回的话术和话术是否可用的状态码 = {explanation_ind}, {explanation_statu}")
            # 话术不可用, 给出保底话术
            if explanation_statu == '0':
                use_hits = [hgi["_selfid"] + '|' + hgi["_source"]["resourcename"] for hgi in hits_graph_ind]
                explanation_ind = add_label_easy(
                    reason=res_explain,
                    cites=use_hits
                )
                logger.info(f"话术不可用时，给出保底话术 = {explanation_ind}, {explanation_statu}")
            # 搜索结果和话术都可用
            res_statu = '1'
            explanation_statu = '1'
        else:
            explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
    else:
        # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
        explanation_ind, res_statu, explanation_statu = ' ', '0', '0'

    # 逻辑视图
    # 只要交集不为空, res_statu = 1
    # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
    # logger.debug('hits_graph_view=', len(hits_graph_view),hits_graph_view)
    # logger.debug('res_view=', len(res_view),res_view)


    if len(hits_graph_view) > 0:
        # 如果交集(搜索结果和大模型返回结果的交集hits_graph_view)和大模型返回结果res_view数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
        if len(hits_graph_view) == len(res_view):
            explanation_formview, explanation_st = add_label(
                reason=res_view_reason,
                cites=hits_view,
                a=len(hits_graph_ind)
            )
            res_statu += '1'
            # logger.debug("explanation_st=",explanation_st)
            explanation_statu += explanation_st
        else:
            explanation_formview = ' '
            res_statu += '1'
            explanation_statu += '0'
    else:
        explanation_formview = ' '
        res_statu += '0'
        explanation_statu += '0'

    # 接口服务, 解释中要有["explanation_params"]和["explanation_text"]两个字段
    # 只要交集不为空, res_statu = 1
    # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
    if len(hits_graph_svc) > 0:
        # 如果交集(搜索结果和大模型返回结果的交集)和大模型返回结果数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用

        if len(hits_graph_svc) == len(res_svc):
            explanation_service["explanation_params"] = res_load_svc
            for rst in res_load_svc['推荐实例']:
                rst['interface_name'] = rst["interface_name"].split('|')[1]
            explanation_service["explanation_text"], explana_s = add_label(
                reason=res_svc_reason,
                cites=hits_svc,
                a=len(hits_graph_ind) + len(hits_graph_view)
            )
            res_statu += '1'
            explanation_statu += explana_s
        else:
            c_res = res_load_svc['推荐实例']
            c_res1 = c_res[:]
            for i in c_res1:
                if i["interface_name"].split('|')[1] not in hits_all_name:
                    res_load_svc.remove(i)
            for i in c_res:
                i['interface_name'] = i["interface_name"].split('|')[1]
            res_load_svc['推荐实例'] = c_res
            explanation_service["explanation_params"] = res_load_svc
            explanation_service["explanation_text"] = ''
            res_statu += '1'
            explanation_statu += '0'
    else:
        explanation_service["explanation_params"] = ''
        explanation_service["explanation_text"] = ''
        res_statu += '0'
        explanation_statu += '0'

    # 最终返回
    # entities_all 是所有命中的逻辑视图+接口服务+指标
    # resource_entity 是预定义的返回结构, 和图谱中数据资源实体的结构主体部分一致
    # 按照这个结构, 把所有命中的逻辑视图+接口服务+指标, 按照这个结构, 组装成一个列表, 赋值给 entities
    for num, entity in enumerate(entities_all):
        resource_entity_copy = copy.deepcopy(prompts_config.resource_entity)
        resource_entity_copy["id"] = entity["_id"]
        resource_entity_copy["default_property"]["value"] = entity["_source"]["resourcename"]
        for props in resource_entity_copy["properties"][0]["props"]:
            if props["name"] in entity["_source"]:
                props['value'] = entity["_source"][props["name"]]
        entities.append({
            "starts": [],
            "entity": resource_entity_copy,
            "score": search_params.limit - num
        })
    # 需要在 entities 第一个加入主推表
    output['explanation_ind'] = explanation_ind
    output['explanation_formview'] = explanation_formview
    output['explanation_service'] = explanation_service
    output['entities'] = entities
    output['count'] = len(entities_all)
    output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []

    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    logger.info(f"""===================指标返回结果==============\n {output['explanation_ind']}
              \n===================视图返回结果===================\n
              {output['explanation_formview']}\n===================接口返回结果===================\n
              {output['explanation_service']['explanation_text']}""")
    logger.info('--------------问答部分最终召回的资源-----------------\n')
    log_content = "\n".join(
        f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
        for entity in output["entities"]
    )
    logger.info(log_content)

    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
        # logger.debug(json.dumps(output, indent=4, ensure_ascii=False),res_statu, explanation_statu)
    # output: json, 返回的结果
    # res_statu: string , 返回的结果是否可用, 0代表不可用,1代表可用,
    # 第1位代表指标, 第2位代表逻辑视图(按照代码顺序判断,conf文档中说是接口服务),第3位代表接口服务(按照代码顺序判断,conf文档中说是逻辑视图),
    # 值形如000,001,010,011...
    # explanation_statu: string, 返回的话术是否为空,0代表为空,1代表不为空, 与 res_statu 同样的编码方式
    # logger.info(f'resource_analysis_search_kecc, output={output}')
    return output, res_statu, explanation_statu, related_info

# 分析问答型搜索加入关键字搜索和关联搜索能力,
# 内部处理是否对问答的数据资源鉴权，不再通过单独的函数 resource_analysis_main_kecc_no_auth()
# 加入关键字搜索和关联搜索能力的resource_analysis_search_kecc 取代只有向量搜索能力的
# resource_analysis_main_kecc() 和 resource_analysis_main_kecc_no_auth()


# 带有部门职责知识增强的分析问答型搜索
# 原名：resource_analysis_main_kecc
# 切换为 resource_analysis_main
# 2025.05.25 切换回到resource_analysis_main_kecc，因为主线没有部门职责知识增强
# 加入关键字搜索和关联搜索能力的resource_analysis_search_kecc 取代只有向量搜索能力的
# resource_analysis_main_kecc() 和 resource_analysis_main_kecc_no_auth()
# async def resource_analysis_main_kecc(request, search_params):
#     """有部门职责知识增强的分析问答型搜索"""
#     # 因为认知搜索图谱和部门职责图谱向量搜索都需要用到query的embedding，所以第一步先做query向量化
#     # query_embedding, m_status = await query_m3e(search_params.query)
#
#     search_configs = get_search_configs()
#     try:
#         query_embedding, embedding_status = await query_m3e(search_params.query)
#         # 检查返回值的有效性
#         if not query_embedding or embedding_status is None:
#             logger.error("查询嵌入或状态无效")
#             return ANALYSIS_SEARCH_EMPTY_RESULT
#     except Exception as e:
#         logger.error(f'M3E embedding 错误: {settings.ML_EMBEDDING_URL} Internal Server Error. Exception= ', str(e))
#         # raise M3ERequestException(reason=f'{settings.ML_EMBEDDING_URL} Internal Server Error')
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#         # 可以在这里添加更多的错误处理逻辑
#
#     # 以下graph_vector_retriever_search_qa()函数
#     # 完成 (1)获取认知搜索图谱信息;(2) 认知搜索图谱向量搜索
#     try:
#         task_search_qa_retriever = asyncio.create_task(
#             graph_vector_retriever_search_qa(
#                 request=request,
#                 search_params=search_params,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status
#             )
#         )
#
#         # 查询知识增强图谱，获取query对应的部门-信息系统-业务职责-业务事项 all_hits_kecc, 是字典列表
#         # 图谱id不能写死在这里, 产品化时需要采用和认知搜索同样的方式, af-sailor-service 程序构建后, 调用 af-sailor-service 接口获取图谱id
#         # 先加到config中
#         kg_id_kecc = safe_str_to_int(search_configs.kg_id_kecc)
#         if kg_id_kecc is None:
#             logger.error(f"获取'组织结构-部门职责-信息系统'知识图谱id失败!")
#         vec_size_kecc = safe_str_to_int(search_configs.sailor_vec_size_kecc)
#         if vec_size_kecc is None:
#             logger.error(f'获取向量检索 返回文档数上限 参数失败!')
#         vec_min_score_kecc = safe_str_to_float(search_configs.sailor_vec_min_score_kecc)
#         if vec_min_score_kecc is None:
#             logger.error(f'获取向量检索 分数下限 参数失败!')
#         vec_knn_k_kecc = safe_str_to_int(search_configs.sailor_vec_knn_k_kecc)
#         if vec_knn_k_kecc is None:
#             logger.error(f'获取向量检索 knn-k 参数失败!')
#
#         task_retriever_kecc = asyncio.create_task(
#             graph_vector_retriever_kecc(
#                 ad_appid=search_params.ad_appid,
#                 kg_id_kecc=kg_id_kecc,
#                 query=search_params.query,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status,
#                 vec_size_kecc=vec_size_kecc,
#                 vec_min_score_kecc=vec_min_score_kecc,
#                 vec_knn_k_kecc=vec_knn_k_kecc
#             )
#         )
#
#         # all_hits 是认知搜索图谱中与搜索词query向量相似的所有实体（数据资源或数据目录）
#         # drop_indices_vec是按照停用实体信息(原页面左栏),应该被过滤掉的向量,现在已经废弃
#         output, headers, total_start_time, all_hits, _ = await task_search_qa_retriever
#         logger.info(f"认知搜索图谱 OpenSearch 召回实体数量：{len(all_hits)}")
#         logger.debug(f'all_hits = \n{all_hits}')
#
#         # all_hits_kecc 是部门职责知识增强图谱中与搜索词query向量相似的所有实体（单位-部门职责-业务事项-信息系统）
#         _, all_hits_kecc = await task_retriever_kecc
#         logger.info(f'all_hits of graph_vector_retriever_kecc = \n{all_hits_kecc}')
#         # logger.debug("length of all_hits_kecc=", len(all_hits_kecc))
#     # logger.debug("all_hits_kecc=\n", all_hits_kecc)
#     except Exception as e:
#         logger.error(f"获取图谱信息或向量搜索错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # pro_data_formview(旧代码中pro_data） 是逻辑视图
#     # pro_data_svc(旧代码中resour）是接口服务
#     # indicator是指标
#     pro_data_formview, pro_data_svc, pro_data_indicator = [], [], []
#
#     # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
#     # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
#     query_filters = search_params.filter
#     asset_type = query_filters.get('asset_type', '')
#     # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
#     # 只有 application-developer 可以搜到接口服务
#     if asset_type == [-1]:  # 全部tab
#         # 只有应用开发者的角色可以搜到接口服务
#         # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
#         if "application-developer" in search_params.roles:
#             # 恢复分析问答型搜索返回指标
#             # catalog = "1"  # 目录
#             # api = "2"  # API
#             # view = "3"  # 视图
#             # metric = "4"  # 指标 ？
#             allowed_asset_type = ['1', '2', '3', '4']
#         else:
#             allowed_asset_type = ['1', '3', '4']
#     else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
#         allowed_asset_type = asset_type
#     # 这里的 subject_id 是用户id
#
#     # 获取用户拥有权限的所有资源id, auth_id
#     try:
#         auth_id = await find_number_api.user_all_auth(
#             headers=headers,
#             subject_id=search_params.subject_id
#         )
#     except Exception as e:
#         logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
#     if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
#         logger.info('用户是数据开发工程师和运营工程师')
#     else:
#         logger.info(f'该用户有权限的id = {auth_id}')
#
#     for num, i in enumerate(all_hits):
#         # 描述和名称拼起来作为提示词的一部分
#         description = i['_source']['description'] if 'description' in i['_source'] else '暂无描述'
#         # 1数据目录 2接口服务 3逻辑视图 4指标
#         # 从图谱get的i['_source']['asset_type']为字符型
#         # 分析问答型搜索要求必须是已经上线的资源
#         # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
#         valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
#         has_asset_type = 'asset_type' in i['_source']
#         asset_type_valid = has_asset_type and i['_source']['asset_type'] in {str(t) for t in allowed_asset_type}
#
#         online_status_valid = i['_source'].get('online_status') in valid_online_statuses
#
#         # if 'asset_type' in i['_source'] and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
#         #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
#         if has_asset_type and asset_type_valid and online_status_valid:
#             res_auth = await find_number_api.sub_user_auth_state(
#                 assets=i['_source'],
#                 params=search_params,
#                 headers=headers,
#                 auth_id=auth_id
#             )
#             # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
#             i['_selfid'] = str(num)
#             # logger.debug(i['_source']['resourcename'], res_auth)
#             # 3 逻辑视图
#             if i['_source']['asset_type'] == '3' and res_auth == "allow":
#                 # 描述和名称拼起来作为提示词的一部分
#                 # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
#                 # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
#                 pro_data_formview.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#             #  2接口服务
#             if i['_source']['asset_type'] == '2' and res_auth == "allow":
#                 pro_data_svc.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#             #  4指标
#             if i['_source']['asset_type'] == '4' and res_auth == "allow":
#                 pro_data_indicator.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#
#         else:
#             pass
#     # 保留用户有权限并且已上线的资源    #
#     logger.info(f'pro_data_formview = {pro_data_formview}')
#     logger.info(f'pro_data_svc = {pro_data_svc}')
#     logger.info(f'pro_data_indicator = {pro_data_indicator}')
#     #
#     # async def skip_model():
#     #     logger.info('大模型入参为空，减少此次交互')
#     #     return [], [], [], '', {}
#
#     # 根据逻辑视图、接口服务、指标的返回结果，分别并发调用 llm_invoke
#     # 如果逻辑视图的召回结果为空
#     if not pro_data_formview:
#         task_llm_invoke_kecc = asyncio.create_task(skip_model('form_view'))
#     # 如果逻辑视图有召回结果，并发调用llm_invoke
#     else:
#         task_llm_invoke_kecc = asyncio.create_task(
#             llm_invoke_kecc(
#                 pro_data=pro_data_formview,
#                 query=search_params.query,
#                 dept_infosystem_duty=all_hits_kecc,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_table_kecc",
#                 table_name='table_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果接口服务的召回结果为空
#     if not pro_data_svc:
#         task6 = asyncio.create_task(skip_model('interface_service'))
#     # 如果接口服务有召回结果，并发调用llm_invoke
#     else:
#         task6 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_svc,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_interface",
#                 table_name='interface_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果指标的召回结果为空
#     if not pro_data_indicator:
#         task7 = asyncio.create_task(skip_model('pro_data_indicator'))
#     # 如果指标有召回结果，并发调用llm_invoke
#     else:
#         task7 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_indicator,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_indicator",
#                 table_name='indicator_name',
#                 all_hits=all_hits
#             )
#         )
#     # 触发事件循环开始迭代，接收大模型调用的返回结果
#     # hits_graph_view 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
#     # hits_view 提供了一个更简洁的形式来表示 `hits_graph_view` 中的项目，仅保留了项目的 ID 和名称信息。
#     # res_view 是大模型返回的答案
#     # 逻辑视图
#     hits_graph_view, hits_view, res_view, res_view_reason, res_load_view = await task_llm_invoke_kecc
#     # 接口服务
#     hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task6
#     # 指标
#     hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task7
#     #
#     entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc
#
#     hits_all_name = [entity["_source"]["resourcename"] for entity in entities_all]
#     #
#     entities = []
#     #
#     explanation_service = {}
#
#     # 指标
#     #    因为业务规则时,如果全部tab的搜索结果有指标,则不走text2sql和text2api，直接给出分析思路解释话术;如果解释话术不可用，则走保底话术
#     res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_ind) > 0:
#         # 如果交集(向量搜索结果和大模型返回结果的交集hits_graph_ind)和大模型返回结果res_ind数量相等, 说明大模型没有编造新的搜索结果,否则话术不可用
#         if len(hits_graph_ind) == len(res_ind):
#             explanation_ind, explanation_statu = add_label(
#                 reason=res_ind_reason,
#                 cites=hits_ind,
#                 a=0
#             )
#             logger.info(f"返回的话术和话术是否可用的状态码 = {explanation_ind}, {explanation_statu}")
#             # 话术不可用, 给出保底话术
#             if explanation_statu == '0':
#                 use_hits = [hgi["_selfid"] + '|' + hgi["_source"]["resourcename"] for hgi in hits_graph_ind]
#                 explanation_ind = add_label_easy(
#                     reason=res_explain,
#                     cites=use_hits
#                 )
#                 logger.info(f"话术不可用时，给出保底话术 = {explanation_ind}, {explanation_statu}")
#             # 搜索结果和话术都可用
#             res_statu = '1'
#             explanation_statu = '1'
#         else:
#             explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
#     else:
#         # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#         explanation_ind, res_statu, explanation_statu = ' ', '0', '0'
#
#     # 逻辑视图
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     # logger.debug('hits_graph_view=', len(hits_graph_view),hits_graph_view)
#     # logger.debug('res_view=', len(res_view),res_view)
#
#
#     if len(hits_graph_view) > 0:
#         # 如果交集(搜索结果和大模型返回结果的交集hits_graph_view)和大模型返回结果res_view数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#         if len(hits_graph_view) == len(res_view):
#             explanation_formview, explanation_st = add_label(
#                 reason=res_view_reason,
#                 cites=hits_view,
#                 a=len(hits_graph_ind)
#             )
#             res_statu += '1'
#             # logger.debug("explanation_st=",explanation_st)
#             explanation_statu += explanation_st
#         else:
#             explanation_formview = ' '
#             res_statu += '1'
#             explanation_statu += '0'
#     else:
#         explanation_formview = ' '
#         res_statu += '0'
#         explanation_statu += '0'
#
#     # 接口服务, 解释中要有["explanation_params"]和["explanation_text"]两个字段
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_svc) > 0:
#         # 如果交集(搜索结果和大模型返回结果的交集)和大模型返回结果数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#
#         if len(hits_graph_svc) == len(res_svc):
#             explanation_service["explanation_params"] = res_load_svc
#             for rst in res_load_svc['推荐实例']:
#                 rst['interface_name'] = rst["interface_name"].split('|')[1]
#             explanation_service["explanation_text"], explana_s = add_label(
#                 reason=res_svc_reason,
#                 cites=hits_svc,
#                 a=len(hits_graph_ind) + len(hits_graph_view)
#             )
#             res_statu += '1'
#             explanation_statu += explana_s
#         else:
#             c_res = res_load_svc['推荐实例']
#             c_res1 = c_res[:]
#             for i in c_res1:
#                 if i["interface_name"].split('|')[1] not in hits_all_name:
#                     res_load_svc.remove(i)
#             for i in c_res:
#                 i['interface_name'] = i["interface_name"].split('|')[1]
#             res_load_svc['推荐实例'] = c_res
#             explanation_service["explanation_params"] = res_load_svc
#             explanation_service["explanation_text"] = ''
#             res_statu += '1'
#             explanation_statu += '0'
#     else:
#         explanation_service["explanation_params"] = ''
#         explanation_service["explanation_text"] = ''
#         res_statu += '0'
#         explanation_statu += '0'
#
#     # 最终返回
#     # entities_all 是所有命中的逻辑视图+接口服务+指标, 数据结构是 hit，图谱搜索返回的 all_hits中的数据资源实体
#     # 是opensearch 索引的数据结构，下面需要转成图谱中返回值的数据结构
#     # resource_entity 是预定义的返回结构, 和图谱中数据资源实体的结构主体部分一致
#     # 按照这个结构, 把所有命中的逻辑视图+接口服务+指标, 按照这个结构, 组装成一个列表, 赋值给 entities
#     for num, entity in enumerate(entities_all):
#         resource_entity_copy = copy.deepcopy(prompts_config.resource_entity)
#         resource_entity_copy["id"] = entity["_id"]
#         resource_entity_copy["default_property"]["value"] = entity["_source"]["resourcename"]
#         # all_hits 返回的数据结构中， 如果某个属性字段为空值，则不出现该字段，以下按照图谱返回的数据结构进行组装
#         # 包括所有属性字段， 如果all_hits中没有出现， 则保留预定义结构中的默认值， 一般为"__NULL__"或者空字符串
#         for props in resource_entity_copy["properties"][0]["props"]:
#             if props["name"] in entity["_source"]:
#                 props['value'] = entity["_source"][props["name"]]
#         entities.append({
#             "starts": [],
#             "entity": resource_entity_copy,
#             "score": search_params.limit - num
#         })
#
#     output['explanation_ind'] = explanation_ind
#     output['explanation_formview'] = explanation_formview
#     output['explanation_service'] = explanation_service
#     output['entities'] = entities
#     output['count'] = len(entities_all)
#     output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
#
#     total_end_time = time.time()
#     total_time_cost = total_end_time - total_start_time
#     logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
#     # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
#     logger.info(f"""===================指标返回结果==============\n {output['explanation_ind']}
#               \n===================视图返回结果===================\n
#               {output['explanation_formview']}\n===================接口返回结果===================\n
#               {output['explanation_service']['explanation_text']}""")
#     logger.info('--------------问答部分最终召回的资源-----------------\n')
#     log_content = "\n".join(
#         f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
#         for entity in output["entities"]
#     )
#     logger.info(log_content)
#
#     # for i in output["entities"]:
#     #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
#         # logger.debug(json.dumps(output, indent=4, ensure_ascii=False),res_statu, explanation_statu)
#     # output: json, 返回的结果
#     # res_statu: string , 返回的结果是否可用, 0代表不可用,1代表可用,
#     # 第1位代表指标, 第2位代表逻辑视图(按照代码顺序判断,conf文档中说是接口服务),第3位代表接口服务(按照代码顺序判断,conf文档中说是逻辑视图),
#     # 值形如000,001,010,011...
#     # explanation_statu: string, 返回的话术是否为空,0代表为空,1代表不为空, 与 res_statu 同样的编码方式
#     return output, res_statu, explanation_statu
#
# # 带有部门职责知识增强的分析问答型搜索, 增加输出部门职责的数据，放在 text 字段中，不走大模型（仅逻辑视图，接口服务和指标没有改）
# async def resource_analysis_main_kecc_no_llm(request, search_params):
# # async def resource_analysis_main_kecc_v2(request, search_params):
#     """有部门职责知识增强的分析问答型搜索"""
#     # 因为认知搜索图谱和部门职责图谱向量搜索都需要用到query的embedding，所以第一步先做query向量化
#     # query_embedding, m_status = await query_m3e(search_params.query)
#     search_configs = get_search_configs()
#
#     logger.debug('resource_analysis_main_kecc_no_llm running ...')
#     # logger.debug('resource_analysis_main_kecc_v2 running ...')
#     try:
#         query_embedding, embedding_status = await query_m3e(search_params.query)
#         # 检查返回值的有效性
#         if not query_embedding or embedding_status is None:
#             logger.error("查询嵌入或状态无效")
#             return ANALYSIS_SEARCH_EMPTY_RESULT
#     except Exception as e:
#         logger.error(f'M3E embedding 错误: {settings.ML_EMBEDDING_URL} Internal Server Error. Exception= ', str(e))
#         # raise M3ERequestException(reason=f'{settings.ML_EMBEDDING_URL} Internal Server Error')
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#         # 可以在这里添加更多的错误处理逻辑
#
#     # 以下graph_vector_retriever_search_qa()函数，完成：
#     # (1) 获取认知搜索图谱信息;
#     # (2) 认知搜索图谱向量搜索
#     try:
#         task_search_qa_retriever = asyncio.create_task(
#             graph_vector_retriever_search_qa(
#                 request=request,
#                 search_params=search_params,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status
#             )
#         )
#
#         # 查询知识增强图谱，获取query对应的部门-信息系统-业务职责-业务事项 all_hits_kecc, 是字典列表
#         # 图谱id不能写死在这里, 产品化时需要采用和认知搜索同样的方式, af-sailor-service 程序构建后, 调用 af-sailor-service 接口获取图谱id
#         # 先加到config中
#         kg_id_kecc = safe_str_to_int(search_configs.kg_id_kecc)
#         if kg_id_kecc is None:
#             logger.error(f"获取'组织结构-部门职责-信息系统'知识图谱id失败!")
#         vec_size_kecc = safe_str_to_int(search_configs.sailor_vec_size_kecc)
#         if vec_size_kecc is None:
#             logger.error(f'获取向量检索 返回文档数上限 参数失败!')
#         vec_min_score_kecc = safe_str_to_float(search_configs.sailor_vec_min_score_kecc)
#         if vec_min_score_kecc is None:
#             logger.error(f'获取向量检索 分数下限 参数失败!')
#         vec_knn_k_kecc = safe_str_to_int(search_configs.sailor_vec_knn_k_kecc)
#         if vec_knn_k_kecc is None:
#             logger.error(f'获取向量检索 knn-k 参数失败!')
#
#         task_retriever_kecc = asyncio.create_task(
#             graph_vector_retriever_kecc(
#                 ad_appid=search_params.ad_appid,
#                 kg_id_kecc=kg_id_kecc,
#                 query=search_params.query,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status,
#                 vec_size_kecc=vec_size_kecc,
#                 vec_min_score_kecc=vec_min_score_kecc,
#                 vec_knn_k_kecc=vec_knn_k_kecc
#             )
#         )
#
#         # all_hits 是认知搜索图谱中与搜索词query向量相似的所有实体（数据资源或数据目录）
#         # drop_indices_vec是按照停用实体信息(原页面左栏),应该被过滤掉的向量,现在已经废弃
#         output, headers, total_start_time, all_hits, _ = await task_search_qa_retriever
#         # logger.info(f'认知搜索图谱向量搜索结果 output = \n{output}')
#         # output =
#         # {'count': 0, 'entities': [], 'answer': '抱歉未查询到相关信息。', 'subgraphs': []}
#         logger.info(f"认知搜索图谱向量搜索 OpenSearch 召回实体数量：{len(all_hits)}")
#         # logger.debug(f'认知搜索图谱向量搜索所有召回实体 all_hits = \n{all_hits}')
#
#         # all_hits_kecc 是部门职责知识增强图谱中与搜索词query向量相似的所有实体（单位-部门职责-业务事项-信息系统）
#         _, all_hits_kecc = await task_retriever_kecc
#         logger.info(f"部门职责知识增强图谱向量搜索 OpenSearch 召回实体数量：{len(all_hits_kecc)}")
#         logger.info(f'部门职责知识增强图谱向量搜索所有召回实体 all_hits of graph_vector_retriever_kecc = \n{all_hits_kecc}')
#         # logger.debug("length of all_hits_kecc=", len(all_hits_kecc))
#     # logger.debug("all_hits_kecc=\n", all_hits_kecc)
#     except Exception as e:
#         logger.error(f"获取图谱信息或向量搜索错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # pro_data_formview(旧代码中pro_data） 是逻辑视图
#     # pro_data_svc(旧代码中resour）是接口服务
#     # indicator是指标
#     pro_data_formview, pro_data_svc, pro_data_indicator = [], [], []
#
#     # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
#     # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
#     query_filters = search_params.filter
#     asset_type = query_filters.get('asset_type', '')
#     # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
#     # 只有 application-developer 可以搜到接口服务
#     if asset_type == [-1]:  # 全部tab
#         # 只有应用开发者的角色可以搜到接口服务
#         # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
#         if "application-developer" in search_params.roles:
#             # 恢复分析问答型搜索返回指标
#             # catalog = "1"  # 目录
#             # api = "2"  # API
#             # view = "3"  # 视图
#             # metric = "4"  # 指标 ？
#             allowed_asset_type = ['1', '2', '3', '4']
#         else:
#             allowed_asset_type = ['1', '3', '4']
#     else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
#         allowed_asset_type = asset_type
#     # 这里的 subject_id 是用户id
#
#     # 获取用户拥有权限的所有资源id, auth_id
#     try:
#         auth_id = await find_number_api.user_all_auth(
#             headers=headers,
#             subject_id=search_params.subject_id
#         )
#     except Exception as e:
#         logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
#     if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
#         logger.info('用户是数据开发工程师和运营工程师')
#     else:
#         logger.info(f'该用户有权限的id = {auth_id}')
#
#     for num, hit in enumerate(all_hits):
#         # 描述和名称拼起来作为提示词的一部分
#         description = hit['_source']['description'] if 'description' in hit['_source'] else '暂无描述'
#         # 1数据目录 2接口服务 3逻辑视图 4指标
#         # 从图谱get的i['_source']['asset_type']为字符型
#         # 分析问答型搜索要求必须是已经上线的资源
#         # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
#         valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
#         has_asset_type = 'asset_type' in hit['_source']
#         asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}
#
#         online_status_valid = hit['_source'].get('online_status') in valid_online_statuses
#
#         # if 'asset_type' in i['_source'] and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
#         #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
#         if has_asset_type and asset_type_valid and online_status_valid:
#             res_auth = await find_number_api.sub_user_auth_state(
#                 assets=hit['_source'],
#                 params=search_params,
#                 headers=headers,
#                 auth_id=auth_id
#             )
#             # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
#             hit['_selfid'] = str(num)
#             # logger.debug(i['_source']['resourcename'], res_auth)
#             # 3 逻辑视图
#             if hit['_source']['asset_type'] == '3' and res_auth == "allow":
#                 # 描述和名称拼起来作为提示词的一部分
#                 # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
#                 # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
#                 pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
#             #  2接口服务
#             if hit['_source']['asset_type'] == '2' and res_auth == "allow":
#                 pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
#             #  4指标
#             if hit['_source']['asset_type'] == '4' and res_auth == "allow":
#                 pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
#
#         else:
#             pass
#     # all_hits的每一个hit已经加上了序号 ，比如'_selfid': '0'， '_selfid': '7'
#     # logger.info(f'after processed , all_hits = {all_hits}')
#     # 保留用户有权限并且已上线的资源
#     logger.info(f'pro_data_formview = {pro_data_formview}')
#     logger.info(f'pro_data_svc = {pro_data_svc}')
#     logger.info(f'pro_data_indicator = {pro_data_indicator}')
#     #
#     # async def skip_model():
#     #     logger.info('大模型入参为空，减少此次交互')
#     #     return [], [], [], '', {}
#
#     # 根据逻辑视图、接口服务、指标的返回结果，分别并发调用 llm_invoke
#     # 如果逻辑视图的召回结果为空
#     if not pro_data_formview:
#         task_llm_invoke_kecc = asyncio.create_task(skip_model('form_view'))
#     # 如果逻辑视图有召回结果，并发调用llm_invoke,改为不经过大模型， 直接返回搜索结果（略做处理）
#     else:
#         task_llm_invoke_kecc = asyncio.create_task(
#             # llm_invoke_kecc_v2(
#             llm_invoke_kecc_no_llm(
#                 pro_data=pro_data_formview,
#                 query=search_params.query,
#                 dept_infosystem_duty=all_hits_kecc,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_table_kecc",
#                 table_name='table_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果接口服务的召回结果为空
#     if not pro_data_svc:
#         task6 = asyncio.create_task(skip_model('interface_service'))
#     # 如果接口服务有召回结果，并发调用llm_invoke
#     else:
#         task6 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_svc,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_interface",
#                 table_name='interface_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果指标的召回结果为空
#     if not pro_data_indicator:
#         task7 = asyncio.create_task(skip_model('pro_data_indicator'))
#     # 如果指标有召回结果，并发调用llm_invoke
#     else:
#         task7 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_indicator,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_indicator",
#                 table_name='indicator_name',
#                 all_hits=all_hits
#             )
#         )
#     # 触发事件循环开始迭代，接收大模型调用的返回结果
#     # hits_graph_view 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
#     # hits_view 提供了一个更简洁的形式来表示 `hits_graph_view` 中的项目，仅保留了项目的 ID 和名称信息。
#     # res_view 是大模型返回的答案
#     # 逻辑视图
#     hits_graph_view, hits_view, res_view, res_view_reason, res_load_view = await task_llm_invoke_kecc
#     logger.debug(f'hits_graph_view = {hits_graph_view}')
#     logger.debug(f'hits_view = {hits_view}')
#     logger.debug(f'res_view = {res_view}')
#     logger.debug(f'res_view_reason = {res_view_reason}')
#     logger.info(f'res_load_view = {res_load_view}')
#     # 接口服务
#     hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task6
#     # 指标
#     hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task7
#     #
#     entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc
#
#     hits_all_name = [entity["_source"]["resourcename"] for entity in entities_all]
#     #
#     entities = []
#     #
#     explanation_service = {}
#
#     # 指标
#     #    因为业务规则时,如果全部tab的搜索结果有指标,则不走text2sql和text2api，直接给出分析思路解释话术;如果解释话术不可用，则走保底话术
#     res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_ind) > 0:
#         # 如果交集(向量搜索结果和大模型返回结果的交集hits_graph_ind)和大模型返回结果res_ind数量相等, 说明大模型没有编造新的搜索结果,否则话术不可用
#         if len(hits_graph_ind) == len(res_ind):
#             explanation_ind, explanation_statu = add_label(
#                 reason=res_ind_reason,
#                 cites=hits_ind,
#                 a=0
#             )
#             logger.info(f"返回的话术和话术是否可用的状态码 = {explanation_ind}, {explanation_statu}")
#             # 话术不可用, 给出保底话术
#             if explanation_statu == '0':
#                 use_hits = [hgi["_selfid"] + '|' + hgi["_source"]["resourcename"] for hgi in hits_graph_ind]
#                 explanation_ind = add_label_easy(
#                     reason=res_explain,
#                     cites=use_hits
#                 )
#                 logger.info(f"话术不可用时，给出保底话术 = {explanation_ind}, {explanation_statu}")
#             # 搜索结果和话术都可用
#             res_statu = '1'
#             explanation_statu = '1'
#         else:
#             explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
#     else:
#         # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#         explanation_ind, res_statu, explanation_statu = ' ', '0', '0'
#
#     # 逻辑视图
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     # logger.debug('hits_graph_view=', len(hits_graph_view),hits_graph_view)
#     # logger.debug('res_view=', len(res_view),res_view)
#
#     # 因为不经过大模型， reson为空字符串， 所以无需做以下 结果和话术是否可用的判断
#     # if len(hits_graph_view) > 0:
#     #     # 如果交集(搜索结果和大模型返回结果的交集hits_graph_view)和大模型返回结果res_view数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#     #     if len(hits_graph_view) == len(res_view):
#     #         explanation_formview, explanation_st = add_label(
#     #             reason=res_view_reason,
#     #             cites=hits_view,
#     #             a=len(hits_graph_ind)
#     #         )
#     #         res_statu += '1'
#     #         # logger.debug("explanation_st=",explanation_st)
#     #         explanation_statu += explanation_st
#     #     else:
#     #         explanation_formview = ' '
#     #         res_statu += '1'
#     #         explanation_statu += '0'
#     # else:
#     #     explanation_formview = ' '
#     #     res_statu += '0'
#     #     explanation_statu += '0'
#     # 以下 把查出来的部门职责部门职责数据放在 explanation_formview， 即输出的 text 字段中
#     explanation_formview = str(all_hits_kecc)
#     res_statu += '1'
#     explanation_statu += '1'
#
#     # 接口服务, 解释中要有["explanation_params"]和["explanation_text"]两个字段
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_svc) > 0:
#         # 如果交集(搜索结果和大模型返回结果的交集)和大模型返回结果数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#
#         if len(hits_graph_svc) == len(res_svc):
#             explanation_service["explanation_params"] = res_load_svc
#             for rst in res_load_svc['推荐实例']:
#                 rst['interface_name'] = rst["interface_name"].split('|')[1]
#             explanation_service["explanation_text"], explana_s = add_label(
#                 reason=res_svc_reason,
#                 cites=hits_svc,
#                 a=len(hits_graph_ind) + len(hits_graph_view)
#             )
#             res_statu += '1'
#             explanation_statu += explana_s
#         else:
#             c_res = res_load_svc['推荐实例']
#             c_res1 = c_res[:]
#             for i in c_res1:
#                 if i["interface_name"].split('|')[1] not in hits_all_name:
#                     res_load_svc.remove(i)
#             for i in c_res:
#                 i['interface_name'] = i["interface_name"].split('|')[1]
#             res_load_svc['推荐实例'] = c_res
#             explanation_service["explanation_params"] = res_load_svc
#             explanation_service["explanation_text"] = ''
#             res_statu += '1'
#             explanation_statu += '0'
#     else:
#         explanation_service["explanation_params"] = ''
#         explanation_service["explanation_text"] = ''
#         res_statu += '0'
#         explanation_statu += '0'
#
#     # 最终返回
#     # entities_all 是所有命中的逻辑视图+接口服务+指标
#     # resource_entity 是预定义的返回结构, 和图谱中数据资源实体的结构主体部分一致
#     # 按照这个结构, 把所有命中的逻辑视图+接口服务+指标, 按照这个结构, 组装成一个列表, 赋值给 entities
#     for num, entity in enumerate(entities_all):
#         resource_entity_copy = copy.deepcopy(prompts_config.resource_entity)
#         resource_entity_copy["id"] = entity["_id"]
#         resource_entity_copy["default_property"]["value"] = entity["_source"]["resourcename"]
#         for props in resource_entity_copy["properties"][0]["props"]:
#             if props["name"] in entity["_source"]:
#                 props['value'] = entity["_source"][props["name"]]
#         entities.append({
#             "starts": [],
#             "entity": resource_entity_copy,
#             "score": search_params.limit - num
#         })
#
#     output['explanation_ind'] = explanation_ind
#     output['explanation_formview'] = explanation_formview
#     # output['explanation_formview'] = ''
#     output['explanation_service'] = explanation_service
#     output['entities'] = entities
#     output['count'] = len(entities_all)
#     output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
#
#     total_end_time = time.time()
#     total_time_cost = total_end_time - total_start_time
#     logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
#     # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
#     logger.info(f"""\n===================指标返回话术===================\n {output['explanation_ind']}
#               \n===================逻辑视图返回话术===================\n
#               {output['explanation_formview']}\n===================接口服务返回话术===================\n
#               {output['explanation_service']['explanation_text']}""")
#     # logger.info('--------------问答部分最终召回的资源-----------------\n')
#     log_content = "\n".join(
#         f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
#         for entity in output["entities"]
#     )
#     logger.info(f"--------------问答部分最终召回的资源-----------------\n\n{log_content}")
#
#     # for i in output["entities"]:
#     #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
#         # logger.debug(json.dumps(output, indent=4, ensure_ascii=False),res_statu, explanation_statu)
#     # output: json, 返回的结果
#     # res_statu: string , 返回的结果是否可用, 0代表不可用,1代表可用,
#     # 第1位代表指标, 第2位代表逻辑视图(按照代码顺序判断,conf文档中说是接口服务),第3位代表接口服务(按照代码顺序判断,conf文档中说是逻辑视图),
#     # 值形如000,001,010,011...
#     # explanation_statu: string, 返回的话术是否为空,0代表为空,1代表不为空, 与 res_statu 同样的编码方式
#
#     return output, res_statu, explanation_statu

# 带有部门职责知识增强的分析问答型搜索
# # 2025.06.06 找数问答放开表权限限制, 没有权限的表也可以进行找数问答, 但是问数问答还需要进行权限控制
# 加入关键字搜索和关联搜索能力的resource_analysis_search_kecc 取代只有向量搜索能力的
# resource_analysis_main_kecc() 和 resource_analysis_main_kecc_no_auth()
# async def resource_analysis_main_kecc_no_auth(request, search_params):
#     """有部门职责知识增强的分析问答型搜索"""
#     # 因为认知搜索图谱和部门职责图谱向量搜索都需要用到query的embedding，所以第一步先做query向量化
#     search_configs=get_search_configs()
#     try:
#         query_embedding, embedding_status = await query_m3e(search_params.query)
#         # 检查返回值的有效性
#         if not query_embedding or embedding_status is None:
#             logger.error("查询嵌入或状态无效")
#             return ANALYSIS_SEARCH_EMPTY_RESULT
#     except Exception as e:
#         logger.error(f'M3E embedding 错误: {settings.ML_EMBEDDING_URL} Internal Server Error. Exception= ', str(e))
#         # raise M3ERequestException(reason=f'{settings.ML_EMBEDDING_URL} Internal Server Error')
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#         # 可以在这里添加更多的错误处理逻辑
#     logger.info(f'embedding_status = {embedding_status}')
#     # 以下graph_vector_retriever_search_qa()函数
#     # 完成 (1)获取认知搜索图谱信息;(2) 认知搜索图谱向量搜索
#     try:
#         task_search_qa_retriever = asyncio.create_task(
#             graph_vector_retriever_search_qa(
#                 request=request,
#                 search_params=search_params,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status
#             )
#         )
#         # all_hits 是认知搜索图谱中与搜索词query向量相似的所有实体（数据资源或数据目录）
#         # drop_indices_vec是按照停用实体信息(原页面左栏),应该被过滤掉的向量,现在已经废弃
#         output, headers, total_start_time, all_hits, _ = await task_search_qa_retriever
#         logger.info(f"认知搜索图谱 OpenSearch 召回实体数量：{len(all_hits)}")
#         logger.debug(f'all_hits = \n{all_hits}')
#
#
#     except Exception as e:
#         logger.error(f"获取认知搜索图谱信息或向量搜索错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     try:
#         # 查询知识增强图谱，获取query对应的部门-信息系统-业务职责-业务事项 all_hits_kecc, 是字典列表
#         # 图谱id不能写死在这里, 产品化时需要采用和认知搜索同样的方式, af-sailor-service 程序构建后, 调用 af-sailor-service 接口获取图谱id
#         # 先加到config中
#         kg_id_kecc = safe_str_to_int(search_configs.kg_id_kecc)
#         if kg_id_kecc is None:
#             logger.error(f"获取'组织结构-部门职责-信息系统'知识图谱id失败!")
#         vec_size_kecc = safe_str_to_int(search_configs.sailor_vec_size_kecc)
#         if vec_size_kecc is None:
#             logger.error(f'获取向量检索 返回文档数上限 参数失败!')
#         vec_min_score_kecc = safe_str_to_float(search_configs.sailor_vec_min_score_kecc)
#         if vec_min_score_kecc is None:
#             logger.error(f'获取向量检索 分数下限 参数失败!')
#         vec_knn_k_kecc = safe_str_to_int(search_configs.sailor_vec_knn_k_kecc)
#         if vec_knn_k_kecc is None:
#             logger.error(f'获取向量检索 knn-k 参数失败!')
#
#         task_retriever_kecc = asyncio.create_task(
#             graph_vector_retriever_kecc(
#                 ad_appid=search_params.ad_appid,
#                 kg_id_kecc=kg_id_kecc,
#                 query=search_params.query,
#                 query_embedding=query_embedding,
#                 m_status=embedding_status,
#                 vec_size_kecc=vec_size_kecc,
#                 vec_min_score_kecc=vec_min_score_kecc,
#                 vec_knn_k_kecc=vec_knn_k_kecc
#             )
#         )
#
#         # all_hits_kecc 是部门职责知识增强图谱中与搜索词query向量相似的所有实体（单位-部门职责-业务事项-信息系统）
#         _, all_hits_kecc = await task_retriever_kecc
#         logger.info(f'all_hits of graph_vector_retriever_kecc = \n{all_hits_kecc}')
#         logger.info(f"length of all_hits_kecc={len(all_hits_kecc)}")
#
#     except Exception as e:
#         logger.error(f"获取'组织结构-部门职责-信息系统'图谱信息或向量搜索错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # pro_data_formview(旧代码中pro_data） 是逻辑视图
#     # pro_data_svc(旧代码中resour）是接口服务
#     # indicator是指标
#     pro_data_formview, pro_data_svc, pro_data_indicator = [], [], []
#
#     # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
#     # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
#     query_filters = search_params.filter
#     asset_type = query_filters.get('asset_type', '')
#     # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
#     # 只有 application-developer 可以搜到接口服务
#     if asset_type == [-1]:  # 全部tab
#         # 只有应用开发者的角色可以搜到接口服务
#         # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
#         if "application-developer" in search_params.roles:
#             # 恢复分析问答型搜索返回指标
#             # catalog = "1"  # 目录
#             # api = "2"  # API
#             # view = "3"  # 视图
#             # metric = "4"  # 指标 ？
#             allowed_asset_type = ['1', '2', '3', '4']
#         else:
#             allowed_asset_type = ['1', '3', '4']
#     else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
#         allowed_asset_type = asset_type
#     # 这里的 subject_id 是用户id
#
#     # 获取用户拥有权限的所有资源id, auth_id
#     try:
#         auth_id = await find_number_api.user_all_auth(
#             headers=headers,
#             subject_id=search_params.subject_id
#         )
#     except Exception as e:
#         logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
#         return ANALYSIS_SEARCH_EMPTY_RESULT
#
#     # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
#     if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
#         logger.info('用户是数据开发工程师和运营工程师')
#     else:
#         logger.info(f'该用户有权限的id = {auth_id}')
#
#     for num, i in enumerate(all_hits):
#         # 描述和名称拼起来作为提示词的一部分
#         description = i['_source']['description'] if 'description' in i['_source'] else '暂无描述'
#         # 1数据目录 2接口服务 3逻辑视图 4指标
#         # 从图谱get的i['_source']['asset_type']为字符型
#         # 分析问答型搜索要求必须是已经上线的资源
#         # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
#         valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
#         has_asset_type = 'asset_type' in i['_source']
#         asset_type_valid = has_asset_type and i['_source']['asset_type'] in {str(t) for t in allowed_asset_type}
#
#         online_status_valid = i['_source'].get('online_status') in valid_online_statuses
#
#         # if 'asset_type' in i['_source'] and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
#         #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
#         # 2025.06.06 找数问答放开表权限限制, 没有权限的表也可以进行找数问答, 但是问数问答还需要进行权限控制
#         if has_asset_type and asset_type_valid and online_status_valid:
#             # res_auth = await find_number_api.sub_user_auth_state(
#             #     assets=i['_source'],
#             #     params=search_params,
#             #     headers=headers,
#             #     auth_id=auth_id
#             # )
#             # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
#             i['_selfid'] = str(num)
#             # logger.debug(i['_source']['resourcename'], res_auth)
#             # 3 逻辑视图
#             # if i['_source']['asset_type'] == '3' and res_auth == "allow":
#             if i['_source']['asset_type'] == '3':
#                 # 描述和名称拼起来作为提示词的一部分
#                 # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
#                 # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
#                 pro_data_formview.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#             #  2接口服务
#             # if i['_source']['asset_type'] == '2' and res_auth == "allow":
#             if i['_source']['asset_type'] == '2':
#                 pro_data_svc.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#             #  4指标
#             # if i['_source']['asset_type'] == '4' and res_auth == "allow":
#             if i['_source']['asset_type'] == '4':
#                 pro_data_indicator.append({i['_selfid'] + '|' + i['_source']['resourcename']: description})
#
#         else:
#             pass
#     # 保留用户有权限并且已上线的资源    #
#     logger.info(f'pro_data_formview = {pro_data_formview}')
#     logger.info(f'pro_data_svc = {pro_data_svc}')
#     logger.info(f'pro_data_indicator = {pro_data_indicator}')
#
#     # async def skip_model():
#     #     logger.info('大模型入参为空，减少此次交互')
#     #     return [], [], [], '', {}
#
#     # 根据逻辑视图、接口服务、指标的返回结果，分别并发调用 llm_invoke
#     # 如果逻辑视图的召回结果为空
#     if not pro_data_formview:
#         task_llm_invoke_kecc = asyncio.create_task(skip_model('form_view'))
#     # 如果逻辑视图有召回结果，并发调用llm_invoke
#     else:
#         task_llm_invoke_kecc = asyncio.create_task(
#             llm_invoke_kecc(
#                 pro_data=pro_data_formview,
#                 query=search_params.query,
#                 dept_infosystem_duty=all_hits_kecc,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_table_kecc",
#                 table_name='table_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果接口服务的召回结果为空
#     if not pro_data_svc:
#         task6 = asyncio.create_task(skip_model('interface_service'))
#     # 如果接口服务有召回结果，并发调用llm_invoke
#     else:
#         task6 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_svc,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_interface",
#                 table_name='interface_name',
#                 all_hits=all_hits
#             )
#         )
#     # 如果指标的召回结果为空
#     if not pro_data_indicator:
#         task7 = asyncio.create_task(skip_model('pro_data_indicator'))
#     # 如果指标有召回结果，并发调用llm_invoke
#     else:
#         task7 = asyncio.create_task(
#             llm_invoke(
#                 pro_data=pro_data_indicator,
#                 query=search_params.query,
#                 ad_appid=search_params.ad_appid,
#                 prompt_id_table="all_indicator",
#                 table_name='indicator_name',
#                 all_hits=all_hits
#             )
#         )
#     # 触发事件循环开始迭代，接收大模型调用的返回结果
#     # hits_graph_view 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
#     # hits_view 提供了一个更简洁的形式来表示 `hits_graph_view` 中的项目，仅保留了项目的 ID 和名称信息。
#     # res_view 是大模型返回的答案
#     # 逻辑视图
#     hits_graph_view, hits_view, res_view, res_view_reason, res_load_view = await task_llm_invoke_kecc
#     # 接口服务
#     hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task6
#     # 指标
#     hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task7
#     #
#     entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc
#
#     hits_all_name = [entity["_source"]["resourcename"] for entity in entities_all]
#     #
#     entities = []
#     #
#     explanation_service = {}
#
#     # 指标
#     #    因为业务规则时,如果全部tab的搜索结果有指标,则不走text2sql和text2api，直接给出分析思路解释话术;如果解释话术不可用，则走保底话术
#     res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_ind) > 0:
#         # 如果交集(向量搜索结果和大模型返回结果的交集hits_graph_ind)和大模型返回结果res_ind数量相等, 说明大模型没有编造新的搜索结果,否则话术不可用
#         if len(hits_graph_ind) == len(res_ind):
#             explanation_ind, explanation_statu = add_label(
#                 reason=res_ind_reason,
#                 cites=hits_ind,
#                 a=0
#             )
#             logger.info(f"返回的话术和话术是否可用的状态码 = {explanation_ind}, {explanation_statu}")
#             # 话术不可用, 给出保底话术
#             if explanation_statu == '0':
#                 use_hits = [hgi["_selfid"] + '|' + hgi["_source"]["resourcename"] for hgi in hits_graph_ind]
#                 explanation_ind = add_label_easy(
#                     reason=res_explain,
#                     cites=use_hits
#                 )
#                 logger.info(f"话术不可用时，给出保底话术 = {explanation_ind}, {explanation_statu}")
#             # 搜索结果和话术都可用
#             res_statu = '1'
#             explanation_statu = '1'
#         else:
#             explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
#     else:
#         # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#         explanation_ind, res_statu, explanation_statu = ' ', '0', '0'
#
#     # 逻辑视图
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     logger.info(f'length of hits_graph_view={len(hits_graph_view)}')
#     logger.info(f'hits_graph_view = \n{hits_graph_view}')
#     logger.info(f'length of res_view={len(res_view)}')
#     logger.info(f'res_view=\n{res_view}')
#
#
#     if len(hits_graph_view) > 0:
#         # 如果交集(搜索结果和大模型返回结果的交集hits_graph_view)和大模型返回结果res_view数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#         if len(hits_graph_view) == len(res_view):
#             explanation_formview, explanation_st = add_label(
#                 reason=res_view_reason,
#                 cites=hits_view,
#                 a=len(hits_graph_ind)
#             )
#             res_statu += '1'
#             # logger.debug("explanation_st=",explanation_st)
#             explanation_statu += explanation_st
#         else:
#             explanation_formview = ' '
#             res_statu += '1'
#             explanation_statu += '0'
#     else:
#         explanation_formview = ' '
#         res_statu += '0'
#         explanation_statu += '0'
#
#     # 接口服务, 解释中要有["explanation_params"]和["explanation_text"]两个字段
#     # 只要交集不为空, res_statu = 1
#     # 如果交集为空, 搜索结果和话术都不可用,前端出保底话术
#     if len(hits_graph_svc) > 0:
#         # 如果交集(搜索结果和大模型返回结果的交集)和大模型返回结果数量相等, 说明大模型没有编造新的搜索结果, 否则话术不可用
#
#         if len(hits_graph_svc) == len(res_svc):
#             explanation_service["explanation_params"] = res_load_svc
#             for rst in res_load_svc['推荐实例']:
#                 rst['interface_name'] = rst["interface_name"].split('|')[1]
#             explanation_service["explanation_text"], explana_s = add_label(
#                 reason=res_svc_reason,
#                 cites=hits_svc,
#                 a=len(hits_graph_ind) + len(hits_graph_view)
#             )
#             res_statu += '1'
#             explanation_statu += explana_s
#         else:
#             c_res = res_load_svc['推荐实例']
#             c_res1 = c_res[:]
#             for i in c_res1:
#                 if i["interface_name"].split('|')[1] not in hits_all_name:
#                     res_load_svc.remove(i)
#             for i in c_res:
#                 i['interface_name'] = i["interface_name"].split('|')[1]
#             res_load_svc['推荐实例'] = c_res
#             explanation_service["explanation_params"] = res_load_svc
#             explanation_service["explanation_text"] = ''
#             res_statu += '1'
#             explanation_statu += '0'
#     else:
#         explanation_service["explanation_params"] = ''
#         explanation_service["explanation_text"] = ''
#         res_statu += '0'
#         explanation_statu += '0'
#
#     # 最终返回
#     # entities_all 是所有命中的逻辑视图+接口服务+指标
#     # resource_entity 是预定义的返回结构, 和图谱中数据资源实体的结构主体部分一致
#     # 按照这个结构, 把所有命中的逻辑视图+接口服务+指标, 按照这个结构, 组装成一个列表, 赋值给 entities
#     for num, entity in enumerate(entities_all):
#         resource_entity_copy = copy.deepcopy(prompts_config.resource_entity)
#         resource_entity_copy["id"] = entity["_id"]
#         resource_entity_copy["default_property"]["value"] = entity["_source"]["resourcename"]
#         for props in resource_entity_copy["properties"][0]["props"]:
#             if props["name"] in entity["_source"]:
#                 props['value'] = entity["_source"][props["name"]]
#         entities.append({
#             "starts": [],
#             "entity": resource_entity_copy,
#             "score": search_params.limit - num
#         })
#
#     output['explanation_ind'] = explanation_ind
#     output['explanation_formview'] = explanation_formview
#     output['explanation_service'] = explanation_service
#     output['entities'] = entities
#     output['count'] = len(entities_all)
#     output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
#
#     total_end_time = time.time()
#     total_time_cost = total_end_time - total_start_time
#     logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
#     # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
#     logger.info(f"""===================指标返回结果==============\n {output['explanation_ind']}
#               \n===================视图返回结果===================\n
#               {output['explanation_formview']}\n===================接口返回结果===================\n
#               {output['explanation_service']['explanation_text']}""")
#     logger.info('--------------问答部分最终召回的资源-----------------\n')
#     log_content = "\n".join(
#         f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
#         for entity in output["entities"]
#     )
#     logger.info(log_content)
#     # output: json, 返回的结果
#     # res_statu: string , 返回的结果是否可用, 0代表不可用,1代表可用,
#     # 第1位代表指标, 第2位代表逻辑视图(按照代码顺序判断,conf文档中说是接口服务),第3位代表接口服务(按照代码顺序判断,conf文档中说是逻辑视图),
#     # 值形如000,001,010,011...
#     # explanation_statu: string, 返回的话术是否为空,0代表为空,1代表不为空, 与 res_statu 同样的编码方式
#     return output, res_statu, explanation_statu

async def main():
    # from kafka import KafkaProducer
    ad_appid = '
    # 认知搜索图谱
    # kg_id = 6838
    # 部门职责知识增强图谱
    kg_id = 6839
    limit = 3
    min_score = 0.86
    query = "垃圾分类投放分析"
    query_embedding, m_status = await query_m3e(query)
    # logger.debug(f"query_embedding=\n{query_embedding}")
    # logger.debug(f"m_status=\n{m_status}")
    try:
        # rst1,rst2,rst3,rst4 = asyncio.run(knowledge_enhancement_catalog_chain(ad_appid, kg_id,limit,query))
        total_elapsed_time, all_hits_kecc = await graph_vector_retriever_kecc(
                ad_appid=ad_appid,
                kg_id_kecc=kg_id,
                query=query,
                query_embedding=query_embedding,
                m_status=m_status,
                vec_size_kecc=limit,
                vec_min_score_kecc=min_score,
                vec_knn_k_kecc=limit
        )

        # output, total_start_time, all_hits, drop_indices
        # logger.debug("output=\n", rst1)
        logger.debug("total_elapsed_time=\n", total_elapsed_time)
        # logger.debug("all_hits=\n", json.dumps(all_hits_entity, indent=4, ensure_ascii=False))
        # logger.debug("drop_indices=\n", rst4)
        # ebd = asyncio.run(query_m3e(query))
        # logger.debug(type(ebd),"\n",ebd)
        # dept_infosystem_bdsps = []
        #
        # for hit in rst3:
        #     if (hit["_source"]["dept_name_bdsp"], hit["_source"]["info_system_bdsp"]) not in dept_infosystem_bdsps:
        #         dept_infosystem_bdsps.append(
        #             (hit["_source"]["dept_name_bdsp"], hit["_source"]["info_system_bdsp"]))
        #
        # logger.debug("dept_infosystem_bdsps=\n", dept_infosystem_bdsps)

        # all_hits_cn = []
        # for item in all_hits_entity:
        #     new_item = {
        #         "信息相关性得分": item["_score"],
        #         "问题相关信息": {
        #             "单位": item["_source"]["dept_name_bdsp"],
        #             "信息系统": item["_source"]["info_system_bdsp"],
        #             "单位职责": item["_source"]["dept_duty"],
        #             "单位职责-明细": item["_source"]["sub_dept_duty"],
        #             "业务事项": item["_source"]["duty_items"],
        #             "业务事项类型": item["_source"]["duty_items_type"],
        #             "数据资源": item["_source"]["data_resource"],
        #             "核心数据项": item["_source"]["core_data_fields"]
        #         }
        #     }
        #     all_hits_cn.append(new_item)

        logger.debug("all_hits_kecc = \n", json.dumps(all_hits_kecc, indent=4, ensure_ascii=False))



    except Exception as e:
        logger.debug(f"执行过程中出现异常: {e}")




if __name__ == '__main__':
    asyncio.run(main())
