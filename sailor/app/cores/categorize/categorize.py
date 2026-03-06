"""
@File: recommend.py
@Date:2024-03-11
@Author : Danny.gao
@Desc: 推荐接口
"""

import math

from app.logs.logger import logger
# from app.cores.categorize.models import categorize_recall, categorize_rank, categorize_filter


async def dataCategorize(data, graph_id, appid, af_auth):
    props = {}
    logger.info('API：数据分类分级接口......')
    logger.info(f'INPUT：\ndata: {data}\ngraph_id: {graph_id}\nappid: {appid}')

    # ad 参数
    categorize_recall.appid = appid
    categorize_recall.graph_id = graph_id
    categorize_rank.appid = appid
    categorize_rank.graph_id = graph_id
    categorize_filter.graph_id = graph_id
    categorize_filter.appid = appid

    # texts
    view_id = data.view_id
    view_name = data.view_business_name
    view_technical_name = data.view_technical_name
    subject_id = data.subject_id
    view_fields = data.view_fields
    fields = [field.view_field_business_name for field in view_fields]

    # 探查的识别范围、逻辑视图所属的catalog信息
    explore_subject_ids = data.explore_subject_ids
    view_source_catalog_name = data.view_source_catalog_name
    term_musts = [[{'key': 'type', 'values': explore_subject_ids}] for _ in fields] \
        if explore_subject_ids else []

    # 召回
    try:
        recall_res = await categorize_recall.run(texts=fields, term_musts=term_musts)
    except:
        logger.info('召回阶段报错！！！')
        return {'answers': props}

    # 排序
    try:
        rank_res = await categorize_rank.run(view_name=view_name,
                                             view_subject_id=subject_id,
                                             view_fields=view_fields,
                                             recall_res=recall_res)
    except:
        logger.info('排序阶段报错！！！')
        rank_res = recall_res

    # 识别规则优先
    try:
        rule_res = await categorize_filter.run(technical_name=view_technical_name,
                                         fields=fields,
                                         search_datas=rank_res,
                                         explore_subject_ids=explore_subject_ids,
                                         view_source_catalog_name=view_source_catalog_name,
                                         af_auth=af_auth)
    except Exception as e:
        logger.info(f'识别规则阶段报错：{e}')
        rule_res = rank_res

    # 封装结果
    try:
        prop_infos = []
        for field, res in zip(view_fields, rule_res):
            subjects = []
            if field.view_field_business_name:
                count = int(categorize_recall.topn)
                res= res[:count] if len(res) > count else res
                scores = [math.exp(_.get('score', 0)) for _ in res]
                sum_score = sum(scores)
                for score, item in zip(scores, res):
                    score = score / sum_score
                    score = '{:.2f}'.format(score*100)
                    _source = item.get("_source", {})
                    subjects.append({
                        'subject_id': _source.get('id', ''),
                        'subject_name': _source.get('name', ''),
                        'score': score
                    })
            prop_infos.append({
                'view_field_id': field.view_field_id,
                'rel_subjects': subjects
            })
        props = {
            'view_id': view_id,
            'view_fields': prop_infos
        }
    except:
        logger.info('封装结果报错！！！')
        return {'answers': props}
    logger.info(f'OUTPUT: {props}')
    return {'answers': props}




