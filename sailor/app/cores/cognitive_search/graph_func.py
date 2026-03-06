import hashlib
import json, asyncio
from decimal import Decimal
from itertools import groupby
from dataclasses import dataclass
from textwrap import dedent

import app.cores.cognitive_search.prompts_config as prompts_config
# from app.cores.cognitive_search.sdk_utils import ad_builder_get_kg_info, ad_builder_get_kg_info_dip
from app.cores.cognitive_search.search_func import (custom_graph_call, find_value_list_of_dict, find_idx_list_of_dict,
                                                    init_lexicon, query_syn_expansion, init_lexicon_dip,
                                                    custom_graph_call_dip)
from app.cores.cognitive_search.vector_index_parser import parse_vector_index_fields,parse_all_entity_info
# from app.cores.cognitive_search.search_func import fetch
from app.cores.cognitive_search.search_config.get_params import get_search_configs
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.logs.logger import logger
from config import settings
# from anydata.services.engine_dip import CogEngineDIP

find_number_api = FindNumberAPI()
# engine_dip=CogEngineDIP()

def should_auth_check(search_configs):
    return  search_configs.sailor_search_if_auth_in_find_data_qa=="1"

# 整合 no_auth ，通过参数确定是否进行权限校验
async def graph_analysis_general(hits, properties_alias, entity_types,
                                 search_params, request, source_type, graph_filter_params, data_params, search_configs,
                                 re_limit=30):
    logger.info('executing graph_analysis_general')
    logger.info(f'search_params = {search_params.dict()}')
    logger.info(f'search_params.available_option = {search_params.available_option}')
    space_name = data_params['space_name']
    result_types = data_params['result_types']
    ad_appid = search_params.ad_appid
    hit_names = []
    # 调用图分析服务
    node2score = {}
    service_names = set()
    service_results = []
    path_source = []
    # 按实体类型，批量调用图分析
    end2start = {}
    vid2hit = {hit['_id']: hit for hit in hits}
    """新的调用方法"""
    data = {}
    # source_type = data_type,  值为'resource'是数据资源版， 值为'datacatalog'是数据目录版
    # 值为'form_view'是场景分析版本，有单独的图分析函数 graph_analysis_formview()
    if source_type == 'resource':
        logger.info('AF版本是数据资源版')
        data['resource_entity_search'] = []
        data['resource_graph_search'] = []
        graph_nebula_statement_template = {'resource_entity_search': prompts_config.resource_entity_search,
                                           'resource_graph_search': prompts_config.resource_graph_search}
    else:
        logger.info('AF版本是数据目录版')
        data['catalog_entity_search'] = []
        data['catalog_graph_search'] = []
        graph_nebula_statement_template = {'catalog_entity_search': prompts_config.catalog_entity_search,
                                           'catalog_graph_search': prompts_config.catalog_graph_search}
    # hits 是关键词搜索和向量搜索后得到的所有召回实体
    for hit in hits:

        if not hit:
            continue
        # tag是实体类型名
        # '_index'是AD图谱opensearch的索引名，命名规律是 space_name + '_' + tag
        tag = hit['_index'][len(space_name) + 1:]
        if tag not in data_params['indextag2tag']:
            service_results.append({})
            continue
        if tag == 'dataowner':
            continue
        # entity2service 是图谱关系边的权重
        cur_entity_service = data_params['entity2service'].get(tag, {})
        props = hit['_source']
        hit_names.append(props.get(entity_types[tag]['default_tag'], ''))
        hit['relation'] = cur_entity_service.get('relation', '')
        hit['type'] = entity_types[tag]['name']
        hit['type_alias'] = entity_types[tag]['alias']
        hit['name'] = props.get(entity_types[tag]['default_tag'], '')
        hit['max_score_prop']['alias'] = properties_alias[tag].get(hit['max_score_prop']['prop'], '')
        hit['service_weight'] = cur_entity_service.get('weight', 1.0)
        if 'resource' in result_types:
            if tag in result_types:
                data['resource_entity_search'].append(hit['_id'])
            else:
                data['resource_graph_search'].append(hit['_id'])
        else:
            if tag in result_types:
                data['catalog_entity_search'].append(hit['_id'])
            else:
                data['catalog_graph_search'].append(hit['_id'])
    # params_list = {}
    # 遍历结束， data 中包含了所有命中的中间节点实体和周围节点实体
    # graph_nebula_statements 用于保存变量替换为实际值以后的图查询语句graph_nebula_statements
    graph_nebula_statements = {}
    for key1, value in data.items():
        if value and key1.split('_')[1] == "entity":
            start_vids = str(set(value))
        elif value and key1.split('_')[1] == "graph":
            start_vids = str(set(value))[1:-1]
        elif not value and key1.split('_')[1] == "graph":
            start_vids = "'00000'"
        elif not value and key1.split('_')[1] == "entity":
            start_vids = "{'00000'}"
        else:
            start_vids = {}
        # params 是图查询语句模板中的变量
        params = {
            "start_vids": start_vids,
            'update_cycle': graph_filter_params.update_cycle,
            'shared_type': graph_filter_params.shared_type,
            'start_time': graph_filter_params.start_time,
            'end_time': graph_filter_params.end_time,
            "asset_type": graph_filter_params.asset_type,
            "department_id": graph_filter_params.department_id,
            "cate_node_id": graph_filter_params.cate_node_id,
            "resource_type": graph_filter_params.resource_type,
            "owner_id": graph_filter_params.owner_id,
            "info_system": graph_filter_params.info_system,
            "subject_id": graph_filter_params.subject_id,
            "online_status": graph_filter_params.online_status,
            "publish_status": graph_filter_params.publish_status
        }

        graph_nebula_statements[key1] = graph_nebula_statement_template[key1].format(**params)
    # logger.debug('图分析服务', params_list)
    # for statement in graph_nebula_statements.values():
    #     logger.debug(f"nebula graph statement：{statement}")

    # 并发执行多个图查询语句
    tasks = [custom_graph_call(kg_id=search_params.kg_id, ad_appid=ad_appid, params=params) for params in
             graph_nebula_statements.values()]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # logger.debug('#'*50)
    # logger.debug(f'图分析结果:\n{results}')
    # logger.debug('#' * 50)

    for s_res, key, value in zip(results, graph_nebula_statements.keys(), data.values()):
        # 图分析结果实体得分
        # nodes： 图查询后得到多条路径，遍历所有的路径，node 用来记录遍历过的路径终点（数据资产）

        if s_res is not None:
            if 'nodes' in s_res.keys() and s_res['nodes'] is None:
                nodes = []
            else:
                nodes = s_res.get('nodes', [])
            vid2node = {x['id']: x for x in nodes}
            node_id_set = set()
            if s_res['nodes'] == []:
                logger.info(f'图分析无结果')
                continue
            if s_res['edges'] == []:
                res_nodes = s_res.get('nodes')
            else:
                res_nodes = s_res.get('edges')
                for path in s_res['edges']:
                    if path["source"] in value:
                        path_source.append(path)
            for path in res_nodes:
                if "source" and "target" in path:
                    if path["source"] not in value:
                        start_vid = find_value_list_of_dict(
                            props_lst=path_source,
                            value_to_find=path["source"]
                        )
                        if start_vid not in value:
                            start_vid = find_value_list_of_dict(
                                props_lst=path_source,
                                value_to_find=start_vid
                            )
                            if start_vid not in value:
                                continue
                        end_vid = path["target"]
                        pn_id = path["target"]
                        start = vid2hit[start_vid]
                    else:
                        start = vid2hit[path["source"]]
                        start_vid = path["source"]
                        end_vid = path["target"]
                        pn_id = path["target"]
                else:
                    start_vid = path["id"]
                    start = vid2hit[start_vid]
                    end_vid = path["id"]
                    pn_id = path["id"]
                # 只看最后一个点
                # bug: nebula存在一端悬挂边，搜到了对应边，但是指向的终点不存在
                if pn_id in vid2node.keys():
                    node = vid2node[pn_id]
                else:
                    continue
                # 关键词搜索和向量搜索融合的分数
                os_score = start['_score']
                hit_key_words = start['max_score_prop']['keys']
                service_weight = start['service_weight']
                if result_types and node['class_name'] not in result_types:
                    # 终点不是数据资产
                    continue
                if pn_id in node_id_set and start_vid in end2start.get(pn_id, {}).get("starts", []):
                    # 重复的起点终点，不重复计算得分
                    continue
                node_id_set.add(pn_id)
                if end_vid not in end2start:
                    end2start[end_vid] = {"starts": [], "end": end_vid}
                end2start[end_vid]["starts"].append(start_vid)
                # https://confluence.xxx.cn/pages/viewpage.action?pageId=218768811
                # 如果第i个终点记录在node中
                # node_score ： 字典类型， max(起点的实体分数)
                # node_key : add（起点命中的关键词）
                if node['id'] in node2score:
                    node2score[node['id']]['score'] = max(node2score[node['id']]['score'], os_score * service_weight)
                    node2score[node['id']]['key'].update(hit_key_words)
                else:
                    node2score[node['id']] = {}
                    node2score[node['id']] = node
                    node2score[node['id']]['score'] = os_score * service_weight
                    node2score[node['id']]['key'] = set(hit_key_words)
            else:
                pass
        else:
            logger.info('图查询语句错误！')
    #  node2score中的score还没有排序
    # logger.info(f'node2score = {node2score}')
    # 对图分析结果进行排序
    # - 命中的关键词越多，排序越靠前
    # - 按照实体得分，需要将得分格式化为固定精度的小数，确保排序的一致性
    # - 以上分数相同， 再按字母顺序排序，作为次要排序条件
    # - 查找"资产类型"在属性列表中的位置索引，乘以-1实现降序排列（索引越小越靠前）
    # 注意：因为是按照以上算法综合排序的， 内层的score分数只是第二优先级的分数，所以要以外层的score为准（就是8、7、6.。。1这样的分数）
    # 所以内层的score看起来是乱序的
    vertices = sorted(list(node2score.values()), key=lambda x: (
        len(x['key']), Decimal(x['score']).quantize(Decimal('1.000000000000')), x['default_property']['value'],
        (-1) * int(find_idx_list_of_dict(
            props_lst=x['properties'][0]['props'],
            key_to_find='alias',
            value_to_find='资产类型'
        )
        )
    ), reverse=True
    )
    # logger.info(f'after sorted 图分析结果排序后 vertices = {vertices}')
    entities = []
    subgraphs = []
    # RE_limit = int(settings.Finally_NUM)
    RE_limit = re_limit
    logger.info(f'图分析最终返回前端数量限制 = {RE_limit}')
    vertices = vertices[:RE_limit]

    # 根据参数决定是否进行权限校验
    if should_auth_check(search_configs):
        headers = {"Authorization": request.headers.get('Authorization')}
        auth_id = await find_number_api.user_all_auth(
            headers=headers,
            subject_id=search_params.subject_id
        )

    for i, vertex in enumerate(vertices[:]):
        starts = []
        start_vids = end2start[vertex['id']]['starts']
        start_vids2 = list(set(start_vids))
        start_vids2.sort(key=start_vids.index)
        for start_vid in start_vids2:
            start = vid2hit[start_vid]
            starts.append({
                "relation": start['relation'],
                "class_name": start["type"],
                "name": start["name"],
                "hit": start["max_score_prop"],
                "alias": start["type_alias"]
            })
        if search_params.available_option == 0:
            entities.append({"starts": starts, "entity": vertex})
        else:
            assets = {}
            for prop in vertex['properties'][0]["props"]:
                if prop['name'] == "resourcename": assets["resourcename"] = prop["value"]
                if prop['name'] == "asset_type": assets["asset_type"] = prop["value"]
                if prop['name'] == "owner_id": assets["owner_id"] = prop["value"]
                if prop['name'] == "resourceid": assets["resourceid"] = prop["value"]
                if prop['name'] == "datacatalogid": assets["datacatalogid"] = prop["value"]
                if prop['name'] == "datacatalogname": assets["datacatalogname"] = prop["value"]
            if assets["asset_type"] in ["2", "3", "1", "4"]:
                # 根据参数决定是否进行权限校验
                if should_auth_check(search_configs):
                    res_suth = await find_number_api.sub_user_auth_state(
                        assets=assets,
                        params=search_params,
                        headers=headers,
                        auth_id=auth_id
                    )
                    is_permissions = "1" if res_suth == "allow" else "0"
                else:
                    is_permissions = "1"
            else:
                if should_auth_check(search_configs):
                    res_suth = "allow"
                is_permissions = "1"
            if search_params.available_option == 1:
                entities.append(
                    {"starts": starts, "entity": vertex, 'is_permissions': is_permissions})
            if search_params.available_option == 2:
                if should_auth_check(search_configs):
                    if res_suth == "allow":
                        entities.append(
                            {"starts": starts, "entity": vertex, 'is_permissions': "1"})
                    else:
                        vertices.remove(vertex)
                else:
                    entities.append(
                        {"starts": starts, "entity": vertex, 'is_permissions': "1"})
        subgraphs.append(end2start[vertex['id']])
    for i, ver in enumerate(vertices):
        ver['key'] = list(ver['key'])
    for j, ver in enumerate(entities):
        ver["score"] = len(vertices) - j
    hit_names = list(set([x for x in hit_names if x]))
    service_names = list(service_names)
    # logger.debug(f'vertices = {vertices}')
    # logger.debug(f'hit_names = {hit_names}')
    # logger.debug(f'service_names = {service_names}')
    # logger.debug(f'entities = {entities}')
    # logger.debug(f'subgraphs = {subgraphs}')
    # logger.info(f'in graph_analysis, vertices = {vertices}')
    # 可能存在 all_hits中金命中了周边节点， 但是通过图分析关联出了中间节点，所以 all_hits中没有这些数据资源， 而entities中存在，
    # 所以必须按照 entities 来做后续处理
    # logger.info(f'in graph_analysis_no_auth,vertices = {vertices}')
    # logger.info(f'in graph_analysis_no_auth,entities = {entities}')
    return vertices, hit_names, service_names, entities, subgraphs, ''


