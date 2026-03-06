# """
# @File: model_recall.py
# @Date:2024-02-26
# @Author : Danny.gao
# @Desc: 找回+粗排（opensearch）
# """
#
# import json
# import collections
# import jieba
#
#
# from config import settings
# from app.logs.logger import logger
# # from app.cores.recommend.common import ad_opensearch_connector, m3e_embeddings
# from app.cores.recommend.utils import *
#
#
# ad_version = 3006
# try:
#     ad_version = int(str(settings.AD_VERSION).replace('.', ''))
# except:
#     pass
#
#
# class ModelRecall(object):
#     def __init__(self, params):
#         # 检索索引
#         self.index = params.index
#         # 向量检索参数
#         self.topn = params.top_n
#         self.vector_field = params.vector_search.field
#         self.vector_min_score = params.vector_search.min_score
#         self.vector_size = params.vector_search.size
#         # 关键字检索参数
#         self.query_fields = params.keyword_search.fields
#         self.query_min_score = params.keyword_search.min_score
#         self.query_size = params.keyword_search.size
#         # 返回参数
#         self.source_includes = params.includes
#
#         # 检索的必要条件 must
#         self.opensearch_must = params.opensearch_must if params.opensearch_must else []
#
#         # AD参数
#         self.appid = ''
#         self.graph_id = ''
#
#     def should_query(self, keywords):
#         new_keywords = []
#         for keyword in keywords:
#             new_keywords.extend(keyword)
#         query = {
#             'script_score': {
#                 'query': {
#                     "multi_match": {
#                         "query": '|'.join(new_keywords),
#                         "fields": self.query_fields
#                     }
#                 },
#                 'script': {
#                     'source': '_score'
#                 }
#             }
#         }
#         return query
#
#     async def by_keywords(self, search_index, keywords, should_querys, **kwargs):
#         params = kwargs.get('params', {})
#         min_score = params.get('query', {}).get('query_min_score', 0.0)
#         min_score = min_score if min_score > 0 else params.get('min_score', 0.0)
#         min_score = min_score if min_score > 0 else self.query_min_score
#         top_n = self.query_size
#         terms_musts = kwargs.get('terms_musts', [[]]*len(keywords))
#         params = []
#         for keyword, musts in zip(keywords, terms_musts):
#             should_query = self.should_query(keywords=[keyword])
#             new_should_querys = [should_query] + should_querys
#
#             # 召回时，必须需满足的条件
#             musts += self.opensearch_must
#
#             query_module = {
#                 'size': top_n,
#                 'min_score': min_score+len(musts),
#                 'query': {
#                     "bool": {
#                         "must": musts,
#                         "should": new_should_querys
#                     }
#                 },
#                 '_source': {'includes': self.source_includes}
#             }
#             params.append(
#                 {
#                     'kg_id': self.graph_id,
#                     'query': json.dumps(query_module),
#                     'tags': [search_index]
#                 }
#             )
#         logger.info(f'关键字检索-params：{params}')
#         # 切分数据
#         responses = []
#         response = await ad_opensearch_connector(appid=self.appid, params=params)
#         # 归一化得分
#         for res in response['responses']:
#             hits = res['hits']
#             max_score = hits['max_score']
#             new_hits = []
#             for hit in hits['hits']:
#                 score = hit['_score'] / max_score
#                 if score >= float(min_score):
#                     hit['_score'] = score
#                     new_hits.append(hit)
#             hits['hits'] = new_hits
#             res['hits'] = hits
#             responses.append(res)
#         return responses
#
#     async def by_embeddings(self, search_index, embeddings, **kwargs):
#         params = kwargs.get('params', {})
#         min_score = params.get('query', {}).get('vector_min_score', 0.0)
#         min_score = min_score if min_score > 0 else params.get('min_score', 0.0)
#         min_score = min_score if min_score > 0 else self.query_min_score
#         top_n = self.vector_size
#         terms_musts = kwargs.get('terms_musts', [[]] * len(embeddings))
#         params = []
#         for embedding, musts in zip(embeddings, terms_musts):
#             musts += self.opensearch_must
#             if ad_version >= 3006:
#                 query_module = {
#                     'size': top_n,
#                     'min_score': min_score + len(musts) + 1, # +1是向量检索得分的范围是0-2
#                     'query': {
#                         'bool': {
#                             'must': [
#                                 {
#                         'nested': {
#                             'path': '_vector768',
#                             'query': {
#                                 'script_score': {
#                                     'query': {
#                                                     'match_all': {}
#                                     },
#                                     'script': {
#                                         'source': 'knn_score',
#                                         'lang': 'knn',
#                                         'params': {
#                                             'field': '_vector768.vec',
#                                             'query_value': embedding,
#                                             'space_type': 'cosinesimil'
#                                         }
#                                     }
#                                 }
#                             }
#                         }
#                                 }
#                             ] + musts
#                         }
#
#                     },
#                     '_source': {'includes': self.source_includes}
#                 }
#             else:
#                 query_module = {
#                     'size': self.vector_size,
#                     'min_score': min_score,
#                     'query': {
#                         'script_score': {
#                             'query': {
#                                 "bool": {
#                                     "must": musts
#                                 }
#                             },
#                             'script': {
#                                 'source': 'knn_score',
#                                 'lang': 'knn',
#                                 'params': {
#                                     'field': self.vector_field,
#                                     'query_value': embedding,
#                                     'space_type': 'cosinesimil'
#                                 }
#                             }
#                         }
#                     },
#                     '_source': {'includes': self.source_includes}
#                 }
#             params.append(
#                 {
#                     'kg_id': self.graph_id,
#                     'query': json.dumps(query_module),
#                     'tags': [search_index]
#                 }
#             )
#         # logger.info(f'向量检索-query： {params}')
#         response = await ad_opensearch_connector(self.appid, params)
#         if ad_version >= 3006:
#             # 减去musts的得分
#             for res, musts in zip(response['responses'], terms_musts):
#                 musts += self.opensearch_must
#                 hits = res['hits']
#                 for hit in hits['hits']:
#                     hit['_score'] = hit['_score'] - len(musts)
#
#         # 将分数统一-1
#         for res in response['responses']:
#             hits = res['hits']
#             for hit in hits['hits']:
#                 score = hit['_score']
#                 hit['_score'] = score - 1 if score > 1 else score
#
#         return response['responses']
#
#     async def run(self, texts, **kwargs):
#         # 场景权重分配
#         scenes = kwargs.get('scene', {})
#         num = len(scenes)
#         weight = 1./(num*3) if num > 0 else 0
#         should_querys = []
#         for scene, stexts in scenes.items():
#             stexts, w = stexts
#             query = self.should_query(keywords=[jieba.lcut(text, cut_all=True) for text in stexts])
#             should_querys.append(query)
#
#         # 召回过程的过滤条件
#         terms_musts = kwargs.get('terms_musts', [[]]*len(texts))
#         terms_musts = format_terms(terms_musts=terms_musts)
#
#         # 关键字检索：jieba分词
#         keywords = [jieba.lcut(text, cut_all=True) for text in texts]
#         query_responses = []
#         if keywords:
#             query_responses = await self.by_keywords(search_index=self.index,
#                                                      keywords=keywords,
#                                                      should_querys=should_querys,
#                                                      terms_musts=terms_musts,
#                                                      params=kwargs.get('params', {}))
#         logger.info(f'关键字检索-result：{query_responses}')
#
#         # 向量检索
#         try:
#             embeddings = await m3e_embeddings(texts=texts)
#             vector_responses = await self.by_embeddings(search_index=self.index,
#                                                         embeddings=embeddings,
#                                                         terms_musts=terms_musts,
#                                                         params=kwargs.get('params', {})) if embeddings else []
#             logger.info(f'向量检索-result：{vector_responses}')
#         except:
#             vector_responses = []
#
#         # 粗排：关键字得分 + 向量得分
#         # 关键字得分
#         query_results = []
#         for text, query_response in zip(texts, query_responses):
#             res = collections.OrderedDict()
#             for hit in query_response['hits']['hits']:
#                 res[hit['_id']] = hit
#             query_results.append(res)
#         # 向量得分
#         vector_results = []
#         for text, vector_response in zip(texts, vector_responses):
#             res = collections.OrderedDict()
#             for hit in vector_response['hits']['hits']:
#                 res[hit['_id']] = hit
#             vector_results.append(res)
#         # 得分相加
#         recall_res =[]
#         for idx, text in enumerate(texts):
#             query_res = query_results[idx] if len(query_results) > idx else {}
#             vector_res = vector_results[idx] if len(vector_results) > idx else {}
#             _ids = query_res.keys() | vector_res.keys()
#             merge_res = collections.OrderedDict()
#             for _id in _ids:
#                 if _id in query_res and _id in vector_res:
#                     item = query_res[_id].copy()
#                     query_score = query_res[_id]['_score']
#                     vector_score = vector_res[_id]['_score']
#                     item['_score'] = query_score + vector_score
#                     item['query_score'] = query_score
#                     item['vector_score'] = vector_score
#                     item['score_path'] = f'(keyword_score:{query_score}+vector_score:{vector_score})'
#                 elif _id in query_res:
#                     item = query_res[_id].copy()
#                     query_score = query_res[_id]['_score']
#                     item['query_score'] = query_score
#                     item['vector_score'] = 0
#                     item['score_path'] = f'keyword_score:{query_score}'
#                 else:
#                     item = vector_res[_id].copy()
#                     vector_score = vector_res[_id]['_score']
#                     item['query_score'] = 0
#                     item['vector_score'] = vector_score
#                     item['score_path'] = f'vector_score:{vector_score}'
#                 merge_res[_id] = item
#             merge_res = sorted(merge_res.items(), key=lambda x: x[1]['_score'], reverse=True)
#             merge_res = {x[0]: x[1] for x in merge_res}
#             recall_res.append(merge_res)
#         # for item in recall_res:
#         #     print('*' * 100)
#         #     for k, v in item.items():
#         #         print(k, v)
#         logger.info(f'召回结果：{recall_res}')
#         return recall_res
#
#
# if __name__ == '__main__':
#     import asyncio
#     from app.cores.categorize.configs.config_recall import recall_params
#     import time
#
#     print(recall_params)
#     recall = ModelRecall(params=recall_params)
