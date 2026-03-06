"""
@File: model_rank.py
@Date:2024-02-26
@Author : Danny.gao
@Desc: 排序：包括精排、重拍，后期规划基于业务对象-属性等
"""

import copy
import json
import collections

from config import settings
from app.logs.logger import logger
from app.cores.recommend.common.util import timer
from app.cores.recommend.common import ad_opensearch_connector, m3e_embeddings

ad_version = 3006
try:
    ad_version = int(str(settings.AD_VERSION).replace('.', ''))
except:
    pass


class ModelRank(object):
    def __init__(self, params):
        # 检索索引
        self.index = params.index
        # 参数配置
        self.vector_field = params.vector_search.field
        self.vector_min_score = params.vector_search.min_score
        self.vector_size = params.vector_search.size
        # 返回参数
        self.source_includes = params.includes

        # AD参数
        self.appid = ''
        self.graph_id = ''

    @timer
    async def is_multi_of_props(self, search_index, recall_res):
        # 所有逻辑实体属性集合
        props = []
        for res in recall_res:
            if isinstance(res, dict):
                for _, v in res.items():
                    prop = v.get("_source", dict()).get("name")
                    if prop:
                        props.append(prop)
            else:
                item = res[0] if len(res) > 1 else {}
                prop = item.get('name', '')
                if not prop:
                    continue
                props.append(prop)
        # 检索
        res = []
        if props:

            params = []
            query_module = {
                'size': 2,
                'query': {
                    'terms': {
                        'name.keyword': props
                    }
                },
                '_source': {'includes': ['name']}
            }
            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': [search_index]
                }
            )
            response = await ad_opensearch_connector(appid=self.appid, params=params)
            response = response['responses']
            for resp in response:
                for hit in resp.get('hits', {}).get('hits', {}):
                    name = hit.get('_source', {}).get('name', '')
                    if name:
                        res.append(name)
        return res

    @timer
    async def cal_cosine_similar_(self, search_index, view_name, fields, recall_res):
        # 收集所有的文本，并向量化
        texts = [f'{view_name}/{field.view_field_business_name}' for field in fields]
        embeddings = await m3e_embeddings(texts=texts)
        # 检索到的属性的id
        ids = []
        for res in recall_res:
            ids_ = []
            for key, item in res.items():
                # id_ = item.get('id', '')
                # if id_:
                #     ids_.append(id_)
                ids_.append(key)
            ids.append(ids_)
        # 检索得分
        responses = await self.by_embeddings(ids=ids, search_index=search_index, embeddings=embeddings)

        # 计算相似度
        final_res = collections.OrderedDict()
        for field, ids_, response in zip(fields, ids, responses):
            id_dico = {}
            for hit in response.get('hits', {}).get('hits', {}):
                id_ = hit.get('_source', {}).get('id', '')
                score = hit.get('_score', 0)
                if id_:
                    id_dico[id_] = score
            scores = []
            for id_ in ids_:
                score = id_dico.get(id_, 0)
                scores.append(score)
            final_res[field.view_field_id] = scores
        return final_res

    @timer
    async def by_embeddings(self, ids, search_index, embeddings):
        params = []
        for ids_, embedding in zip(ids, embeddings):
            if ad_version >= 3006:
                query_module = {
                    'size': self.vector_size,
                    'min_score': self.vector_min_score,
                    'query': {
                        'nested': {
                            'path': '_vector768',
                            'query': {
                                'script_score': {
                                    'query': {
                                        'term': {
                                            '_vector768.field': self.vector_field.replace('-vector', '')
                                        }
                                    },
                                    'script': {
                                        'source': 'knn_score',
                                        'lang': 'knn',
                                        'params': {
                                            'field': '_vector768.vec',
                                            'query_value': embedding,
                                            'space_type': 'cosinesimil'
                                        }
                                    }
                                }
                            }
                        }
                    },
                    '_source': {'includes': self.source_includes}
                }
            else:
                query_module = {
                    'size': self.vector_size,
                    'min_score': self.vector_min_score,
                    'query': {
                        'script_score': {
                            'query': {
                                "terms": {
                                    f"id.keyword": ids_
                                }
                            },
                            'script': {
                                'source': 'knn_score',
                                'lang': 'knn',
                                'params': {
                                    'field': self.vector_field,
                                    'query_value': embedding,
                                    'space_type': 'cosinesimil'
                                }
                            }
                        }
                    },
                    '_source': {'includes': self.source_includes}
                }
            params.append(
                {
                    'kg_id': self.graph_id,
                    'query': json.dumps(query_module),
                    'tags': [search_index]
                }
            )
        # logger.info(f'向量检索-query： {query.strip()}')
        response = await ad_opensearch_connector(appid=self.appid, params=params)
        return response['responses']

    @timer
    async def run(self, view_name, view_subject_id, view_fields, recall_res):
        recall_res_ = copy.deepcopy(recall_res)
        # 此函数用于重排、精排
        rank_res = []

        # 判断召回的逻辑实体属性是否重名
        multi_props = await self.is_multi_of_props(search_index=self.index, recall_res=recall_res_)
        # logger.info(f'multi_props: {multi_props}')
        # opensearch检索：计算path与视图图字段的相似程度
        rel_path_scores = await self.cal_cosine_similar_(search_index=self.index,
                                                         view_name=view_name,
                                                         fields=view_fields,
                                                         recall_res=recall_res_)
        # logger.info(f'rel_path_scores_02: {rel_path_scores}')

        # 遍历每个字段的召回结果
        for res, view_field in zip(recall_res_, view_fields):
            new_res = []
            # 和所有检索到的逻辑实体属性的path得分
            scores = rel_path_scores.get(view_field.view_field_id, [])
            # 标记最高得分
            max_score = 0
            # 标记是否关联的逻辑实体属性有重名
            count, flag = 0, False
            # 遍历每个字段的召回结果
            for key, item in res.items():
                score = item.get('_score', 0)
                score_path = item.get('score_path', '')

                # 优先规则：所属主题域优先
                if score >= max_score:
                    max_score = score
                    if view_subject_id:
                        path_ids = item.get('path_id', '')
                        if view_subject_id in path_ids:
                            score += 1
                            score_path += '+rel_subject:1.0'
                # 优先规则：所属关联标准优先
                if view_field.standard_code:
                    standard_id = item.get('standard_id', '')
                    if view_field.standard_code == standard_id:
                        score += 1
                        score_path += '+rel_subject:1.0'
                # 重排序规则：原始字段名检索得分+path相关性得分
                if len(scores) > count:
                    if scores[count] > 0:
                        score += scores[count]
                        score_path += f'+path_score:{scores[count]}'
                # 重名置信度匹配
                prop = item.get('name', '')
                if count == 0 and prop in multi_props:
                    flag = True
                score = score - 0.5 if flag else score
                item['score'] = score
                item['score_path'] = score_path
                new_res.append(item)
                count += 1
            sorted_res = sorted(new_res, key=lambda x: x['score'], reverse=True)
            rank_res.append(sorted_res)
        # for res in rank_res:
        #     print('*' * 100)
        #     for item in res:
        #         print(item)
        # logger.info(f'排序：{rank_res}')
        return rank_res


