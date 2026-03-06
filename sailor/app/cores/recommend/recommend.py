"""
@File: recommend.py
@Date:2024-03-11
@Author : Danny.gao
@Desc: 推荐接口
"""

import math
import jieba
from app.logs.logger import logger
from app.cores.recommend.common import af_params_connector
from app.cores.recommend.models import table_recall, flow_recall, code_recall, check_code_recall, view_recall, \
    label_recall, field_subject_recall, field_rule_recall, explore_rule_recall, check_indicator_recall
from app.cores.recommend.models import table_rank, flow_rank, code_rank, check_code_rank, view_rank, label_rank, \
    field_subject_rank, field_rule_rank, explore_rule_rank, check_indicator_rank
from app.cores.recommend.models import label_filter, fiel_rule_filter, explore_rule_filter
from app.cores.recommend.models import check_code_check, check_indicator_check
from app.cores.recommend.models import field_subject_align
from app.cores.recommend.models import explore_rule_generate
from app.cores.recommend._models import ConfigParams
from app.dependencies.opensearch import OpenSearchClient
from app.utils.stop_word import get_default_stop_words

async def recommendTable(data, graph_id, appid):
    table_infos = []
    logger.info('智能推荐之API1：表单推荐接口......')
    logger.info(f'INPUT：\ndata: {data}\ngraph_id: {graph_id}\nappid: {appid}')

    # ################################################ COMMON UTILS
    # ad 参数
    table_recall.appid = appid
    table_recall.graph_id = graph_id
    table_rank.appid = appid
    table_rank.graph_id = graph_id
    # af 配置字典
    params = await af_params_connector()
    top_n = params.get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10
    min_score = params.get('min_score', 0.75)
    dept_layer = params.get('dept_layer', 3)
    dept_layer = int(dept_layer) if dept_layer else 3
    domain_layer = params.get('domain_layer', 3)
    domain_layer = int(domain_layer) if domain_layer else 3
    q_bus_domain_weight = params.get('q_bus_domain_weight', 0.0)
    s_bus_domain_used_weight = params.get('s_bus_domain_used_weight', 0.0) * params.get('s_bus_domain_weight', 0.0)
    s_bus_domain_unused_weight = params.get('s_bus_domain_unused_weight', 0.0) * params.get('s_bus_domain_weight', 0.0)
    s_dept_used_weight = params.get('s_dept_used_weight', 0.0) * params.get('s_dept_weight', 0.0)
    s_dept_unused_weight = params.get('s_dept_unused_weight', 0.0) * params.get('s_dept_weight', 0.0)
    s_info_sys_used_weight = params.get('s_info_sys_used_weight', 0.0) * params.get('s_info_sys_weight', 0.0)
    s_info_sys_unused_weight = params.get('s_info_sys_unused_weight', 0.0) * params.get('s_info_sys_weight', 0.0)

    # ################################################ QUERY/SORT
    # texts
    text = data.key
    text = data.table.name if not text else text
    if not text:
        logger.info(f'OUTPUT: {table_infos}')
        return {'answers': {'tables': table_infos}}
    # 场景：domain、dept、fields
    scene_query, scene_sort = {}, {}
    # 业务模型：只影响召回
    if data.business_model_name:
        scene_query['model'] = ([data.business_model_name], 1.0/3.0)
    if data.domain:
        domain_name = data.domain.domain_name
        domain_path_ids = data.domain.domain_path_id.split('/')[:domain_layer]
        scene_query['domain'] = ([domain_name], q_bus_domain_weight)
        scene_sort['domain'] = (domain_path_ids, domain_layer, s_bus_domain_used_weight, s_bus_domain_unused_weight)
    if data.dept:
        dept_path_ids = data.dept.dept_path_id.split('/')[:dept_layer]
        scene_sort['dept'] = (dept_path_ids, dept_layer, s_dept_used_weight, s_dept_unused_weight)
    if data.info_system:
        info_system_ids = []
        for _ in data.info_system:
            info_system_ids.append(_.info_system_id)
        scene_sort['info_system'] = (info_system_ids, 1, s_info_sys_used_weight, s_info_sys_unused_weight)

    # ################################################ ALGORITHMS
    # 召回
    try:
        recall_res = await table_recall.run(texts=[text], scene=scene_query, params=params)
    except:
        logger.info('召回阶段报错！！！')
        return {'answers': {'tables': table_infos}}
    # 排序
    try:
        rank_res = await table_rank.run(recall_res=recall_res, scene=scene_sort)
    except:
        logger.info('重排序阶段报错！！！')
        return {'answers': {'tables': table_infos}}
    # ################################################ RESULT
    # 封装结果aaaaaaaa
    try:
        rank_res = rank_res[0] if rank_res else {}
        count = 1
        for id_, res in rank_res.items():
            if count > top_n:
                break
            # 关键字检索得分范围[min_score, 2]，向量检索得分范围[min_score, 2]，相加后得分范围score=[2*min_score, 4]
            # 场景权重得分范围2*score=[4*min_score, 8]
            # 利用softmax计算得分，低于阈值则break
            score = res['_score']
            if res.get('query_score', 0) > 0.9 or res.get('vector_score', 0) > 1.9:
                pass
            else:
                score = 1 / (1 + math.exp(-score))
                if score < min_score:
                    break
            table_infos.append({
                'id': res['_source']['id'],
                'name': res['_source']['name'],
                'hit_score': score,
                'reason': res['score_path']
            })
            count += 1
    except:
        logger.info('封装结果阶段报错！！！')
        return {'answers': {'tables': table_infos}}
    logger.info(f'OUTPUT: {table_infos}')
    return {'answers': {'tables': table_infos}}


