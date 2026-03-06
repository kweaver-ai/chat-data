# -*- coding: utf-8 -*-
# @Time    : 2024/1/21 9:48
# @Author  : Glen.lv
# @File    : asset_search
# @Project : copilot
import asyncio
import os,time
import json
from textwrap import dedent

from config import settings
from app.logs.logger import logger

from app.cores.cognitive_search.search_func import (FindNumberAPI, query_m3e, lexical_search, vector_search,
                                                    vector_search_dip, lexical_search_dip)
from app.cores.cognitive_search.graph_func import (get_kgotl, graph_analysis_formview, find_idx_list_of_dict,
                                                   graph_analysis_general, get_kgotl_dip)
from app.cores.cognitive_search.search_config.get_params import get_search_configs
from app.cores.cognitive_search.utils.utils import safe_str_to_float
from app.cores.cognitive_search.search_model import GraphFilterParamsModel



find_number_api = FindNumberAPI()

base_path = os.path.dirname(os.path.abspath(__file__))
resource_config_path = os.path.join(base_path, "search_config/config_search_resource.json")
catalog_config_path = os.path.join(base_path, "search_config/config_search_catalog.json")


async def combine_rst_of_lexical_and_vector_search(drop_indices_lexical, drop_indices_vec, hits_vec, hits_id_lexical,
                                                   hits_lexical, vid_hits_lexical):
    drop_indices = drop_indices_lexical + drop_indices_vec
    all_hits = []
    # 4 关键词搜索和向量搜索的搜索结果汇总,初步筛选和排序
    if hits_vec:
        for i, hit in enumerate(hits_vec):
            # 向量搜索结果加入all_hits，分数取决于其是否和关键词搜索重合：
            if hit["_id"] in hits_id_lexical:
                # 如果向量搜索结果的id在关键词搜索结果中存在，则将向量搜索结果的分数加到关键词搜索结果的分数中
                hit['vec_score'] = hit['_score'] / 2
                lexical_score = vid_hits_lexical[hit["_id"]]['_score']
                # 将向量搜索的分数折半后和关键词搜索的分数相加，作为新的关键词搜索分数
                vid_hits_lexical[hit["_id"]]['_score'] = hit['vec_score'] + lexical_score
                all_hits.append(vid_hits_lexical[hit["_id"]])
                vid_hits_lexical.pop(hit["_id"])
            else:
                # 如果向量搜索结果的id不在关键词搜索结果中，分数折半
                hit['_score'] = hit['_score'] / 2
                hit['max_score_prop'] = {
                    "prop": '',
                    "value": '',
                    "keys": []
                }
                all_hits.append(hit)
        for value in vid_hits_lexical.values():  # 关键词搜索结果中，向量搜索结果中没有的，加入 all_hits
            all_hits.append(value)
    else:
        all_hits = hits_lexical
    # logger.debug(f'before drop_indices: (all_hits) = {all_hits}')
    # 删除stop_entity_infos
    for i in all_hits[:]:
        if i['_id'] in set(drop_indices):
            all_hits.remove(i)
    logger.info(f"OpenSearch总召回数量：{len(all_hits)}")

    # 按照分数排序，初步筛选出分数大于零的结果
    hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    hits = [h for h in hits if h['_score'] >= 0]
    return hits, drop_indices


async def graph_search(data_type, hits, properties_alias, entity_types, search_params, request, graph_filter_params,
                       data_params, search_configs):
    # 5 图分析服务部分
    # from app.retriever import CognitiveSearch
    from app.cores.cognitive_assistant.qa_model import AfEdition
    # cognitivesearch = CognitiveSearch()
    start_time = time.time()
    # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    # 场景分析版本
    if data_type == 'form_view':
        vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(
            hits=hits,
            properties_alias=properties_alias,
            entity_types=entity_types,
            search_params=search_params,
            request=request,
            source_type=data_type,
            graph_filter_params=graph_filter_params,
            data_params=data_params
        )
    # 非场景分析版本
    else:
        # 搜索列表的inputs中没有af_editions字段， 在qa的inputs中有， 如果qa走到保底策略， 会把af_editions带入
        # 也可以根据 data——type来判断
        logger.info(f"search_params.af_editions = {search_params.af_editions}")
        logger.info(f"data_type = {data_type}")
        re_limit_qa = int(search_configs.sailor_search_qa_cites_num_limit)
        vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(
            hits=hits,
            properties_alias=properties_alias,
            entity_types=entity_types,
            search_params=search_params,
            request=request,
            source_type=data_type,
            graph_filter_params=graph_filter_params,
            data_params=data_params,
            re_limit=re_limit_qa,
            search_configs=search_configs
        )
        # if (data_type == "resource" and search_configs.direct_qa == 'false'
        #         and search_configs.sailor_search_if_auth_in_find_data_qa == '0'
        #         and search_configs.sailor_search_if_history_qa_enhance == '0'
        #         and search_configs.sailor_search_if_kecc == '1'):
        #     # logger.info(f"settings.IF_KECC = {settings.IF_KECC}")
        #     # logger.info(f"settings.IF_AUTH_IN_FIND_DATA_QA = {settings.IF_AUTH_IN_FIND_DATA_QA}")
        #     # if data_type=="resource" and settings.IF_KECC and not settings.IF_AUTH_IN_FIND_DATA_QA:
        #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_no_auth(hits=hits,
        #                                                                                                  properties_alias=properties_alias,
        #                                                                                                  entity_types=entity_types,
        #                                                                                                  search_params=search_params,
        #                                                                                                  request=request,
        #                                                                                                  source_type=data_type,
        #                                                                                                  graph_filter_params=graph_filter_params,
        #                                                                                                  data_params=data_params,
        #                                                                                                  re_limit=re_limit_qa)
        # else:
        #     # text=''
        #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis(hits=hits,
        #                                                                                          properties_alias=properties_alias,
        #                                                                                          entity_types=entity_types,
        #                                                                                          search_params=search_params,
        #                                                                                          request=request,
        #                                                                                          source_type=data_type,
        #                                                                                          graph_filter_params=graph_filter_params,
        #                                                                                          data_params=data_params,
        #                                                                                          re_limit=re_limit_qa)

    end_time = time.time()
    graph_analysis_final_score_time = end_time - start_time
    logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")
    return vertices, hit_names, service_names, entities, subgraphs, text