# # 资源版和目录版图分析整体流程（需要校验权限）
# # @async_timed()
# async def graph_analysis(hits, properties_alias, entity_types,
#                          search_params, request, source_type, graph_filter_params, data_params, re_limit=30):
#     space_name = data_params['space_name']
#     result_types = data_params['result_types']
#     ad_appid = search_params.ad_appid
#     hit_names = []
#     # 调用图分析服务
#     node2score = {}
#     service_names = set()
#     service_results = []
#     path_source = []
#     # 按实体类型，批量调用图分析
#     end2start = {}
#     vid2hit = {hit['_id']: hit for hit in hits}
#     """新的调用方法"""
#     data = {}
#     # source_type = data_type,  值为'resource'是数据资源版， 值为'datacatalog'是数据目录版
#     # 值为'form_view'是场景分析版本，有单独的图分析函数 graph_analysis_formview()
#     if source_type == 'resource':
#         logger.info('AF版本是数据资源版')
#         data['resource_entity_search'] = []
#         data['resource_graph_search'] = []
#         graph_nebula_statement_template = {'resource_entity_search': prompts_config.resource_entity_search,
#                                            'resource_graph_search': prompts_config.resource_graph_search}
#     else:
#         logger.info('AF版本是数据目录版')
#         data['catalog_entity_search'] = []
#         data['catalog_graph_search'] = []
#         graph_nebula_statement_template = {'catalog_entity_search': prompts_config.catalog_entity_search,
#                                            'catalog_graph_search': prompts_config.catalog_graph_search}
#     # hits 是关键词搜索和向量搜索后得到的所有召回实体
#     for hit in hits:
#
#         if not hit:
#             continue
#         # tag是实体类型名
#         # '_index'是AD图谱opensearch的索引名，命名规律是 space_name + '_' + tag
#         tag = hit['_index'][len(space_name) + 1:]
#         if tag not in data_params['indextag2tag']:
#             service_results.append({})
#             continue
#         if tag == 'dataowner':
#             continue
#         # entity2service 是图谱关系边的权重
#         cur_entity_service = data_params['entity2service'].get(tag, {})
#         props = hit['_source']
#         hit_names.append(props.get(entity_types[tag]['default_tag'], ''))
#         hit['relation'] = cur_entity_service.get('relation', '')
#         hit['type'] = entity_types[tag]['name']
#         hit['type_alias'] = entity_types[tag]['alias']
#         hit['name'] = props.get(entity_types[tag]['default_tag'], '')
#         hit['max_score_prop']['alias'] = properties_alias[tag].get(hit['max_score_prop']['prop'], '')
#         hit['service_weight'] = cur_entity_service.get('weight', 1.0)
#         if 'resource' in result_types:
#             if tag in result_types:
#                 data['resource_entity_search'].append(hit['_id'])
#             else:
#                 data['resource_graph_search'].append(hit['_id'])
#         else:
#             if tag in result_types:
#                 data['catalog_entity_search'].append(hit['_id'])
#             else:
#                 data['catalog_graph_search'].append(hit['_id'])
#     # params_list = {}
#     # 遍历结束， data 中包含了所有命中的中间节点实体和周围节点实体
#     # graph_nebula_statements 用于保存变量替换为实际值以后的图查询语句graph_nebula_statements
#     graph_nebula_statements = {}
#     for key1, value in data.items():
#         if value and key1.split('_')[1] == "entity":
#             start_vids = str(set(value))
#         elif value and key1.split('_')[1] == "graph":
#             start_vids = str(set(value))[1:-1]
#         elif not value and key1.split('_')[1] == "graph":
#             start_vids = "'00000'"
#         elif not value and key1.split('_')[1] == "entity":
#             start_vids = "{'00000'}"
#         else:
#             start_vids = {}
#         # params 是图查询语句模板中的变量
#         params = {
#             "start_vids": start_vids,
#             'update_cycle': graph_filter_params.update_cycle,
#             'shared_type': graph_filter_params.shared_type,
#             'start_time': graph_filter_params.start_time,
#             'end_time': graph_filter_params.end_time,
#             "asset_type": graph_filter_params.asset_type,
#             "department_id": graph_filter_params.department_id,
#             "cate_node_id": graph_filter_params.cate_node_id,
#             "resource_type": graph_filter_params.resource_type,
#             "owner_id": graph_filter_params.owner_id,
#             "info_system": graph_filter_params.info_system,
#             "subject_id": graph_filter_params.subject_id,
#             "online_status": graph_filter_params.online_status,
#             "publish_status": graph_filter_params.publish_status
#         }
#
#         graph_nebula_statements[key1] = graph_nebula_statement_template[key1].format(**params)
#     # logger.debug('图分析服务', params_list)
#     # for statement in graph_nebula_statements.values():
#     #     logger.debug(f"nebula graph statement：{statement}")
#
#     # 并发执行多个图查询语句
#     tasks = [custom_graph_call(kg_id=search_params.kg_id, ad_appid=ad_appid, params=params) for params in
#              graph_nebula_statements.values()]
#
#     results = await asyncio.gather(*tasks, return_exceptions=True)
#
#     # logger.debug('#'*50)
#     # logger.debug(f'图分析结果:\n{results}')
#     # logger.debug('#' * 50)
#
#     for s_res, key, value in zip(results, graph_nebula_statements.keys(), data.values()):
#         # 图分析结果实体得分
#         if s_res is not None:
#             if 'nodes' in s_res.keys() and s_res['nodes'] is None:
#                 nodes = []
#             else:
#                 nodes = s_res.get('nodes', [])
#             vid2node = {x['id']: x for x in nodes}
#             node_id_set = set()
#             if s_res['nodes'] == []:
#                 logger.info(f'图分析无结果')
#                 continue
#             if s_res['edges'] == []:
#                 res_nodes = s_res.get('nodes')
#             else:
#                 res_nodes = s_res.get('edges')
#                 for path in s_res['edges']:
#                     if path["source"] in value:
#                         path_source.append(path)
#             for path in res_nodes:
#                 if "source" and "target" in path:
#                     if path["source"] not in value:
#                         start_vid = find_value_list_of_dict(path_source, path["source"])
#                         if start_vid not in value:
#                             start_vid = find_value_list_of_dict(path_source, start_vid)
#                             if start_vid not in value:
#                                 continue
#                         end_vid = path["target"]
#                         pn_id = path["target"]
#                         start = vid2hit[start_vid]
#                     else:
#                         start = vid2hit[path["source"]]
#                         start_vid = path["source"]
#                         end_vid = path["target"]
#                         pn_id = path["target"]
#                 else:
#                     start_vid = path["id"]
#                     start = vid2hit[start_vid]
#                     end_vid = path["id"]
#                     pn_id = path["id"]
#                 # 只看最后一个点
#                 # bugnebula存在一端悬挂边，搜到了对应边，但是指向的终点不存在
#                 if pn_id in vid2node.keys():
#                     node = vid2node[pn_id]
#                 else:
#                     continue
#                 os_score = start['_score']
#                 hit_key_words = start['max_score_prop']['keys']
#                 service_weight = start['service_weight']
#                 if result_types and node['class_name'] not in result_types:
#                     # 终点不是数据资产
#                     continue
#                 if pn_id in node_id_set and start_vid in end2start.get(pn_id, {}).get("starts", []):
#                     # 重复的起点终点，不重复计算得分
#                     continue
#                 node_id_set.add(pn_id)
#                 if end_vid not in end2start:
#                     end2start[end_vid] = {"starts": [], "end": end_vid}
#                 end2start[end_vid]["starts"].append(start_vid)
#                 if node['id'] in node2score:
#                     node2score[node['id']]['score'] = max(node2score[node['id']]['score'], os_score * service_weight)
#                     node2score[node['id']]['key'].update(hit_key_words)
#                 else:
#                     node2score[node['id']] = {}
#                     node2score[node['id']] = node
#                     node2score[node['id']]['score'] = os_score * service_weight
#                     node2score[node['id']]['key'] = set(hit_key_words)
#             else:
#                 pass
#         else:
#             logger.info('图查询语句错误！')
#     vertices = sorted(list(node2score.values()), key=lambda x: (
#         len(x['key']), Decimal(x['score']).quantize(Decimal('1.000000000000')), x['default_property']['value'],
#         (-1) * int(find_idx_list_of_dict(props_lst=x['properties'][0]['props'], key_to_find='alias',
#                                          value_to_find='资产类型'))), reverse=True)
#     entities = []
#     subgraphs = []
#     # RE_limit = int(settings.Finally_NUM)
#     RE_limit = re_limit
#     logger.info(f'图分析最终返回前端数量限制 = {RE_limit}')
#     vertices = vertices[:RE_limit]
#     headers = {"Authorization": request.headers.get('Authorization')}
#     auth_id = await find_number_api.user_all_auth(headers, search_params.subject_id)
#     for i, vertex in enumerate(vertices[:]):
#         starts = []
#         start_vids = end2start[vertex['id']]['starts']
#         start_vids2 = list(set(start_vids))
#         start_vids2.sort(key=start_vids.index)
#         for start_vid in start_vids2:
#             start = vid2hit[start_vid]
#             starts.append({
#                 "relation": start['relation'],
#                 "class_name": start["type"],
#                 "name": start["name"],
#                 "hit": start["max_score_prop"],
#                 "alias": start["type_alias"]
#             })
#         if search_params.available_option == 0:
#             entities.append({"starts": starts, "entity": vertex})
#         else:
#             assets = {}
#             for prop in vertex['properties'][0]["props"]:
#                 if prop['name'] == "resourcename": assets["resourcename"] = prop["value"]
#                 if prop['name'] == "asset_type": assets["asset_type"] = prop["value"]
#                 if prop['name'] == "owner_id": assets["owner_id"] = prop["value"]
#                 if prop['name'] == "resourceid": assets["resourceid"] = prop["value"]
#                 if prop['name'] == "datacatalogid": assets["datacatalogid"] = prop["value"]
#                 if prop['name'] == "datacatalogname": assets["datacatalogname"] = prop["value"]
#             if assets["asset_type"] in ["2", "3", "1", "4"]:
#                 res_suth = await find_number_api.sub_user_auth_state(assets, search_params, headers, auth_id)
#                 is_permissions = "1" if res_suth == "allow" else "0"
#             else:
#                 res_suth = "allow"
#                 is_permissions = "1"
#             if search_params.available_option == 1:
#                 entities.append(
#                     {"starts": starts, "entity": vertex, 'is_permissions': is_permissions})
#             if search_params.available_option == 2:
#                 if res_suth == "allow":
#                     entities.append(
#                         {"starts": starts, "entity": vertex, 'is_permissions': "1"})
#                 else:
#                     vertices.remove(vertex)
#         subgraphs.append(end2start[vertex['id']])
#     for i, ver in enumerate(vertices):
#         ver['key'] = list(ver['key'])
#     for j, ver in enumerate(entities):
#         ver["score"] = len(vertices) - j
#     hit_names = list(set([x for x in hit_names if x]))
#     service_names = list(service_names)
#     # logger.debug(f'vertices = {vertices}')
#     # logger.debug(f'hit_names = {hit_names}')
#     # logger.debug(f'service_names = {service_names}')
#     # logger.debug(f'entities = {entities}')
#     # logger.debug(f'subgraphs = {subgraphs}')
#     # logger.info(f'in graph_analysis, vertices = {vertices}')
#     return vertices, hit_names, service_names, entities, subgraphs, ''