async def recommendFlow(data, graph_id, appid):
    flowchart_infos = []
    logger.info('智能推荐之API2：流程推荐接口......')
    logger.info(f'INPUT：\ndata: {data}\ngraph_id: {graph_id}\nappid: {appid}')
    # ad 参数
    flow_recall.appid = appid
    flow_recall.graph_id = graph_id
    # flow_rank.appid = appid
    # flow_rank.graph_id = graph_id
    # af 配置字典
    params = await af_params_connector()
    top_n = params.get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10
    min_score = params.get('min_score', 0.75)

    # texts
    fc_name = data.node.name
    if not fc_name:
        logger.info(f'OUTPUT: {flowchart_infos}')
        return {'answers': {'flowcharts': flowchart_infos}}

    # 召回
    try:
        recall_res = await flow_recall.run(texts=[fc_name], params=params)
        recall_res = recall_res[0] if recall_res else {}
    except:
        logger.info('召回阶段报错！！！')
        return {'answers': {'flowcharts': flowchart_infos}}
    # 排序

    # 封装结果
    try:
        count = 1
        for id_, res in recall_res.items():
            if count > top_n:
                break
            score = res['_score']
            if res.get('query_score', 0) > 0.9 or res.get('vector_score', 0) > 1.9:
                pass
            else:
                score = 1 / (1 + math.exp(-score))
                if score < min_score:
                    break
            flowchart_infos.append({
                'id': res['_source']['id'],
                'name': res['_source']['name'],
                'hit_score': score,
                'reason': res['score_path']
            })
            count += 1
    except:
        logger.info('封装结果阶段报错！！！')
        return {'answers': {'flowcharts': flowchart_infos}}
    logger.info(f'OUTPUT: {flowchart_infos}')
    return {'answers': {'flowcharts': flowchart_infos}}


async def recommendCode(data, graph_id, appid):
    standard_codes = {}
    logger.info('智能推荐之API3：标准推荐接口......')
    logger.info(f'INPUT：\ndata: {data}\ngraph_id: {graph_id}\nappid: {appid}')
    # ad 参数
    code_recall.appid = appid
    code_recall.graph_id = graph_id
    code_rank.appid = appid
    code_rank.graph_id = graph_id
    code_rank.self_department_ids = data.department_id

    # af 配置字典
    params = await af_params_connector()
    code_rank.first_department_ids = params.get("r_default_department_id", "")
    top_n = params.get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10
    min_score = params.get('min_score', 0.75)
    r_code_class_weight_list = [
        params.get('r_std_type_weight_0', 0.006),
        params.get('r_std_type_weight_1', 0.007),
        params.get('r_std_type_weight_2', 0.008),
        params.get('r_std_type_weight_3', 0.009),
        params.get('r_std_type_weight_4', 0.001),
        params.get('r_std_type_weight_5', 0.005),
        params.get('r_std_type_weight_6', 0.004),
        params.get('r_std_type_weight_99', 0.0)
    ]
    # texts
    table_name = data.table_name
    fields = [field.table_field_name for field in data.table_fields]
    # 召回
    try:
        recall_res = await code_recall.run(texts=fields, params=params)
    except:
        logger.info('召回阶段报错！！！')
        return {'answers': standard_codes}
    # 排序
    try:
        rank_res = await code_rank.run(recall_res=recall_res, scene={'r_code_class_weight_list': r_code_class_weight_list})
    except:
        logger.info('重排序阶段报错！！！')
        return {'answers': standard_codes}
    # 封装结果
    try:
        standard_codes_tmp = []
        for field, rank_res_ in zip(fields, rank_res):
            codes = []
            count = 1
            for id_, res in rank_res_.items():
                if count > top_n:
                    break
                codes.append({
                    'std_ch_name': res['_source']['name_cn'],
                    'std_code': res['_source']['code'],
                    'score': res['_score']
                })
                count += 1
            standard_codes_tmp.append({
                'table_field_name': field,
                'rec_stds': codes
            })
        standard_codes = {
            'table_name': table_name,
            'table_fields': standard_codes_tmp
        }
    except:
        logger.info('封装结果阶段报错！！！')
        return {'answers': standard_codes}
    logger.info(f'OUTPUT: {standard_codes}')
    return {'answers': standard_codes}


