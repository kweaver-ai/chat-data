# -*- coding: utf-8 -*-
# @Time    : 2024/1/21 9:48
# @Author  : Glen.lv
# @File    : asset_search
# @Project : copilot
import json
import os,copy
from app.cores.cognitive_search.graph_func  import *
from app.cores.cognitive_search.search_func import *
from app.cores.cognitive_search.re_asset_search  import run_func
from app.cores.cognitive_search.re_analysis_search   import init_qa
from app.cores.cognitive_search.prompts_config import resource_entity,formview_entity

find_number_api = FindNumberAPI()

"""AI找数——列表部分/数据目录版接口函数"""
async def run_func_formview(request,search_params):
    '''2.0.0.3-AI找数-数据目录版接口函数'''
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "search_config/config_search_catalog.json")
    search_configs = get_search_configs()
    output = await run_func(search_params,request, file_path,'form_view',search_configs)
    print(json.dumps(output,indent=4,ensure_ascii=False))
    return output

"""AI找数——分析型问答部分/数据目录版"""
async def formview_catalog_analysis_main(request, search_params):
    '''2.0.0.3-AI找数-数据资源版接口函数'''
    query, ad_appid, output, headers, total_start_time, all_hits, drop_indices, limit = await init_qa(request, search_params)
    logger.info(f"OS召回数量：{len(all_hits)}")
    pro_view = []
    Permissions={}
    source_list = []
    for i in all_hits[:]:
        # 1数据目录2接口服务3逻辑视图
        if 'formview_uuid' in i['_source'].keys() :
            assets={}
            assets["resourcename"] = i['_source']["business_name"] if "business_name" in i['_source'].keys() else None
            assets["asset_type"] = '3'
            assets["owner_id"] = i['_source']["owner_id"] if "owner_id" in i['_source'].keys() else None
            assets["resourceid"] = i['_source']["formview_uuid"]
            source_list.append(assets)
        else:
            all_hits.remove(i)
    auth_id=find_number_api.user_all_auth(headers,search_params.subject_id)
    tasks = [find_number_api.sub_user_auth_state(i, search_params, headers,auth_id) for i in source_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res_suth, i in zip(results, all_hits):
        Permissions[i['_id']] = '1' if res_suth == "allow" else '0'
    if search_params.available_option == 2 and  "data-operation-engineer" not in search_params.roles and "data-development-engineer" not in search_params.roles:
        for i in all_hits[:]:
            if Permissions[i['_id']] == '1':
                description = i['_source']['description'] if 'description' in i['_source'].keys() else '暂无描述'
                pro_view.append({i['_id'] + '|' + i['_source']['business_name']: description})
    else:
        for i in all_hits[:]:
            description = i['_source']['description'] if 'description' in i['_source'].keys() else '暂无描述'
            pro_view.append({i['_id'] + '|' + i['_source']['business_name']: description})
    print('pro_view',pro_view)
    if 'Qwen2' in settings.LLM_NAME:prompt_name="all_table"
    else:prompt_name="old_all_table"
    task5 = asyncio.create_task(qw_gpt(pro_view, query, ad_appid, prompt_name,'table_name'))
    res, res_catalog_reason,res_load = await task5
    hits_graph = []
    for i in all_hits:
        if i['_id'] in [j.split('|')[0] for j in res]:
            hits_graph.append(i)
    # 组织答案文本
    entities=[]
    res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
    if len(hits_graph) > 0:
        hits_all = [i["_id"]+'|'+i["_source"]["business_name"] for i in hits_graph]
        if  len(hits_graph) == len(res):
            explanation_catalog,explanation_statu = add_label(res_catalog_reason,hits_all,0)
            if explanation_statu=='0':
                use_hits = [i["_id"] + '|' + i["_source"]["business_name"] for i in hits_graph]
                explanation_catalog = add_label_easy(res_explain, use_hits)
                print("话术不可用时，拼凑话术", explanation_catalog, explanation_statu)
            res_statu = '1'
            explanation_statu='1'
        else:
            use_hits = [i["_id"] + '|' + i["_source"]["business_name"] for i in hits_graph]
            explanation_catalog = add_label_easy(res_explain, use_hits)
            print("话术不可用时，拼凑话术", explanation_catalog)
            explanation_catalog,res_statu,explanation_statu = ' ','1','0'
    else:
        explanation_catalog, res_statu, explanation_statu = ' ', '0', '0'
    for num, i in enumerate(hits_graph):
        formview_entity_copy = copy.deepcopy(formview_entity)
        formview_entity_copy["id"] = i["_id"]
        formview_entity_copy["default_property"]["value"] = i["_source"]["business_name"]
        for props in formview_entity_copy["properties"][0]["props"]:
            if props["name"] in i["_source"].keys():
                props['value'] = i["_source"][props["name"]]
        if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
            entities.append({
                "starts": [],
                "entity": formview_entity_copy,
                "score": limit - num,
                'is_permissions': '1'
            })
        else:
            entities.append({
                "starts": [],
                "entity": formview_entity_copy,
                "score": limit - num,
                'is_permissions': Permissions[i["_id"]]
            })
    output['explanation_formview'] = explanation_catalog
    output['entities'] = entities
    output['count'] = len(hits_graph)
    output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    print(json.dumps(output, indent=4, ensure_ascii=False))
    return output, res_statu, explanation_statu

"""AI找数——分析型问答部分/数据资源版"""
async def formview_resource_analysis_main(request, search_params):
    '''2.0.0.3-AI找数-数据资源版接口函数'''
    output, headers, total_start_time, all_hits, drop_indices = await init_qa(request, search_params)
    logger.info(f"OS召回数量：{len(all_hits)}")
    pro_view = []
    Permissions={}
    source_list = []
    for i in all_hits[:]:
        # 1数据目录2接口服务3逻辑视图
        if 'asset_type' in i['_source'].keys() and i['_source']['asset_type'] == '3'\
                and i['_source']['online_status'] in ['online','down-auditing','down-reject']:
            source_list.append(i['_source'])
        else:all_hits.remove(i)
    auth_id = await find_number_api.user_all_auth(headers,search_params.subject_id)
    print('auth_id',auth_id)
    tasks = [find_number_api.sub_user_auth_state(i, search_params, headers, auth_id) for i in source_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res_suth, i in zip(results, all_hits):
        Permissions[i['_id']] = '1' if res_suth == "allow" else '0'
    if search_params.available_option == 2 and "data-operation-engineer" not in search_params.roles and "data-development-engineer" not in search_params.roles:
        for i in all_hits[:]:
            if Permissions[i['_id']] == '1':
                description = i['_source']['description'] if 'description' in i['_source'].keys() else '暂无描述'
                pro_view.append({i['_id'] + '|' + i['_source']['resourcename']: description})
    else:
        for i in all_hits[:]:
            description = i['_source']['description'] if 'description' in i['_source'].keys() else '暂无描述'
            pro_view.append({i['_id'] + '|' + i['_source']['resourcename']: description})
    print('pro_view',pro_view)
    if 'Qwen2' in settings.LLM_NAME:prompt_name="all_table"
    else:prompt_name="old_all_table"
    task5 = asyncio.create_task(qw_gpt(pro_view, search_params.query, search_params.ad_appid, prompt_name,'table_name'))
    res, res_formview_reason,res_load = await task5
    hits_graph = []
    for i in all_hits:
        if i['_id'] in [j.split('|')[0] for j in res]:
            hits_graph.append(i)
    # 组织答案文本
    entities=[]
    res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
    if len(hits_graph) > 0:
        hits_all = [i["_id"]+'|'+i["_source"]["resourcename"] for i in hits_graph]
        if  len(hits_graph) == len(res):
            explanation_formview,explanation_statu = add_label(res_formview_reason,hits_all,0)
            print("大模型返回话术", explanation_formview, explanation_statu)
            if explanation_statu=='0':
                use_hits=[i["_id"]+'|'+i["_source"]["resourcename"] for i in hits_graph]
                explanation_formview=add_label_easy(res_explain,use_hits)
                print("话术不可用时，拼凑话术", explanation_formview, explanation_statu)
            res_statu = '1'
            explanation_statu = '1'
        else:
            use_hits = [i["_id"] + '|' + i["_source"]["resourcename"] for i in hits_graph]
            explanation_formview = add_label_easy(res_explain, use_hits)
            print("话术不可用时，拼凑话术", explanation_formview)
            explanation_formview,res_statu,explanation_statu = ' ','1','0'
    else:
        explanation_formview, res_statu, explanation_statu = ' ', '0', '0'
    for num, i in enumerate(hits_graph):
        resource_entity_copy=copy.deepcopy(resource_entity)
        resource_entity_copy["id"] = i["_id"]
        resource_entity_copy["default_property"]["value"] = i["_source"]["resourcename"]
        for props in resource_entity_copy["properties"][0]["props"]:
            if props["name"] in i["_source"].keys():
                props['value'] = i["_source"][props["name"]]
        if  "data-operation-engineer"  in search_params.roles or "data-development-engineer" in search_params.roles:
           entities.append({
                "starts": [],
                "entity": resource_entity_copy,
                "score": search_params.limit - num,
                'is_permissions':'1'
            })
        else:
            entities.append({
                "starts": [],
                "entity": resource_entity_copy,
                "score": search_params.limit - num,
                'is_permissions': Permissions[i["_id"]]
            })

    output['explanation_formview'] = explanation_formview
    output['entities'] = entities
    output['count'] = len(hits_graph)
    output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
    total_end_time = time.time()
    total_time_cost = total_end_time - total_start_time
    logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
    print(json.dumps(output, indent=4, ensure_ascii=False))
    return output, res_statu, explanation_statu