async def run_func(search_params, request, file_path, data_type,search_configs):
    """
    2.0.0.3-认知搜索-列表页主函数，run_func_resource()和 run_func_catalog()都调用这个函数，
    根据资源版或目录版传入的不同参数来执行

    参数:
        search_params (dict): API 入参的 body 部分。包括：
            query (str): 查询字符串。
            limit (int): 限制返回结果的数量。
            stopwords (List[str]): 停用词列表。
            stop_entities (List[str]): 停用实体列表。
            filter (Dict[str, Any]): 过滤器字典。
            ad_appid (str): AD 应用程序 ID。
            kg_id (int): 知识图谱 ID。
            available_option (int): 可用选项。
            entity2service (Dict[str, str]): 实体到服务的映射字典。
            required_resource (Dict[str, str]): 所需资源字典，同义词库id和停用词库id
            subject_id (str): 用户 ID。
            subject_type (str): 用户类型。
            roles (List[str]): 用户角色， 数据运营工程师、数据开发工程师、普通用户、数据管家、数据owner、应用开发者、系统管理员。
            af_editions (str): AF 版本。
        request: Request 对象。
        file_path (str): 指定配置文件路径，应为'search_config/config_search_resource.json' 或者'search_config/config_search_catalog.json'。
        data_type (str): AF版本标识符，'resource' 对应资源版，'datacatalog' 对应目录版。

    返回:
        output: 函数输出结果。初始化空output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    """
    # 搜索返回结果的数据结构还有"query_cuts" 列表
    # output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": [],"query_cuts": []}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    headers = {"Authorization": request.headers.get('Authorization')}
    query = search_params.query
    if not query:
        return output
    total_start_time = time.time()
    logger.info(
        f'INPUT：\nkg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\nrequired_resource: {search_params.required_resource}\n')
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\nstopwords: {search_params.stopwords}\nstop_entities: {search_params.stop_entities}\nfilter: {search_params.filter}')

    # 获取图谱信息和向量化
    task_get_kgotl = asyncio.create_task(
        get_kgotl(search_params=search_params, output=output, query=query, kgotl_config_file_path=file_path, graph_filter_params=GraphFilterParamsModel()))

    task_query_m3e = asyncio.create_task(query_m3e(query=query))
    # queries：同义词扩展后的多个衍生query组成的列表['上市公司股票信息'],
    # query_cuts：分词结果，同义词，是否停止词[{'source': '上市', 'synonym': [], 'is_stopword': False}, {'source': '公司股票', 'synonym': [], 'is_stopword': False}, {'source': '信息', 'synonym': [], 'is_stopword': False}]
    # all_syns：[]
    # entity_types,所有实体类的详细信息，比如主题域分组实体类，{'domain': {'entity_id': 'entity_id8bbf06bb-b3c8-4c5d-bba6-72273baeb440', 'name': 'domain',
        # 'description': '', 'alias': '主题域分组', 'synonym': [], 'default_tag': 'domainname',
        # 'properties_index': ['domainname'], 'search_prop': 'domainname', 'primary_key': ['domainid'],
        # 'vector_generation': ['domainname'], 'properties': [{'name': 'domainid', 'description': '',
        # 'alias': '主题域分组id', 'data_type': 'string'}, {'name': 'domainname', 'description': '', 'alias': '主题域分组名称',
        # 'data_type': 'string'}, {'name': 'prefixname', 'description': '', 'alias': 'prefixname', 'data_type': 'string'}],
        # 'x': 713.6353774815489, 'y': 620.3576388888889, 'icon': 'empty', 'shape': 'circle', 'size': '0.5x',
        # 'fill_color': 'rgba(145,192,115,1)', 'stroke_color': 'rgba(145,192,115,1)', 'text_color': 'rgba(0,0,0,1)',
        # 'text_position': 'top', 'text_width': 15, 'index_default_switch': False, 'text_type': 'adaptive',
        # 'source_type': 'manual', 'model': '', 'task_id': '', 'icon_color': '#ffffff', 'colour': 'rgba(145,192,115,1)'}}
    #  properties_alias,图谱本体中 每个实体类字段的别名（显示名）字典{'domain': {'domainid': '主题域分组id', 'domainname': '主题域分组名称', 'prefixname': 'prefixname'}, 'subdomain': {'subdomainid': '主题域id', 'subdomainname': '主题域名称', 'prefixname': 'prefixname'}}
    # properties_types,图谱本体中 每个实体类字段的数据类型字典{'domain': {'domainid': 'string', 'domainname': 'string', 'prefixname': 'string'}, 'subdomain': {'subdomainid': 'string', 'subdomainname': 'string', 'prefixname': 'string'}}
    # entity2prop,每个实体类的默认显示属性字段， 形如 entity2prop：{'domain': 'domainname', 'subdomain': 'subdomainname',
        # 'customized_category': 'name', 'customized_category_node': 'name', 'data_catalog_column': 'business_name',
        # 'response_field': 'cn_name', 'service': 'name', 'data_explore_report': 'explore_result_valule',
        # 'form_view_field': 'business_name', 'datasource': 'datasourcename', 'metadataschema': 'metadataschemaname',
        # 'form_view': 'business_name', 'department': 'departmentname', 'info_system': 'infosystemname',
        # 'catalogtag': 'catalogtagname', 'datacatalog': 'datacatalogname'}
    # vector_index_filed,图谱本体中每个实体类向量索引的字段列表{'info_system': ['info_system_description', 'infosystemname'], 'catalogtag': ['catalogtagname'], 'datacatalog': ['description_name', 'datacatalogname']}
    # data_params 时相关参数， 比如搜索结果上限、实体权重、同义词actrie对象、停用词列表对象等
    # graph_filter_params 是筛选项， 调用 get_kgotl( )时，传入的时初始化的筛选项， 在调用时，会更新筛选项
    (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop, vector_index_filed,
     data_params, graph_filter_params) = await task_get_kgotl
    logger.info(f"同义词扩展后的 queries：{queries}")
    logger.info(f"query_cuts：{query_cuts}")
    logger.info(f"all_syns：{all_syns}")
    # logger.debug(f"entity_types：{entity_types}")
    logger.info(f"entity2prop：{entity2prop}")
    # logger.debug(f"data_params：{data_params}")
    # logger.debug(f"graph_filter_params：{graph_filter_params}")
    embeddings, m_status = await task_query_m3e

    # 关键词搜索和向量搜索
    min_score = float(settings.MIN_SCORE)
    task_lexical_search = asyncio.create_task(
        lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
                          data_params=data_params,
                          search_params=search_params))

    task_vector_search = asyncio.create_task(
        vector_search(embeddings=embeddings, m_status=m_status, vector_index_filed=vector_index_filed,
                      entity_types=entity_types, data_params=data_params, min_score=min_score, search_params=search_params))
    # hits_key_id, vid_hits_key, hits_key, drop_indices_key
    hits_key_id, vid_hits_key, hits_key, drop_indices_key = await task_lexical_search
    # hits_vec, drop_indices_vec
    hits_vec, drop_indices_vec = await task_vector_search

    drop_indices = drop_indices_key + drop_indices_vec
    all_hits = []

    # 结果汇总
    if hits_vec:
        for i, hit in enumerate(hits_vec):
            if hit["_id"] in hits_key_id:
                hit['vec_score'] = hit['_score'] / 2
                key_score = vid_hits_key[hit["_id"]]['_score']
                vid_hits_key[hit["_id"]]['_score'] = hit['vec_score'] + key_score
                all_hits.append(vid_hits_key[hit["_id"]])
                vid_hits_key.pop(hit["_id"])
            else:
                hit['_score'] = hit['_score'] / 2
                hit['max_score_prop'] = {
                    "prop": '',
                    "value": '',
                    "keys": []
                }
                all_hits.append(hit)
        for value in vid_hits_key.values():
            all_hits.append(value)
    else:
        all_hits = hits_key

    # 删除stop_entity_infos
    for i in all_hits[:]:
        if i['_id'] in set(drop_indices):
            all_hits.remove(i)
    logger.info(f"OpenSearch总召回数量：{len(all_hits)}")

    # 筛选排序
    hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    hits = [h for h in hits if h['_score'] >= 0]

    # 图分析服务部分
    start_time = time.time()
    RE_limit = int(settings.Finally_NUM)
    # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    if data_type == 'form_view':
        vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(hits=hits,
                                                                                                     properties_alias=properties_alias,
                                                                                                     entity_types=entity_types,
                                                                                                     search_params=search_params,
                                                                                                     request=request,
                                                                                                     source_type=data_type,
                                                                                                     graph_filter_params=graph_filter_params,
                                                                                                     data_params=data_params)
    else:
        vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(hits=hits,
                                                                                                     properties_alias=properties_alias,
                                                                                                     entity_types=entity_types,
                                                                                                     search_params=search_params,
                                                                                                     request=request,
                                                                                                     source_type=data_type,
                                                                                                     graph_filter_params=graph_filter_params,
                                                                                                     data_params=data_params,
                                                                                                     re_limit=RE_limit,
                                                                                                     search_configs=search_configs)

    end_time = time.time()
    graph_analysis_final_score_time = end_time - start_time
    logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")

    # #增加共享申请图标
    # catalog_ids=[]
    # if  data_type=='datacatalog':
    #     for i in entities:
    #         catalog_id=find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
    #                               value_to_find='datacatalogid')
    #         catalog_ids.append(catalog_id)
    #         res= await find_number_api.get_shared_declaration_status(catalog_ids,headers)
    #         i["shared_declaration"]=res
    output['entities'] = entities
    output['count'] = len(entities)
    output['answer'] = text
    output['subgraphs'] = subgraphs
    output['query_cuts'] = query_cuts
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    # logger.debug(f'before  run_func return, output ={output}')
    return output

