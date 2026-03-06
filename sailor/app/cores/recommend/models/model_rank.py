"""
@File: model_rank.py
@Date:2024-02-26
@Author : Danny.gao
@Desc: 排序：包括精排、重拍，后期规划基于业务对象-属性等
"""

import json

from app.logs.logger import logger
from app.cores.recommend.common import ad_opensearch_connector

class ModelRank(object):
    def __init__(self, params):
        self.entity_type = params.entity_type
        self.table2model = params.table2model
        self.model2domain = params.model2domain
        self.domain2dept = params.domain2dept
        self.dept2self = params.dept2self
        self.std_type = params.std_type
        self.filter_num_search = params.filter_num_search

        # AD参数
        self.appid = ''
        self.graph_id = ''
        self.first_department_ids = ''   # 优先匹配部门
        self.self_department_ids = ''  # 本部门

    async def get_layer_infos(self, search_index, ids, includes):
        params = []
        query_module = {
            'size': 200,
            'query': {
                "bool": {
                    "should": [
                        {
                            "terms": {
                                "id.keyword": ids
                            }
                        }
                    ]
                }
            },
            '_source': {'includes': includes}
        }
        params.append(
            {
                'kg_id': self.graph_id,
                'query': json.dumps(query_module),
                'tags': [search_index]
            }
        )
        logger.info(f'场景信息检索-params：{params}')
        response = await ad_opensearch_connector(appid=self.appid, params=params)
        response = response['responses'][0]
        return response

    async def get_count(self, search_index, ids, id_field):
        params = []
        for id_ in ids:
            query_module = {
                'size': 1,
                'min_score': 1,
                'query': {
                    'bool': {
                        'must': [
                            {
                                "terms": {
                                    f"{id_field}.keyword": [id_]
                                }
                            }
                        ]
                    }
                },
                '_source': {'includes': [id_field]}
            }
            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': [search_index]
                }
            )
        # logger.info(f'数量获取-params： {params}')
        response = await ad_opensearch_connector(appid=self.appid, params=params)
        return response['responses']

    async def run(self, recall_res, **kwargs):
        scenes = kwargs.get('scene', {})
        # 1 场景
        domains, domain_layer, s_bus_domain_used_weight, s_bus_domain_unused_weight = scenes.get('domain', ([], 99, 0, 0))
        depts, dept_layer, s_dept_used_weight, s_dept_unused_weight = scenes.get('dept', ([], 99, 0, 0))
        info_system, _, s_info_sys_used_weight, s_info_sys_unused_weight = scenes.get('info_system', ([], 1, 0, 0))
        self_department_weight, first_department_weight = 100, 200
        r_code_class_weight_list = scenes.get('r_code_class_weight_list', self.std_type)
        # 2 获取信息
        # 表单》》业务模型
        table2model_dico = {}
        if self.table2model and domains:
            ids = []
            for res in recall_res:
                for id_, item in res.items():
                    tb_id = item['_source'].get(self.table2model.query_field, '')
                    if tb_id:
                        ids.append(tb_id)
            layer_infos = await self.get_layer_infos(search_index=self.table2model.index,
                                                     ids=ids, includes=self.table2model.includes)
            for hit in layer_infos['hits']['hits']:
                tb_id = hit['_source']['id']
                modle_id = hit['_source']['business_model_id']
                table2model_dico[tb_id] = modle_id
        logger.info(f'表单》》业务模型数据：{table2model_dico}')
        # 业务模型》》业务域
        model2domain_dico = {}
        if self.model2domain and domains:
            if table2model_dico:
                ids = list(table2model_dico.values())
            else:
                ids = []
                for res in recall_res:
                    for id_, item in res.items():
                        domain_id = item['_source'].get(self.model2domain.query_field, '')
                        if domain_id:
                            ids.append(domain_id)
            if ids:
                layer_infos = await self.get_layer_infos(search_index=self.model2domain.index,
                                                         ids=ids, includes=self.model2domain.includes)
                for hit in layer_infos['hits']['hits']:
                    model_id = hit['_source']['id']
                    domain_id = hit['_source'].get('domain_id', '')
                    model2domain_dico[model_id] = domain_id
        logger.info(f'业务模型》》业务域数据：{model2domain_dico}')
        # 业务域》》组织部门
        domain2dept_dico, dept_ids = {}, []
        if self.domain2dept and domains and model2domain_dico:
            ids = list(model2domain_dico.values()) if model2domain_dico else []
            if ids:
                layer_infos = await self.get_layer_infos(search_index=self.domain2dept.index,
                                                         ids=ids, includes=self.domain2dept.includes)
                for hit in layer_infos['hits']['hits']:
                    domain_id = hit['_source']['id']
                    path_id = hit['_source'].get('path_id', '')
                    department_id = hit['_source'].get('department_id', '')
                    # '["0fb99a2a-17a4-46f9-bded-68eba01cc15d"]'
                    business_system = hit['_source'].get('business_system', '')
                    try:
                        business_system = eval(business_system) if business_system else []
                    except:
                        pass
                    domain2dept_dico[domain_id] = (path_id, department_id, business_system)
                    if department_id:
                        dept_ids.append(department_id)
        logger.info(f'业务域》》组织部门数据：{domain2dept_dico}')
        # 组织部门》》pathes
        dept2self_dico = {}
        if self.dept2self and depts and depts and dept_ids:
                layer_infos = await self.get_layer_infos(search_index=self.dept2self.index,
                                                         ids=dept_ids, includes=self.dept2self.includes)
                for hit in layer_infos['hits']['hits']:
                    dept_id = hit['_source']['id']
                    path_id = hit['_source'].get('path_id', '')
                    dept2self_dico[dept_id] = path_id
        logger.info(f'组织部门》》self layer数据：{dept2self_dico}')

        # 3 场景权重分配+分类权重分配（针对标准推荐）
        num = len(scenes)
        weight = 1. / (4*num) if num > 0 else 0
        rank_res = []
        for res in recall_res:
            new_res = {}
            for id_, item in res.items():
                score = item['_score']
                if self.table2model and domains:
                    # 业务模型
                    business_model_id = table2model_dico.get(item['_source']['id'], '')
                    item['_source']['business_model_id'] = business_model_id
                business_model_id = item['_source'].get('business_model_id', '')
                if self.model2domain and domains and business_model_id:
                    # 业务域
                    domain_id = model2domain_dico.get(business_model_id, '')
                    item['_source']['domain_id'] = domain_id
                domain_id = item['_source'].get('domain_id', '')
                if self.domain2dept and domains and domain_id:
                    path_id, department_id, business_system = domain2dept_dico.get(domain_id, ('', '', ''))
                    # 业务域层级/组织部门/信息系统
                    domain_path_ids = path_id.split('/')[:domain_layer]
                    item['_source']['domain_path_ids'] = domain_path_ids
                    item['_source']['department_id'] = department_id
                    item['_source']['business_system'] = business_system
                    # 第1个权重信息：业务域domain
                    intersection_domain = list(set(domains) & set(domain_path_ids))
                    if intersection_domain:
                        score *= (1 + s_bus_domain_used_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+doamin_use_weight:{s_bus_domain_used_weight})'
                    else:
                        score *= (1 + s_bus_domain_unused_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+doamin_unuse_weight:{s_bus_domain_unused_weight})'
                    # 第2个权重信息：信息系统info_system
                    intersection_info_system = list(set(info_system) & set(business_system))
                    if intersection_info_system:
                        score *= (1 + s_info_sys_used_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+info_system_use_weight:{s_info_sys_used_weight})'
                    else:
                        score *= (1 + s_info_sys_unused_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+info_system_unuse_weight:{s_info_sys_unused_weight})'
                dept_id = item['_source'].get('department_id', '')
                if self.dept2self and depts and dept_id and dept_ids:
                    dept_path_ids = dept2self_dico.get(dept_id, '').split('/')[:dept_layer]
                    item['_source']['dept_path_ids'] = dept_path_ids
                    # 第3个权重信息
                    intersection_dept = list(set(depts) & set(dept_path_ids))
                    if intersection_dept:
                        score *= (1 + s_dept_used_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+dept_use_weight:{s_dept_used_weight})'
                    else:
                        score *= (1 + s_info_sys_unused_weight)
                        item['score_path'] = f'{item["score_path"]} * (1+dept_unuse_weight:{s_info_sys_unused_weight})'
                if self.std_type:
                    std_type = item['_source'].get('std_type', '99').split('###')[-1]
                    try:
                        std_type = int(std_type)
                    except:
                        pass
                    std_type_weight = r_code_class_weight_list[std_type] if std_type < len(r_code_class_weight_list) else 0
                    # 第4个权重信息
                    score *= (1 + std_type_weight)
                    item['score_path'] = f'{item["score_path"]} * (1+std_type:{std_type_weight})'
                # 数据标准增加部门视角查询及推荐改造
                if self.first_department_ids or self.self_department_ids:
                    if item["_source"].get("department_ids", "") == self.first_department_ids:
                        score *= (1 + first_department_weight)
                    if item["_source"].get("department_ids", "") == self.self_department_ids:
                        score *= (1 + self_department_weight)

                item['_score'] = score
                new_res[id_] = item
            new_res = sorted(new_res.items(), key=lambda x: x[1]['_score'], reverse=True)
            new_res = {x[0]: x[1] for x in new_res}
            rank_res.append(new_res)

        """ 5. 过滤字段个数=0的表单（针对表单推荐）"""
        filter_rank_res = []
        if self.filter_num_search:
            table_ids = []
            for res in rank_res:
                for id_, item in res.items():
                    table_id = item.get('_source', {}).get('id', '')
                    if table_id:
                        table_ids.append(table_id)
            count_match_table_ids = []
            if table_ids:
                responses = await self.get_count(search_index=self.filter_num_search.index, ids=table_ids, id_field=self.filter_num_search.field)
                for table_id, response in zip(table_ids, responses):
                    total = response.get('hits', {}).get('total', {}).get('value', 0)
                    if total == 0:
                        continue
                    count_match_table_ids.append(table_id)
            logger.info(f'规则：字段个数不为0的表单ID，{count_match_table_ids}')
            # 筛选结果
            for res in rank_res:
                new_res = {}
                for id_, item in res.items():
                    view_id = item.get('_source', {}).get('id', '')
                    if view_id in count_match_table_ids:
                        new_res[id_] = item
                new_res = sorted(new_res.items(), key=lambda x: x[1]['_score'], reverse=True)
                new_res = {x[0]: x[1] for x in new_res}
                filter_rank_res.append(new_res)
        else:
            filter_rank_res = rank_res

        # for item in rank_res:
        #     print('*'*100)
        #     for k, v in item.items():
        #         print(k, v)
        logger.info(f'排序结果：{filter_rank_res}')
        return filter_rank_res


if __name__ == '__main__':
    import json
    import asyncio
    from app.cores.recommend.configs.config_rank import rank_table_params

    """ 推荐表单 """
    recall_res = []
    scene = {
        'domain': (['ebb6c708-0ffe-44b5-b21b-ba94b6478e33'], 3),
        'dept': (['b27d07b2-cfbf-11ee-9c92-f26894970da0'], 3),
        'info_system': (['0fb99a2a-17a4-46f9-bded-68eba01cc15d'], 1)
    }
    rank = ModelRank(params=rank_table_params)
    asyncio.run(rank.run(space_name='uac31ed44db6a11ee92da463c401ac90c-6', recall_res=recall_res, scene=scene))
    # for res in recall_res:
    #     for id_, item in res.items():
    #         print(id_, item)