async def checkCode(datas, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', {}, {}
    logger.info('智能推荐之API4：标准一致性校验接口......')
    logger.info("参数是 {} 配置是 {}".format(datas, config))

    # 获取anydata appid、graph_id
    graph_id, appid =  await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败'
        return status, msg, rec_infos, log_infos


    # ad 参数
    check_code_recall.appid = appid
    check_code_recall.graph_id = graph_id
    check_code_rank.appid = appid
    check_code_rank.graph_id = graph_id
    check_code_check.appid = appid

    # af 配置字典
    params = await af_params_connector()
    params = params.get('rec_check_code', {})
    config = config.dict(exclude_defaults=True)
    params.update(config)

    # texts
    texts, new_data = [], []
    field_ids = []
    for idx, item in enumerate(datas):
        new_item = item.dict()
        if 'fields' in new_item:
            new_item.pop('fields')
        else:
            continue
        for field in item.fields:
            texts.append(field.field_name)
            new_data.append(
                {
                    'id': field.field_id,
                    'standard_id': field.standard_id,
                    'standard_name': field.standard_name,
                    'standard_type': field.standard_type,
                    'name': field.field_name,
                    'desc': field.field_desc,
                    'background': new_item
                }
            )
            field_ids.append(field.field_id)
    terms_musts = [[{'key': 'id', 'values': field_ids}]] * len(texts)

    if len(texts) == 0:
        rec_infos['rate'] = '{:.2f}'.format(0)
        rec_infos['reason'] = ""
        rec_infos['rec'] = []
        return True, f"输入text 为 【{texts}】", rec_infos, log_infos

    # 召回
    try:
        recall_res = await check_code_recall.run(texts=texts, terms_musts=terms_musts, params=params)
    except Exception as e:
        logger.info('召回阶段报错！！！')
        msg = f'封装结果阶段报错: {e}'
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await check_code_rank.run(recall_res=recall_res)
    except Exception as e:
        logger.info('重排序阶段报错！！！')
        msg = f'封装结果阶段报错: {e}'
        return status, msg, rec_infos, log_infos

    # 一致性校验
    try:
        msg, check_res, rate, reason, t_count, in_count = await check_code_check.run(params=params, input_datas=new_data, search_results=rank_res,
                                              group_names=['standard_name', 'standard_type'])
        # 业务侧的设计模板
        reason = f'其中{int(in_count)}个标准化字段名称相同，但{int(t_count-in_count)}个采用的标准依据分类不同。'
    except Exception as e:
        logger.info(f'一致性校验阶段报错：{e}')
        msg = f'一致性校验阶段报错: {e}'
        return status, msg, rec_infos, log_infos

    # 封装日志
    if params.get('log', {}).get('with_all', False):
        log_infos['recall'] = recall_res
        log_infos['rank'] = rank_res
        log_infos['check'] = {
            'rec': check_res,
            'rate': rate,
            'reason': reason
        }
    else:
        if params.get('log', {}).get('with_recall', False):
            log_infos['recall'] = recall_res
        if params.get('log', {}).get('with_rank', False):
            log_infos['rank'] = rank_res
        if params.get('log', {}).get('with_check', False):
            log_infos['check'] = {
                'rec': check_res,
                'rate': rate,
                'reason': reason
            }
    # 封装结果
    status = True
    rec_infos['rate'] = '{:.2f}'.format(rate)
    rec_infos['reason'] = reason
    rec_infos['rec'] = check_res
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos


async def recommendView(data, graph_id, appid):
    view_infos = []
    logger.info('智能推荐之API5：视图推荐接口......')
    logger.info(f'INPUT：\ndata: {data}\ngraph_id: {graph_id}\nappid: {appid}')

    # ################################################ COMMON UTILS
    try:
        # ad 参数
        view_recall.appid = appid
        view_recall.graph_id = graph_id
        view_rank.appid = appid
        view_rank.graph_id = graph_id
        # ################################################ QUERY/SORT
        # texts
        text = data.table.name
        if not text:
            logger.info(f'OUTPUT: {view_infos}')
            return {'answers': {'tables': view_infos}}
        fields = [field.name for field in data.fields]
        # 推荐范围：
        # 视图类型：默认元数据视图
        recommend_view_types = data.recommend_view_types
        recommend_view_types = recommend_view_types if recommend_view_types else ['1']
        terms_musts = [[{'key': 'type', 'values': recommend_view_types}]]
        logger.info(f'推荐视图的视图类型：{recommend_view_types}')
    except:
        logger.info('参数解析阶段报错！！！')
        return {'answers': {'views': view_infos}}
    # ################################################ ALGORITHMS
    # 召回
    try:
        recall_res = await view_recall.run(texts=[text], terms_musts=terms_musts)
    except:
        logger.info('召回阶段报错！！！')
        return {'answers': {'views': view_infos}}
    # 排序
    try:
        rank_res = await view_rank.run(recall_res=recall_res, fields=fields)
    except:
        logger.info('重排序阶段报错！！！')
        return {'answers': {'views': view_infos}}
    # ################################################ RESULT
    # 封装结果
    try:
        rank_res = rank_res[0] if rank_res else {}
        count = 1
        for id_, res in rank_res.items():
            if count > 3:
                break
            # 关键字检索得分范围[min_score, 2]，向量检索得分范围[min_score, 2]，相加后得分范围score=[2*min_score, 4]
            # 场景权重得分范围2*score=[4*min_score, 8]
            # 利用softmax计算得分，低于阈值则break
            score = res['_score']
            view_infos.append({
                'id': res['_source']['id'],
                'name': res['_source']['name'],
                'hit_score': score,
                'reason': res['score_path'],
                'type': res['_source']['type']
            })
            count += 1
    except:
        logger.info('封装结果阶段报错！！！')
        return {'answers': {'views': view_infos}}
    logger.info(f'OUTPUT: {view_infos}')
    return {'answers': {'views': view_infos}}


async def recommendLabel(data: list, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', [], {}
    logger.info('智能推荐之API6：标签推荐接口......')
    logger.info(f'INPUT：\ndata: {data}')

    # 获取anydata appid、graph_id
    graph_id, appid =  await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败'
        return status, msg, rec_infos, log_infos

    # graph_id = '874'
    # appid = 'O7coTzeO7aE5P2u8KAv'
    # ################################################ COMMON UTILS
    try:
        # ad 参数
        label_recall.appid = appid
        label_recall.graph_id = graph_id
        label_rank.appid = appid
        label_rank.graph_id = graph_id
        label_filter.appid = appid

        # af 配置字典
        params = await af_params_connector()
        params = params.get('rec_label', {})
        config = config.dict(exclude_none=True)
        params.update(config)
        top_n = params.get('query', {}).get('top_n', 10)
        top_n = int(top_n) if isinstance(top_n, str) else 10

        # texts, category_id, range_type
        texts, new_data = [], []
        range_types = []
        terms_musts = []
        for item in data:
            if item.name:
                texts.append(item.name)
                new_data.append(item)
                range_types.append(item.range_type)
                musts = []
                if item.range_type:
                    # musts.append({'key': 'category_range_type', 'values': [item.range_type]})
                    musts.append({'key': 'category_range_type', 'values': item.range_type, "type": "wildcard"})
                if item.category_id:
                    musts.append({'key': 'category_id', 'values': item.category_id.split(',')})
                terms_musts.append(musts)
        if not texts:
            logger.info(f'OUTPUT: {rec_infos}')
            status = True
            msg = '解析参数为空，无需推荐'
            return status, msg, rec_infos, log_infos
        # 推荐范围：
        logger.info(f'推荐标签的范围：{terms_musts}')
    except Exception as e:
        logger.info(f'参数解析阶段报错：{e}')
        msg = f'参数解析阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # ################################################ ALGORITHMS
    # 召回
    try:
        recall_res = await label_recall.run(texts=texts, terms_musts=terms_musts, params=params)
    except Exception as e:
        logger.info(f'召回阶段报错：{e}')
        msg = f'召回阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await label_rank.run(recall_res=recall_res)
    except Exception as e:
        logger.info(f'重排序阶段报错：{e}')
        msg = f'重排序阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 筛选
    try:
        msg, filter_res = await label_filter.run(input_datas=new_data, search_results=rank_res, params=params)
    except Exception as e:
        logger.info(f'筛选阶段报错：{e}')
        msg = f'筛选阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # ################################################ RESULT
    # 封装日志fi
    if params.get('log', {}).get('with_all', False):
        log_infos['recall'] = recall_res
        log_infos['rank'] = rank_res
        log_infos['filter'] = filter_res
    else:
        if params.get('log', {}).get('with_recall', False):
            log_infos['recall'] = recall_res
        if params.get('log', {}).get('with_rank', False):
            log_infos['rank'] = rank_res
        if params.get('log', {}).get('with_filter', False):
            log_infos['filter'] = filter_res
    # 封装结果
    try:
        for text, range_type, res_ in zip(texts, range_types, filter_res):
            new_items, new_logs = [], {}
            count = 1
            res_ = res_.get('filter_data', [])
            for res in res_:
                if count > top_n:
                    break
                # score = '{:.2f}'.format(score)
                label_name = res['_source'].get('name', '')
                if not label_name:
                    continue
                new_item = {
                    'id': res['_source']['id'],
                    'name': label_name,
                    'category_name': res['_source'].get('category_name', ''),
                    'range_type': res['_source'].get('category_range_type', ''),
                    # 'hit_score': score,
                    # 'reason': res['score_path']
                }
                new_items.append(new_item)
                count += 1
            rec_infos.append(
                {
                    'name': text,
                    'range_type': range_type,
                    'rec': new_items
                }
            )
            status = True
    except Exception as e:
        logger.info(f'封装结果阶段报错：{e}')
        msg = f'封装结果阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos


async def checkIndicator(datas: list, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', {}, {}
    logger.info('智能推荐之API7：指标一致性校验接口......')

    # 获取anydata appid、graph_id
    graph_id, appid =  await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败'
        return status, msg, rec_infos, log_infos

    # graph_id = '3'
    # appid = 'OIZ6_KHCKIk-ASpNLg5'

    # ad 参数
    check_indicator_recall.appid = appid
    check_indicator_recall.graph_id = graph_id
    check_indicator_rank.appid = appid
    check_indicator_rank.graph_id = graph_id
    check_indicator_check.appid = appid
    # af 配置字典
    params = await af_params_connector()
    params = params.get('rec_check_indicator', {})
    config = config.dict(exclude_defaults=True)
    params.update(config)

    # texts
    texts, new_data = [], []
    indicator_ids = []
    for indicator in datas:
        new_item = {}
        for k, v in indicator.dict().items():
            if k not in ['indicator_id', 'indicator_name', 'indicator_desc']:
                new_item[k] = v
        texts.append(indicator.indicator_name)
        new_data.append(
            {
                'id': indicator.indicator_id,
                'name': indicator.indicator_name,
                'desc': indicator.indicator_desc,
                'business_domain_id': indicator.business_domain_id,
                'business_domain_name': indicator.business_domain_name,
                'indicator_formula': new_item.get("indicator_formula", ""),
                'indicator_unit': new_item.get("indicator_unit", ""),
                'indicator_cycle': new_item.get("indicator_cycle", ""),
                'indicator_caliber': new_item.get("indicator_caliber", ""),
                'background': new_item,
            }
        )
        indicator_ids.append(indicator.indicator_id)
    terms_musts = [[{'key': 'id', 'values': indicator_ids}]] * len(texts)

    # 召回
    try:
        recall_res = await check_indicator_recall.run(texts=texts, terms_musts=terms_musts, user_vector=False)
    except Exception as e:
        logger.info(f'召回阶段报错: {e}')
        msg = f'召回阶段报错: {e}'
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await check_indicator_rank.run(recall_res=recall_res)
    except Exception as e:
        logger.info(f'重排序阶段报错: {e}')
        msg = f'重排序阶段报错: {e}'
        return status, msg, rec_infos, log_infos
    # 一致性校验
    try:
        msg, check_res, rate, reason, t_count, in_count = await check_indicator_check.run(params=params,
                                                                                          input_datas=new_data,
                                                                                          search_results=rank_res,
                                                                                          group_names=['indicator_formula',
                                                                                                      'indicator_unit',
                                                                                                       'indicator_cycle',
                                                                                                       'indicator_caliber'],
                                                                                          distinct=True,
                                                                                          i_type="check_indicator")
        # 业务侧的设计模板
        reason = f'共{int(t_count)}个相同名称的指标，其中{int(in_count)}个指标在多个业务流程中复用。'
    except Exception as e:
        logger.info(f'一致性校验阶段报错：{e}')
        msg = f'一致性校验阶段报错: {e}'
        return status, msg, rec_infos, log_infos

    # 封装日志
    if params.get('log', {}).get('with_all', False):
        log_infos['recall'] = recall_res
        log_infos['rank'] = rank_res
        log_infos['check'] = {
            'rec': check_res,
            'rate': rate,
            'reason': reason
        }
    else:
        if params.get('log', {}).get('with_recall', False):
            log_infos['recall'] = recall_res
        if params.get('log', {}).get('with_rank', False):
            log_infos['rank'] = rank_res
        if params.get('log', {}).get('with_check', False):
            log_infos['check'] = {
                'rec': check_res,
                'rate': rate,
                'reason': reason
            }
    # 封装结果
    status = True
    rec_infos['rate'] = '{:.2f}'.format(rate)
    rec_infos['reason'] = reason
    rec_infos['rec'] = check_res
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos


async def recommendFieldSubject(datas: list, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', [], {}
    logger.info('智能推荐之API8：业务对象识别（对齐字段、逻辑实体属性）......')
    logger.info(f'INPUT：\ndata: {datas}')

    # 获取anydata appid、graph_id
    graph_id, appid =  await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败。'
        return status, msg, rec_infos, log_infos

    # graph_id = '3'
    # appid = 'OIZ6_KHCKIk-ASpNLg5'

    # ad 参数
    field_subject_recall.appid = appid
    field_subject_recall.graph_id = graph_id
    field_subject_rank.appid = appid
    field_subject_rank.graph_id = graph_id
    field_subject_align.appid = appid

    # af 配置字典
    params = await af_params_connector()
    params = params.get('rec_field_subject', {})
    config = config.dict(exclude_defaults=True)
    params.update(config)
    top_n = params.get('query', {}).get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10

    # texts
    texts, new_data, align_data = [], [], []
    subject_ids_list = []
    for item in datas:
        tmp_data, tmp_align_data = [], []
        subject_ids = []
        for subject in item.subjects:
            subject_ids.append(subject.subject_id)
            tmp_align_data.append(
                {
                    'id': subject.subject_id,
                    'name': subject.subject_name,
                    'path': subject.subject_path,
                }
            )
        if not subject_ids:
            continue
        new_item = item.dict()
        if 'fields' in new_item:
            new_item.pop('fields')
        else:
            continue
        if 'subjects' in new_item:
            new_item.pop('subjects')
        else:
            continue
        for field in item.fields:
            texts.append(field.field_name)
            subject_ids_list.append(subject_ids)
            tmp_data.append(
                {
                    'id': field.field_id,
                    'standard_id': field.standard_id,
                    'name': field.field_name,
                    'desc': field.field_desc,
                    'background': new_item
                }
            )
        new_data.append(tmp_data)
        align_data.append(tmp_align_data)
    terms_musts = [[{'key': 'id', 'values': subject_ids}] for subject_ids in subject_ids_list]

    # 召回
    try:
        recall_res = await field_subject_recall.run(texts=texts, terms_musts=terms_musts, balance_weight={"vector": 0.2, "query": 0.8})
    except Exception as e:
        msg = f'召回阶段报错: {e}'
        logger.info(msg)
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await field_subject_rank.run(recall_res=recall_res)
    except Exception as e:
        msg = f'重排序阶段报错: {e}'
        logger.info(msg)
        return status, msg, rec_infos, log_infos
    # # 对齐（匹配）
    # try:
    #     # align_res[idx] = {'source': infox, 'target': infoy}
    #     msg, align_res, reasons = await field_subject_align.run(params=params, input_datas=new_data, align_datas=align_data, search_results=rank_res)
    # except Exception as e:
    #     msg = f'对齐（匹配）阶段报错: {e}'
    #     logger.info(msg)
    #     return status, msg, rec_infos, log_infos
    # 封装日志
    # if params.get('log', {}).get('with_all', False):
    #     log_infos['recall'] = recall_res
    #     log_infos['rank'] = rank_res
    #     log_infos['align'] = {
    #         'rec': align_res,
    #         'reason': reasons
    #     }
    # else:
    #     if params.get('log', {}).get('with_recall', False):
    #         log_infos['recall'] = recall_res
    #     if params.get('log', {}).get('with_rank', False):
    #         log_infos['rank'] = rank_res
    #     if params.get('log', {}).get('with_check', False):
    #         log_infos['check'] = {
    #             'rec': align_res,
    #             'reason': reasons
    #         }
    # 封装结果
    # try:
    #     for item in datas:
    #         table_name = item.table_name
    #
    #         res = []
    #         for field in item.fields:
    #             field_id = field.field_id
    #             field_name = field.field_name
    #             if field_id not in align_res or not field_name:
    #                 continue
    #
    #             info = align_res[field_id]
    #             target = info['target']
    #             if 'id' not in target:
    #                 continue
    #             subject_id = target['id']
    #             subject_name = target.get('name', '')
    #             res.append(
    #                 {
    #                     'field_id': field_id,
    #                     'field_name': field_name,
    #                     'subject_id': subject_id,
    #                     'subject_name': subject_name
    #                 }
    #             )
    #         rec_infos.append(
    #             {
    #                 'table_name': table_name,
    #                 'rec': res
    #             }
    #         )
    #     status = True
    # except Exception as e:
    #     msg = f'封装结果阶段报错: {e}'
    #     logger.info(msg)
    #     return status, msg, rec_infos, log_infos



    # for item in  rank_res:
    idx = 0
    align_data_all = []
    for inputs, aligns in zip(new_data, align_data):
        match_list = []
        target_info = dict()
        align_data_res = dict()
        for data in inputs:
            r_res = rank_res[idx]
            _id_x = data["id"]
            for _id_y, rs in r_res.items():
                match_list.append((_id_x, rs["_source"]["id"], rs["_score"]))

            idx += 1
        for align_sub in aligns:
            target_info[align_sub["id"]] = {"target": align_sub}
        match_list.sort(key=lambda x: x[2], reverse=True)

        visitor_x = dict()
        visitor_y = dict()
        for sub_match in match_list:
            if sub_match[0] in visitor_x or sub_match[1] in visitor_y:
                continue
            align_data_res[sub_match[0]] = target_info[sub_match[1]]
            visitor_x[sub_match[0]] = 1
            visitor_y[sub_match[1]] = 1
        align_data_all.append(align_data_res)

    try:
        for ix, item in enumerate(datas):
            table_name = item.table_name
            align_res_sub = align_data_all[ix]

            res = []
            for field in item.fields:
                field_id = field.field_id
                field_name = field.field_name
                if field_id not in align_res_sub or not field_name:
                    continue

                info = align_res_sub[field_id]
                target = info['target']
                if 'id' not in target:
                    continue
                subject_id = target['id']
                subject_name = target.get('name', '')
                res.append(
                    {
                        'field_id': field_id,
                        'field_name': field_name,
                        'subject_id': subject_id,
                        'subject_name': subject_name
                    }
                )
            rec_infos.append(
                {
                    'table_name': table_name,
                    'rec': res
                }
            )
        status = True
    except Exception as e:
        msg = f'封装结果阶段报错: {e}'
        logger.info(msg)
        return status, msg, rec_infos, log_infos
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos


async def recommendFieldRule(datas: list, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', [], {}
    logger.info('智能推荐之API9：业务规则推荐（推荐字段值域的编码规则）......')
    logger.info(f'INPUT：\ndata: {datas}')

    # 获取anydata appid、graph_id
    graph_id, appid = await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败'
        return status, msg, rec_infos, log_infos

    # graph_id = '3'
    # appid = 'OIZ6_KHCKIk-ASpNLg5'

    # ad 参数
    field_rule_recall.appid = appid
    field_rule_recall.graph_id = graph_id
    field_rule_rank.appid = appid
    field_rule_rank.graph_id = graph_id
    fiel_rule_filter.appid = appid

    # af 配置字典
    params = await af_params_connector()

    field_rule_rank.first_department_ids = params.get("r_default_department_id", "")
    field_rule_rank.self_department_ids = datas[0].department_id
    params = params.get('rec_field_rule', {})
    config = config.dict(exclude_defaults=True)
    params.update(config)
    top_n =  params.get('query', {}).get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10

    # texts
    texts, new_data = [], []
    for idx, item in enumerate(datas):
        new_item = item.dict()
        if 'field' in new_item:
            new_item.pop('field')
        for field in item.fields:
            if field.field_name:
                texts.append(field.field_name)
                new_data.append(
                    {
                        'field_name': field.field_name,
                        'background': new_item
                    }
                )

    # 召回
    try:
        recall_res = await field_rule_recall.run(texts=texts, params=params)
    except Exception as e:
        logger.info(f'召回阶段报错：{e}')
        msg = f'召回阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await field_rule_rank.run(recall_res=recall_res)
    except Exception as e:
        logger.info(f'重排序阶段报错：{e}')
        msg = f'重排序阶段报错：{e}'
        return status, msg, rec_infos, log_infos

    # 筛选
    try:
        msg, filter_res = await fiel_rule_filter.run(input_datas=new_data, search_results=rank_res, params=params)
    except Exception as e:
        logger.info(f'筛选阶段报错：{e}')
        msg = f'筛选阶段报错：{e}'
        return status, msg, rec_infos, log_infos

    # ################################################ RESULT
    # 封装日志
    if params.get('log', {}).get('with_all', False):
        log_infos['recall'] = recall_res
        log_infos['rank'] = rank_res
        log_infos['filter'] = filter_res
    else:
        if params.get('log', {}).get('with_recall', False):
            log_infos['recall'] = recall_res
        if params.get('log', {}).get('with_rank', False):
            log_infos['rank'] = rank_res
        if params.get('log', {}).get('with_filter', False):
            log_infos['filter'] = filter_res
    # 封装结果
    try:
        index = 0
        for item in datas:
            table_name = item.table_name
            field_rec_res = []
            for field in item.fields:
                rec_res = []
                text = field.field_name
                if not text:
                    continue
                filter_data = {} if len(filter_res) <= index else filter_res[index]
                filter_data = filter_data.get('filter_data', [])
                count = 1
                for res in filter_data:
                    if count > top_n:
                        break
                    name = res['_source'].get('name', '')
                    if not name:
                        continue
                    res = {
                        'rule_id': res['_source'].get('id', ''),
                        'rule_name': name,
                        # 'score': score,
                        # 'reason': res.get('score_path', '')
                    }
                    rec_res.append(res)
                    count += 1
                field_rec_res.append(
                    {
                        'name': text,
                        'rec': rec_res
                    }
                )
                index += 1

            rec_infos.append(
                {
                    'table_name': table_name,
                    'fields': field_rec_res
                }
            )
            status = True
    except Exception as e:
        logger.info(f'封装结果阶段报错：{e}')
        msg = f'封装结果阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos


async def recommendExploreRule(datas: list, config: ConfigParams):
    status, msg, rec_infos, log_infos = False, '', [], {}
    logger.info('智能推荐之API10：质量规则推荐（为逻辑视图推荐字段级别的编码规则、生成类SQL规则语句）......')
    logger.info(f'INPUT：\ndata: {datas}')

    # 获取anydata appid、graph_id
    graph_id, appid = await ad_basic_infos_connector()
    if not graph_id or not appid:
        msg = 'AnyData权限不正确：图谱获取失败'
        return status, msg, rec_infos, log_infos
    # graph_id = '3'
    # appid = 'OIZ6_KHCKIk-ASpNLg5'

    # ad 参数
    explore_rule_recall.appid = appid
    explore_rule_recall.graph_id = graph_id
    explore_rule_rank.appid = appid
    explore_rule_rank.graph_id = graph_id
    explore_rule_filter.appid = appid
    explore_rule_generate.appid = appid


    # af 配置字典
    params = await af_params_connector()
    params = params.get('rec_explore_rule', {})
    config = config.dict(exclude_defaults=True)
    params.update(config)
    top_n = params.get('query', {}).get('top_n', 10)
    top_n = int(top_n) if isinstance(top_n, str) else 10

    # texts
    texts, new_data = [], []
    for item in datas:
        new_item = item.dict()
        if 'field' in new_item:
            new_item.pop('field')
        for field in item.fields:
            if field.field_name:
                texts.append(field.field_name)
                new_data.append(
                    {
                        'id': field.field_id,
                        'name': field.field_name,
                        'desc': field.field_desc,
                        'background': new_item
                    }
                )
    # 召回
    try:
        recall_res = await explore_rule_recall.run(texts=texts, params=params)
    except Exception as e:
        logger.info(f'召回阶段报错: {e}')
        msg = f'召回阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 排序
    try:
        rank_res = await explore_rule_rank.run(recall_res=recall_res)
    except Exception as e:
        logger.info(f'重排序阶段报错: {e}')
        msg = f'重排序阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 筛选
    try:
        msg, filter_res = await explore_rule_filter.run(input_datas=new_data, search_results=rank_res, params=params)
    except Exception as e:
        logger.info(f'筛选阶段报错：{e}')
        msg = f'筛选阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    # 生成
    try:
        msg, generate_res = await explore_rule_generate.run(params=params, input_datas=new_data, api_flag='explore_rule')
    except Exception as e:
        msg = f'生成阶段报错：{e}'
        logger.info(msg)
        return status, msg, rec_infos, log_infos
    # ################################################ RESULT
    # 封装日志
    if params.get('log', {}).get('with_all', False):
        log_infos['recall'] = recall_res
        log_infos['rank'] = rank_res
        log_infos['filter'] = filter_res
    else:
        if params.get('log', {}).get('with_recall', False):
            log_infos['recall'] = recall_res
        if params.get('log', {}).get('with_rank', False):
            log_infos['rank'] = rank_res
        if params.get('log', {}).get('with_filter', False):
            log_infos['filter'] = filter_res
    # 封装结果
    try:
        index = 0
        for item in datas:
            table_name = item.view_name
            field_rec_res = []
            for field in item.fields:
                field_id = field.field_id
                text = field.field_name
                if not text:
                    continue
                # 推荐结果
                rec_res = []
                filter_data = {} if len(filter_res) <= index else filter_res[index]
                filter_data = filter_data.get('filter_data', [])
                count = 1
                for res in filter_data:
                    if count > top_n:
                        break
                    name = res['_source'].get('name', '')
                    if not name:
                        continue
                    res = {
                        'rule_id': res['_source'].get('id', ''),
                        'rule_name': name,
                    }
                    rec_res.append(res)
                    count += 1
                # 生成结果
                llm_res = generate_res.get(field_id, {})
                field_rec_res.append(
                    {
                        'field_name': text,
                        'recommend': rec_res,
                        'generate': llm_res.get('generate', ''),
                        'distinct': llm_res.get('distinct', ''),
                        'reason': llm_res.get('reason', '')
                    }
                )
                index += 1

            rec_infos.append(
                {
                    'view_name': table_name,
                    'rec': field_rec_res
                }
            )
        status = True
    except Exception as e:
        logger.info(f'封装结果阶段报: {e}')
        msg = f'封装结果阶段报错：{e}'
        return status, msg, rec_infos, log_infos
    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos






if __name__ == '__main__':
    import asyncio
    from app.handlers.recommend_handler import RecommendTableParams, RecommendFlowParams, RecommendCodeParams, CheckCodeParams
    domain = {
        "domain_id": "业务域id",
        "domain_name": "业务域名称",
        "domain_path": "业务域层级",
        "domain_path_id": "业务域层级id"
    }
    dept = {
        "dept_id": "组织部门id",
        "dept_name": "组织部门名称",
        "dept_path": "组织部门层级",
        "dept_path_id": "组织部门层级id"
    }
    info_system = [{
        "info_system_id": "信息系统id",
        "info_system_name": "信息系统名称",
        # "info_system_desc": "信息系统描述"
    }]

    logger.info('*****************表单推荐*****************')
    # data = {
    #     'af_query': {
    #         "business_model_id": "业务模型id",
    #         "business_model_name": "业务模型名称",
    #         "domain": domain,
    #         "dept": dept,
    #         "info_system": info_system,
    #         "table": {
    #             "name": "表单名称",
    #             "description": "表单描述"
    #         },
    #         "fields": [{
    #             "id": '0',
    #             "name": "字段中文名",
    #             "description": "字段描述"
    #         }],
    #         "key": "房屋信息"
    #     },
    #     'graph_id': '40',
    #     'appid': 'Nr8KsyyoK8x8B1Nk-vO'
    # }
    # params = RecommendTableParams(**data)
    # res = asyncio.run(recommendTable(data=params.af_query, graph_id=params.graph_id, appid=params.appid))
    # for item in res['answers']['tables']:
    #     print(item)

    logger.info('*****************流程推荐*****************')
    # data = {
    #     "af_query": {
    #         "business_model_id": "业务模型id,当前理解为主干业务id,后期做调整",
    #         "node": {
    #                 "id": "数据库中流程节点ID,即uuid",
    #                 "mxcell_id": "前端节点ID",
    #                 "name": "业务模型 ",
    #                 "description": "节点描述"
    #         },
    #         "parent_node": {
    #                 "id": "数据库中流程节点ID,即uuid",
    #                 "mxcell_id": "前端节点ID ",
    #                 "name": "节点名称 ",
    #                 "description": "节点描述 ",
    #                 "flowchart_id": "所属流程图的ID ",
    #                 "tables": ["表单ID1", "表单ID2"]
    #         },
    #         "flowchart": {
    #                 "id": "当前需要推荐流程的节点所在流程图ID",
    #                 "name": "流程图名称",
    #                 "description": "流程图描述 ",
    #                 "business_model_id": "流程图所在业务模型,当前理解为主干业务id,后期做调整",
    #                 "nodes": [
    #                         {
    #                                 "id": "数据库中流程节点ID,即uuid",
    #                                 "mxcell_id": "前端节点ID",
    #                                 "name": "节点名称",
    #                                 "description": "节点描述 "
    #                         }, {
    #                                 "id": "数据库中流程节点ID, 即uuid",
    #                                 "mxcell_id" :"前端节点ID ",
    #                                 "name": "节点名称",
    #                                 "description": "节点描述"
    #                         }
    #                 ]
    #         }
    #     },
    #     "graph_id": "40",
    #     "appid": "Nr8KsyyoK8x8B1Nk-vO"
    # }
    # params = RecommendFlowParams(**data)
    # res = asyncio.run(recommendFlow(data=params.af_query, graph_id=params.graph_id, appid=params.appid))
    # for item in res['answers']['flowcharts']:
    #     print(item)

    logger.info('*****************标准推荐*****************')
    data = {
        "query": {
            "table_id": "表单ID",
            "table_name": "全员核酸检测数据",
            "table_desc": "表单描述",
            "table_fields": [
                {
                    "table_field_id": "field-id-01",
                    "table_field_name": "身份证号码"
                },
                {
                    "table_field_id": "field-id-02",
                    "table_field_name": "移动电话号码"
                }
            ]
        },
        "graph_id": "40",
        "appid": "Nr8KsyyoK8x8B1Nk-vO"
    }
    params = RecommendCodeParams(**data)
    res = asyncio.run(recommendCode(data=params.query, graph_id=params.graph_id, appid=params.appid))
    for item in res['answers']['table_fields']:
        print(item['table_field_name'])
        for stds in item['rec_stds']:
            print(stds)

    logger.info('*****************标准一致性校验*****************')
    # data = {
    #     "check_af_query": [
    #         {
    #             "business_model_id": "业务模型id",
    #             "business_model_name": "业务模型名称",
    #             "domain": domain,
    #             "dept": dept,
    #             "info_system": info_system,
    #             "tables": [
    #                 {
    #                     "table_id": "table-01",
    #                     "table_name": "全员核酸检测数据",
    #                     "table_desc": "表单描述",
    #                     "table_fields": [
    #                         {
    #                             "field_id": "field-01",
    #                             "table_field_name": "身份证",
    #                             "table_field_desc": "字段描述",
    #                             "standard_id": "1762007480745689091"
    #                         }
    #                     ]
    #                 }
    #             ]
    #         }
    #     ],
    #     "graph_id": "40",
    #     "appid": "Nr8KsyyoK8x8B1Nk-vO"
    # }
    # params = CheckCodeParams(**data)
    # res = asyncio.run(checkCode(data=params.check_af_query, graph_id=params.graph_id, appid=params.appid))
    # for item in res['answers']:
    #     print(item)