# # 资源版和目录版图分析整体流程（不需要校验权限）
# async def graph_analysis_no_auth(hits, properties_alias, entity_types,
#                          search_params, request, source_type, graph_filter_params, data_params,re_limit=30):
#     logger.info('executing graph_analysis_no_auth')
#     logger.info(f'search_params = {search_params.dict()}')
#     logger.info(f'search_params.available_option = {search_params.available_option}')
#     space_name = data_params['space_name']
#     result_types = data_params['result_types']
#     ad_appid = search_params.ad_appid
#     hit_names = []
#     # 调用图分析服务
#     node2score = {}
#     service_names = set()
#     service_results = []
#     path_source = []
#     # 按实体类型，批量调用图分析
#     end2start = {}
#     vid2hit = {hit['_id']: hit for hit in hits}
#     """新的调用方法"""
#     data = {}
#     if source_type == 'resource':
#         logger.info('AF版本是数据资源版')
#         data['resource_entity_search'] = []
#         data['resource_graph_search'] = []
#         graph_nebula_statement_template = {'resource_entity_search': prompts_config.resource_entity_search,
#                                            'resource_graph_search': prompts_config.resource_graph_search}
#     else:
#         logger.info('AF版本是数据目录版')
#         data['catalog_entity_search'] = []
#         data['catalog_graph_search'] = []
#         graph_nebula_statement_template = {'catalog_entity_search': prompts_config.catalog_entity_search,
#                                            'catalog_graph_search': prompts_config.catalog_graph_search}
#     for hit in hits:
#         if not hit:
#             continue
#         tag = hit['_index'][len(space_name) + 1:]
#         if tag not in data_params['indextag2tag']:
#             service_results.append({})
#             continue
#         if tag == 'dataowner':
#             continue
#         cur_entity_service = data_params['entity2service'].get(tag, {})
#         props = hit['_source']
#         hit_names.append(props.get(entity_types[tag]['default_tag'], ''))
#         hit['relation'] = cur_entity_service.get('relation', '')
#         hit['type'] = entity_types[tag]['name']
#         hit['type_alias'] = entity_types[tag]['alias']
#         hit['name'] = props.get(entity_types[tag]['default_tag'], '')
#         hit['max_score_prop']['alias'] = properties_alias[tag].get(hit['max_score_prop']['prop'], '')
#         hit['service_weight'] = cur_entity_service.get('weight', 1.0)
#         if 'resource' in result_types:
#             if tag in result_types:
#                 data['resource_entity_search'].append(hit['_id'])
#             else:
#                 data['resource_graph_search'].append(hit['_id'])
#         else:
#             if tag in result_types:
#                 data['catalog_entity_search'].append(hit['_id'])
#             else:
#                 data['catalog_graph_search'].append(hit['_id'])
#     # params_list = {}
#     graph_nebula_statements = {}
#     for key1, value in data.items():
#         if value and key1.split('_')[1] == "entity":
#             start_vids = str(set(value))
#         elif value and key1.split('_')[1] == "graph":
#             start_vids = str(set(value))[1:-1]
#         elif not value and key1.split('_')[1] == "graph":
#             start_vids = "'00000'"
#         elif not value and key1.split('_')[1] == "entity":
#             start_vids = "{'00000'}"
#         else:
#             start_vids = {}
#         params = {
#             "start_vids": start_vids,
#             'update_cycle': graph_filter_params.update_cycle,
#             'shared_type': graph_filter_params.shared_type,
#             'start_time': graph_filter_params.start_time,
#             'end_time': graph_filter_params.end_time,
#             "asset_type": graph_filter_params.asset_type,
#             "department_id": graph_filter_params.department_id,
#             "cate_node_id": graph_filter_params.cate_node_id,
#             "resource_type": graph_filter_params.resource_type,
#             "owner_id": graph_filter_params.owner_id,
#             "info_system": graph_filter_params.info_system,
#             "subject_id": graph_filter_params.subject_id,
#             "online_status": graph_filter_params.online_status,
#             "publish_status": graph_filter_params.publish_status
#         }
#
#         graph_nebula_statements[key1] = graph_nebula_statement_template[key1].format(**params)
#     # logger.debug('图分析服务', params_list)
#     # for statement in graph_nebula_statements.values():
#     #     logger.debug(f"statement：{statement}")
#
#     tasks = [custom_graph_call(kg_id=search_params.kg_id, ad_appid=ad_appid, params=params) for params in graph_nebula_statements.values()]
#
#     results = await asyncio.gather(*tasks, return_exceptions=True)
#
#     # logger.debug('#'*50)
#     # logger.debug(f'图分析结果:\n{results}')
#     # logger.debug('#' * 50)
#
#     for s_res, key, value in zip(results, graph_nebula_statements.keys(), data.values()):
#         # 图分析结果实体得分
#         # nodes： 图查询后得到多条路径，遍历所有的路径，node 用来记录遍历过的路径终点（数据资产）
#         if s_res is not None:
#             if 'nodes' in s_res.keys() and s_res['nodes'] is None:
#                 nodes = []
#             else:
#                 nodes = s_res.get('nodes', [])
#             vid2node = {x['id']: x for x in nodes}
#             node_id_set = set()
#             if s_res['nodes'] == []:
#                 logger.info(f'图分析无结果')
#                 continue
#             if s_res['edges'] == []:
#                 res_nodes = s_res.get('nodes')
#             else:
#                 res_nodes = s_res.get('edges')
#                 for path in s_res['edges']:
#                     if path["source"] in value:
#                         path_source.append(path)
#             for path in res_nodes:
#                 if "source" and "target" in path:
#                     if path["source"] not in value:
#                         start_vid = find_value_list_of_dict(path_source, path["source"])
#                         if start_vid not in value:
#                             start_vid = find_value_list_of_dict(path_source, start_vid)
#                             if start_vid not in value:
#                                 continue
#                         end_vid = path["target"]
#                         pn_id = path["target"]
#                         start = vid2hit[start_vid]
#                     else:
#                         start = vid2hit[path["source"]]
#                         start_vid = path["source"]
#                         end_vid = path["target"]
#                         pn_id = path["target"]
#                 else:
#                     start_vid = path["id"]
#                     start = vid2hit[start_vid]
#                     end_vid = path["id"]
#                     pn_id = path["id"]
#                 # 只看最后一个点
#                 # bug：nebula存在一端悬挂边，搜到了对应边，但是指向的终点不存在
#                 if pn_id in vid2node.keys():
#                     node = vid2node[pn_id]
#                 else:
#                     continue
#                 # 关键词搜索和向量搜索融合的分数
#                 os_score = start['_score']
#                 hit_key_words = start['max_score_prop']['keys']
#                 service_weight = start['service_weight']
#                 if result_types and node['class_name'] not in result_types:
#                     # 终点不是数据资产
#                     continue
#                 if pn_id in node_id_set and start_vid in end2start.get(pn_id, {}).get("starts", []):
#                     # 重复的起点终点，不重复计算得分
#                     continue
#                 node_id_set.add(pn_id)
#                 if end_vid not in end2start:
#                     end2start[end_vid] = {"starts": [], "end": end_vid}
#                 end2start[end_vid]["starts"].append(start_vid)
#                 # https://confluence.xxx.cn/pages/viewpage.action?pageId=218768811
#                 # 如果第i个终点记录在node中
#                 # node_score ： 字典类型， max(起点的实体分数)
#                 # node_key : add（起点命中的关键词）
#                 if node['id'] in node2score:
#                     node2score[node['id']]['score'] = max(node2score[node['id']]['score'], os_score * service_weight)
#                     node2score[node['id']]['key'].update(hit_key_words)
#                 else:
#                     # 如果第i个终点没有记录在node中
#                     # node_score ：字典类型 起点的实体分数
#                     # node_key : 起点命中的关键词
#                     node2score[node['id']] = {}
#                     node2score[node['id']] = node
#                     node2score[node['id']]['score'] = os_score * service_weight
#                     node2score[node['id']]['key'] = set(hit_key_words)
#             else:
#                 pass
#         else:
#             logger.info('图查询语句错误！')
#     #  node2score中的score还没有排序
#     # logger.info(f'node2score = {node2score}')
#     # 对图分析结果进行排序
#     # - 命中的关键词越多，排序越靠前
#     # - 按照实体得分，需要将得分格式化为固定精度的小数，确保排序的一致性
#     # - 以上分数相同， 再按字母顺序排序，作为次要排序条件
#     # - 查找"资产类型"在属性列表中的位置索引，乘以-1实现降序排列（索引越小越靠前）
#     # 注意：因为是按照以上算法综合排序的， 内层的score分数只是第二优先级的分数，所以要以外层的score为准（就是8、7、6.。。1这样的分数）
#     # 所以内层的score看起来是乱序的
#     vertices = sorted(list(node2score.values()), key=lambda x: (
#         len(x['key']), Decimal(x['score']).quantize(Decimal('1.000000000000')), x['default_property']['value'],
#         (-1) * int(find_idx_list_of_dict(props_lst=x['properties'][0]['props'], key_to_find='alias',
#                                          value_to_find='资产类型'))), reverse=True)
#     # logger.info(f'after sorted 图分析结果排序后 vertices = {vertices}')
#     entities = []
#     subgraphs = []
#     # RE_limit = int(settings.Finally_NUM)
#     RE_limit = re_limit
#     logger.info(f'图分析最终返回前端数量限制 = {RE_limit}')
#     vertices = vertices[:RE_limit]
#     # headers = {"Authorization": request.headers.get('Authorization')}
#     # auth_id = await find_number_api.user_all_auth(headers, search_params.subject_id)
#     for i, vertex in enumerate(vertices[:]):
#         starts = []
#         start_vids = end2start[vertex['id']]['starts']
#         start_vids2 = list(set(start_vids))
#         start_vids2.sort(key=start_vids.index)
#         for start_vid in start_vids2:
#             start = vid2hit[start_vid]
#             starts.append({
#                 "relation": start['relation'],
#                 "class_name": start["type"],
#                 "name": start["name"],
#                 "hit": start["max_score_prop"],
#                 "alias": start["type_alias"]
#             })
#         if search_params.available_option == 0:
#             entities.append({"starts": starts, "entity": vertex})
#         else:
#             assets = {}
#             for prop in vertex['properties'][0]["props"]:
#                 if prop['name'] == "resourcename": assets["resourcename"] = prop["value"]
#                 if prop['name'] == "asset_type": assets["asset_type"] = prop["value"]
#                 if prop['name'] == "owner_id": assets["owner_id"] = prop["value"]
#                 if prop['name'] == "resourceid": assets["resourceid"] = prop["value"]
#                 if prop['name'] == "datacatalogid": assets["datacatalogid"] = prop["value"]
#                 if prop['name'] == "datacatalogname": assets["datacatalogname"] = prop["value"]
#             if assets["asset_type"] in ["2", "3", "1", "4"]:
#                 # res_suth = await find_number_api.sub_user_auth_state(assets, search_params, headers, auth_id)
#                 # is_permissions = "1" if res_suth == "allow" else "0"
#                 is_permissions = "1"
#             else:
#                 # res_suth = "allow"
#                 is_permissions = "1"
#             if search_params.available_option == 1:
#                 entities.append(
#                     {"starts": starts, "entity": vertex, 'is_permissions': is_permissions})
#             if search_params.available_option == 2:
#                 entities.append(
#                     {"starts": starts, "entity": vertex, 'is_permissions': "1"})
#                 # if res_suth == "allow":
#                 #     entities.append(
#                 #         {"starts": starts, "entity": vertex, 'is_permissions': "1"})
#                 # else:
#                 #     vertices.remove(vertex)
#         subgraphs.append(end2start[vertex['id']])
#     for i, ver in enumerate(vertices):
#         ver['key'] = list(ver['key'])
#     for j, ver in enumerate(entities):
#         ver["score"] = len(vertices) - j
#     hit_names = list(set([x for x in hit_names if x]))
#     service_names = list(service_names)
#     # 可能存在 all_hits中金命中了周边节点， 但是通过图分析关联出了中间节点，所以 all_hits中没有这些数据资源， 而entities中存在，
#     # 所以必须按照 entities 来做后续处理
#     # logger.info(f'in graph_analysis_no_auth,vertices = {vertices}')
#     # logger.info(f'in graph_analysis_no_auth,entities = {entities}')
#     return vertices, hit_names, service_names, entities, subgraphs, ''
#     # vertices、hit_names后续都没用到


