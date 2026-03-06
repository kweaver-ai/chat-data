# # -*- coding: utf-8 -*-
# """
# 面向对象版本的搜索功能模块
# 将 search_func.py 中的函数式代码重构为面向对象设计
# """
# import os
# import ahocorasick
# import ast
# import jieba
# import json
# import math
# import numpy
# import re
# import time
# from abc import ABC, abstractmethod
# from typing import Dict, Optional, List, Any, Tuple
# import numpy as np
# from pydantic import BaseModel
# from sklearn.feature_extraction.text import CountVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from sklearn.preprocessing import MinMaxScaler
# from starlette import status
#
# from app.cores.cognitive_assistant.qa_api import FindNumberAPI
# # from app.cores.cognitive_search.sdk_utils import (
# #     ad_builder_download_lexicon,
# #     ad_opensearch_connector,
# #     m3e_embeddings,
# #     ad_opensearch_connector_dip,
# #     custom_search_graph_call_dip
# # )
# from app.cores.cognitive_search.search_model import ANALYSIS_SEARCH_EMPTY_RESULT
# from app.cores.prompt.manage.ad_service import PromptServices
# from app.cores.prompt.manage.payload_prompt import prompt_map
# from app.logs.logger import logger
# from app.utils.exception import NewErrorBase, ErrVal
# from app.utils.stop_word import get_default_stop_words
# from config import settings
#
#
# # ==================== 基础工具类 ====================
#
# class SimilarityCalculator:
#     """相似度计算工具类"""
#
#     @staticmethod
#     def get_word_vector(list_a: List[str], list_b: List[str], all_words: List[str]) -> Tuple[List[int], List[int]]:
#         """词频向量化"""
#         la = []
#         lb = []
#         for word in all_words:
#             la.append(list_a.count(word))
#             lb.append(list_b.count(word))
#         return la, lb
#
#     @staticmethod
#     def calculate_cos(list_a: List[str], list_b: List[str]) -> float:
#         """计算余弦值"""
#         all_words = list(set(list_a + list_b))
#         la, lb = SimilarityCalculator.get_word_vector(list_a, list_b, all_words)
#         laa = numpy.array(la)
#         lbb = numpy.array(lb)
#         cos = (numpy.dot(laa, lbb.T)) / (
#             ((math.sqrt(numpy.dot(laa, laa.T))) * (math.sqrt(numpy.dot(lbb, lbb.T)))) + 0.01
#         )
#         return cos
#
#     @staticmethod
#     def calculate_cosine_similarity(text1: str, text2: str) -> float:
#         """计算两个文本的余弦相似度"""
#         vectorizer = CountVectorizer()
#         corpus = [text1, text2]
#         vectors = vectorizer.fit_transform(corpus)
#         similarity = cosine_similarity(vectors)
#         return similarity[0][1]
#
#     @staticmethod
#     def lev_dis_score(a: List[str], b: List[str]) -> Tuple[float, int, float]:
#         """
#         计算编辑距离相关的分数
#         :param a: 查询词列表
#         :param b: 匹配词列表
#         :return: (score_class, score_num, score)
#         """
#         # its是匹配上的词（已去重）
#         its = set(a).intersection(set(b))
#         # 计算匹配上的词占总query分词数的百分比
#         score_class = round(len(its) / (len(a) + 0.01), 2)
#         # 统计分词query在属性值中一共出现多少次
#         score_num = 0
#         for i in a:
#             c = b.count(i)
#             score_num += c
#         # 计算匹配上的词占字符总数的百分比
#         score = round(len(its) / (len(b) + 0.01), 2) if len(b) != 0 else 0
#         return score_class, score_num, score
#
#
# class TextUtils:
#     """文本处理工具类"""
#
#     @staticmethod
#     def cut_explore_result(s: str) -> List[str]:
#         """explore_result 字段特殊处理，解析json后取 key 和 result"""
#         s = str(s).lower()
#         try:
#             dicts = ast.literal_eval(s)
#         except:
#             logger.error(f"json parse error: {s}")
#             return [s]
#         if not dicts:
#             return []
#         keywords = []
#         if not isinstance(dicts, list):
#             return [str(dicts)]
#         for dic in dicts:
#             if not isinstance(dic, dict):
#                 keywords.append(str(dic))
#             for key in dic.keys():
#                 if key in ['key', 'result']:
#                     keywords.append(str(dic[key]))
#         keywords = list(filter(None, keywords))
#         return keywords
#
#     @staticmethod
#     def cut_by_punc(s: str) -> List[str]:
#         """按中英文分割，标点符号分割"""
#         rgr = re.findall(r'(\w*)(\W*)', s)
#         cuts = []
#         for tup in rgr:
#             if tup[0]:
#                 beg = 0
#                 flag = -1  # 0: en, 1: zh
#                 for i, ch in enumerate(tup[0]):
#                     if 'a' <= ch <= 'z' or '0' <= ch <= '9' or 'A' <= ch <= 'Z':
#                         cur_flag = 0
#                     else:
#                         cur_flag = 1
#                     if flag == -1 or cur_flag == flag:
#                         flag = cur_flag
#                         continue
#                     else:
#                         cuts.append(tup[0][beg:i])
#                         beg = i
#                         flag = cur_flag
#                 if beg < len(tup[0]):
#                     cuts.append(tup[0][beg:])
#             if tup[1]:
#                 cuts.append(tup[1])
#         return cuts
#
#     @staticmethod
#     def find_idx_list_of_dict(props_lst: List[Dict], key_to_find: str, value_to_find: Any) -> Any:
#         """在字典列表中查找某个key:value的值"""
#         try:
#             for i in range(len(props_lst)):
#                 if props_lst[i][key_to_find] == value_to_find:
#                     idx = props_lst[i]["value"]
#                     return idx
#         except:
#             logger.error(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")
#             raise Exception(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")
#
#     @staticmethod
#     def find_value_list_of_dict(props_lst: List[Dict], value_to_find: Any) -> Optional[Any]:
#         """在字典列表中查找target对应的source值"""
#         try:
#             for i in range(len(props_lst)):
#                 if props_lst[i]['target'] == value_to_find:
#                     return props_lst[i]['source']
#         except:
#             logger.error(f"datacatalog entity hasn't property {value_to_find} error: {props_lst}")
#
#
# # ==================== 词典管理类 ====================
#
# class LexiconManager:
#     """词典管理器，负责加载和管理同义词库、停用词库"""
#
#     def __init__(self, base_path: Optional[str] = None):
#         self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
#         self.synonym_file_path = os.path.join(self.base_path, "resources/synonym_lexicon")
#         self.stopwords_file_path = os.path.join(self.base_path, "resources/stopwords_lexicon")
#         self._synonym_trie: Optional[ahocorasick.Automaton] = None
#         self._stopwords: Optional[List[str]] = None
#
#     # 原为 set_actrie_dip（）
#     def load_synonym_trie_from_file(self, sep: str = ';') -> Optional[ahocorasick.Automaton]:
#         """从本地文件读取同义词库构建Aho-Corasick Trie树"""
#         try:
#             with open(self.synonym_file_path, 'r', encoding='utf-8') as f:
#                 synonym_content = f.read()
#
#             if isinstance(synonym_content, str):
#                 synonym_content = synonym_content.lstrip('\ufeff')
#
#             logger.info(f"从本地文件读取同义词库: {self.synonym_file_path}")
#
#             if not synonym_content:
#                 logger.warning('同义词库文件为空')
#                 return None
#
#             if not isinstance(synonym_content, str):
#                 logger.error('Download synonym dict failed.')
#                 msg = synonym_content
#                 if 'LexiconIdNotExist' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Synonym_LexiconID_Err,
#                         cause=msg.get('ErrorDetails', '') + 'Please check the synonym_id in config file.'
#                     )
#                 elif 'ParamError' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Args_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#                 else:
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                         err_code=ErrVal.Err_Internal_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#
#             lines = synonym_content.split('\n')
#             lines.pop(0)
#             if len(lines) == 0:
#                 return None
#
#             actrie = ahocorasick.Automaton()
#             for line in lines:
#                 line = line.strip()
#                 if not line:
#                     continue
#                 elems = line.split(sep)
#                 for i, elem in enumerate(elems):
#                     word = elem.lower().replace(' ', '')
#                     syns = [elems[i]] + elems[:i] + elems[i + 1:]
#                     actrie.add_word(word, tuple(syns))
#             actrie.make_automaton()
#             self._synonym_trie = actrie
#             return actrie
#         except Exception as e:
#             logger.error(str(e))
#             return None
#
#     # 原为 set_actrie（）
#     def load_synonym_trie_from_ad(self, ad_appid: str, synonym_id: str, sep: str = ';') -> Optional[ahocorasick.Automaton]:
#         """从AD下载同义词库构建Trie树"""
#         try:
#             synonym_content = ad_builder_download_lexicon(ad_appid, synonym_id)
#
#             if not isinstance(synonym_content, str):
#                 logger.error('Download synonym dict failed.')
#                 msg = synonym_content
#                 if 'LexiconIdNotExist' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Synonym_LexiconID_Err,
#                         cause=msg.get('ErrorDetails', '') + 'Please check the synonym_id in config file.'
#                     )
#                 elif 'ParamError' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Args_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#                 else:
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                         err_code=ErrVal.Err_Internal_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#
#             lines = synonym_content.split('\n')
#             lines.pop(0)
#             if len(lines) == 0:
#                 return None
#
#             actrie = ahocorasick.Automaton()
#             for line in lines:
#                 line = line.strip()
#                 if not line:
#                     continue
#                 elems = line.split(sep)
#                 for i, elem in enumerate(elems):
#                     word = elem.lower().replace(' ', '')
#                     syns = [elems[i]] + elems[:i] + elems[i + 1:]
#                     actrie.add_word(word, tuple(syns))
#             actrie.make_automaton()
#             self._synonym_trie = actrie
#             return actrie
#         except Exception as e:
#             logger.error(str(e))
#             return None
#
#     # 原为 set_stopwords_dip（）
#     def load_stopwords_from_file(self) -> List[str]:
#         """从本地文件读取停用词库"""
#         try:
#             with open(self.stopwords_file_path, 'r', encoding='utf-8') as f:
#                 stopwords_content = f.read()
#
#             if isinstance(stopwords_content, str):
#                 stopwords_content = stopwords_content.lstrip('\ufeff')
#
#             logger.info(f"从本地文件读取停用词库: {self.stopwords_file_path}")
#
#             if not stopwords_content:
#                 logger.warning('停用词库文件为空')
#                 return []
#
#             if not isinstance(stopwords_content, str):
#                 logger.error('Download stopwords dict failed.')
#                 msg = stopwords_content
#                 if 'LexiconIdNotExist' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Synonym_LexiconID_Err,
#                         cause=msg.get('ErrorDetails', '') + 'Please check the synonym_id in config file.'
#                     )
#                 elif 'ParamError' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Args_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#                 else:
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                         err_code=ErrVal.Err_Internal_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#
#             lines = stopwords_content.split('\n')
#             lines.pop(0)
#             stopwords = [line.strip() for line in lines]
#             self._stopwords = stopwords
#             return stopwords
#         except Exception as e:
#             logger.error(str(e))
#             return []
#
#     # 原为 set_stopwords（）
#     def load_stopwords_from_ad(self, ad_appid: str, stopwords_lid: str) -> List[str]:
#         """从AD下载停用词库"""
#         if stopwords_lid is None:
#             return []
#         try:
#             stopwords_content = ad_builder_download_lexicon(ad_appid, stopwords_lid)
#             if not isinstance(stopwords_content, str):
#                 logger.error('Download stopwords dict failed.')
#                 msg = stopwords_content
#                 if 'LexiconIdNotExist' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Synonym_LexiconID_Err,
#                         cause=msg.get('ErrorDetails', '') + 'Please check the synonym_id in config file.'
#                     )
#                 elif 'ParamError' in msg.get('ErrorCode', ''):
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_400_BAD_REQUEST,
#                         err_code=ErrVal.Err_Args_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#                 else:
#                     raise NewErrorBase(
#                         statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                         err_code=ErrVal.Err_Internal_Err,
#                         cause=msg.get('ErrorDetails', '')
#                     )
#             lines = stopwords_content.split('\n')
#             lines.pop(0)
#             stopwords = [line.strip() for line in lines]
#             self._stopwords = stopwords
#             return stopwords
#         except Exception as e:
#             logger.error(str(e))
#             return []
#
#     # 原为 init_lexicon_dip（）
#     def initialize_dip(self) -> Dict:
#         """初始化DIP版本的词典资源"""
#         resource = {}
#         syn_actrie = self.load_synonym_trie_from_file()
#         stopwords = self.load_stopwords_from_file()
#         resource['lexicon_actrie'] = syn_actrie
#         resource['stopwords'] = stopwords
#         return resource
#
#     # 原为 init_lexicon（）
#     def initialize(self, ad_appid: str, required_resource: Dict) -> Dict:
#         """初始化AD版本的词典资源"""
#         resource = {}
#         syn_lexicon = required_resource.get('lexicon_actrie', {})
#         syn_lexicon_id = syn_lexicon.get('lexicon_id', None)
#         syn_lexicon_sep = syn_lexicon.get('lexicon_sep', ';')
#
#         if syn_lexicon_id is None:
#             syn_actrie = None
#         else:
#             syn_actrie = self.load_synonym_trie_from_ad(ad_appid, syn_lexicon_id, syn_lexicon_sep)
#
#         stopwords_lexicon = required_resource.get('stopwords', {})
#         stopwords_lexicon_id = stopwords_lexicon.get('lexicon_id', None)
#
#         if stopwords_lexicon_id is None:
#             stopwords = []
#         else:
#             stopwords = self.load_stopwords_from_ad(ad_appid, stopwords_lexicon_id)
#
#         resource['lexicon_actrie'] = syn_actrie
#         resource['stopwords'] = stopwords
#         return resource
#
#     @property
#     def synonym_trie(self) -> Optional[ahocorasick.Automaton]:
#         """获取同义词Trie树"""
#         return self._synonym_trie
#
#     @property
#     def stopwords(self) -> Optional[List[str]]:
#         """获取停用词列表"""
#         return self._stopwords
#
#
# # ==================== 文本处理类 ====================
#
# class TextProcessor:
#     """文本处理器，负责分词、同义词扩展等"""
#
#     def __init__(self, lexicon_manager: LexiconManager):
#         self.lexicon_manager = lexicon_manager
#
#     # 原为 query_syn_expansion（）
#     async def expand_synonyms(
#         self,
#         query: str,
#         dropped_words: List[str] = None
#     ) -> Tuple[List[str], List[Dict], List[str]]:
#         """
#         对query进行同义词扩展分词
#         :return: (queries, query_cuts, all_syns)
#         """
#         if dropped_words is None:
#             dropped_words = []
#
#         actrie = self.lexicon_manager.synonym_trie
#         stopwords = self.lexicon_manager.stopwords or []
#
#         # 从actrie获取同义词
#         if actrie is None:
#             std_mentions = []
#         else:
#             std_mentions = [
#                 (index_value_tuple[0] + 1 - len(index_value_tuple[1][0]),
#                  index_value_tuple[0] + 1,
#                  index_value_tuple[1])
#                 for index_value_tuple in actrie.iter_long(query.lower().replace(' ', ''))
#             ]
#
#         syn2src2syns = {}
#         for mention in std_mentions:
#             for syn in mention[2]:
#                 syn = syn.lower().replace(' ', '')
#                 if syn in dropped_words:
#                     continue
#                 if syn not in syn2src2syns:
#                     syn2src2syns[syn] = {}
#                 syn2src2syns[syn][mention[2][0]] = list(mention[2])
#
#         all_syns = [item for mention in std_mentions for item in mention[2]]
#         all_syns = list(set([x.lower().replace(' ', '') for x in all_syns]))
#         all_syns = [x for x in all_syns if x not in dropped_words]
#
#         # 改写query
#         query_cuts = []
#         q_add_syn = query
#         slices = []
#         last_end = 0
#
#         for mention in std_mentions:
#             slices.append(query[last_end:mention[0]])
#             cur_cuts = jieba.lcut(query[last_end:mention[0]])
#             for cur_cut in cur_cuts:
#                 if not cur_cut.strip():
#                     continue
#                 is_stopword = cur_cut in stopwords
#                 query_cuts.append({
#                     "source": cur_cut,
#                     "synonym": [],
#                     "is_stopword": is_stopword
#                 })
#             last_end = mention[1]
#             for syn in list(mention[2])[1:]:
#                 if syn in dropped_words:
#                     continue
#                 q_add_syn += ' ' + syn
#             query_cuts.append({
#                 "source": list(mention[2])[0],
#                 "synonym": list(mention[2][1:]),
#                 "is_stopword": False
#             })
#
#         slices.append(query[last_end:])
#         logger.info(f'使用jieba分词...')
#         cur_cuts = jieba.lcut(query[last_end:])
#
#         for cur_cut in cur_cuts:
#             if not cur_cut.strip():
#                 continue
#             is_stopword = cur_cut in stopwords
#             query_cuts.append({
#                 "source": cur_cut,
#                 "synonym": [],
#                 "is_stopword": is_stopword
#             })
#
#         queries = []
#
#         def backtrack(std_mentions, i, q):
#             if i >= len(std_mentions):
#                 queries.append(q + slices[i])
#                 return
#             mention = std_mentions[i]
#             syns = [x for x in mention[2] if x not in dropped_words]
#             for syn in syns:
#                 backtrack(std_mentions, i + 1, q + slices[i] + syn)
#
#         backtrack(std_mentions, 0, '')
#         return queries, query_cuts, all_syns
#
#     # 原为 query_segment（）
#     async def segment(self, query: str) -> List[str]:
#         """对query进行分词, 用于字段召回"""
#         query_seg_list = [
#             q_cut.lower()
#             for q_cut in jieba.cut(query, cut_all=False)
#             if q_cut.lower().strip()
#         ]
#         logger.info("query cut result {}".format(query_seg_list))
#         stop_set = get_default_stop_words()
#         query_seg_list = [q_word for q_word in query_seg_list if q_word not in stop_set]
#         logger.info("off stop word query cut result {}".format(query_seg_list))
#         return query_seg_list
#
#
# # ==================== 搜索引擎基类 ====================
#
# class SearchEngine(ABC):
#     """搜索引擎抽象基类"""
#
#     def __init__(self, config: Dict):
#         self.config = config
#
#     @abstractmethod
#     async def search_by_keyword(
#         self,
#         query: str,
#         queries: List[str],
#         all_syns: List[str],
#         entity_types: Dict,
#         data_params: Dict,
#         search_params: BaseModel
#     ) -> Tuple[List[str], Dict, List[Dict], List[str]]:
#         """关键词搜索"""
#         pass
#
#     @abstractmethod
#     async def search_by_vector(
#         self,
#         embeddings: List[str],
#         m_status: int,
#         vector_index_filed: Dict[str, Any],
#         entity_types: Dict,
#         data_params: Dict,
#         min_score: float,
#         search_params: BaseModel,
#         vec_knn_k: int = 50
#     ) -> Tuple[List[Dict], List[str]]:
#         """向量搜索"""
#         pass
#
#     @abstractmethod
#     async def query_embedding(self, query: str) -> Tuple[List[str], int]:
#         """查询向量化"""
#         pass
#
#
# class ADSearchEngine(SearchEngine):
#     """AD版本搜索引擎"""
#     # 原为 lexical_search（）
#     async def search_by_keyword(
#         self,
#         query: str,
#         queries: List[str],
#         all_syns: List[str],
#         entity_types: Dict,
#         data_params: Dict,
#         search_params: BaseModel
#     ) -> Tuple[List[str], Dict, List[Dict], List[str]]:
#         """AD版本关键词搜索"""
#         from app.cores.cognitive_search.search_func import lexical_search
#         return await lexical_search(query, queries, all_syns, entity_types, data_params, search_params)
#
#     # 原为 vector_search（）
#     async def search_by_vector(
#         self,
#         embeddings: List[str],
#         m_status: int,
#         vector_index_filed: Dict[str, Any],
#         entity_types: Dict,
#         data_params: Dict,
#         min_score: float,
#         search_params: BaseModel,
#         vec_knn_k: int = 50
#     ) -> Tuple[List[Dict], List[str]]:
#         """AD版本向量搜索"""
#         from app.cores.cognitive_search.search_func import vector_search
#         return await vector_search(
#             embeddings, m_status, vector_index_filed, entity_types,
#             data_params, min_score, search_params, vec_knn_k
#         )
#     # 原为 query_m3e
#     async def query_embedding(self, query: str) -> Tuple[List[str], int]:
#         """AD版本查询向量化"""
#         from app.cores.cognitive_search.search_func import query_m3e
#         return await query_m3e(query)
#
#
# class DIPSearchEngine(SearchEngine):
#     """DIP版本搜索引擎"""
#     # 原为 lexical_search_dip（）
#     async def search_by_keyword(
#         self,
#         query: str,
#         queries: List[str],
#         all_syns: List[str],
#         entity_types: Dict,
#         data_params: Dict,
#         search_params: BaseModel
#     ) -> Tuple[List[str], Dict, List[Dict], List[str]]:
#         """DIP版本关键词搜索"""
#         from app.cores.cognitive_search.search_func import lexical_search_dip
#         return await lexical_search_dip(query, queries, all_syns, entity_types, data_params, search_params)
#
#     # 原为 vector_search_dip（） 和 vector_search_dip_new（）
#     async def search_by_vector(
#         self,
#         embeddings: List[str],
#         m_status: int,
#         vector_index_filed: Dict[str, Any],
#         entity_types: Dict,
#         data_params: Dict,
#         min_score: float,
#         search_params: BaseModel,
#         vec_knn_k: int = 50
#     ) -> Tuple[List[Dict], List[str]]:
#         """DIP版本向量搜索"""
#         from app.cores.cognitive_search.search_func import vector_search_dip
#         return await vector_search_dip(
#             embeddings, m_status, vector_index_filed, entity_types,
#             data_params, min_score, search_params, vec_knn_k
#         )
#
#     async def query_embedding(self, query: str) -> Tuple[List[str], int]:
#         """DIP版本查询向量化"""
#         from app.cores.cognitive_search.search_func import query_m3e
#         return await query_m3e(query)
#
#
# # ==================== 大模型服务类 ====================
#
# class LLMService:
#     """大模型服务类"""
#
#     def __init__(
#         self,
#             headers: Dict,
#         find_number_api: FindNumberAPI,
#         prompt_service: Optional[PromptServices] = None
#     ):
#         self.find_number_api = find_number_api
#         self.prompt_service = prompt_service or PromptServices()
#         self.headers = headers
#
#     async def generate_recommendations(
#         self,
#         data: Dict,
#         query: str,
#         prompt_name: str,
#         table_name: str,
#         mode: str = "ad",
#         appid: Optional[str] = None,
#         x_account_id: Optional[str] = None,
#         search_configs: Optional[Any] = None
#     ) -> Tuple[List[str], str, Dict]:
#         """
#         生成推荐结果
#         :param mode: "ad" 或 "dip"
#         :return: (list_catalog, list_catalog_reason, res_json)
#         """
#         if mode == "dip":
#             return await self._generate_dip(self.headers,data, query,  search_configs, prompt_name, table_name)
#         else:
#             return await self._generate_ad(data, query, appid, prompt_name, table_name)
#
#     # 原为 qw_gpt()
#     async def _generate_ad(
#         self,
#         data: Dict,
#         query: str,
#         appid: str,
#         prompt_name: str,
#         table_name: str
#     ) -> Tuple[List[str], str, Dict]:
#         """AD版本生成推荐"""
#         from app.cores.cognitive_search.search_func import qw_gpt
#         return await qw_gpt(data, query, appid, prompt_name, table_name)
#
#     # 原为 qw_gpt()
#     async def _generate_dip(
#         self,
#         data: Dict,
#         query: str,
#         search_configs: Any,
#         prompt_name: str,
#         table_name: str
#     ) -> Tuple[List[str], str, Dict]:
#         """DIP版本生成推荐"""
#         from app.cores.cognitive_search.search_func import qw_gpt_dip
#         return await qw_gpt_dip(
#             headers=self.headers,
#             data=data,
#             query=query,
#             search_configs=search_configs,
#             prompt_name=prompt_name,
#             table_name=table_name
#         )
#
#     # 原为 qw_gpt_kecc（）
#     async def generate_recommendations_with_context(
#         self,
#         data: Dict,
#         query: str,
#         dept_infosystem_duty: Dict,
#         appid: str,
#         prompt_name: str,
#         table_name: str
#     ) -> Tuple[List[str], str, List[Dict], Dict]:
#         """生成带上下文的推荐（用于KECC）"""
#         from app.cores.cognitive_search.search_func import qw_gpt_kecc
#         return await qw_gpt_kecc(data, query, dept_infosystem_duty, appid, prompt_name, table_name)
#
#
# # ==================== 结果处理类 ====================
#
# class ResultProcessor:
#     """结果处理类，负责过滤、排序、标签添加等"""
#
#     @staticmethod
#     def add_label(reason: str, cites: List[str], a: int) -> Tuple[str, str]:
#         """
#         数据应用思路话术中打上搜索结果资源编号的标签
#         :param reason: 话术
#         :param cites: 推荐实例列表，格式为 ["id|name", ...]
#         :param a: 起始编号
#         :return: (修改后的话术, 状态标识 '1'或'0')
#         """
#         from app.cores.cognitive_search.search_func import add_label
#         return add_label(reason, cites, a)
#
#     @staticmethod
#     def add_label_easy(reason: str, cites: List[str]) -> str:
#         """专用于指标的数据应用思路话术中打上搜索结果资源编号的标签"""
#         from app.cores.cognitive_search.search_func import add_label_easy
#         return add_label_easy(reason, cites)
#
#     @staticmethod
#     async def get_user_allowed_asset_type(search_params: BaseModel) -> List[str]:
#         """根据用户的角色判断可以搜索到的资源类型"""
#         from app.cores.cognitive_search.search_func import get_user_allowed_asset_type
#         return await get_user_allowed_asset_type(search_params)
#
#     @staticmethod
#     async def get_user_authed_resource(
#         headers: Dict,
#         find_number_api: FindNumberAPI,
#         search_params: BaseModel
#     ) -> List[str]:
#         """获取用户拥有权限的所有资源id"""
#         from app.cores.cognitive_search.search_func import get_user_authed_resource
#         return await get_user_authed_resource(headers, find_number_api, search_params)
#
#     @staticmethod
#     async def keep_authed_online_resource(
#         headers: Dict,
#         search_params: BaseModel,
#         find_number_api: FindNumberAPI,
#         all_hits: List[Dict],
#         allowed_asset_type: List[str],
#         auth_id: List[str]
#     ) -> Tuple[List[Dict], List[str], List[Dict], List[Dict]]:
#         """保留用户有权限并且已上线的资源"""
#         from app.cores.cognitive_search.search_func import keep_authed_online_resource
#         return await keep_authed_online_resource(
#             headers, search_params, find_number_api, all_hits, allowed_asset_type, auth_id
#         )
#
#     @staticmethod
#     async def keep_online_resource_no_auth(
#         all_hits: List[Dict],
#         allowed_asset_type: List[str]
#     ) -> Tuple[List[Dict], List[str], List[Dict], List[Dict]]:
#         """保留已上线的资源（不需要权限检查）"""
#         from app.cores.cognitive_search.search_func import keep_online_resource_no_auth
#         return await keep_online_resource_no_auth(all_hits, allowed_asset_type)
#
#     @staticmethod
#     async def skip_model(resource_type: str) -> Tuple[List, List, List, str, Dict]:
#         """跳过模型调用"""
#         from app.cores.cognitive_search.search_func import skip_model
#         return await skip_model(resource_type)
#
#
# # ==================== 图分析服务类 ====================
#
# class GraphAnalysisService:
#     """图分析服务类"""
#
#     @staticmethod
#     async def custom_graph_call(kg_id: int, ad_appid: str, params: Dict) -> Optional[Dict]:
#         """调用图分析函数（AD版本）"""
#         from app.cores.cognitive_search.search_func import custom_graph_call
#         return await custom_graph_call(kg_id, ad_appid, params)
#
#     @staticmethod
#     async def custom_graph_call_dip(
#         x_account_id: str,
#         x_account_type: str,
#         kg_id: int,
#         params: Dict
#     ) -> Optional[Dict]:
#         """调用图分析函数（DIP版本）"""
#         from app.cores.cognitive_search.search_func import custom_graph_call_dip
#         return await custom_graph_call_dip(x_account_id, x_account_type, kg_id, params)
#
#
# # ==================== 主服务类 ====================
#
# class SearchFunctionManager:
#     """
#     搜索功能管理器
#     统一管理所有搜索相关的功能，提供面向对象的接口
#     """
#
#     def __init__(
#         self,
#         mode: str = "dip",  # "ad" 或 "dip"
#         base_path: Optional[str] = None,
#         find_number_api: Optional[FindNumberAPI] = None,
#         prompt_service: Optional[PromptServices] = None
#     ):
#         """
#         初始化搜索功能管理器
#         :param mode: 模式，"ad" 或 "dip"
#         :param base_path: 资源文件基础路径
#         :param find_number_api: FindNumberAPI实例
#         :param prompt_service: PromptServices实例
#         """
#         self.mode = mode
#         self.lexicon_manager = LexiconManager(base_path)
#         self.text_processor = TextProcessor(self.lexicon_manager)
#         self.similarity_calculator = SimilarityCalculator()
#         self.text_utils = TextUtils()
#
#         # 根据模式选择搜索引擎
#         if mode == "dip":
#             self.search_engine: SearchEngine = DIPSearchEngine({})
#         else:
#             self.search_engine: SearchEngine = ADSearchEngine({})
#
#         self.llm_service = LLMService(
#             headers=headers,
#             find_number_api=find_number_api or FindNumberAPI(),
#             prompt_service=prompt_service
#         )
#         self.result_processor = ResultProcessor()
#         self.graph_service = GraphAnalysisService()
#
#     def initialize_lexicon(self, ad_appid: Optional[str] = None, required_resource: Optional[Dict] = None) -> Dict:
#         """初始化词典资源"""
#         if self.mode == "dip":
#             return self.lexicon_manager.initialize_dip()
#         else:
#             if ad_appid is None or required_resource is None:
#                 raise ValueError("AD模式需要提供ad_appid和required_resource")
#             return self.lexicon_manager.initialize(ad_appid, required_resource)
#
#     async def expand_query_synonyms(
#         self,
#         query: str,
#         dropped_words: List[str] = None
#     ) -> Tuple[List[str], List[Dict], List[str]]:
#         """扩展查询同义词"""
#         return await self.text_processor.expand_synonyms(query, dropped_words or [])
#
#     async def segment_query(self, query: str) -> List[str]:
#         """对查询进行分词"""
#         return await self.text_processor.segment(query)
#
#     async def search(
#         self,
#         query: str,
#         queries: List[str],
#         all_syns: List[str],
#         entity_types: Dict,
#         data_params: Dict,
#         search_params: BaseModel
#     ) -> Tuple[List[str], Dict, List[Dict], List[str]]:
#         """执行关键词搜索"""
#         return await self.search_engine.search_by_keyword(
#             query, queries, all_syns, entity_types, data_params, search_params
#         )
#
#     async def vector_search(
#         self,
#         embeddings: List[str],
#         m_status: int,
#         vector_index_filed: Dict[str, Any],
#         entity_types: Dict,
#         data_params: Dict,
#         min_score: float,
#         search_params: BaseModel,
#         vec_knn_k: int = 50
#     ) -> Tuple[List[Dict], List[str]]:
#         """执行向量搜索"""
#         return await self.search_engine.search_by_vector(
#             embeddings, m_status, vector_index_filed, entity_types,
#             data_params, min_score, search_params, vec_knn_k
#         )
#
#     async def get_query_embedding(self, query: str) -> Tuple[List[str], int]:
#         """获取查询向量"""
#         return await self.search_engine.query_embedding(query)
#
#     async def generate_llm_recommendations(
#         self,
#         data: Dict,
#         query: str,
#         prompt_name: str,
#         table_name: str,
#         appid: Optional[str] = None,
#         x_account_id: Optional[str] = None,
#         search_configs: Optional[Any] = None
#     ) -> Tuple[List[str], str, Dict]:
#         """生成大模型推荐"""
#         return await self.llm_service.generate_recommendations(
#             data, query, prompt_name, table_name, self.mode,
#             appid, x_account_id, search_configs
#         )
#
#
# # ==================== 向后兼容的函数接口 ====================
# # 为了保持向后兼容，提供函数式接口，内部调用类方法
#
# def init_lexicon_dip() -> Dict:
#     """向后兼容：初始化DIP词典"""
#     manager = LexiconManager()
#     return manager.initialize_dip()
#
#
# def init_lexicon(ad_appid: str, required_resource: Dict) -> Dict:
#     """向后兼容：初始化AD词典"""
#     manager = LexiconManager()
#     return manager.initialize(ad_appid, required_resource)
#
#
# async def query_syn_expansion(actrie, query, stopwords, dropped_words):
#     """向后兼容：查询同义词扩展"""
#     manager = LexiconManager()
#     manager._synonym_trie = actrie
#     manager._stopwords = stopwords if isinstance(stopwords, list) else []
#     processor = TextProcessor(manager)
#     return await processor.expand_synonyms(query, dropped_words or [])
#
#
# async def query_segment(query):
#     """向后兼容：查询分词"""
#     manager = LexiconManager()
#     processor = TextProcessor(manager)
#     return await processor.segment(query)
#
#
# def calculate_cos(list_a, list_b):
#     """向后兼容：计算余弦值"""
#     return SimilarityCalculator.calculate_cos(list_a, list_b)
#
#
# def calculate_cosine_similarity(text1, text2):
#     """向后兼容：计算余弦相似度"""
#     return SimilarityCalculator.calculate_cosine_similarity(text1, text2)
#
#
# def lev_dis_score(a, b):
#     """向后兼容：计算编辑距离分数"""
#     return SimilarityCalculator.lev_dis_score(a, b)
#
#
# def cut_explore_result(s):
#     """向后兼容：解析explore_result"""
#     return TextUtils.cut_explore_result(s)
#
#
# def cut_by_punc(s):
#     """向后兼容：按标点符号分割"""
#     return TextUtils.cut_by_punc(s)
#
#
# def find_idx_list_of_dict(props_lst, key_to_find, value_to_find):
#     """向后兼容：查找字典列表中的值"""
#     return TextUtils.find_idx_list_of_dict(props_lst, key_to_find, value_to_find)
#
#
# def find_value_list_of_dict(props_lst, value_to_find):
#     """向后兼容：查找字典列表中的值"""
#     return TextUtils.find_value_list_of_dict(props_lst, value_to_find)