# 分析问答型搜索的托底算法
async def run_func_for_qa(search_params, request, file_path, data_type, search_configs):
    """
    认知搜索-列表页主函数，run_func_resource()和 run_func_catalog()都调用这个函数，
    根据资源版或目录版传入的不同参数来执行

    参数:
        search_params (dict): API 入参的 body 部分。包括：
            query (str): 查询字符串。
            limit (int): 限制返回结果的数量。
            stopwords (List[str]): 停用词列表。
            stop_entities (List[str]): 停用实体列表。
            filter (Dict[str, Any]): 过滤器字典。
            ad_appid (str): AD 应用程序 ID。
            kg_id (int): 知识图谱 ID。
            available_option (int): 可用选项。
            entity2service (Dict[str, str]): 实体到服务的映射字典。
            required_resource (Dict[str, str]): 所需资源字典，同义词库id和停用词库id
            subject_id (str): 用户 ID。
            subject_type (str): 用户类型。
            roles (List[str]): 用户角色， 数据运营工程师、数据开发工程师、普通用户、数据管家、数据owner、应用开发者、系统管理员。
            af_editions (str): AF 版本。
        request: Request 对象。
        file_path (str): 指定配置文件路径，应为'search_config/config_search_resource.json' 或者'search_config/config_search_catalog.json'。
        data_type (str): AF版本标识符，'resource' 对应资源版，'datacatalog' 对应目录版。

    返回:
        output: 函数输出结果。初始化空output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    """

    # 搜索返回结果的数据结构还有"query_cuts" 列表
    # output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": [],"query_cuts": []}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    headers = {"Authorization": request.headers.get('Authorization')}
    query = search_params.query
    if not query:
        return output
    total_start_time = time.time()
    logger.info(
        f'INPUT：\nkg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\nrequired_resource: {search_params.required_resource}\n')
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\nstopwords: {search_params.stopwords}\nstop_entities: {search_params.stop_entities}\nfilter: {search_params.filter}')

    # 获取图谱信息和向量化
    task_get_kgotl = asyncio.create_task(
        get_kgotl(search_params=search_params, output=output, query=query, kgotl_config_file_path=file_path, graph_filter_params=GraphFilterParamsModel()))

    task_query_m3e = asyncio.create_task(query_m3e(query=query))
    # queries：同义词扩展后的多个衍生query组成的列表['上市公司股票信息'],
    # query_cuts：分词结果，同义词，是否停止词[{'source': '上市', 'synonym': [], 'is_stopword': False}, {'source': '公司股票', 'synonym': [], 'is_stopword': False}, {'source': '信息', 'synonym': [], 'is_stopword': False}]
    # all_syns：[]
    # entity_types,所有实体类的详细信息，比如主题域分组实体类，{'domain': {'entity_id': 'entity_id8bbf06bb-b3c8-4c5d-bba6-72273baeb440', 'name': 'domain',
        # 'description': '', 'alias': '主题域分组', 'synonym': [], 'default_tag': 'domainname',
        # 'properties_index': ['domainname'], 'search_prop': 'domainname', 'primary_key': ['domainid'],
        # 'vector_generation': ['domainname'], 'properties': [{'name': 'domainid', 'description': '',
        # 'alias': '主题域分组id', 'data_type': 'string'}, {'name': 'domainname', 'description': '', 'alias': '主题域分组名称',
        # 'data_type': 'string'}, {'name': 'prefixname', 'description': '', 'alias': 'prefixname', 'data_type': 'string'}],
        # 'x': 713.6353774815489, 'y': 620.3576388888889, 'icon': 'empty', 'shape': 'circle', 'size': '0.5x',
        # 'fill_color': 'rgba(145,192,115,1)', 'stroke_color': 'rgba(145,192,115,1)', 'text_color': 'rgba(0,0,0,1)',
        # 'text_position': 'top', 'text_width': 15, 'index_default_switch': False, 'text_type': 'adaptive',
        # 'source_type': 'manual', 'model': '', 'task_id': '', 'icon_color': '#ffffff', 'colour': 'rgba(145,192,115,1)'}}
    #  properties_alias,图谱本体中 每个实体类字段的别名（显示名）字典{'domain': {'domainid': '主题域分组id', 'domainname': '主题域分组名称', 'prefixname': 'prefixname'}, 'subdomain': {'subdomainid': '主题域id', 'subdomainname': '主题域名称', 'prefixname': 'prefixname'}}
    # properties_types,图谱本体中 每个实体类字段的数据类型字典{'domain': {'domainid': 'string', 'domainname': 'string', 'prefixname': 'string'}, 'subdomain': {'subdomainid': 'string', 'subdomainname': 'string', 'prefixname': 'string'}}
    # entity2prop,每个实体类的默认显示属性字段， 形如 entity2prop：{'domain': 'domainname', 'subdomain': 'subdomainname',
        # 'customized_category': 'name', 'customized_category_node': 'name', 'data_catalog_column': 'business_name',
        # 'response_field': 'cn_name', 'service': 'name', 'data_explore_report': 'explore_result_valule',
        # 'form_view_field': 'business_name', 'datasource': 'datasourcename', 'metadataschema': 'metadataschemaname',
        # 'form_view': 'business_name', 'department': 'departmentname', 'info_system': 'infosystemname',
        # 'catalogtag': 'catalogtagname', 'datacatalog': 'datacatalogname'}
    # vector_index_filed,图谱本体中每个实体类向量索引的字段列表{'info_system': ['info_system_description', 'infosystemname'], 'catalogtag': ['catalogtagname'], 'datacatalog': ['description_name', 'datacatalogname']}
    # data_params 时相关参数， 比如搜索结果上限、实体权重、同义词actrie对象、停用词列表对象等
    # graph_filter_params 是筛选项， 调用 get_kgotl( )时，传入的时初始化的筛选项， 在调用时，会更新筛选项
    (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop, vector_index_filed,
     data_params, graph_filter_params) = await task_get_kgotl
    logger.info(f"同义词扩展后的queries：{queries}")
    logger.info(f"query_cuts：{query_cuts}")
    logger.info(f"all_syns：{all_syns}")
    # logger.debug(f"entity_types：{entity_types}")
    logger.info(f"entity2prop：{entity2prop}")
    # logger.debug(f"data_params：{data_params}")
    # logger.debug(f"graph_filter_params：{graph_filter_params}")
    query_embedding, m_status = await task_query_m3e

    # 关键词搜索和向量搜索
    min_score = float(settings.MIN_SCORE)

    (hits_id_lexical, vid_hits_lexical, hits_lexical,
     drop_indices_lexical), (hits_vec, drop_indices_vec) = await asyncio.gather(
        lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
                       data_params=data_params, search_params=search_params),
        vector_search(embeddings=query_embedding, m_status=m_status, vector_index_filed=vector_index_filed,
                      entity_types=entity_types, data_params=data_params, min_score=min_score,
                      search_params=search_params)
    )
    # task_lexical_search = asyncio.create_task(
    #     lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
    #                       data_params=data_params,
    #                       search_params=search_params))
    #
    # task_vector_search = asyncio.create_task(
    #     vector_search(embeddings=query_embedding, m_status=m_status, vector_index_filed=vector_index_filed,
    #                   entity_types=entity_types, data_params=data_params, min_score=min_score, search_params=search_params))
    # # hits_key_id, vid_hits_key, hits_key, drop_indices_key
    # hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical = await task_lexical_search
    # # hits_vec, drop_indices_vec
    # hits_vec, drop_indices_vec = await task_vector_search

    # 4 关键词搜索和向量搜索的搜索结果汇总,初步筛选和排序
    hits, drop_indices = await combine_rst_of_lexical_and_vector_search(
        drop_indices_lexical,
        drop_indices_vec,
        hits_vec,
        hits_id_lexical,
        hits_lexical,
        vid_hits_lexical)
    # 5 图分析服务部分
    vertices, hit_names, service_names, entities, subgraphs, text = await graph_search(
        data_type, hits,
        properties_alias, entity_types,
        search_params, request,
        graph_filter_params,
        data_params, search_configs)

    # drop_indices = drop_indices_key + drop_indices_vec
    # all_hits = []
    #
    # # 结果汇总
    # if hits_vec:
    #     for i, hit in enumerate(hits_vec):
    #         if hit["_id"] in hits_key_id:
    #             hit['vec_score'] = hit['_score'] / 2
    #             key_score = vid_hits_key[hit["_id"]]['_score']
    #             vid_hits_key[hit["_id"]]['_score'] = hit['vec_score'] + key_score
    #             all_hits.append(vid_hits_key[hit["_id"]])
    #             vid_hits_key.pop(hit["_id"])
    #         else:
    #             hit['_score'] = hit['_score'] / 2
    #             hit['max_score_prop'] = {
    #                 "prop": '',
    #                 "value": '',
    #                 "keys": []
    #             }
    #             all_hits.append(hit)
    #     for value in vid_hits_key.values():
    #         all_hits.append(value)
    # else:
    #     all_hits = hits_key
    #
    # # 删除stop_entity_infos
    # for i in all_hits[:]:
    #     if i['_id'] in set(drop_indices):
    #         all_hits.remove(i)
    # logger.info(f"OpenSearch总召回数量：{len(all_hits)}")
    #
    # # 筛选排序
    # hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    # hits = [h for h in hits if h['_score'] >= 0]
    #
    # # search_configs = get_search_configs()
    # # 图分析服务部分
    # # from app.retriever import CognitiveSearch
    # from app.cores.cognitive_assistant.qa_model import AfEdition
    # # cognitivesearch = CognitiveSearch()
    # start_time = time.time()
    # # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    # if data_type == 'form_view':
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params)
    # else:
    #     # 搜索列表的inputs中没有af_editions字段， 在qa的inputs中有， 如果qa走到保底策略， 会把af_editions带入
    #     # 也可以根据 data——type来判断
    #     logger.info(f"search_params.af_editions = {search_params.af_editions}")
    #     logger.info(f"data_type = {data_type}")
    #     re_limit_qa = int(search_configs.sailor_search_qa_cites_num_limit)
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params,
    #                                                                                                  re_limit=re_limit_qa,
    #                                                                                                  search_configs=search_configs)
    #     # if (data_type=="resource" and search_configs.direct_qa == 'false'
    #     #         and search_configs.sailor_search_if_auth_in_find_data_qa == '0'
    #     #         and search_configs.sailor_search_if_history_qa_enhance == '0'
    #     #         and search_configs.sailor_search_if_kecc == '1'):
    #     #
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_no_auth(hits=hits,
    #     #                                                                                                  properties_alias=properties_alias,
    #     #                                                                                                  entity_types=entity_types,
    #     #                                                                                                  search_params=search_params,
    #     #                                                                                                  request=request,
    #     #                                                                                                  source_type=data_type,
    #     #                                                                                                  graph_filter_params=graph_filter_params,
    #     #                                                                                                  data_params=data_params,
    #     #                                                                                                  re_limit=re_limit_qa)
    #     # else:
    #     #     # text=''
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis(hits=hits,
    #     #                                                                                          properties_alias=properties_alias,
    #     #                                                                                          entity_types=entity_types,
    #     #                                                                                          search_params=search_params,
    #     #                                                                                          request=request,
    #     #                                                                                          source_type=data_type,
    #     #                                                                                          graph_filter_params=graph_filter_params,
    #     #                                                                                          data_params=data_params,
    #     #                                                                                          re_limit=re_limit_qa)
    #
    # end_time = time.time()
    # graph_analysis_final_score_time = end_time - start_time
    # logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")

    # #增加共享申请图标
    # catalog_ids=[]
    # if  data_type=='datacatalog':
    #     for i in entities:
    #         catalog_id=find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
    #                               value_to_find='datacatalogid')
    #         catalog_ids.append(catalog_id)
    #         res= await find_number_api.get_shared_declaration_status(catalog_ids,headers)
    #         i["shared_declaration"]=res
    output['entities'] = entities
    output['count'] = len(entities)
    output['answer'] = text
    output['subgraphs'] = subgraphs
    output['query_cuts'] = query_cuts
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    return output


async def run_func_for_qa_dip(search_params, request, file_path, data_type, search_configs):
    """
    认知搜索-列表页主函数，run_func_resource()和 run_func_catalog()都调用这个函数，
    根据资源版或目录版传入的不同参数来执行

    参数:
        search_params (dict): API 入参的 body 部分。包括：
            query (str): 查询字符串。
            limit (int): 限制返回结果的数量。
            stopwords (List[str]): 停用词列表。
            stop_entities (List[str]): 停用实体列表。
            filter (Dict[str, Any]): 过滤器字典。
            kg_id (int): 知识图谱 ID。
            available_option (int): 可用选项。
            entity2service (Dict[str, str]): 实体到服务的映射字典。
            required_resource (Dict[str, str]): 所需资源字典，同义词库id和停用词库id
            subject_id (str): 用户 ID。
            subject_type (str): 用户类型。
            roles (List[str]): 用户角色， 数据运营工程师、数据开发工程师、普通用户、数据管家、数据owner、应用开发者、系统管理员。
            af_editions (str): AF 版本。
        request: Request 对象。
        file_path (str): 指定配置文件路径，应为'search_config/config_search_resource.json' 或者'search_config/config_search_catalog.json'。
        data_type (str): AF版本标识符，'resource' 对应资源版，'datacatalog' 对应目录版。

    返回:
        output: 函数输出结果。初始化空output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    """

    # 搜索返回结果的数据结构还有"query_cuts" 列表
    # output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": [],"query_cuts": []}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    headers = {"Authorization": request.headers.get('Authorization')}
    query = search_params.query
    if not query:
        return output
    total_start_time = time.time()
    logger.info(
        f'INPUT：\nkg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\nrequired_resource: {search_params.required_resource}\n')
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\nstopwords: {search_params.stopwords}\nstop_entities: {search_params.stop_entities}\nfilter: {search_params.filter}')

    # 获取图谱信息和向量化
    task_get_kgotl = asyncio.create_task(
        get_kgotl_dip(search_params=search_params, output=output, query=query, kgotl_config_file_path=file_path, graph_filter_params=GraphFilterParamsModel()))

    task_query_m3e = asyncio.create_task(query_m3e(query=query))
    # queries：同义词扩展后的多个衍生query组成的列表['上市公司股票信息'],
    # query_cuts：分词结果，同义词，是否停止词[{'source': '上市', 'synonym': [], 'is_stopword': False}, {'source': '公司股票', 'synonym': [], 'is_stopword': False}, {'source': '信息', 'synonym': [], 'is_stopword': False}]
    # all_syns：[]
    # entity_types,所有实体类的详细信息，比如主题域分组实体类，{'domain': {'entity_id': 'entity_id8bbf06bb-b3c8-4c5d-bba6-72273baeb440', 'name': 'domain',
        # 'description': '', 'alias': '主题域分组', 'synonym': [], 'default_tag': 'domainname',
        # 'properties_index': ['domainname'], 'search_prop': 'domainname', 'primary_key': ['domainid'],
        # 'vector_generation': ['domainname'], 'properties': [{'name': 'domainid', 'description': '',
        # 'alias': '主题域分组id', 'data_type': 'string'}, {'name': 'domainname', 'description': '', 'alias': '主题域分组名称',
        # 'data_type': 'string'}, {'name': 'prefixname', 'description': '', 'alias': 'prefixname', 'data_type': 'string'}],
        # 'x': 713.6353774815489, 'y': 620.3576388888889, 'icon': 'empty', 'shape': 'circle', 'size': '0.5x',
        # 'fill_color': 'rgba(145,192,115,1)', 'stroke_color': 'rgba(145,192,115,1)', 'text_color': 'rgba(0,0,0,1)',
        # 'text_position': 'top', 'text_width': 15, 'index_default_switch': False, 'text_type': 'adaptive',
        # 'source_type': 'manual', 'model': '', 'task_id': '', 'icon_color': '#ffffff', 'colour': 'rgba(145,192,115,1)'}}
    #  properties_alias,图谱本体中 每个实体类字段的别名（显示名）字典{'domain': {'domainid': '主题域分组id', 'domainname': '主题域分组名称', 'prefixname': 'prefixname'}, 'subdomain': {'subdomainid': '主题域id', 'subdomainname': '主题域名称', 'prefixname': 'prefixname'}}
    # properties_types,图谱本体中 每个实体类字段的数据类型字典{'domain': {'domainid': 'string', 'domainname': 'string', 'prefixname': 'string'}, 'subdomain': {'subdomainid': 'string', 'subdomainname': 'string', 'prefixname': 'string'}}
    # entity2prop,每个实体类的默认显示属性字段， 形如 entity2prop：{'domain': 'domainname', 'subdomain': 'subdomainname',
        # 'customized_category': 'name', 'customized_category_node': 'name', 'data_catalog_column': 'business_name',
        # 'response_field': 'cn_name', 'service': 'name', 'data_explore_report': 'explore_result_valule',
        # 'form_view_field': 'business_name', 'datasource': 'datasourcename', 'metadataschema': 'metadataschemaname',
        # 'form_view': 'business_name', 'department': 'departmentname', 'info_system': 'infosystemname',
        # 'catalogtag': 'catalogtagname', 'datacatalog': 'datacatalogname'}
    # vector_index_filed,图谱本体中每个实体类向量索引的字段列表{'info_system': ['info_system_description', 'infosystemname'], 'catalogtag': ['catalogtagname'], 'datacatalog': ['description_name', 'datacatalogname']}
    # data_params 时相关参数， 比如搜索结果上限、实体权重、同义词actrie对象、停用词列表对象等
    # graph_filter_params 是筛选项， 调用 get_kgotl( )时，传入的时初始化的筛选项， 在调用时，会更新筛选项
    (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop, vector_index_filed,
     data_params, graph_filter_params) = await task_get_kgotl
    logger.info(f"同义词扩展后的queries：{queries}")
    logger.info(f"query_cuts：{query_cuts}")
    logger.info(f"all_syns：{all_syns}")
    # logger.debug(f"entity_types：{entity_types}")
    logger.info(f"entity2prop：{entity2prop}")
    # logger.debug(f"data_params：{data_params}")
    # logger.debug(f"graph_filter_params：{graph_filter_params}")
    query_embedding, m_status = await task_query_m3e

    # 关键词搜索和向量搜索
    min_score = float(settings.MIN_SCORE)

    (hits_id_lexical, vid_hits_lexical, hits_lexical,
     drop_indices_lexical), (hits_vec, drop_indices_vec) = await asyncio.gather(
        lexical_search_dip(
            query=query,
            queries=queries,
            all_syns=all_syns,
            entity_types=entity_types,
            data_params=data_params,
            search_params=search_params
        ),
        vector_search_dip(
            embeddings=query_embedding,
            m_status=m_status,
            vector_index_filed=vector_index_filed,
            entity_types=entity_types,
            data_params=data_params,
            min_score=min_score,
            search_params=search_params
        )
    )
    # task_lexical_search = asyncio.create_task(
    #     lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
    #                       data_params=data_params,
    #                       search_params=search_params))
    #
    # task_vector_search = asyncio.create_task(
    #     vector_search(embeddings=query_embedding, m_status=m_status, vector_index_filed=vector_index_filed,
    #                   entity_types=entity_types, data_params=data_params, min_score=min_score, search_params=search_params))
    # # hits_key_id, vid_hits_key, hits_key, drop_indices_key
    # hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical = await task_lexical_search
    # # hits_vec, drop_indices_vec
    # hits_vec, drop_indices_vec = await task_vector_search

    # 4 关键词搜索和向量搜索的搜索结果汇总,初步筛选和排序
    hits, drop_indices = await combine_rst_of_lexical_and_vector_search(
        drop_indices_lexical,
        drop_indices_vec,
        hits_vec,
        hits_id_lexical,
        hits_lexical,
        vid_hits_lexical)
    # 5 图分析服务部分
    vertices, hit_names, service_names, entities, subgraphs, text = await graph_search(
        data_type, hits,
        properties_alias, entity_types,
        search_params, request,
        graph_filter_params,
        data_params, search_configs)

    # drop_indices = drop_indices_key + drop_indices_vec
    # all_hits = []
    #
    # # 结果汇总
    # if hits_vec:
    #     for i, hit in enumerate(hits_vec):
    #         if hit["_id"] in hits_key_id:
    #             hit['vec_score'] = hit['_score'] / 2
    #             key_score = vid_hits_key[hit["_id"]]['_score']
    #             vid_hits_key[hit["_id"]]['_score'] = hit['vec_score'] + key_score
    #             all_hits.append(vid_hits_key[hit["_id"]])
    #             vid_hits_key.pop(hit["_id"])
    #         else:
    #             hit['_score'] = hit['_score'] / 2
    #             hit['max_score_prop'] = {
    #                 "prop": '',
    #                 "value": '',
    #                 "keys": []
    #             }
    #             all_hits.append(hit)
    #     for value in vid_hits_key.values():
    #         all_hits.append(value)
    # else:
    #     all_hits = hits_key
    #
    # # 删除stop_entity_infos
    # for i in all_hits[:]:
    #     if i['_id'] in set(drop_indices):
    #         all_hits.remove(i)
    # logger.info(f"OpenSearch总召回数量：{len(all_hits)}")
    #
    # # 筛选排序
    # hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    # hits = [h for h in hits if h['_score'] >= 0]
    #
    # # search_configs = get_search_configs()
    # # 图分析服务部分
    # # from app.retriever import CognitiveSearch
    # from app.cores.cognitive_assistant.qa_model import AfEdition
    # # cognitivesearch = CognitiveSearch()
    # start_time = time.time()
    # # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    # if data_type == 'form_view':
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params)
    # else:
    #     # 搜索列表的inputs中没有af_editions字段， 在qa的inputs中有， 如果qa走到保底策略， 会把af_editions带入
    #     # 也可以根据 data——type来判断
    #     logger.info(f"search_params.af_editions = {search_params.af_editions}")
    #     logger.info(f"data_type = {data_type}")
    #     re_limit_qa = int(search_configs.sailor_search_qa_cites_num_limit)
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params,
    #                                                                                                  re_limit=re_limit_qa,
    #                                                                                                  search_configs=search_configs)
    #     # if (data_type=="resource" and search_configs.direct_qa == 'false'
    #     #         and search_configs.sailor_search_if_auth_in_find_data_qa == '0'
    #     #         and search_configs.sailor_search_if_history_qa_enhance == '0'
    #     #         and search_configs.sailor_search_if_kecc == '1'):
    #     #
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_no_auth(hits=hits,
    #     #                                                                                                  properties_alias=properties_alias,
    #     #                                                                                                  entity_types=entity_types,
    #     #                                                                                                  search_params=search_params,
    #     #                                                                                                  request=request,
    #     #                                                                                                  source_type=data_type,
    #     #                                                                                                  graph_filter_params=graph_filter_params,
    #     #                                                                                                  data_params=data_params,
    #     #                                                                                                  re_limit=re_limit_qa)
    #     # else:
    #     #     # text=''
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis(hits=hits,
    #     #                                                                                          properties_alias=properties_alias,
    #     #                                                                                          entity_types=entity_types,
    #     #                                                                                          search_params=search_params,
    #     #                                                                                          request=request,
    #     #                                                                                          source_type=data_type,
    #     #                                                                                          graph_filter_params=graph_filter_params,
    #     #                                                                                          data_params=data_params,
    #     #                                                                                          re_limit=re_limit_qa)
    #
    # end_time = time.time()
    # graph_analysis_final_score_time = end_time - start_time
    # logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")

    # #增加共享申请图标
    # catalog_ids=[]
    # if  data_type=='datacatalog':
    #     for i in entities:
    #         catalog_id=find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
    #                               value_to_find='datacatalogid')
    #         catalog_ids.append(catalog_id)
    #         res= await find_number_api.get_shared_declaration_status(catalog_ids,headers)
    #         i["shared_declaration"]=res
    output['entities'] = entities
    output['count'] = len(entities)
    output['answer'] = text
    output['subgraphs'] = subgraphs
    output['query_cuts'] = query_cuts
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    return output

async def run_func_for_qa_dip_new(search_params, request, file_path, data_type, search_configs):
    """
    认知搜索-列表页主函数，run_func_resource()和 run_func_catalog()都调用这个函数，
    根据资源版或目录版传入的不同参数来执行

    参数:
        search_params (dict): API 入参的 body 部分。包括：
            query (str): 查询字符串。
            limit (int): 限制返回结果的数量。
            stopwords (List[str]): 停用词列表。
            stop_entities (List[str]): 停用实体列表。
            filter (Dict[str, Any]): 过滤器字典。
            kg_id (int): 知识图谱 ID。
            available_option (int): 可用选项。
            entity2service (Dict[str, str]): 实体到服务的映射字典。
            required_resource (Dict[str, str]): 所需资源字典，同义词库id和停用词库id
            subject_id (str): 用户 ID。
            subject_type (str): 用户类型。
            roles (List[str]): 用户角色， 数据运营工程师、数据开发工程师、普通用户、数据管家、数据owner、应用开发者、系统管理员。
            af_editions (str): AF 版本。
        request: Request 对象。
        file_path (str): 指定配置文件路径，应为'search_config/config_search_resource.json' 或者'search_config/config_search_catalog.json'。
        data_type (str): AF版本标识符，'resource' 对应资源版，'datacatalog' 对应目录版。

    返回:
        output: 函数输出结果。初始化空output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    """

    # 搜索返回结果的数据结构还有"query_cuts" 列表
    # output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": [],"query_cuts": []}
    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    headers = {"Authorization": request.headers.get('Authorization')}
    query = search_params.query
    if not query:
        return output
    total_start_time = time.time()
    logger.info(
        f'INPUT：\nkg_id: {search_params.kg_id}\nquery: {search_params.query}\nlimit: {search_params.limit}\nrequired_resource: {search_params.required_resource}\n')
    logger.info(
        f'INPUT：entity2service: {search_params.entity2service}\nstopwords: {search_params.stopwords}\nstop_entities: {search_params.stop_entities}\nfilter: {search_params.filter}')

    # 获取图谱信息和向量化
    task_get_kgotl = asyncio.create_task(
        get_kgotl_dip(search_params=search_params, output=output, query=query, kgotl_config_file_path=file_path, graph_filter_params=GraphFilterParamsModel()))

    task_query_m3e = asyncio.create_task(query_m3e(query=query))
    # queries：同义词扩展后的多个衍生query组成的列表['上市公司股票信息'],
    # query_cuts：分词结果，同义词，是否停止词[{'source': '上市', 'synonym': [], 'is_stopword': False}, {'source': '公司股票', 'synonym': [], 'is_stopword': False}, {'source': '信息', 'synonym': [], 'is_stopword': False}]
    # all_syns：[]
    # entity_types,所有实体类的详细信息，比如主题域分组实体类，{'domain': {'entity_id': 'entity_id8bbf06bb-b3c8-4c5d-bba6-72273baeb440', 'name': 'domain',
        # 'description': '', 'alias': '主题域分组', 'synonym': [], 'default_tag': 'domainname',
        # 'properties_index': ['domainname'], 'search_prop': 'domainname', 'primary_key': ['domainid'],
        # 'vector_generation': ['domainname'], 'properties': [{'name': 'domainid', 'description': '',
        # 'alias': '主题域分组id', 'data_type': 'string'}, {'name': 'domainname', 'description': '', 'alias': '主题域分组名称',
        # 'data_type': 'string'}, {'name': 'prefixname', 'description': '', 'alias': 'prefixname', 'data_type': 'string'}],
        # 'x': 713.6353774815489, 'y': 620.3576388888889, 'icon': 'empty', 'shape': 'circle', 'size': '0.5x',
        # 'fill_color': 'rgba(145,192,115,1)', 'stroke_color': 'rgba(145,192,115,1)', 'text_color': 'rgba(0,0,0,1)',
        # 'text_position': 'top', 'text_width': 15, 'index_default_switch': False, 'text_type': 'adaptive',
        # 'source_type': 'manual', 'model': '', 'task_id': '', 'icon_color': '#ffffff', 'colour': 'rgba(145,192,115,1)'}}
    #  properties_alias,图谱本体中 每个实体类字段的别名（显示名）字典{'domain': {'domainid': '主题域分组id', 'domainname': '主题域分组名称', 'prefixname': 'prefixname'}, 'subdomain': {'subdomainid': '主题域id', 'subdomainname': '主题域名称', 'prefixname': 'prefixname'}}
    # properties_types,图谱本体中 每个实体类字段的数据类型字典{'domain': {'domainid': 'string', 'domainname': 'string', 'prefixname': 'string'}, 'subdomain': {'subdomainid': 'string', 'subdomainname': 'string', 'prefixname': 'string'}}
    # entity2prop,每个实体类的默认显示属性字段， 形如 entity2prop：{'domain': 'domainname', 'subdomain': 'subdomainname',
        # 'customized_category': 'name', 'customized_category_node': 'name', 'data_catalog_column': 'business_name',
        # 'response_field': 'cn_name', 'service': 'name', 'data_explore_report': 'explore_result_valule',
        # 'form_view_field': 'business_name', 'datasource': 'datasourcename', 'metadataschema': 'metadataschemaname',
        # 'form_view': 'business_name', 'department': 'departmentname', 'info_system': 'infosystemname',
        # 'catalogtag': 'catalogtagname', 'datacatalog': 'datacatalogname'}
    # vector_index_filed,图谱本体中每个实体类向量索引的字段列表{'info_system': ['info_system_description', 'infosystemname'], 'catalogtag': ['catalogtagname'], 'datacatalog': ['description_name', 'datacatalogname']}
    # data_params 时相关参数， 比如搜索结果上限、实体权重、同义词actrie对象、停用词列表对象等
    # graph_filter_params 是筛选项， 调用 get_kgotl( )时，传入的时初始化的筛选项， 在调用时，会更新筛选项
    (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop, vector_index_filed,
     data_params, graph_filter_params) = await task_get_kgotl
    logger.info(f"同义词扩展后的queries：{queries}")
    logger.info(f"query_cuts：{query_cuts}")
    logger.info(f"all_syns：{all_syns}")
    # logger.debug(f"entity_types：{entity_types}")
    logger.info(f"entity2prop：{entity2prop}")
    # logger.debug(f"data_params：{data_params}")
    # logger.debug(f"graph_filter_params：{graph_filter_params}")
    query_embedding, m_status = await task_query_m3e

    # 关键词搜索和向量搜索
    min_score = float(settings.MIN_SCORE)

    (hits_id_lexical, vid_hits_lexical, hits_lexical,
     drop_indices_lexical), (hits_vec, drop_indices_vec) = await asyncio.gather(
        lexical_search_dip(
            query=query,
            queries=queries,
            all_syns=all_syns,
            entity_types=entity_types,
            data_params=data_params,
            search_params=search_params
        ),
        vector_search_dip(
            embeddings=query_embedding,
            m_status=m_status,
            vector_index_filed=vector_index_filed,
            entity_types=entity_types,
            data_params=data_params,
            min_score=min_score,
            search_params=search_params
        )
    )
    # task_lexical_search = asyncio.create_task(
    #     lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
    #                       data_params=data_params,
    #                       search_params=search_params))
    #
    # task_vector_search = asyncio.create_task(
    #     vector_search(embeddings=query_embedding, m_status=m_status, vector_index_filed=vector_index_filed,
    #                   entity_types=entity_types, data_params=data_params, min_score=min_score, search_params=search_params))
    # # hits_key_id, vid_hits_key, hits_key, drop_indices_key
    # hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical = await task_lexical_search
    # # hits_vec, drop_indices_vec
    # hits_vec, drop_indices_vec = await task_vector_search

    # 4 关键词搜索和向量搜索的搜索结果汇总,初步筛选和排序
    hits, drop_indices = await combine_rst_of_lexical_and_vector_search(
        drop_indices_lexical,
        drop_indices_vec,
        hits_vec,
        hits_id_lexical,
        hits_lexical,
        vid_hits_lexical)
    # 5 图分析服务部分
    vertices, hit_names, service_names, entities, subgraphs, text = await graph_search(
        data_type, hits,
        properties_alias, entity_types,
        search_params, request,
        graph_filter_params,
        data_params, search_configs)

    # drop_indices = drop_indices_key + drop_indices_vec
    # all_hits = []
    #
    # # 结果汇总
    # if hits_vec:
    #     for i, hit in enumerate(hits_vec):
    #         if hit["_id"] in hits_key_id:
    #             hit['vec_score'] = hit['_score'] / 2
    #             key_score = vid_hits_key[hit["_id"]]['_score']
    #             vid_hits_key[hit["_id"]]['_score'] = hit['vec_score'] + key_score
    #             all_hits.append(vid_hits_key[hit["_id"]])
    #             vid_hits_key.pop(hit["_id"])
    #         else:
    #             hit['_score'] = hit['_score'] / 2
    #             hit['max_score_prop'] = {
    #                 "prop": '',
    #                 "value": '',
    #                 "keys": []
    #             }
    #             all_hits.append(hit)
    #     for value in vid_hits_key.values():
    #         all_hits.append(value)
    # else:
    #     all_hits = hits_key
    #
    # # 删除stop_entity_infos
    # for i in all_hits[:]:
    #     if i['_id'] in set(drop_indices):
    #         all_hits.remove(i)
    # logger.info(f"OpenSearch总召回数量：{len(all_hits)}")
    #
    # # 筛选排序
    # hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    # hits = [h for h in hits if h['_score'] >= 0]
    #
    # # search_configs = get_search_configs()
    # # 图分析服务部分
    # # from app.retriever import CognitiveSearch
    # from app.cores.cognitive_assistant.qa_model import AfEdition
    # # cognitivesearch = CognitiveSearch()
    # start_time = time.time()
    # # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    # if data_type == 'form_view':
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params)
    # else:
    #     # 搜索列表的inputs中没有af_editions字段， 在qa的inputs中有， 如果qa走到保底策略， 会把af_editions带入
    #     # 也可以根据 data——type来判断
    #     logger.info(f"search_params.af_editions = {search_params.af_editions}")
    #     logger.info(f"data_type = {data_type}")
    #     re_limit_qa = int(search_configs.sailor_search_qa_cites_num_limit)
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(hits=hits,
    #                                                                                                  properties_alias=properties_alias,
    #                                                                                                  entity_types=entity_types,
    #                                                                                                  search_params=search_params,
    #                                                                                                  request=request,
    #                                                                                                  source_type=data_type,
    #                                                                                                  graph_filter_params=graph_filter_params,
    #                                                                                                  data_params=data_params,
    #                                                                                                  re_limit=re_limit_qa,
    #                                                                                                  search_configs=search_configs)
    #     # if (data_type=="resource" and search_configs.direct_qa == 'false'
    #     #         and search_configs.sailor_search_if_auth_in_find_data_qa == '0'
    #     #         and search_configs.sailor_search_if_history_qa_enhance == '0'
    #     #         and search_configs.sailor_search_if_kecc == '1'):
    #     #
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_no_auth(hits=hits,
    #     #                                                                                                  properties_alias=properties_alias,
    #     #                                                                                                  entity_types=entity_types,
    #     #                                                                                                  search_params=search_params,
    #     #                                                                                                  request=request,
    #     #                                                                                                  source_type=data_type,
    #     #                                                                                                  graph_filter_params=graph_filter_params,
    #     #                                                                                                  data_params=data_params,
    #     #                                                                                                  re_limit=re_limit_qa)
    #     # else:
    #     #     # text=''
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis(hits=hits,
    #     #                                                                                          properties_alias=properties_alias,
    #     #                                                                                          entity_types=entity_types,
    #     #                                                                                          search_params=search_params,
    #     #                                                                                          request=request,
    #     #                                                                                          source_type=data_type,
    #     #                                                                                          graph_filter_params=graph_filter_params,
    #     #                                                                                          data_params=data_params,
    #     #                                                                                          re_limit=re_limit_qa)
    #
    # end_time = time.time()
    # graph_analysis_final_score_time = end_time - start_time
    # logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")

    # #增加共享申请图标
    # catalog_ids=[]
    # if  data_type=='datacatalog':
    #     for i in entities:
    #         catalog_id=find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
    #                               value_to_find='datacatalogid')
    #         catalog_ids.append(catalog_id)
    #         res= await find_number_api.get_shared_declaration_status(catalog_ids,headers)
    #         i["shared_declaration"]=res
    output['entities'] = entities
    output['count'] = len(entities)
    output['answer'] = text
    output['subgraphs'] = subgraphs
    output['query_cuts'] = query_cuts
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    return output

"""认知搜索——数据资源版"""


async def run_func_resource(request, search_params,search_configs):
    '''数据资源版认知搜索列表的算法入口函数'''
    # file_path是本地配置文件路径
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_resource.json")

    output = await run_func(
        search_params=search_params,
        request=request,
        file_path=resource_config_path,
        data_type='resource',
        search_configs=search_configs
    )
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output

# 分析问答型搜索的托底算法
async def run_func_resource_for_qa(request, search_params,search_configs):
    '''数据资源版认知搜索列表的算法入口函数'''
    # file_path是本地配置文件路径
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_resource.json")

    output = await run_func_for_qa_dip(
        search_params=search_params,
        request=request,
        file_path=resource_config_path,
        data_type='resource',
        search_configs=search_configs
    )
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    logger.info(f'in run_func_resource_for_qa,output={output}')
    return output

async def run_func_resource_for_qa_dip(request, search_params,search_configs):
    '''数据资源版认知搜索列表的算法入口函数'''
    # file_path是本地配置文件路径
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_resource.json")

    output = await run_func_for_qa_dip_new(
        search_params=search_params,
        request=request,
        file_path=resource_config_path,
        data_type='resource',
        search_configs=search_configs
    )
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    logger.info(f'in run_func_resource_for_qa,output={output}')
    return output

"""认知搜索——数据目录版"""

async def run_func_catalog(request, search_params,search_configs):
    '''数据目录版认知搜索列表的算法入口函数'''
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_catalog.json")
    output = await run_func(
        search_params=search_params,
        request=request,
        file_path=catalog_config_path,
        data_type='datacatalog',
        search_configs=search_configs
    )
    logger.debug(f"处理前搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    for i in output["entities"]:
        try:
            # https://confluence.xxx.cn/pages/viewpage.action?pageId=236564495
            # resource_type是挂接的数据资源类型1逻辑视图2接口
            # "is_permissions"：表示目前资源的权限，（available_option字段，传参为1时返回），"1"代表有权限，“0”代表无权限
            # available_option字段：0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
            # 如果数据目录挂接的数据资源类型是“逻辑视图”，那么就置为无权限
            if find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
                                     value_to_find='resource_type') == '2':
                i["is_permissions"] = '0'
        except:
            pass
    logger.debug(f"处理后搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output

# 分析问答型搜索的托底算法
async def run_func_catalog_for_qa(request, search_params,search_configs):
    '''数据目录版认知搜索列表的算法入口函数'''
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_catalog.json")
    output = await run_func_for_qa_dip(
        search_params=search_params,
        request=request,
        file_path=catalog_config_path,
        data_type='datacatalog',
        search_configs=search_configs
    )
    logger.debug(f"处理前搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    for i in output["entities"]:
        try:
            # https://confluence.xxx.cn/pages/viewpage.action?pageId=236564495
            # resource_type是挂接的数据资源类型1逻辑视图2接口
            # "is_permissions"：表示目前资源的权限，（available_option字段，传参为1时返回），"1"代表有权限，“0”代表无权限
            # available_option字段：0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
            # 如果数据目录挂接的数据资源类型是“逻辑视图”，那么就置为无权限
            if find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
                                     value_to_find='resource_type') == '2':
                i["is_permissions"] = '0'
        except:
            pass
    logger.debug(f"处理后搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output

async def run_func_catalog_for_qa_dip(request, search_params,search_configs):
    '''数据目录版认知搜索列表的算法入口函数'''
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_catalog.json")
    output = await run_func_for_qa_dip_new(
        search_params=search_params,
        request=request,
        file_path=catalog_config_path,
        data_type='datacatalog',
        search_configs=search_configs
    )
    logger.debug(f"处理前搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    for i in output["entities"]:
        try:
            # https://confluence.xxx.cn/pages/viewpage.action?pageId=236564495
            # resource_type是挂接的数据资源类型1逻辑视图2接口
            # "is_permissions"：表示目前资源的权限，（available_option字段，传参为1时返回），"1"代表有权限，“0”代表无权限
            # available_option字段：0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
            # 如果数据目录挂接的数据资源类型是“逻辑视图”，那么就置为无权限
            if find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
                                     value_to_find='resource_type') == '2':
                i["is_permissions"] = '0'
        except:
            pass
    logger.debug(f"处理后搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    logger.info('--------------认知搜索最终召回的资源-----------------')
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"]
    )
    logger.info(f"\n{log_content}")
    # for i in output["entities"]:
    #     logger.debug(i['entity']["id"], i['entity']["default_property"]["value"])
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output

# 分析问答型搜索增加关键词搜索和关联搜索能力
# query 向量化单独进行， 这里作为入参
async def cognitive_search_for_qa(request, search_params, file_path, data_type, query_embedding, m_status,
                                  search_configs):
    """
    分析问答型搜索主函数，cognitive_search_resource_for_qa和 cognitive_search_catalog_for_qa都调用这个函数，
    根据资源版或目录版传入的不同参数来执行

    参数:
        search_params (dict): API 入参的 body 部分。包括：
            query (str): 查询字符串。
            limit (int): 限制返回结果的数量。
            stopwords (List[str]): 停用词列表。
            stop_entities (List[str]): 停用实体列表。
            filter (Dict[str, Any]): 过滤器字典。
            ad_appid (str): AD 应用程序 ID。
            kg_id (int): 知识图谱 ID。
            available_option (int): 可用选项。
            entity2service (Dict[str, str]): 实体到服务的映射字典。
            required_resource (Dict[str, str]): 所需资源字典，同义词库id和停用词库id
            subject_id (str): 用户 ID。
            subject_type (str): 用户类型。
            roles (List[str]): 用户角色， 数据运营工程师、数据开发工程师、普通用户、数据管家、数据owner、应用开发者、系统管理员。
            af_editions (str): AF 版本。
        request: Request 对象。
        file_path (str): 指定配置文件路径，应为'search_config/config_search_resource.json' 或者'search_config/config_search_catalog.json'。
        data_type (str): AF版本标识符，'resource' 对应资源版，'datacatalog' 对应目录版。

    返回:
        output: 函数输出结果。初始化空output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
    """

    # 搜索返回结果的数据结构还有"query_cuts" 列表
    headers = {"Authorization": request.headers.get('Authorization')}

    output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": [], "query_cuts": []}
    query = search_params.query
    total_time_cost = 0
    all_hits, drop_indices = [], []

    if not search_params.query:
        return output, headers, total_time_cost, all_hits, drop_indices

    total_start_time = time.time()
    logger.info(dedent(f"""
        AF版本是：{data_type}， search_params：
        
        kg_id: {search_params.kg_id}
        query: {search_params.query}
        limit: {search_params.limit} 
        required_resource: {search_params.required_resource}
        entity2service: {search_params.entity2service}
        stopwords: {search_params.stopwords}
        stop_entities: {search_params.stop_entities}
        filter: {search_params.filter}
        """).strip())

    # 1 获取图谱信息,分词，同义词扩展
    (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop, vector_index_filed,
     data_params, graph_filter_params) = await get_kgotl_dip(
        search_params=search_params,
        output=output,
        query=query,
        kgotl_config_file_path=file_path,
        graph_filter_params=GraphFilterParamsModel()
    )
    # queries：同义词扩展后的多个衍生query组成的列表 ['上市公司股票信息'],
    # query_cuts：分词结果，同义词，是否停止词
        #   [
        #       {'source': '上市', 'synonym': [], 'is_stopword': False},
        #       {'source': '公司股票', 'synonym': [], 'is_stopword': False},
        #       {'source': '信息', 'synonym': [], 'is_stopword': False}
        #   ]
    # all_syns：[]
    # entity_types,所有实体类的详细信息，比如主题域分组实体类:
        # {'domain': {'entity_id': 'entity_id8bbf06bb-b3c8-4c5d-bba6-72273baeb440', 'name': 'domain',
        # 'description': '', 'alias': '主题域分组', 'synonym': [], 'default_tag': 'domainname',
        # 'properties_index': ['domainname'], 'search_prop': 'domainname', 'primary_key': ['domainid'],
        # 'vector_generation': ['domainname'], 'properties': [{'name': 'domainid', 'description': '',
        # 'alias': '主题域分组id', 'data_type': 'string'}, {'name': 'domainname', 'description': '', 'alias': '主题域分组名称',
        # 'data_type': 'string'}, {'name': 'prefixname', 'description': '', 'alias': 'prefixname', 'data_type': 'string'}],
        # 'x': 713.6353774815489, 'y': 620.3576388888889, 'icon': 'empty', 'shape': 'circle', 'size': '0.5x',
        # 'fill_color': 'rgba(145,192,115,1)', 'stroke_color': 'rgba(145,192,115,1)', 'text_color': 'rgba(0,0,0,1)',
        # 'text_position': 'top', 'text_width': 15, 'index_default_switch': False, 'text_type': 'adaptive',
        # 'source_type': 'manual', 'model': '', 'task_id': '', 'icon_color': '#ffffff', 'colour': 'rgba(145,192,115,1)'}}
    # properties_alias,图谱本体中 每个实体类字段的别名（显示名）字典{'domain': {'domainid': '主题域分组id', 'domainname': '主题域分组名称', 'prefixname': 'prefixname'}, 'subdomain': {'subdomainid': '主题域id', 'subdomainname': '主题域名称', 'prefixname': 'prefixname'}}
    # properties_types,图谱本体中 每个实体类字段的数据类型字典{'domain': {'domainid': 'string', 'domainname': 'string', 'prefixname': 'string'}, 'subdomain': {'subdomainid': 'string', 'subdomainname': 'string', 'prefixname': 'string'}}
    # entity2prop,每个实体类的默认显示属性字段， 形如 entity2prop：{'domain': 'domainname', 'subdomain': 'subdomainname',
        # 'customized_category': 'name', 'customized_category_node': 'name', 'data_catalog_column': 'business_name',
        # 'response_field': 'cn_name', 'service': 'name', 'data_explore_report': 'explore_result_valule',
        # 'form_view_field': 'business_name', 'datasource': 'datasourcename', 'metadataschema': 'metadataschemaname',
        # 'form_view': 'business_name', 'department': 'departmentname', 'info_system': 'infosystemname',
        # 'catalogtag': 'catalogtagname', 'datacatalog': 'datacatalogname'}
    # vector_index_filed,图谱本体中每个实体类向量索引的字段列表{'info_system': ['info_system_description', 'infosystemname'], 'catalogtag': ['catalogtagname'], 'datacatalog': ['description_name', 'datacatalogname']}
    # data_params 是相关参数， 比如搜索结果上限、实体权重、同义词actrie对象、停用词列表对象等
    # graph_filter_params 是筛选项， 调用 get_kgotl( )时传入的是初始化的筛选项， 在调用时，会更新筛选项

    logger.info(f"同义词扩展后的queries：{queries}")
    logger.info(f"query_cuts：{query_cuts}")
    logger.info(f"all_syns：{all_syns}")
    # logger.debug(f"entity_types：{entity_types}")
    logger.info(f"entity2prop：{entity2prop}")  # 实体类的默认显示属性字段
    # logger.debug(f"data_params：{data_params}")
    logger.info(f"graph_filter_params：\n{graph_filter_params}")

    # 2 关键词搜索
    # 3 向量搜索
    min_score = safe_str_to_float(search_configs.sailor_vec_min_score_analysis_search)

    (hits_id_lexical, vid_hits_lexical, hits_lexical,
     drop_indices_lexical), (hits_vec, drop_indices_vec) = await asyncio.gather(
        lexical_search(query=query, queries=queries, all_syns=all_syns, entity_types=entity_types,
                       data_params=data_params, search_params=search_params),
        vector_search(embeddings=query_embedding, m_status=m_status, vector_index_filed=vector_index_filed,
                      entity_types=entity_types, data_params=data_params, min_score=min_score,
                      search_params=search_params)
    )

    # 关键词搜索, 原名 key 指 keyword
    # hits_key_id, vid_hits_key, hits_key, drop_indices_key
    # hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical = await task_lexical_search
    # 向量搜索
    # hits_vec, drop_indices_vec = await task_vector_search

    # 4 关键词搜索和向量搜索的搜索结果汇总, 按照分数排序后， 初步筛选出分数大于零的结果
    hits, drop_indices = await combine_rst_of_lexical_and_vector_search(
        drop_indices_lexical=drop_indices_lexical,
        drop_indices_vec=drop_indices_vec,
        hits_vec=hits_vec,
        hits_id_lexical=hits_id_lexical,
        hits_lexical=hits_lexical,
        vid_hits_lexical=vid_hits_lexical)
    # 5 图分析服务部分
    vertices, hit_names, service_names, entities, subgraphs, text = await graph_search(
        data_type=data_type,
        hits=hits,
        properties_alias=properties_alias,
        entity_types=entity_types,
        search_params=search_params,
        request=request,
        graph_filter_params=graph_filter_params,
        data_params=data_params,
        search_configs=search_configs)
    # drop_indices = drop_indices_lexical + drop_indices_vec
    # all_hits = []
    #
    # # 4 关键词搜索和向量搜索的搜索结果汇总,初步筛选和排序
    # if hits_vec:
    #     for i, hit in enumerate(hits_vec):
    #         # 向量搜索结果加入all_hits，分数取决于其是否和关键词搜索重合：
    #         if hit["_id"] in hits_id_lexical:
    #             # 如果向量搜索结果的id在关键词搜索结果中存在，则将向量搜索结果的分数加到关键词搜索结果的分数中
    #             hit['vec_score'] = hit['_score'] / 2
    #             lexical_score = vid_hits_lexical[hit["_id"]]['_score']
    #             # 将向量搜索的分数折半后和关键词搜索的分数相加，作为新的关键词搜索分数
    #             vid_hits_lexical[hit["_id"]]['_score'] = hit['vec_score'] + lexical_score
    #             all_hits.append(vid_hits_lexical[hit["_id"]])
    #             vid_hits_lexical.pop(hit["_id"])
    #         else:
    #             # 如果向量搜索结果的id不在关键词搜索结果中，分数折半
    #             hit['_score'] = hit['_score'] / 2
    #             hit['max_score_prop'] = {
    #                 "prop": '',
    #                 "value": '',
    #                 "keys": []
    #             }
    #             all_hits.append(hit)
    #     for value in vid_hits_lexical.values():  # 关键词搜索结果中，向量搜索结果中没有的，加入 all_hits
    #         all_hits.append(value)
    # else:
    #     all_hits = hits_lexical
    # # logger.debug(f'before drop_indices: (all_hits) = {all_hits}')
    # # 删除stop_entity_infos
    # for i in all_hits[:]:
    #     if i['_id'] in set(drop_indices):
    #         all_hits.remove(i)
    # logger.info(f"OpenSearch总召回数量：{len(all_hits)}")
    #
    # # 初步筛选和排序
    # hits = sorted(all_hits, key=lambda x: x['_score'], reverse=True)
    # hits = [h for h in hits if h['_score'] >= 0]

    # 5 图分析服务部分
    # from app.retriever import CognitiveSearch
    # from app.cores.cognitive_assistant.qa_model import AfEdition
    # cognitivesearch = CognitiveSearch()
    # start_time = time.time()
    # # data_type的值是'form_view'是场景分析版本， 值是'resource'是数据资源版， 值是'datacatalog'是数据目录版
    # # 场景分析版本
    # if data_type == 'form_view':
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_formview(
    #         hits=hits,
    #         properties_alias=properties_alias,
    #         entity_types=entity_types,
    #         search_params=search_params,
    #         request=request,
    #         source_type=data_type,
    #         graph_filter_params=graph_filter_params,
    #         data_params=data_params
    #     )
    # # 非场景分析版本
    # else:
    #     # 搜索列表的inputs中没有af_editions字段， 在qa的inputs中有， 如果qa走到保底策略， 会把af_editions带入
    #     # 也可以根据 data——type来判断
    #     logger.info(f"search_params.af_editions = {search_params.af_editions}")
    #     logger.info(f"data_type = {data_type}")
    #     re_limit_qa = int(search_configs.sailor_search_qa_cites_num_limit)
    #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_general(
    #         hits=hits,
    #         properties_alias=properties_alias,
    #         entity_types=entity_types,
    #         search_params=search_params,
    #         request=request,
    #         source_type=data_type,
    #         graph_filter_params=graph_filter_params,
    #         data_params=data_params,
    #         re_limit=re_limit_qa,
    #         search_configs=search_configs
    #     )
    #     # if (data_type == "resource" and search_configs.direct_qa == 'false'
    #     #         and search_configs.sailor_search_if_auth_in_find_data_qa == '0'
    #     #         and search_configs.sailor_search_if_history_qa_enhance == '0'
    #     #         and search_configs.sailor_search_if_kecc == '1'):
    #     #     # logger.info(f"settings.IF_KECC = {settings.IF_KECC}")
    #     #     # logger.info(f"settings.IF_AUTH_IN_FIND_DATA_QA = {settings.IF_AUTH_IN_FIND_DATA_QA}")
    #     #     # if data_type=="resource" and settings.IF_KECC and not settings.IF_AUTH_IN_FIND_DATA_QA:
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis_no_auth(hits=hits,
    #     #                                                                                                  properties_alias=properties_alias,
    #     #                                                                                                  entity_types=entity_types,
    #     #                                                                                                  search_params=search_params,
    #     #                                                                                                  request=request,
    #     #                                                                                                  source_type=data_type,
    #     #                                                                                                  graph_filter_params=graph_filter_params,
    #     #                                                                                                  data_params=data_params,
    #     #                                                                                                  re_limit=re_limit_qa)
    #     # else:
    #     #     # text=''
    #     #     vertices, hit_names, service_names, entities, subgraphs, text = await graph_analysis(hits=hits,
    #     #                                                                                          properties_alias=properties_alias,
    #     #                                                                                          entity_types=entity_types,
    #     #                                                                                          search_params=search_params,
    #     #                                                                                          request=request,
    #     #                                                                                          source_type=data_type,
    #     #                                                                                          graph_filter_params=graph_filter_params,
    #     #                                                                                          data_params=data_params,
    #     #                                                                                          re_limit=re_limit_qa)
    #
    # end_time = time.time()
    # graph_analysis_final_score_time = end_time - start_time
    # logger.info(f"调用图分析，计算最终得分 耗时 {graph_analysis_final_score_time} 秒")

    # #增加共享申请图标
    # catalog_ids=[]
    # if  data_type=='datacatalog':
    #     for i in entities:
    #         catalog_id=find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
    #                               value_to_find='datacatalogid')
    #         catalog_ids.append(catalog_id)
    #         res= await find_number_api.get_shared_declaration_status(catalog_ids,headers)
    #         i["shared_declaration"]=res
    # 召回的结果实体，
    # {
        # starts,
        # entity, 其中properties比hits的属性字段更丰富， 包括主题层级路径、部门层级路径
        # is_permissions:"1",
        # score:50
    # }
    # 6 组织数据，输出结果
    len_output = len(entities)
    output_updates = {
        'entities': entities,
        'count': len_output,
        'answer': text,
        'subgraphs': subgraphs,
        'query_cuts': query_cuts
    }
    output.update({k: v for k, v in output_updates.items() if v is not None})

    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f'cognitive_search_for_qa, 召回数量 = {len_output}')
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    # logger.debug(f'output=\n{output}')
    # logger.debug(f'all_hits=\n{all_hits}')
    # all_hits中包括 向量 vec， 需要过滤掉， 否则往后传的数据太多了
    # return output
    # logger.debug(f'before return after drop_indices: (all_hits) = {all_hits}')
    # 搜索列表的算法仅输出 output， 但是现在要在分析问答型搜索中使用搜索列表的算法，
    # 分析问答型搜索原来的处理逻辑中，需要这些输出变量，需要看看后续如何使用，如果是必要的，怎样输出
    # 认知搜索返回结果数量是通过图分析控制的， 反映在output数量上，需要按照output的数量m， 选取hits的前m个元素， 作为all_hits返回
    # return output, headers, total_time_cost, hits[:len_output], drop_indices
    # output['entities'] 是nebula中存储的数据结构， all_hits是opensearch中存储的数据结构，
    # 因为分析问答型搜索之前只用向量搜索，即只用opensearch搜索， 所以全部都是以 all_hits的数据结构做处理
    # 现在加入了关键词搜索和关联搜索图分析后， all_hits包含过多非中心点的实体，score也和最终output['entities'外层score不同
    # 后续需要对all_hits进行处理，否则会导致数据资源搜索结果错误

    return output, headers, total_time_cost, hits, drop_indices

# 数据资源版分析问答型搜索的数据资源搜索召回部分，
async def cognitive_search_resource_for_qa(request, search_params,query_embedding,m_status,search_configs):
    '''数据资源版认知搜索列表的算法入口函数'''
    # file_path是本地配置文件路径
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_resource.json")
    output, headers, total_time_cost, all_hits, drop_indices = await cognitive_search_for_qa(
        request=request,
        search_params=search_params,
        file_path=resource_config_path,
        data_type='resource',
        query_embedding=query_embedding,
        m_status=m_status,
        search_configs=search_configs
    )
    # log_content = "\n".join(
    #     f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
    #     for i in output["entities"])
    # logger.info(f"--------------认知搜索最终召回的资源-----------------\n{log_content}")
    # logger.info(f"--------------认知搜索最终召回的资源-----------------output=\n{output}")
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output, headers, total_time_cost, all_hits, drop_indices

# 还未使用
async def cognitive_search_catalog_for_qa(request, search_params,query_embedding,m_status,search_configs):
    '''数据目录版认知搜索列表的算法入口函数'''
    # base_path = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(base_path, "search_config/config_search_catalog.json")
    output, headers, total_time_cost, all_hits, drop_indices = await cognitive_search_for_qa(
        request=request,
        search_params=search_params,
        file_path=catalog_config_path,
        data_type='datacatalog',
        query_embedding=query_embedding,
        m_status=m_status,
        search_configs=search_configs
    )
    # logger.debug(f"处理前搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    for i in output["entities"]:
        try:
            # https://confluence.xxx.cn/pages/viewpage.action?pageId=236564495
            # resource_type是挂接的数据资源类型1逻辑视图2接口
            # "is_permissions"：表示目前资源的权限，（available_option字段，传参为1时返回），"1"代表有权限，“0”代表无权限
            # available_option字段：0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
            # 如果数据目录挂接的数据资源类型是“逻辑视图”，那么就置为无权限
            if find_idx_list_of_dict(props_lst=i["entity"]['properties'][0]['props'], key_to_find='name',
                                     value_to_find='resource_type') == '2':
                i["is_permissions"] = '0'
        except:
            pass
    # logger.debug(f"处理后搜索输出：{json.dumps(output, indent=4, ensure_ascii=False)}\n")
    log_content = "\n".join(
        f"{i['entity']['id']}  {i['entity']['default_property']['value']}"
        for i in output["entities"])
    logger.info(f"--------------认知搜索最终召回的资源-----------------\n{log_content}")
    # logger.debug(json.dumps(output, indent=4, ensure_ascii=False))
    return output, headers, total_time_cost, all_hits, drop_indices