# graph_analysis_formview 是场景分析用的图分析函数
async def graph_analysis_formview(hits, properties_alias, entity_types, search_params, request, source_type, graph_filter_params,
                                 data_params):
    space_name = data_params['space_name']
    ad_appid = search_params.ad_appid
    hit_names = []
    # 调用图分析服务
    node2score = {}
    service_names = set()
    service_results = []
    path_source = []
    # 按实体类型，批量调用图分析
    end2start = {}
    vid2hit = {hit['_id']: hit for hit in hits}
    """新的调用方法"""
    data = {}
    data['formview_entity_search'] = []
    data['formview_graph_search'] = []
    graph_nebula_statement_template = {'formview_entity_search': prompts_config.formview_entity_search,
                    'formview_graph_search': prompts_config.formview_graph_search}
    for hit in hits:
        if not hit:
            continue
        tag = hit['_index'][len(space_name) + 1:]
        if tag not in data_params['indextag2tag']:
            service_results.append({})
            continue
        if tag == 'dataowner':
            continue
        cur_entity_service = data_params['entity2service'].get(tag, {})
        props = hit['_source']
        hit_names.append(props.get(entity_types[tag]['default_tag'], ''))
        hit['relation'] = cur_entity_service.get('relation', '')
        hit['type'] = entity_types[tag]['name']
        hit['type_alias'] = entity_types[tag]['alias']
        hit['name'] = props.get(entity_types[tag]['default_tag'], '')
        hit['max_score_prop']['alias'] = properties_alias[tag].get(hit['max_score_prop']['prop'], '')
        hit['service_weight'] = cur_entity_service.get('weight', 1.0)
        if tag == 'form_view':
            data['formview_entity_search'].append(hit['_id'])
        else:
            data['formview_graph_search'].append(hit['_id'])
    graph_nebula_statements = {}
    for key1, value in data.items():
        if value and key1.split('_')[1] == "entity":
            start_vids = str(set(value))
        elif value and key1.split('_')[1] == "graph":
            start_vids = str(set(value))[1:-1]
        elif not value and key1.split('_')[1] == "graph":
            start_vids = "'00000'"
        elif not value and key1.split('_')[1] == "entity":
            start_vids = "{'00000'}"
        else:
            start_vids = {}
        params = {"start_vids": start_vids, 'source_type': source_type}
        graph_nebula_statements[key1] = graph_nebula_statement_template[key1].format(**params)
    # logger.debug(f'图分析语句 =\n{graph_nebula_statements}')
    tasks = [custom_graph_call(search_params.kg_id, ad_appid, params) for params in graph_nebula_statements.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for s_res, key, value in zip(results, graph_nebula_statements.keys(), data.values()):
        # 图分析结果实体得分
        if s_res is not None:
            if 'nodes' in s_res.keys() and s_res['nodes'] is None:
                nodes = []
            else:
                nodes = s_res.get('nodes', [])
            vid2node = {x['id']: x for x in nodes}
            node_id_set = set()
            if s_res['nodes'] == []:
                logger.info(f'图分析无结果')
                continue
            if s_res['edges'] == []:
                res_nodes = s_res.get('nodes')
            else:
                res_nodes = s_res.get('edges')
                for path in s_res['edges']:
                    if path["source"] in value:
                        path_source.append(path)
            for path in res_nodes:
                if "source" and "target" in path:
                    if path["source"] not in value:
                        start_vid = find_value_list_of_dict(path_source, path["source"])
                        if start_vid not in value:
                            start_vid = find_value_list_of_dict(path_source, start_vid)
                            if start_vid not in value:
                                continue
                        end_vid = path["target"]
                        pn_id = path["target"]
                        start = vid2hit[start_vid]
                    else:
                        start = vid2hit[path["source"]]
                        start_vid = path["source"]
                        end_vid = path["target"]
                        pn_id = path["target"]
                else:
                    start_vid = path["id"]
                    start = vid2hit[start_vid]
                    end_vid = path["id"]
                    pn_id = path["id"]
                # 只看最后一个点
                node = vid2node[pn_id]
                os_score = start['_score']
                hit_key_words = start['max_score_prop']['keys']
                service_weight = start['service_weight']
                if node['class_name'] not in ['form_view']:
                    # 终点不是数据资产
                    continue
                if pn_id in node_id_set and start_vid in end2start.get(pn_id, {}).get("starts", []):
                    # 重复的起点终点，不重复计算得分
                    continue
                node_id_set.add(pn_id)
                if end_vid not in end2start:
                    end2start[end_vid] = {"starts": [], "end": end_vid}
                end2start[end_vid]["starts"].append(start_vid)
                if node['id'] in node2score:
                    node2score[node['id']]['score'] = max(node2score[node['id']]['score'], os_score * service_weight)
                    node2score[node['id']]['key'].update(hit_key_words)
                else:
                    node2score[node['id']] = {}
                    node2score[node['id']] = node
                    node2score[node['id']]['score'] = os_score * service_weight
                    node2score[node['id']]['key'] = set(hit_key_words)
            else:
                pass
        else:
            logger.info('图查询语句错误！')
    vertices = sorted(list(node2score.values()), key=lambda x: (
        len(x['key']), Decimal(x['score']).quantize(Decimal('1.000000000000')), x['default_property']['value'],),
                      reverse=True)
    entities = []
    subgraphs = []
    RE_limit = int(settings.Finally_NUM)
    logger.info(f'图分析最终返回前端数量限制 = {RE_limit}')
    vertices = vertices[:RE_limit]
    headers = {"Authorization": request.headers.get('Authorization')}
    auth_id = await find_number_api.user_all_auth(headers, search_params.subject_id)
    for i, vertex in enumerate(vertices[:]):
        starts = []
        start_vids = end2start[vertex['id']]['starts']
        start_vids2 = list(set(start_vids))
        start_vids2.sort(key=start_vids.index)
        for start_vid in start_vids2:
            start = vid2hit[start_vid]
            starts.append({
                "relation": start['relation'],
                "class_name": start["type"],
                "name": start["name"],
                "hit": start["max_score_prop"],
                "alias": start["type_alias"]
            })
        if search_params.available_option == 0:
            entities.append({"starts": starts, "entity": vertex})
        else:
            assets = {}
            for prop in vertex['properties'][0]["props"]:
                if prop['name'] == "business_name": assets["resourcename"] = prop["value"]
                assets["asset_type"] = "3"
                if prop['name'] == "owner_id": assets["owner_id"] = prop["value"]
                if prop['name'] == "formview_uuid": assets["resourceid"] = prop["value"]
            res_suth = await find_number_api.sub_user_auth_state(assets, search_params, headers, auth_id)
            is_permissions = "1" if res_suth == "allow" else "0"
            if search_params.available_option == 1:
                entities.append(
                    {"starts": starts, "entity": vertex, 'is_permissions': is_permissions})
            if search_params.available_option == 2:
                if res_suth == "allow":
                    entities.append(
                        {"starts": starts, "entity": vertex, 'is_permissions': "1"})
                else:
                    vertices.remove(vertex)
        subgraphs.append(end2start[vertex['id']])
    for i, ver in enumerate(vertices):
        ver['key'] = list(ver['key'])
    for j, ver in enumerate(entities):
        ver["score"] = len(vertices) - j
    hit_names = list(set([x for x in hit_names if x]))
    service_names = list(service_names)
    return vertices, hit_names, service_names, entities, subgraphs, ''

# search_params, API 入参的 body 部分
# output,是初始化的 输出json， 形如 {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
# query, 就是用户输入的搜索词
# file_path,配置文件， 就是search_config目录下的两个json文件，
# graph_params是筛选项的 pydantic 数据模型
# 搜索列表搜索算法,获取图谱信息,所有实体类的信息都需要
# data_params_file_path 改名为 kgotl_config_file_path
# config_data 改名为 kgotl_config_dict
async def get_kgotl(search_params, output, query, kgotl_config_file_path, graph_filter_params):
    """获取图谱信息"""
    # search_params:{ad_appid,kg_id,required_resource,stopwords,stop_entities,filter,roles}
    ad_appid = search_params.ad_appid
    kg_id = search_params.kg_id
    data_params = {}
    # "required_resource": {
    #     "lexicon_actrie": {
    #       "lexicon_id": "46"
    #     },
    #     "stopwords": {
    #       "lexicon_id": "47"
    #     }
    #   }
    # 1 init_lexicon( )获取、加载同义词词库和停用词词库，
    # resource 是一个字典， 包括一个actrie对象， 和一个stopwords列表对象,可能为None、空列表
    # resource = init_lexicon(ad_appid=ad_appid, required_resource=search_params.required_resource)
    resource = init_lexicon_dip()
    # 定义配置文件路径
    # 2 读取并解析 图谱配置模板 文件， 是 data_params中的数据模板，
    # 包含了实体排序权重，返回结果类型，实体数量限制，实体到和中心实体的关系以及排序权重等
    try:
        with open(kgotl_config_file_path, 'r', encoding='utf-8') as file:
            kgotl_config_dict = json.load(file)
    except FileNotFoundError:
        logger.error("FileNotFoundError")
        return output
    # 从解析的数据中提取字段并赋值给变量
    # 数据目录版为 "result_types": [ "datacatalog", "form_view" ]， form_view 指场景分析
    # 数据资源版为 "result_types": [ "resource" ]
    result_types = kgotl_config_dict.get('result_types', [])  # list[str]类型 需要搜的数据资源类型
    if result_types:
        # 数据目录版仅需要返回 “datacatalog”,因为配置文件中有两个值 [ "datacatalog", "form_view" ]，所以需要取第一个值
        data_params['result_types'] = result_types[0]
    else:
        return output
    data_params['entity_rank'] = kgotl_config_dict.get('entity_weight', {})  # dict类型 图谱中实体的权重
    data_params['entity_limit'] = kgotl_config_dict.get('entity_limit', 1000)  # int 实体数量限制
    data_params['entity2service'] = kgotl_config_dict.get('entity2service', {})  # dict 图谱中关系边的权重
    data_params['actrie'] = resource.get('lexicon_actrie', None)  # 同义词trie树对象
    data_params['stopwords'] = resource.get('stopwords', [])  # 停用词库获得的停用词列表对象
    data_params['dropped_words'] = [x.lower().replace(' ', '') for x in search_params.stopwords]  # 前端传入的指定停用词
    data_params['entity_types_not_search'] = search_params.stop_entities  # 不需要搜的类型
    logger.info(dedent(f"""
        图谱搜索配置文件 CONFIG = 
        entity_limit: {data_params["entity_limit"]}
        result_types: {data_params["result_types"]}
        entity_rank: {data_params["entity_rank"]}""").strip()
                )
    # 3 筛选项业务逻辑处理
    # 资源版，filter:
    # {'asset_type': [-1], 'department_id': [-1], 'end_time': '0', 'online_status': [-1], 'owner_id': [-1],
    # 'publish_status_category': [-1], 'start_time': '0', 'stop_entity_infos': [], 'subject_id': [-1]}
    filter_conds = search_params.filter  # 过滤条件
    asset_type = filter_conds.get('asset_type', '')

    logger.info(f'用户角色 = {search_params.roles}')
    # 如果用户没有应用开发工程师角色，就不搜2：接口服务
    if "application-developer" not in search_params.roles and int(2) in asset_type:
        asset_type.remove(2)
    graph_filter_params.asset_type = asset_type

    # 如果用户有数据运营工程师角色， 或者数据开发工程师角色，
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        graph_filter_params.online_status = json.dumps(filter_conds.get('online_status', ''))
        graph_filter_params.publish_status = json.dumps(filter_conds.get('publish_status_category', ''))
        # graph_filter_params.publish_status_c = json.dumps(filter_conds.get('publish_status', ''))
    # online_status=[-1]支持上下线筛选
    else:
        # 如果用户不是数据运营工程师角色和数据开发工程师角色，只能搜已上线已发布的数据资源目录
        graph_filter_params.online_status = json.dumps(["online", "down-auditing", "down-reject"])
        graph_filter_params.publish_status = json.dumps(["published_category"])
        # graph_filter_params.publish_status_c = json.dumps(["published"])

    graph_filter_params.update_cycle = filter_conds.get('update_cycle', '')
    graph_filter_params.shared_type = filter_conds.get('shared_type', '')
    graph_filter_params.start_time = filter_conds.get('start_time', '')
    graph_filter_params.end_time = filter_conds.get('end_time', '')
    graph_filter_params.asset_type = filter_conds.get('asset_type', '')
    graph_filter_params.resource_type = filter_conds.get('resource_type', '')

    # replace解决nebule双引号出错问题
    dept_id = filter_conds.get('department_id', '')
    data_owner_id = filter_conds.get('owner_id', '')
    info_system_id = filter_conds.get('info_system_id', '')
    subject_id = filter_conds.get('subject_id', '')
    cate_node_id = filter_conds.get('cate_node_id', '')
    graph_filter_params.department_id = json.dumps(dept_id) if not isinstance(dept_id, str) else dept_id
    graph_filter_params.owner_id = json.dumps(data_owner_id) if not isinstance(data_owner_id, str) else data_owner_id
    graph_filter_params.info_system = json.dumps(info_system_id) if not isinstance(info_system_id, str) else info_system_id
    graph_filter_params.subject_id = json.dumps(subject_id) if not isinstance(subject_id, str) else subject_id
    graph_filter_params.cate_node_id = json.dumps(cate_node_id) if not isinstance(cate_node_id, str) else cate_node_id
    stop_entity_infos = filter_conds.get('stop_entity_infos', [])
    data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    data_params['indextag2tag'] = {}  # 实体类型有大写时 转小写

    # 4 获取图谱本体信息
    kg_otl = await ad_builder_get_kg_info(ad_appid, kg_id)
    kg_otl = kg_otl['res']
    if isinstance(kg_otl['graph_baseInfo'], list):
        data_params['space_name'] = kg_otl['graph_baseInfo'][0]['graph_DBName']
    else:
        data_params['space_name'] = kg_otl['graph_baseInfo']['graph_DBName']
    vertices = kg_otl['graph_otl'][0]['entity']
    entity_types = {}
    # {实体类型名：实体本体信息}
    properties_alias = {}
    properties_types = {}
    entity2prop = {}
    # 记录向量和索引名
    vector_index_filed = {}
    for vertex in vertices:
        # 实体类型别名/颜色/唯一标识属性
        entity2prop[vertex['name']] = vertex['default_tag']
        data_params['indextag2tag'][vertex['name'].lower()] = vertex['name']
        vertex['colour'] = vertex['fill_color']
        entity_types[vertex['name']] = vertex
        properties_alias[vertex['name']] = {}
        properties_types[vertex['name']] = {}
        # 索引名和索引下的向量名，按字典方式存储
        vector_index_filed[vertex['name']] = vertex['vector_generation']
        for prop in vertex['properties']:
            properties_alias[vertex['name']][prop['name']] = prop['alias']
            properties_types[vertex['name']][prop['name']] = prop['data_type']
    # 没有设置权重的实体，将权重设为0
    # 不需要搜的类型，从entity_rank中去掉
    entity_rank_types = list(data_params['entity_rank'].keys())
    for entity_type in entity_rank_types:
        if entity_type in data_params['entity_types_not_search']:
            data_params['entity_rank'].pop(entity_type)
    for entity_type in entity_types.keys():
        if entity_type not in data_params['entity_types_not_search'] and entity_type not in data_params[
            'entity_rank'].keys():
            data_params['entity_rank'][entity_type] = 0
    # 权重分组，权重高的先搜opensearch
    weights_group = [(w, list(group)) for w, group in
                     groupby(list(data_params['entity_rank'].items()), key=lambda x: x[1])]
    data_params['weights_group'] = sorted(weights_group, key=lambda x: x[0], reverse=True)

    # 5 对query进行同义词扩展， query_syn_expansion 原名 cal_queries
    queries, query_cuts, all_syns = await query_syn_expansion(
        actrie=data_params['actrie'],
        query=query,
        stopwords=data_params['stopwords'],
        dropped_words=data_params['dropped_words']
    )

    return (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop,
            vector_index_filed, data_params, graph_filter_params)


async def get_kgotl_dip(search_params, output, query, kgotl_config_file_path, graph_filter_params):
    """获取图谱信息"""
    # search_params:{ad_appid,kg_id,required_resource,stopwords,stop_entities,filter,roles}

    # kg_id = search_params.kg_id
    data_params = {}
    # "required_resource": {
    #     "lexicon_actrie": {
    #       "lexicon_id": "46"
    #     },
    #     "stopwords": {
    #       "lexicon_id": "47"
    #     }
    #   }
    # 1 init_lexicon( )获取、加载同义词词库和停用词词库，
    # resource 是一个字典， 包括一个actrie对象， 和一个stopwords列表对象,可能为None、空列表
    # resource = init_lexicon(ad_appid=ad_appid, required_resource=search_params.required_resource)
    resource = init_lexicon_dip()
    # 定义配置文件路径
    # 2 读取并解析 图谱配置模板 文件， 是 data_params中的数据模板，
    # 包含了实体排序权重，返回结果类型，实体数量限制，实体到和中心实体的关系以及排序权重等
    try:
        with open(kgotl_config_file_path, 'r', encoding='utf-8') as file:
            kgotl_config_dict = json.load(file)
    except FileNotFoundError:
        logger.error("FileNotFoundError")
        return output
    # 从解析的数据中提取字段并赋值给变量
    # 数据目录版为 "result_types": [ "datacatalog", "form_view" ]， form_view 指场景分析
    # 数据资源版为 "result_types": [ "resource" ]
    result_types = kgotl_config_dict.get('result_types', [])  # list[str]类型 需要搜的数据资源类型
    if result_types:
        # 数据目录版仅需要返回 “datacatalog”,因为配置文件中有两个值 [ "datacatalog", "form_view" ]，所以需要取第一个值
        data_params['result_types'] = result_types[0]
    else:
        return output
    data_params['entity_rank'] = kgotl_config_dict.get('entity_weight', {})  # dict类型 图谱中实体的权重
    data_params['entity_limit'] = kgotl_config_dict.get('entity_limit', 1000)  # int 实体数量限制
    data_params['entity2service'] = kgotl_config_dict.get('entity2service', {})  # dict 图谱中关系边的权重
    data_params['actrie'] = resource.get('lexicon_actrie', None)  # 同义词trie树对象
    data_params['stopwords'] = resource.get('stopwords', [])  # 停用词库获得的停用词列表对象
    data_params['dropped_words'] = [x.lower().replace(' ', '') for x in search_params.stopwords]  # 前端传入的指定停用词
    data_params['entity_types_not_search'] = search_params.stop_entities  # 不需要搜的类型
    logger.info(dedent(f"""
        图谱搜索配置文件 CONFIG = 
        entity_limit: {data_params["entity_limit"]}
        result_types: {data_params["result_types"]}
        entity_rank: {data_params["entity_rank"]}""").strip()
                )
    # 3 筛选项业务逻辑处理
    # 资源版，filter:
    # {'asset_type': [-1], 'department_id': [-1], 'end_time': '0', 'online_status': [-1], 'owner_id': [-1],
    # 'publish_status_category': [-1], 'start_time': '0', 'stop_entity_infos': [], 'subject_id': [-1]}
    filter_conds = search_params.filter  # 过滤条件
    asset_type = filter_conds.get('asset_type', '')

    logger.info(f'用户角色 = {search_params.roles}')
    # 如果用户没有应用开发工程师角色，就不搜2：接口服务
    if "application-developer" not in search_params.roles and int(2) in asset_type:
        asset_type.remove(2)
    graph_filter_params.asset_type = asset_type

    # 如果用户有数据运营工程师角色， 或者数据开发工程师角色，
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        graph_filter_params.online_status = json.dumps(filter_conds.get('online_status', ''))
        graph_filter_params.publish_status = json.dumps(filter_conds.get('publish_status_category', ''))
        # graph_filter_params.publish_status_c = json.dumps(filter_conds.get('publish_status', ''))
    # online_status=[-1]支持上下线筛选
    else:
        # 如果用户不是数据运营工程师角色和数据开发工程师角色，只能搜已上线已发布的数据资源目录
        graph_filter_params.online_status = json.dumps(["online", "down-auditing", "down-reject"])
        graph_filter_params.publish_status = json.dumps(["published_category"])
        # graph_filter_params.publish_status_c = json.dumps(["published"])

    graph_filter_params.update_cycle = filter_conds.get('update_cycle', '')
    graph_filter_params.shared_type = filter_conds.get('shared_type', '')
    graph_filter_params.start_time = filter_conds.get('start_time', '')
    graph_filter_params.end_time = filter_conds.get('end_time', '')
    graph_filter_params.asset_type = filter_conds.get('asset_type', '')
    graph_filter_params.resource_type = filter_conds.get('resource_type', '')

    # replace解决nebule双引号出错问题
    dept_id = filter_conds.get('department_id', '')
    data_owner_id = filter_conds.get('owner_id', '')
    info_system_id = filter_conds.get('info_system_id', '')
    subject_id = filter_conds.get('subject_id', '')
    cate_node_id = filter_conds.get('cate_node_id', '')
    graph_filter_params.department_id = json.dumps(dept_id) if not isinstance(dept_id, str) else dept_id
    graph_filter_params.owner_id = json.dumps(data_owner_id) if not isinstance(data_owner_id, str) else data_owner_id
    graph_filter_params.info_system = json.dumps(info_system_id) if not isinstance(info_system_id, str) else info_system_id
    graph_filter_params.subject_id = json.dumps(subject_id) if not isinstance(subject_id, str) else subject_id
    graph_filter_params.cate_node_id = json.dumps(cate_node_id) if not isinstance(cate_node_id, str) else cate_node_id
    stop_entity_infos = filter_conds.get('stop_entity_infos', [])
    data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    data_params['indextag2tag'] = {}  # 实体类型有大写时 转小写

    # 4 获取图谱本体信息
    kg_otl = await ad_builder_get_kg_info_dip(
        x_account_id=search_params.subject_id,
        x_account_type=search_params.subject_type,
        kg_id=search_params.kg_id
    )
    kg_otl = kg_otl['res']
    if isinstance(kg_otl['graph_baseInfo'], list):
        data_params['space_name'] = kg_otl['graph_baseInfo'][0]['graph_DBName']
    else:
        data_params['space_name'] = kg_otl['graph_baseInfo']['graph_DBName']
    vertices = kg_otl['graph_otl'][0]['entity']
    entity_types = {}
    # {实体类型名：实体本体信息}
    properties_alias = {}
    properties_types = {}
    entity2prop = {}
    # 记录向量和索引名
    vector_index_filed = {}
    for vertex in vertices:
        # 实体类型别名/颜色/唯一标识属性
        entity2prop[vertex['name']] = vertex['default_tag']
        data_params['indextag2tag'][vertex['name'].lower()] = vertex['name']
        vertex['colour'] = vertex['fill_color']
        entity_types[vertex['name']] = vertex
        properties_alias[vertex['name']] = {}
        properties_types[vertex['name']] = {}
        # 索引名和索引下的向量名，按字典方式存储
        vector_index_filed[vertex['name']] = vertex['vector_generation']
        for prop in vertex['properties']:
            properties_alias[vertex['name']][prop['name']] = prop['alias']
            properties_types[vertex['name']][prop['name']] = prop['data_type']
    # 没有设置权重的实体，将权重设为0
    # 不需要搜的类型，从entity_rank中去掉
    entity_rank_types = list(data_params['entity_rank'].keys())
    for entity_type in entity_rank_types:
        if entity_type in data_params['entity_types_not_search']:
            data_params['entity_rank'].pop(entity_type)
    for entity_type in entity_types.keys():
        if entity_type not in data_params['entity_types_not_search'] and entity_type not in data_params[
            'entity_rank'].keys():
            data_params['entity_rank'][entity_type] = 0
    # 权重分组，权重高的先搜opensearch
    weights_group = [(w, list(group)) for w, group in
                     groupby(list(data_params['entity_rank'].items()), key=lambda x: x[1])]
    data_params['weights_group'] = sorted(weights_group, key=lambda x: x[0], reverse=True)

    # 5 对query进行同义词扩展， query_syn_expansion 原名 cal_queries
    queries, query_cuts, all_syns = await query_syn_expansion(
        actrie=data_params['actrie'],
        query=query,
        stopwords=data_params['stopwords'],
        dropped_words=data_params['dropped_words']
    )

    return (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop,
            vector_index_filed, data_params, graph_filter_params)
# 还未完成
async def get_kgotl_dip_new(headers,search_params, output, query, kgotl_config_file_path, graph_filter_params):
    """获取图谱信息"""
    # kg_id = search_params.kg_id
    data_params = {}

    # 1 init_lexicon( )获取、加载同义词词库和停用词词库，
    # resource 是一个字典， 包括一个actrie对象， 和一个stopwords列表对象,可能为None、空列表
    # resource = init_lexicon(ad_appid=ad_appid, required_resource=search_params.required_resource)
    resource = init_lexicon_dip()
    # 定义配置文件路径
    # 2 读取并解析 图谱配置模板 文件， 是 data_params中的数据模板，
    # 包含了实体排序权重，返回结果类型，实体数量限制，实体到和中心实体的关系以及排序权重等
    try:
        with open(kgotl_config_file_path, 'r', encoding='utf-8') as file:
            kgotl_config_dict = json.load(file)
    except FileNotFoundError:
        logger.error("FileNotFoundError")
        return output
    # 从解析的数据中提取字段并赋值给变量
    # 数据目录版为 "result_types": [ "datacatalog", "form_view" ]， form_view 指场景分析
    # 数据资源版为 "result_types": [ "resource" ]
    result_types = kgotl_config_dict.get('result_types', [])  # list[str]类型 需要搜的数据资源类型
    if result_types:
        # 数据目录版仅需要返回 “datacatalog”,因为配置文件中有两个值 [ "datacatalog", "form_view" ]，所以需要取第一个值
        data_params['result_types'] = result_types[0]
    else:
        return output
    data_params['entity_rank'] = kgotl_config_dict.get('entity_weight', {})  # dict类型 图谱中实体的权重
    data_params['entity_limit'] = kgotl_config_dict.get('entity_limit', 1000)  # int 实体数量限制
    data_params['entity2service'] = kgotl_config_dict.get('entity2service', {})  # dict 图谱中关系边的权重
    data_params['actrie'] = resource.get('lexicon_actrie', None)  # 同义词trie树对象
    data_params['stopwords'] = resource.get('stopwords', [])  # 停用词库获得的停用词列表对象
    data_params['dropped_words'] = [x.lower().replace(' ', '') for x in search_params.stopwords]  # 前端传入的指定停用词
    data_params['entity_types_not_search'] = search_params.stop_entities  # 不需要搜的类型
    logger.info(dedent(f"""
        图谱搜索配置文件 CONFIG = 
        entity_limit: {data_params["entity_limit"]}
        result_types: {data_params["result_types"]}
        entity_rank: {data_params["entity_rank"]}""").strip()
                )
    # 3 筛选项业务逻辑处理
    # 资源版，filter:
    # {'asset_type': [-1], 'department_id': [-1], 'end_time': '0', 'online_status': [-1], 'owner_id': [-1],
    # 'publish_status_category': [-1], 'start_time': '0', 'stop_entity_infos': [], 'subject_id': [-1]}
    filter_conds = search_params.filter  # 过滤条件
    asset_type = filter_conds.get('asset_type', '')

    logger.info(f'用户角色 = {search_params.roles}')
    # 如果用户没有应用开发工程师角色，就不搜2：接口服务
    if "application-developer" not in search_params.roles and int(2) in asset_type:
        asset_type.remove(2)
    graph_filter_params.asset_type = asset_type

    # 如果用户有数据运营工程师角色， 或者数据开发工程师角色，
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        graph_filter_params.online_status = json.dumps(filter_conds.get('online_status', ''))
        graph_filter_params.publish_status = json.dumps(filter_conds.get('publish_status_category', ''))
        # graph_filter_params.publish_status_c = json.dumps(filter_conds.get('publish_status', ''))
    # online_status=[-1]支持上下线筛选
    else:
        # 如果用户不是数据运营工程师角色和数据开发工程师角色，只能搜已上线已发布的数据资源目录
        graph_filter_params.online_status = json.dumps(["online", "down-auditing", "down-reject"])
        graph_filter_params.publish_status = json.dumps(["published_category"])
        # graph_filter_params.publish_status_c = json.dumps(["published"])

    graph_filter_params.update_cycle = filter_conds.get('update_cycle', '')
    graph_filter_params.shared_type = filter_conds.get('shared_type', '')
    graph_filter_params.start_time = filter_conds.get('start_time', '')
    graph_filter_params.end_time = filter_conds.get('end_time', '')
    graph_filter_params.asset_type = filter_conds.get('asset_type', '')
    graph_filter_params.resource_type = filter_conds.get('resource_type', '')

    # replace解决nebule双引号出错问题
    dept_id = filter_conds.get('department_id', '')
    data_owner_id = filter_conds.get('owner_id', '')
    info_system_id = filter_conds.get('info_system_id', '')
    subject_id = filter_conds.get('subject_id', '')
    cate_node_id = filter_conds.get('cate_node_id', '')
    graph_filter_params.department_id = json.dumps(dept_id) if not isinstance(dept_id, str) else dept_id
    graph_filter_params.owner_id = json.dumps(data_owner_id) if not isinstance(data_owner_id, str) else data_owner_id
    graph_filter_params.info_system = json.dumps(info_system_id) if not isinstance(info_system_id, str) else info_system_id
    graph_filter_params.subject_id = json.dumps(subject_id) if not isinstance(subject_id, str) else subject_id
    graph_filter_params.cate_node_id = json.dumps(cate_node_id) if not isinstance(cate_node_id, str) else cate_node_id
    stop_entity_infos = filter_conds.get('stop_entity_infos', [])
    data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    data_params['indextag2tag'] = {}  # 实体类型有大写时 转小写

    # 4 获取图谱本体信息
    # kg_otl = await ad_builder_get_kg_info_dip(
    #     x_account_id=search_params.subject_id,
    #     x_account_type=search_params.subject_type,
    #     kg_id=search_params.kg_id
    # )
    # 获取新业务知识网络所有实体类的信息
    # kg_otl = await  find_number_api.dip_get_object_types_internal(
    #     x_account_id=search_params.subject_id,
    #     x_account_type=search_params.subject_type,
    #     kn_id=search_params.kg_id
    # )
    # 改为外部接口调用
    token = headers.get("Authorization")
    kg_otl = await  find_number_api.dip_get_object_types_external(
        token=token,
        kn_id=search_params.kg_id
    )
    logger.debug(f"获取认知搜索图谱信息 kg_otl = {kg_otl}")

    vector_index_filed, entity_types, data_params = parse_all_entity_info(
        entries_data=kg_otl
    )
    # data_params['indextag2tag'] = indextag2tag
    # logger.info(f'data_params={data_params}')
    # logger.info(f'entity_types={entity_types}')
    # type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names']
    # data_params['space_name']
    # data_params['indextag2tag']
    logger.debug(f"after get_kgotl_qa_dip_new():")
    logger.debug(f"entity_types = {entity_types}")
    logger.debug(f"vector_index_filed = {vector_index_filed}")
    logger.debug(f"data_params = {data_params}")


    kg_otl = kg_otl['res']
    if isinstance(kg_otl['graph_baseInfo'], list):
        data_params['space_name'] = kg_otl['graph_baseInfo'][0]['graph_DBName']
    else:
        data_params['space_name'] = kg_otl['graph_baseInfo']['graph_DBName']
    vertices = kg_otl['graph_otl'][0]['entity']
    entity_types = {}
    # {实体类型名：实体本体信息}
    properties_alias = {}
    properties_types = {}
    entity2prop = {}
    # 记录向量和索引名
    vector_index_filed = {}
    for vertex in vertices:
        # 实体类型别名/颜色/唯一标识属性
        entity2prop[vertex['name']] = vertex['default_tag']
        data_params['indextag2tag'][vertex['name'].lower()] = vertex['name']
        vertex['colour'] = vertex['fill_color']
        entity_types[vertex['name']] = vertex
        properties_alias[vertex['name']] = {}
        properties_types[vertex['name']] = {}
        # 索引名和索引下的向量名，按字典方式存储
        vector_index_filed[vertex['name']] = vertex['vector_generation']
        for prop in vertex['properties']:
            properties_alias[vertex['name']][prop['name']] = prop['alias']
            properties_types[vertex['name']][prop['name']] = prop['data_type']
    # 没有设置权重的实体，将权重设为0
    # 不需要搜的类型，从entity_rank中去掉
    entity_rank_types = list(data_params['entity_rank'].keys())
    for entity_type in entity_rank_types:
        if entity_type in data_params['entity_types_not_search']:
            data_params['entity_rank'].pop(entity_type)
    for entity_type in entity_types.keys():
        if entity_type not in data_params['entity_types_not_search'] and entity_type not in data_params[
            'entity_rank'].keys():
            data_params['entity_rank'][entity_type] = 0
    # 权重分组，权重高的先搜opensearch
    weights_group = [(w, list(group)) for w, group in
                     groupby(list(data_params['entity_rank'].items()), key=lambda x: x[1])]
    data_params['weights_group'] = sorted(weights_group, key=lambda x: x[0], reverse=True)

    # 5 对query进行同义词扩展， query_syn_expansion 原名 cal_queries
    queries, query_cuts, all_syns = await query_syn_expansion(
        actrie=data_params['actrie'],
        query=query,
        stopwords=data_params['stopwords'],
        dropped_words=data_params['dropped_words']
    )

    return (queries, query_cuts, all_syns, entity_types, properties_alias, properties_types, entity2prop,
            vector_index_filed, data_params, graph_filter_params)

# 分析问答型搜索获取图谱信息,因为分析问答型搜索只查中间的点, 不做关联搜索,所以只需要处理中间点的图谱信息即可,
async def get_kgotl_qa(search_params):
    """
    获取图谱信息并处理相关数据。

    该函数从输入中提取过滤条件，处理停用实体信息，构建实体类型与名称的映射关系，
    并从图谱本体信息中提取所需的数据。最后返回处理后的实体类型信息、向量索引字段和数据参数。

    Args:
        search_params: 包含必要参数的对象

    Returns:
        entity_types: 实体类型与本体信息的字典，分析问答型搜索仅包含认知搜索图谱中间的点， 数据资源或者数据目录
        vector_index_filed: 实体类型与向量索引字段的字典
        data_params: 包含空间名称、实体类型与名称映射等信息的字典
    """
    data_params = {}
    """获取图谱信息"""
    # logger.info(f'获取认知搜索图谱信息')
    # 从解析的数据中提取字段并赋值给变量
    try:
        filter_conds = search_params.filter
    except:
        filter_conds = {}
    stop_entity_infos = filter_conds.get('stop_entity_infos', [])
    # type2names 字典 是前端传来的停用实体,现在已经废弃
    data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
    indextag2tag = {}  # 实体类型有大写时
    # 获取图谱本体信息
    # self.kg_info_url: str = self.builder_url + "/graph/{kg_id}"
    # builder_url: str = "/api/builder/v1"
    kg_otl = await ad_builder_get_kg_info_dip(
        x_account_id=search_params.subject_id,
        x_account_type=search_params.subject_type,
        kg_id=search_params.kg_id
    )
    # logger.debug(f"获取认知搜索图谱信息 kg_otl = {kg_otl}")
    # logger.debug(f'kg_otl = \n{kg_otl}')
    # 图谱信息kg_otl是json, res为key
    # kg_otl['graph_baseInfo']['graph_DBName']是土空间名称, 命名为变了space_name,值比如 u27744cdad32811efac247a78d1fb505e-15
    # AD图谱的opensearch索引名称命名规则是 {space_name}_{实体类名称}
    kg_otl = kg_otl['res']
    if isinstance(kg_otl['graph_baseInfo'], list):
        space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
    else:
        space_name = kg_otl['graph_baseInfo']['graph_DBName']
    data_params['space_name'] = space_name
    # kg_otl['graph_otl'][0]['entity']是所有实体的配置信息
    # kg_otl['graph_otl'][0]['edge']是所有边的配置信息
    vertices = kg_otl['graph_otl'][0]['entity']
    # entity_types 字典{实体类型名：实体本体信息}
    entity_types = {}
    # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
    vector_index_filed = {}
    # vertex['name']是实体类型名,比如 dimension_model,
    for vertex in vertices:
        # 如果实体类是中间的点,也就是搜索列表需要返回的数据资源(逻辑视图/接口服务/指标),数据资源目录,

        # important！ 分析问答型搜索只查中间的点, 不做关联搜索,所以只需要处理中间点的图谱信息即可

        # ‘form_view'是场景分析版本， 值是’resource‘是数据资源版， 值是‘datacatalog’是数据目录版
        # logger.debug(f'vertex = {vertex}')
        if vertex['name'] == 'resource' or vertex['name'] == 'datacatalog' or vertex['name'] == 'form_view':
            # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
            indextag2tag[vertex['name'].lower()] = vertex['name']
            # entity_types 字典{实体类型名：实体本体信息}
            entity_types[vertex['name']] = vertex
            # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
            # 数据样例 "vector_generation": ["description", "name"]
            vector_index_filed[vertex['name']] = vertex['vector_generation']
    data_params['indextag2tag'] = indextag2tag
    # type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names']
    # data_params['space_name']
    # data_params['indextag2tag']
    # logger.debug(f"after get_kgotl_qa:")
    # logger.debug(f"entity_types = {entity_types}")
    # logger.debug(f"vector_index_filed = {vector_index_filed}")
    # logger.debug(f"data_params = {data_params}")
    return entity_types, vector_index_filed, data_params

# async def get_kgotl_qa_dip(search_params):
#     """
#     获取图谱信息并处理相关数据。
#
#     该函数从输入中提取过滤条件，处理停用实体信息，构建实体类型与名称的映射关系，
#     并从图谱本体信息中提取所需的数据。最后返回处理后的实体类型信息、向量索引字段和数据参数。
#
#     Args:
#         search_params: 包含必要参数的对象
#
#     Returns:
#         entity_types: 实体类型与本体信息的字典，分析问答型搜索仅包含认知搜索图谱中间的点， 数据资源或者数据目录
#         vector_index_filed: 实体类型与向量索引字段的字典
#         data_params: 包含空间名称、实体类型与名称映射等信息的字典
#     """
#     data_params = {}
#     """获取图谱信息"""
#     # logger.info(f'获取认知搜索图谱信息')
#     # 从解析的数据中提取字段并赋值给变量
#     try:
#         filter_conds = search_params.filter
#     except:
#         filter_conds = {}
#     stop_entity_infos = filter_conds.get('stop_entity_infos', [])
#     # type2names 字典 是前端传来的停用实体,现在已经废弃
#     data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
#     # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#     indextag2tag = {}  # 实体类型有大写时
#     # 获取图谱本体信息
#     # self.kg_info_url: str = self.builder_url + "/graph/{kg_id}"
#     # builder_url: str = "/api/builder/v1"
#     kg_otl = await ad_builder_get_kg_info_dip(
#         x_account_id=search_params.subject_id,
#         x_account_type=search_params.subject_type,
#         kg_id=search_params.kg_id
#     )
#     # logger.debug(f"获取认知搜索图谱信息 kg_otl = {kg_otl}")
#     # logger.debug(f'kg_otl = \n{kg_otl}')
#     # 图谱信息kg_otl是json, res为key
#     # kg_otl['graph_baseInfo']['graph_DBName']是土空间名称, 命名为变了space_name,值比如 u27744cdad32811efac247a78d1fb505e-15
#     # AD图谱的opensearch索引名称命名规则是 {space_name}_{实体类名称}
#     kg_otl = kg_otl['res']
#     if isinstance(kg_otl['graph_baseInfo'], list):
#         space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
#     else:
#         space_name = kg_otl['graph_baseInfo']['graph_DBName']
#     data_params['space_name'] = space_name
#     # kg_otl['graph_otl'][0]['entity']是所有实体的配置信息
#     # kg_otl['graph_otl'][0]['edge']是所有边的配置信息
#     vertices = kg_otl['graph_otl'][0]['entity']
#     # entity_types 字典{实体类型名：实体本体信息}
#     entity_types = {}
#     # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#     vector_index_filed = {}
#     # vertex['name']是实体类型名,比如 dimension_model,
#     for vertex in vertices:
#         # 如果实体类是中间的点,也就是搜索列表需要返回的数据资源(逻辑视图/接口服务/指标),数据资源目录,
#
#         # important！ 分析问答型搜索只查中间的点, 不做关联搜索,所以只需要处理中间点的图谱信息即可
#
#         # ‘form_view'是场景分析版本， 值是’resource‘是数据资源版， 值是‘datacatalog’是数据目录版
#         # logger.debug(f'vertex = {vertex}')
#         if vertex['name'] == 'resource' or vertex['name'] == 'datacatalog' or vertex['name'] == 'form_view':
#             # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#             indextag2tag[vertex['name'].lower()] = vertex['name']
#             # entity_types 字典{实体类型名：实体本体信息}
#             entity_types[vertex['name']] = vertex
#             # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#             # 数据样例 "vector_generation": ["description", "name"]
#             vector_index_filed[vertex['name']] = vertex['vector_generation']
#     data_params['indextag2tag'] = indextag2tag
#     # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # data_params['type2names']
#     # data_params['space_name']
#     # data_params['indextag2tag']
#     # logger.debug(f"after get_kgotl_qa:")
#     # logger.debug(f"entity_types = {entity_types}")
#     # logger.debug(f"vector_index_filed = {vector_index_filed}")
#     # logger.debug(f"data_params = {data_params}")
#     return entity_types, vector_index_filed, data_params

async def get_kgotl_qa_dip_new(headers,search_params):
    """
    获取图谱信息并处理相关数据。
    该函数从输入中提取过滤条件，处理停用实体信息，构建实体类型与名称的映射关系，
    并从图谱本体信息中提取所需的数据。最后返回处理后的实体类型信息、向量索引字段和数据参数。

    Args:
        search_params: 包含必要参数的对象

    Returns:
        entity_types: 实体类型与本体信息的字典，分析问答型搜索仅包含认知搜索图谱中间的点， 数据资源或者数据目录
        vector_index_filed: 实体类型与向量索引字段的字典
        data_params: 包含空间名称、实体类型与名称映射等信息的字典
    """
    data_params = {}
    try:
        filter_conditions = search_params.filter
    except Exception:
        filter_conditions = {}
    stop_entity_infos = filter_conditions.get('stop_entity_infos', [])
    data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
    indextag2tag = {}  # 实体类型有大写时

    # 获取新业务知识网络所有实体类的信息
    # kg_otl = await  find_number_api.dip_get_object_types_internal(
    #     x_account_id=search_params.subject_id,
    #     x_account_type=search_params.subject_type,
    #     kn_id=search_params.kg_id
    # )
    # 改为调用外部接口
    token = headers.get("Authorization")
    kg_otl = await  find_number_api.dip_get_object_types_external(
        token=token,
        kn_id=search_params.kg_id
    )

    logger.debug(f"获取认知搜索图谱信息 kg_otl = {kg_otl}")

    vector_index_filed, entity_types, data_params = parse_all_entity_info(
        entries_data=kg_otl
    )
    data_params['indextag2tag'] = indextag2tag
    # logger.info(f'data_params={data_params}')
    # logger.info(f'entity_types={entity_types}')
    # type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names']
    # data_params['space_name']
    # data_params['indextag2tag']
    logger.debug(f"after get_kgotl_qa_dip_new():")
    logger.debug(f"entity_types = {entity_types}")
    logger.debug(f"vector_index_filed = {vector_index_filed}")
    logger.debug(f"data_params = {data_params}")
    return entity_types, vector_index_filed, data_params

# 部门职责知识增强, 获取图谱信息, 目前POC版本只需要获取部门职责一个点的图谱信息
# KECC 是部门职责知识增强的缩写 knowledge_enhancement_catalog_chain
# async def get_kgotl_kecc(search_params):
async def get_kgotl_kecc(ad_appid, kg_id_kecc):
    """
    获取图谱信息并处理相关数据。

    该函数从指定的应用ID和图谱ID中获取图谱信息，提取特定实体类型的配置信息，并构建相关的数据字典。返回的字典包括实体类型及其本体信息、向量索引字段以及一些辅助信息如空间名称等。

    :arg ad_appid: 应用ID
    :arg kg_id_kecc: 图谱ID

    :returns: 三个字典，分别是实体类型及其本体信息(entity_types)、实体类型及其向量索引字段(vector_index_filed)和其他辅助信息(data_params)

    :raises: 无明确异常说明

    """
    # logger.info(f'获取部门职责知识增强图谱信息')
    data_params = {}
    # logger.info(f"data_params = {data_params}")
    # 从解析的数据中提取字段并赋值给变量
    # try:
    #     filter_conds = search_params.filter
    # except:
    #     filter_conds = {}
    # stop_entity_infos = filter_conds.get('stop_entity_infos', [])
    # # type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
    indextag2tag = {}  # 实体类型有大写时
    # logger.debug(f"indextag2tag = {indextag2tag}")
    # 获取图谱本体信息
    # self.kg_info_url: str = self.builder_url + "/graph/{kg_id}"
    # builder_url: str = "/api/builder/v1"
    # kg_otl = await ad_builder_get_kg_info(search_params.ad_appid, search_params.kg_id)

    kg_otl = await ad_builder_get_kg_info(ad_appid, kg_id_kecc)
    # logger.debug(f"获取部门职责知识增强图谱信息 kg_otl = {kg_otl}")
    # 图谱信息kg_otl是字典, res为key
    # kg_otl['graph_baseInfo']['graph_DBName']是土空间名称, 命名为变量space_name,值比如 ud2178f9ef81711ef9d057a78d1fb505e-2
    # AD图谱的opensearch索引名称命名规则是 {space_name}_{实体类名称}
    # return  json.dumps(kg_otl,indent=4, ensure_ascii=False, sort_keys=True)
    # return json.dumps(kg_otl, indent=4, ensure_ascii=False, sort_keys=False)
    kg_otl = kg_otl['res']
    # 某些AD版本中(kg_otl['graph_baseInfo']是list
    if isinstance(kg_otl['graph_baseInfo'], list):
        space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
    else:
        space_name = kg_otl['graph_baseInfo']['graph_DBName']
    data_params['space_name'] = space_name
    # # kg_otl['graph_otl'][0]['entity']是所有实体的配置信息
    # # kg_otl['graph_otl'][0]['edge']是所有边的配置信息
    vertices = kg_otl['graph_otl'][0]['entity']
    # # entity_types 字典{实体类型名：实体本体信息}
    entity_types = {}
    # # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
    vector_index_filed = {}
    # # vertex['name']是实体类型名,比如 dimension_model,
    # vertices是字典列表,每个字典是一个实体类的配置信息
    for vertex in vertices:
        # 目前版本只需要获取部门职责一个点的图谱信息
        if vertex['name'] == 'dept_duty' :
            # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
            indextag2tag[vertex['name'].lower()] = vertex['name']
            # entity_types 字典{实体类型名：实体本体信息}
            entity_types[vertex['name']] = vertex
            # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
            # 数据样例 "vector_generation": ["description", "name"]
            vector_index_filed[vertex['name']] = vertex['vector_generation']
    # data_params['indextag2tag'] = indextag2tag
    # # type2names 字典 是前端传来的停用实体,现在已经废弃
    # # data_params['type2names']
    # # data_params['space_name']
    # # data_params['indextag2tag']
    # return json.dumps(entity_types, indent=4, ensure_ascii=False, sort_keys=False), \
    # json.dumps(vector_index_filed, indent=4, ensure_ascii=False, sort_keys=False), \
    # json.dumps(data_params, indent=4, ensure_ascii=False, sort_keys=False)
    return entity_types, vector_index_filed, data_params


# # 历史问答对知识增强, 获取图谱信息, 目前POC版本只需要获取`samples_requirements`(`正负样例`) 一个点的图谱信息
# async def get_kgotl_history_qa(ad_appid, kg_id_history_qa):
#     """
#     获取图谱信息并处理相关数据。
#
#     该函数从指定的应用ID和图谱ID中获取图谱信息，提取特定实体类型的配置信息，并构建相关的数据字典。返回的字典包括实体类型及其本体信息、向量索引字段以及一些辅助信息如空间名称等。
#
#     :arg ad_appid: 应用ID
#     :arg kg_id_history_qa: 图谱ID
#
#     :returns: 三个字典，分别是实体类型及其本体信息(entity_types)、实体类型及其向量索引字段(vector_index_filed)和其他辅助信息(data_params)
#
#     :raises: 无明确异常说明
#
#     """
#     data_params = {}
#     logger.info(f"data_params = {data_params}")
#     """获取图谱信息"""
#     # 从解析的数据中提取字段并赋值给变量
#     # try:
#     #     filter_conds = search_params.filter
#     # except:
#     #     filter_conds = {}
#     # stop_entity_infos = filter_conds.get('stop_entity_infos', [])
#     # # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
#     # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#     indextag2tag = {}  # 实体类型有大写时
#     # 获取图谱本体信息
#     # self.kg_info_url: str = self.builder_url + "/graph/{kg_id}"
#     # builder_url: str = "/api/builder/v1"
#     # kg_otl = await ad_builder_get_kg_info(search_params.ad_appid, search_params.kg_id)
#
#     kg_otl = await ad_builder_get_kg_info(ad_appid, kg_id_history_qa)
#     # logger.debug(f"kg_otl = {kg_otl}")
#     # 图谱信息kg_otl是字典, res为key
#     # kg_otl['graph_baseInfo']['graph_DBName']是土空间名称, 命名为变量space_name,值比如 ud2178f9ef81711ef9d057a78d1fb505e-2
#     # AD图谱的opensearch索引名称命名规则是 {space_name}_{实体类名称}
#     # return  json.dumps(kg_otl,indent=4, ensure_ascii=False, sort_keys=True)
#     # return json.dumps(kg_otl, indent=4, ensure_ascii=False, sort_keys=False)
#     kg_otl = kg_otl['res']
#     # 某些AD版本中(kg_otl['graph_baseInfo']是list
#     if isinstance(kg_otl['graph_baseInfo'], list):
#         space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
#     else:
#         space_name = kg_otl['graph_baseInfo']['graph_DBName']
#     data_params['space_name'] = space_name
#     # # kg_otl['graph_otl'][0]['entity']是所有实体的配置信息
#     # # kg_otl['graph_otl'][0]['edge']是所有边的配置信息
#     vertices = kg_otl['graph_otl'][0]['entity']
#     # # entity_types 字典{实体类型名：实体本体信息}
#     entity_types = {}
#     # # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#     vector_index_filed = {}
#     # # vertex['name']是实体类型名,比如 dimension_model,
#     # vertices是字典列表,每个字典是一个实体类的配置信息
#     for vertex in vertices:
#         # 目前版本只需要获取 `samples_requirements`(`正负样例`) 一个点的图谱信息
#         if vertex['name'] == 'samples_requirements' :
#             # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#             indextag2tag[vertex['name'].lower()] = vertex['name']
#             # entity_types 字典{实体类型名：实体本体信息}
#             entity_types[vertex['name']] = vertex
#             # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#             # 数据样例 "vector_generation": ["description", "name"]
#             vector_index_filed[vertex['name']] = vertex['vector_generation']
#     # data_params['indextag2tag'] = indextag2tag
#     # # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # # data_params['type2names']
#     # # data_params['space_name']
#     # # data_params['indextag2tag']
#     # return json.dumps(entity_types, indent=4, ensure_ascii=False, sort_keys=False), \
#     # json.dumps(vector_index_filed, indent=4, ensure_ascii=False, sort_keys=False), \
#     # json.dumps(data_params, indent=4, ensure_ascii=False, sort_keys=False)
#     return entity_types, vector_index_filed, data_params


# async def get_kgotl_search_ke_single(ad_appid, kg_id_search_ke_single, vertex_name):
#     """
#     获取服务超市找数问答知识增强图谱信息并处理相关数据的通用函数, 只有单一节点时（ ke 是 knowledge enhancement 的缩写）
#
#     该函数从指定的应用ID和图谱ID中获取图谱信息，提取特定实体类型的配置信息，并构建相关的数据字典。返回的字典包括实体类型及其本体信息、向量索引字段以及一些辅助信息如空间名称等。
#
#     :arg ad_appid: 应用ID
#     :arg kg_id_ke_single: 只有单一节点时,服务超市找数问答知识增强图谱ID
#
#     :returns: 三个字典，分别是实体类型及其本体信息(entity_types)、实体类型及其向量索引字段(vector_index_filed)和其他辅助信息(data_params)
#
#     :raises: 无明确异常说明
#
#     """
#     data_params = {}
#     logger.info(f"data_params = {data_params}")
#     """获取图谱信息"""
#     # 从解析的数据中提取字段并赋值给变量
#     # try:
#     #     filter_conds = search_params.filter
#     # except:
#     #     filter_conds = {}
#     # stop_entity_infos = filter_conds.get('stop_entity_infos', [])
#     # # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
#     # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#     indextag2tag = {}  # 实体类型有大写时
#     # 获取图谱本体信息
#     # self.kg_info_url: str = self.builder_url + "/graph/{kg_id}"
#     # builder_url: str = "/api/builder/v1"
#     # kg_otl = await ad_builder_get_kg_info(search_params.ad_appid, search_params.kg_id)
#
#     kg_otl = await ad_builder_get_kg_info(
#         appid=ad_appid,
#         graph_id=kg_id_search_ke_single
#     )
#     # logger.debug(f"kg_otl = {kg_otl}")
#     # 图谱信息kg_otl是字典, res为key
#     # kg_otl['graph_baseInfo']['graph_DBName']是土空间名称, 命名为变量space_name,值比如 ud2178f9ef81711ef9d057a78d1fb505e-2
#     # AD图谱的opensearch索引名称命名规则是 {space_name}_{实体类名称}
#     # return  json.dumps(kg_otl,indent=4, ensure_ascii=False, sort_keys=True)
#     # return json.dumps(kg_otl, indent=4, ensure_ascii=False, sort_keys=False)
#     kg_otl = kg_otl['res']
#     # 某些AD版本中(kg_otl['graph_baseInfo']是list
#     if isinstance(kg_otl['graph_baseInfo'], list):
#         space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
#     else:
#         space_name = kg_otl['graph_baseInfo']['graph_DBName']
#     data_params['space_name'] = space_name
#     # # kg_otl['graph_otl'][0]['entity']是所有实体的配置信息
#     # # kg_otl['graph_otl'][0]['edge']是所有边的配置信息
#     vertices = kg_otl['graph_otl'][0]['entity']
#     # # entity_types 字典{实体类型名：实体本体信息}
#     entity_types = {}
#     # # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#     vector_index_filed = {}
#     # # vertex['name']是实体类型名,比如 dimension_model,
#     # vertices是字典列表,每个字典是一个实体类的配置信息
#     for vertex in vertices:
#         # 目前版本只需要获取 `samples_requirements`(`正负样例`) 一个点的图谱信息
#         # if vertex['name'] == 'samples_requirements' :
#         if vertex['name'] == vertex_name:
#             # indextag2tag 字典 {实体类型名称的小写形式: 实体类型名称的实际形式},因为有时候实际名称中有大写,用这个映射关系查实际的实体类型名称
#             indextag2tag[vertex['name'].lower()] = vertex['name']
#             # entity_types 字典{实体类型名：实体本体信息}
#             entity_types[vertex['name']] = vertex
#             # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
#             # 数据样例 "vector_generation": ["description", "name"]
#             vector_index_filed[vertex['name']] = vertex['vector_generation']
#     # data_params['indextag2tag'] = indextag2tag
#     # # type2names 字典 是前端传来的停用实体,现在已经废弃
#     # # data_params['type2names']
#     # # data_params['space_name']
#     # # data_params['indextag2tag']
#     # return json.dumps(entity_types, indent=4, ensure_ascii=False, sort_keys=False), \
#     # json.dumps(vector_index_filed, indent=4, ensure_ascii=False, sort_keys=False), \
#     # json.dumps(data_params, indent=4, ensure_ascii=False, sort_keys=False)
#     return entity_types, vector_index_filed, data_params


# async def graph_call(ad_appid, kg_id, params):
#     result= await custom_graph_call(kg_id=kg_id, ad_appid=ad_appid, params=params)
#     return result

# async def graph_call_dip(x_account_id,x_account_type, kg_id, params):
#     result= await custom_graph_call_dip(
#         x_account_id=x_account_id,
#         x_account_type=x_account_type,
#         kg_id=kg_id,
#         params=params
#     )
#     return result

async  def get_connected_subgraph_catalog(ad_appid, kg_id, datacatalog_graph_vid):
    formatted_nebula_clause = prompts_config.nebula_get_connected_subgraph_catalog_match.replace(
        "{datacatalog_graph_vid}",
        f"'{datacatalog_graph_vid}'")

    logger.info(f"formatted_nebula_clause = {formatted_nebula_clause}")
    result = await custom_graph_call(
        kg_id=kg_id,
        ad_appid=ad_appid,
        params=formatted_nebula_clause
    )
    final_result = {}
    # final_result["nodes"] = result["nodes"]
    # 过滤掉 properties 字段，防止数据量过大
    final_result["nodes"] = [
        {
            key: value for key, value in node.items() if key != "properties"
        }
        for node in result["nodes"]
    ]
    unique_edges = []
    unique_edge_id = set()
    for edge in result["edges"]:
        # logger.debug(f"edge = {edge}")
        if edge["id"] not in unique_edge_id:
            unique_edge_id.add(edge["id"])
            unique_edges.append(edge)
            # logger.debug(f"pass! this egge is unique!")

    # 更新数据中的 edges 列表
    final_result["edges"] = unique_edges
    return final_result


async def get_connected_subgraph_catalog_dip(x_account_id, x_account_type, kg_id, datacatalog_graph_vid):
    formatted_nebula_clause = prompts_config.nebula_get_connected_subgraph_catalog_match.replace(
        "{datacatalog_graph_vid}",
        f"'{datacatalog_graph_vid}'")

    logger.info(f"formatted_nebula_clause = {formatted_nebula_clause}")
    result = await custom_graph_call_dip(
        x_account_id=x_account_id,
        x_account_type=x_account_type,
        kg_id=kg_id,
        params=formatted_nebula_clause
    )
    final_result = {}
    # final_result["nodes"] = result["nodes"]
    # 过滤掉 properties 字段，防止数据量过大
    final_result["nodes"] = [
        {
            key: value for key, value in node.items() if key != "properties"
        }
        for node in result["nodes"]
    ]
    unique_edges = []
    unique_edge_id = set()
    for edge in result["edges"]:
        # logger.debug(f"edge = {edge}")
        if edge["id"] not in unique_edge_id:
            unique_edge_id.add(edge["id"])
            unique_edges.append(edge)
            # logger.debug(f"pass! this egge is unique!")

    # 更新数据中的 edges 列表
    final_result["edges"] = unique_edges
    return final_result

# AnyData 根据图谱实体的融合属性生成 vid
def get_md5(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    md = hashlib.md5()
    md.update(data)
    return md.hexdigest()

async def main():
    pass



