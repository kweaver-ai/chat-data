"""
@File: model_rank.py
@Date:2024-02-26
@Author : Danny.gao
@Desc: 排序：包括精排、重拍，后期规划基于业务对象-属性等
"""

import re
import json
from collections import defaultdict

from app.logs.logger import logger
from app.cores.categorize.common import ad_opensearch_connector
from app.cores.categorize.common import get_samples


class ModelFilter(object):
    def __init__(self):
        # AD参数
        self.appid = ''
        self.graph_id = ''

    async def get_prop_category_rules(self, prop_ids):
        """
        获取逻辑实体属性信息：获取对应的识别对象列表
        """
        params = []
        for prop_id in prop_ids:
            query_module = {
                'size': 10,
                'query': {
                    "bool": {
                        "must": [
                            {
                                'term': {
                                    'id.keyword': f'{prop_id}'
                                }
                            }
                        ]
                    }
                },
                '_source': {'includes': ['id', 'name', '识别规则列表']}
            }

            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': ['属性探查规则实体']
                }
            )
        logger.info(f'属性探查规则实体检索-params：{params}')
        # 切分数据
        responses = await ad_opensearch_connector(appid=self.appid, params=params)
        prop_category_infos = {}
        for prop_id, response in zip(prop_ids, responses['responses']):
            hits = response['hits']
            prop_category_infos[prop_id] = [hit['_source'] for hit in hits]
        return prop_category_infos

    async def get_prop_class_rules(self, prop_ids):
        """
        获取逻辑实体属性信息：获取对应的分级规则列表
        """
        params = []
        for prop_id in prop_ids:
            query_module = {
                'size': 10,
                'query': {
                    "bool": {
                        "must": [
                            {
                                'term': {
                                    'id.keyword': f'{prop_id}'
                                }
                            }
                        ]
                    }
                },
                '_source': {'includes': ['id', 'name', '分级规则列表']}
            }

            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': ['分级规则实体']
                }
            )
        logger.info(f'属性探查规则实体检索-params：{params}')
        # 切分数据
        responses = await ad_opensearch_connector(appid=self.appid, params=params)
        prop_class_nfos = {}
        for prop_id, response in zip(prop_ids, responses['responses']):
            hits = response['hits']
            prop_class_nfos[prop_id] = [hit['_source'] for hit in hits]
        return prop_class_nfos
    
    async def get_category_rules(self, rule_ids):
        """
        获取逻辑实体属性信息：获取对应的识别对象列表
        """
        params = []
        for rule_id in rule_ids:
            query_module = {
                'size': 10,
                'query': {
                    "bool": {
                        "must": [
                            {
                                'term': {
                                    'id.keyword': f'{rule_id}'
                                }
                            }
                        ]
                    }
                },
                '_source': {'includes': ['id', 'name', '识别规则正则']}
            }

            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': ['数据识别规则实体']
                }
            )
        logger.info(f'数据识别规则实体检索-params：{params}')
        # 切分数据
        responses = await ad_opensearch_connector(appid=self.appid, params=params)
        rule_infos = {}
        for rule_id, response in zip(rule_ids, responses['responses']):
            hits = response['hits']
            rule_infos[rule_id] = [hit['_source'] for hit in hits]
        return rule_infos
    
    async def get_class_rules(self, rule_ids):
        """
        获取逻辑实体属性信息：获取对应的识别对象列表
        """
        params = []
        for rule_id in rule_ids:
            query_module = {
                'size': 10,
                'query': {
                    "bool": {
                        "must": [
                            {
                                'term': {
                                    'id.keyword': f'{rule_id}'
                                }
                            }
                        ]
                    }
                },
                '_source': {'includes': ['id', 'name', '分级规则']}
            }

            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': ['分级规则实体']
                }
            )
        logger.info(f'数据识别规则实体检索-params：{params}')
        # 切分数据
        responses = await ad_opensearch_connector(appid=self.appid, params=params)
        class_rule_infos = {}
        for rule_id, response in zip(rule_ids, responses['responses']):
            hits = response['hits']
            class_rule_infos[rule_id] = [hit['_source'] for hit in hits]
        return class_rule_infos

    def apply_rules_to_samples(self, rule2prop, rule_infos, samples):
        """
        获取每个字段适配的数据识别规则列表
        """
        # 存储每个规则应用到的字段
        field2prop, prop2field = defaultdict(list), defaultdict(list)

        # 遍历每个规则
        for rule_id, rule_info in rule_infos.items():
            regex = re.compile(rule_info['正则表达式'])
            field_match_count = defaultdict(int)

            # 遍历每个样本
            for sample in samples:
                # 遍历每个字段
                for field_name, field_value in sample.items():
                    if regex.match(field_value):
                        field_match_count[field_name] += 1

            # 检查哪些字段大部分满足规则：80%
            for field_name, match_count in field_match_count.items():
                if match_count > len(samples) * 0.8:
                    prop_ids = rule2prop.get(rule_id, [])
                    if prop_ids:
                        field2prop[field_name].extend(prop_ids)
                        for prop_id in prop_ids:
                            prop2field[prop_id].append(field_name)
        # {'字段名称': ['逻辑实体属性ID']} 、 {'逻辑实体属性ID': ['字段名称']}
        return field2prop, prop2field

    def optimal_prop_groups(self, field_names, field2prop, prop2field, group_class_infos, last_field2prop_optimal: dict = None):
        """ TODO: 选择最优分类规则，目前是局部最优，可能需要改成全局最优 """
        field2prop_optimal = {}
        for field_name, prop_ids in field2prop.items():
            if last_field2prop_optimal and field_name in last_field2prop_optimal:
                continue
            # 如果之前规则
            # 初始化最优规则和安全级别
            optimal_group = None
            highest_class = 10

            # 遍历属性组合
            for prop_combination, current_class in group_class_infos.keys():
                # 检查当前规则组合是否是字段匹配规则的子集
                if set(prop_combination).issubset(set(prop_ids)):
                    # 这个属性组合对应的字段
                    is_all_visited = True
                    for prop_id in prop_combination:
                        _ = prop2field.get(prop_id)
                        if not set(_).intersection(field_names):
                            is_all_visited = False
                            break
                    # 按照从严原则选择安全级别最高的规则（值越小级别越高）
                    if current_class < highest_class and is_all_visited:
                        highest_class = current_class
                        optimal_group = prop_combination
                        # 存储最优规则
                        field2prop_optimal[field_name] = optimal_group
                        for prop_id in prop_combination:
                            _ = prop2field.get(prop_id)
                            for f in _:
                                if f in field2prop_optimal and field2prop_optimal[f][1] < highest_class:
                                    continue
                                else:
                                    if last_field2prop_optimal and f in last_field2prop_optimal:
                                        continue 
                                    field2prop_optimal[f] = optimal_group
        
        # 识别规则优先
        if last_field2prop_optimal:
            field2prop_optimal.update(last_field2prop_optimal)
        # {'字段名称': ['属性ID', '属性ID']}
        return field2prop_optimal

    async def run(self,
        technical_name,
        fields,
        search_datas,
        explore_subject_ids,
        view_source_catalog_name,
        af_auth
    ):
        # 解析逻辑实体属性关联的探查识别规则，并检索
        prop_ids = []
        if explore_subject_ids:
            prop_ids = explore_subject_ids
        else:
            # 只检索名称相似的属性探查规则
            for data in search_datas:
                for item in data:
                    prop_id = item.get('id', '')
                    if prop_id:
                        prop_ids.append(prop_id)
        prop_category_rule_infos = await self.get_category_rules(prop_ids=prop_ids)
        prop_class_rule_infos = await self.get_class_rules(prop_ids=prop_ids)

        # 解析探查识别规则对应的数据识别规则，并检索
        rule2prop, category_rule_ids = {}, []
        for prop_id, data in prop_category_rule_infos.items():
            rule_ids_ = [data['识别规则ID'] for item in data]
            for rule_id in rule_ids_:
                values = rule2prop.get(rule_id, [])
                values.append(prop_id)
                rule2prop[rule_id] = values
            category_rule_ids.extend(rule_ids_)
        category_rule_infos = self.get_category_rules(rule_ids=category_rule_ids)

        # 分级规则：属性组合的分级信息
        class_rule_ids = {}, []
        for prop_id, data in prop_class_rule_infos.items():
            rule_ids_ = [item['识别规则ID'] for item in data]
            class_rule_ids.extend(rule_ids_)
        class_rule_infos = self.get_category_rules(rule_ids=class_rule_ids)
        group_class_infos = {}
        for _, item in class_rule_infos.items():
            # TODO: 属性组合
            group_prop_ids = item.get('属性组合', [])
            group_prop_ids.append(prop_id)
            # 分级
            class_ = item['级别']
            group_class_infos[group_prop_ids] = class_
        
        # 采样逻辑视图数据
        samples = await get_samples(technical_name=technical_name,
                                    view_source_catalog_name=view_source_catalog_name,
                                    af_auth=af_auth)
        # 匹配数据识别规则
        field2prop, prop2field = self.apply_rules_to_samples(rule_infos=category_rule_infos, samples=samples)
        
        # 根据相似度，字段名称匹配属性
        field2prop_sim, prop2field_sim = defaultdict(list), defaultdict(list) 
        for field, datas in zip(search_datas):
            for item in datas:
                prop_id = item.get('id', '')
                if prop_id:
                    field2prop_sim[field].append(prop_id)
                    prop2field_sim[prop_id].append(field)

        # 根据 识别规则（最优组合） -> 相似 的优先级进行排序
        optimal_groups = self.optimal_prop_groups(group_class_infos=group_class_infos, 
                                                  field2prop=field2prop, 
                                                  prop2field=prop2field)
        optimal_groups = self.optimal_prop_groups(group_class_infos=group_class_infos,
                                                  field2prop=field2prop_sim,
                                                  prop2field=prop2field_sim,
                                                  last_field2prop_optimal=optimal_groups)
        filter_res = []
        for field_name, datas in zip(fields, search_datas):
            optimal_prop_ids = optimal_groups.get(field_name, [])
            prop_ids = [item.get('id', '') for item in datas if item.get('id', '')]
            prop_ids = optimal_prop_ids + [prop_id for prop_id in prop_ids if prop_id not in optimal_prop_ids]
            datas = sorted(datas, key=lambda x: prop_ids.index(x['id']))
            filter_res.append(datas)
        return filter_res

        


        