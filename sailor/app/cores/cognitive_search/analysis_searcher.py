# -*- coding: utf-8 -*-
# @Time    : 2025/11/8 11:21
# @Author  : Glen.lv
# @File    : analysis_searcher
# @Project : af-sailor

import copy
from textwrap import dedent
from typing import Any, Union, Optional

# from sqlalchemy.engine.result import null_result
from pydantic import BaseModel
from fastapi import Request

from app.cores.cognitive_assistant.qa_error import DataCataLogError
from app.cores.cognitive_assistant.qa_model import QueryIntentionName
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
# from app.cores.cognitive_search.graph_analyser import GraphFunctionManager
# from app.cores.cognitive_search.search_func_manager import SearchFunctionManager
from app.cores.prompt.manage.payload_prompt import prompt_map
from app.retriever.base import RetrieverAPI
# from app.cores.datasource.dimension_reduce import DimensionReduce
from app.cores.prompt.manage.ad_service import PromptServices

from app.cores.cognitive_search.search_func import *
from app.cores.cognitive_search.graph_func import *
from app.cores.cognitive_search.prompts_config import resource_entity
from app.cores.cognitive_search.search_model import (ANALYSIS_SEARCH_EMPTY_RESULT, AnalysisSearchParams,
                                                     RetrieverHistoryQAParams, AnalysisSearchResponseModel,
                                                     AnalysisSearchParamsDIP)
from app.cores.cognitive_search.search_config.get_params import SearchConfigs
from app.cores.cognitive_search.utils.utils import safe_str_to_int, safe_str_to_float
from app.cores.cognitive_search.re_asset_search import cognitive_search_resource_for_qa

from app.cores.prompt.search import ALL_TABLE_TEMPLATE, ALL_TABLE_TEMPLATE_KECC

from config import settings

find_number_api = FindNumberAPI()
retriever_api = RetrieverAPI()
# dimension_reduce = DimensionReduce()  # 字段召回
prompt_svc = PromptServices()


class AnalysisSearcher:
    def __init__(self, request, search_params: AnalysisSearchParamsDIP, search_configs: SearchConfigs):

        self.request = request
        self.search_params = search_params
        self.search_configs = search_configs

        self.headers = {"Authorization": request.headers.get('Authorization')}
        self.query_embedding = None
        self.embedding_status = None
        self.output = {
            "count": 0,
            "entities": [],
            "answer": "抱歉未查询到相关信息。",
            "subgraphs": []
        }
        self.all_hits = []
        self.all_hits_new = []
        self.all_hits_kecc = []
        # 给大模型进行判断，整理的逻辑视图、接口服务、指标数据
        # 还没有支持数据资源目录
        self.pro_data_formview = []
        self.pro_data_svc = []
        self.pro_data_indicator = []
        self.pro_data_catalog = []

        # self.search_func_manager = SearchFunctionManager()
        # self.graph_func_manager = GraphFunctionManager()

        self.x_account_id = settings.DIP_GATEWAY_USER
        self.x_account_type = settings.DIP_GATEWAY_USER_TYPE

        # 大模型调用后处理的中间结果
        # 为每种资源类型维护独立的结果容器
        # list_catalog_reason 就是res_reason, 原代码中函数内返回值是list_catalog_reason，调用方接收后命名为res_reason
        # list-catalog  就是 res，原代码中函数内返回值是list_catalog，调用方接收后命名为res
        self.formview_results = {
            'hits_graph': [],
            'hits': [],
            'res': [],
            'res_reason': '',
            'res_load': {},
            'related_info': [],
            # 'list_catalog': [],
            # 'list_catalog_reason': '',
            'res_json': {}
        }
        self.svc_results = {
            'hits_graph': [],
            'hits': [],
            'res': [],
            'res_reason': '',
            'res_load': {},
            'related_info': [],
            # 'list_catalog': [],
            # 'list_catalog_reason': '',
            'res_json': {}
        }
        self.ind_results = {
            'hits_graph': [],
            'hits': [],
            'res': [],
            'res_reason': '',
            'res_load': {},
            'related_info': [],
            # 'list_catalog': [],
            # 'list_catalog_reason': '',
            'res_json': {}
        }
        self.catalog_results = {
            'hits_graph': [],
            'hits': [],
            'res': [],
            'res_reason': '',
            'res_load': {},
            'related_info': [],
            # 'list_catalog': [],
            # 'list_catalog_reason': '',
            'res_json': {}
        }
        # self.result_container={}

    def _should_auth_check(self) -> bool:
        """检查是否需要进行权限验证"""
        return self.search_configs.sailor_search_if_auth_in_find_data_qa == '1'

    # def _if_history_qa_enhance(self) -> bool:
    #     """检查是否启用历史问答增强功能"""
    #     return self.search_configs.sailor_search_if_history_qa_enhance == '1'

    def _if_kecc(self) -> bool:
        """检查是否启用部门职责知识增强（KECC）功能"""
        return self.search_configs.sailor_search_if_kecc == '1'

    # async def _ensure_embedding(self, query):
    #     """确保 query embedding 已计算"""
    #     if self.query_embedding is None:
    #         self.query_embedding, self.embedding_status = await query_m3e(query)
    #     return self.query_embedding, self.embedding_status

    # async def _init_search(self):
    async def _query_embedding(self):
        """初始化搜索，获取query embedding"""
        try:
            self.query_embedding, self.embedding_status = await query_m3e(self.search_params.query)
            logger.info(f'query = {self.search_params.query}')
            logger.info(f'query embedding status =  {self.embedding_status}')
            if not self.query_embedding or self.embedding_status is None:
                logger.error("查询embedding结果无效或状态无效")
                return False
            return True
        except Exception as e:
            logger.error(f'M3E embedding 错误: {settings.ML_EMBEDDING_URL} \nException= ', str(e))
            return False

    # 还未使用， 还在用 catalog_analysis_main_dip(), 待切换到 catalog_analysis_search_for_qa
    async def _perform_cognitive_search_catalog(self):
        """执行目录版认知搜索(仅向量搜索)"""
        total_start_time = time.time()

        # 获取图谱信息和向量化
        task_get_kgotl_qa = asyncio.create_task(get_kgotl_qa_dip_new(
            headers=self.headers,
            search_params=self.search_params
        ))

        # entity_types 字典{实体类型名：实体本体信息}
        # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        # type2names 字典 是前端传来的停用实体,现在已经废弃
        # data_params['type2names']
        # data_params['space_name']
        # data_params['indextag2tag']
        entity_types, vector_index_filed, data_params = await task_get_kgotl_qa

        # 分析问答型搜索只做向量搜索
        # 向量搜索
        min_score = 0.5
        task_vector_search = asyncio.create_task(
            vector_search_dip(
                embeddings=self.query_embedding,
                m_status=self.embedding_status,
                vector_index_filed=vector_index_filed,
                entity_types=entity_types,
                data_params=data_params,
                min_score=min_score,
                search_params=self.search_params
            )
        )
        #
        # all_hits 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素
        # drop_indices是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
        self.all_hits, drop_indices = await task_vector_search
        for hit in self.all_hits:
            if hit['_id'] in set(drop_indices):
                self.all_hits.remove(hit)
        return total_start_time, drop_indices

    async def _perform_cognitive_search_resource(self):
        """执行认知搜索（向量搜索+关键词搜索+关联搜索）"""
        try:
            self.output, self.headers, total_time_cost, self.all_hits, _ = await cognitive_search_resource_for_qa(
                request=self.request,
                search_params=self.search_params,
                query_embedding=self.query_embedding,
                m_status=self.embedding_status,
                search_configs=self.search_configs
            )
            logger.info(f"认知搜索图谱 OpenSearch 召回实体数量：all_hits={len(self.all_hits)}")
            return True
        except Exception as e:
            logger.error(f"认知搜索执行错误：{str(e)}")
            raise

    async def _perform_kecc_search(self):
        """执行部门职责知识增强搜索"""

        try:
            # 获取配置参数
            kg_id_kecc = safe_str_to_int(self.search_configs.kg_id_kecc)
            vec_size_kecc = safe_str_to_int(self.search_configs.sailor_vec_size_kecc)
            vec_min_score_kecc = safe_str_to_float(self.search_configs.sailor_vec_min_score_kecc)
            vec_knn_k_kecc = safe_str_to_int(self.search_configs.sailor_vec_knn_k_kecc)
            logger.info(f'kg_id_kecc={kg_id_kecc}')
            logger.info(f'vec_size_kecc={vec_size_kecc}')
            logger.info(f'vec_min_score_kecc={vec_min_score_kecc}')
            logger.info(f'vec_knn_k_kecc={vec_knn_k_kecc}')

            # 参数校验
            if kg_id_kecc is None:
                logger.error(f"获取'组织结构-部门职责-信息系统'知识图谱id失败!")
            if vec_size_kecc is None:
                logger.error(f'获取向量检索 返回文档数上限 参数失败!')
            if vec_min_score_kecc is None:
                logger.error(f'获取向量检索 分数下限 参数失败!')
            if vec_knn_k_kecc is None:
                logger.error(f'获取向量检索 knn-k 参数失败!')

            # 执行部门职责知识增强搜索
            _, self.all_hits_kecc = await self.graph_vector_retriever_kecc(
                ad_appid=self.search_params.ad_appid,
                kg_id_kecc=kg_id_kecc,
                query=self.search_params.query,
                query_embedding=self.query_embedding,
                m_status=self.embedding_status,
                vec_size_kecc=vec_size_kecc,
                vec_min_score_kecc=vec_min_score_kecc,
                vec_knn_k_kecc=vec_knn_k_kecc
            )

            logger.info(f"length of all_hits_kecc={len(self.all_hits_kecc)}")
            return True
        except Exception as e:
            logger.error(f"部门职责知识增强搜索执行错误：{str(e)}")
            raise

    async def _filter_results_and_prepare_llm_input(self, auth_id):
        logger.info(f'execute _filter_search_results, auth_id = {auth_id}')
        """过滤搜索结果，根据用户权限和资源类型"""
        # 根据用户的角色判断可以搜索到的资源类型
        query_filters = self.search_params.filter
        asset_type = query_filters.get('asset_type', '')
        # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
        # 只有 application-developer 可以搜到接口服务
        # 确定允许的资源类型
        if asset_type == [-1]:  # 全部tab
            # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
            if "application-developer" in self.search_params.roles:
                # catalog = "1"  # 目录
                # api = "2"  # API
                # view = "3"  # 视图
                # metric = "4"  # 指标
                allowed_asset_type = ['1', '2', '3', '4']
            else:
                allowed_asset_type = ['1', '3', '4']
        else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
            allowed_asset_type = asset_type
        logger.info(f'allowed_asset_type = {allowed_asset_type}')

        # # 获取用户拥有权限的所有资源id, auth_id
        # try:
        #     auth_id = await find_number_api.user_all_auth(
        #         headers=self.headers,
        #         subject_id=self.search_params.subject_id
        #     )
        # except Exception as e:
        #     logger.error(f"取用户拥有权限的所有资源id，发生错误：{str(e)}")
        #     return ANALYSIS_SEARCH_EMPTY_RESULT
        #
        # # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
        # if "data-operation-engineer" in self.search_params.roles or "data-development-engineer" in self.search_params.roles:
        #     logger.info('用户是数据开发工程师和运营工程师')
        # else:
        #     logger.info(f'该用户有权限的id = {auth_id}')

        # 重置数据容器
        self.pro_data_formview, self.pro_data_svc, self.pro_data_indicator = [], [], []


        # 必须按照 entity 来构造 all_hits, 仅构造必须的属性字段
        # all_hits_new = []
        # 因为有关联搜索， 要走图查询，所以self.output是nebula的数据结构
        for num, entity in enumerate(self.output['entities']):
            # logger.info(f'num = {num}')
            # logger.info(f'entity = {entity}')
            # 从entity的properties中提取属性值
            props_list = entity['entity']['properties'][0]['props']
            props_dict = {prop['name']: prop['value'] for prop in props_list}

            hit = {
                '_id': entity['entity']['id'],
                '_score': entity['entity']['score'],
                '_source': {
                    'asset_type': props_dict.get('asset_type'),
                    'code': props_dict.get('code'),
                    'color': props_dict.get('color'),
                    'description': props_dict.get('description'),
                    'online_at': props_dict.get('online_at'),
                    'online_status': props_dict.get('online_status'),
                    'publish_status': props_dict.get('publish_status'),
                    'publish_status_category': props_dict.get('publish_status_category'),
                    'resourceid': props_dict.get('resourceid'),
                    'resourcename': props_dict.get('resourcename'),
                    'technical_name': props_dict.get('technical_name'),
                    'department': props_dict.get('department'),
                    'department_path': props_dict.get('department_path'),
                    'department_id': props_dict.get('department_id'),
                    'department_path_id': props_dict.get('department_path_id'),
                    'owner_id': props_dict.get('owner_id'),
                    'owner_name': props_dict.get('owner_name'),
                    'info_system_name': props_dict.get('info_system_name'),
                    'info_system_uuid': props_dict.get('info_system_uuid'),
                    'subject_id': props_dict.get('subject_id'),
                    'subject_name': props_dict.get('subject_name'),
                    'subject_path': props_dict.get('subject_path'),
                    'subject_path_id': props_dict.get('subject_path_id'),
                    'published_at': props_dict.get('published_at')
                },
                "relation": "",
                "type": "resource",
                "type_alias": "数据资源",
                "name": props_dict.get('resourcename'),
                "service_weight": 4
            }

            self.all_hits_new.append(hit)
            # logger.info(f'self.all_hits_new={self.all_hits_new}')
        logger.info(f"按照 output['entities'] 构造的all_hits_new 长度 = {len(self.all_hits_new)}")

        # query 分词 用于字段召回
        query_seg_list = await query_segment(self.search_params.query)
        logger.info(f'query 分词 用于字段召回 = {query_seg_list}')

        # 过滤搜索结果
        for num, hit in enumerate(self.all_hits_new):
            # logger.info(f'num = {num}')
            # logger.info(f'hit = {hit}')
            # 检查必要字段
            # logger.info(f'hit[_source].keys()={hit["_source"].keys()}')
            if 'asset_type' not in hit['_source']:
                continue
            # hit['_source'] 是图谱实体点的属性数据， hit可能是图谱中各种类型的实体，搜索的最终目标是数据资源
            # 描述和名称拼起来作为提示词的一部分
            # description = hit['_source']['description'] if 'description' in hit['_source'] else '暂无描述'
            # 1数据目录 2接口服务 3逻辑视图 4指标
            # 从图谱get的i['_source']['asset_type']为字符型
            # 分析问答型搜索要求必须是已经上线的资源
            # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
            valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
            has_asset_type = 'asset_type' in hit['_source']
            asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}

            online_status_valid = hit['_source'].get('online_status') in valid_online_statuses

            form_view_common_fields = []

            # 检查资源类型和在线状态
            if asset_type_valid and online_status_valid:

                res_auth = "allow" # 如果关闭权限检查，或者登录用户是数据运营和开发， 都不会做以下校验， 默认允许
                # 取决于配置参数， 是否要对普通用户进行权限校验
                if self._should_auth_check() and not ("data-operation-engineer" in self.search_params.roles or
                                                      "data-development-engineer" in self.search_params.roles):
                    res_auth = await find_number_api.sub_user_auth_state(
                        assets=hit['_source'],
                        params=self.search_params,
                        headers=self.headers,
                        auth_id=auth_id
                    )
                # # 权限检查
                # res_auth = "allow"  # 默认允许
                # if not ("data-operation-engineer" in self.search_params.roles or
                #         "data-development-engineer" in self.search_params.roles):
                #     res_auth = await find_number_api.sub_user_auth_state(hit['_source'], self.search_params, self.headers,
                #                                                     auth_id)

                # 设置_selfid并根据资源类型分类
                hit['_selfid'] = str(num)
                description = hit['_source'].get('description', '暂无描述')
                # logger.info(f'num = {num}')
                # logger.info(f'hit = {hit}')

                if hit['_source']['asset_type'] == '3' and (res_auth == "allow" or not self._should_auth_check()):
                    # 逻辑视图
                    # 描述和名称拼起来作为提示词的一部分
                    # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
                    # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
                    # hit['_source']['resourceid'] 是逻辑视图的uuid，可用于请求获取字段信息
                    fields_info = await retriever_api.get_form_view_column_info(idx=hit['_source']['resourceid'],
                                                                                headers=self.headers)
                    # logger.info(f'resource_analysis_search_kecc_for_qa(), fields_info = {fields_info}')
                    # logger.info(f'resource_analysis_search_kecc_for_qa(), fields_info[0] = {fields_info[0]}')
                    # input_common_fields: 必须保留的字段
                    # input_query_seg_list: query 分词列表
                    # common_filed 多个逻辑视图都有的字段优先召回
                    # special_fields 优先召回特定字段
                    reduced_fields_info = fields_info
                    # reduced_fields_info = dimension_reduce.data_view_reduce(input_query=self.search_params.query,
                    #                                                         input_fields=fields_info[0],
                    #                                                         num=30,
                    #                                                         input_common_fields=form_view_common_fields,
                    #                                                         input_query_seg_list=query_seg_list,
                    #                                                         input_data_view_id=hit['_source'][
                    #                                                             'resourceid']
                    #                                                         )
                    # 将reduced_fields_info转为字符串
                    str_reduced_fields_info = "、".join(reduced_fields_info.values())
                    description_append_fields_info = description + ' 主要相关字段有：' + str_reduced_fields_info + '。'
                    # pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
                    # 考虑自己不用原 description，而是自己拼接：单位+信息系统+主要相关字段
                    self.pro_data_formview.append(
                        {hit['_selfid'] + '|' + hit['_source']['resourcename']: description_append_fields_info})
                    # logger.info(f'resource_analysis_search_kecc, pro_data_formview = {pro_data_formview}')

                elif hit['_source']['asset_type'] == '2' and (res_auth == "allow" or not self._should_auth_check()):
                    # 接口服务
                    self.pro_data_svc.append({
                        hit['_selfid'] + '|' + hit['_source']['resourcename']: description
                    })
                elif hit['_source']['asset_type'] == '4' and (res_auth == "allow" or not self._should_auth_check()):
                    # 指标
                    indicator_analysis_dimensions_business_name_list = await retriever_api.get_indicator_analysis_dimensions_business_name(
                        idx=hit['_source']['resourceid'],
                        headers=self.headers)
                    indicator_analysis_dimensions_business_name = '、'.join(
                        indicator_analysis_dimensions_business_name_list)
                    description_append_analysis_dimensions_info = description + ' 主要分析维度有：' + indicator_analysis_dimensions_business_name + '。'
                    self.pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source'][
                        'resourcename']: description_append_analysis_dimensions_info})

        all_hits_limit = int(self.search_configs.sailor_search_qa_cites_num_limit)
        self.pro_data_formview = self.pro_data_formview[:all_hits_limit]

        logger.info(f'after cutoff : pro_data_formview = {self.pro_data_formview}')
        logger.info(f'pro_data_svc = {self.pro_data_svc}')
        logger.info(f'pro_data_indicator = {self.pro_data_indicator}')

    # # 调用大模型
    # # prompt_name 是提示词模版的名称
    # # table_name 是前一步查询知识库得到的所有候选表名,调用大模型的时候没有用到, 是在解析大模型返回结果的时候用到的
    # # 数据资源版中, table_name是形如 'table_name','interface_name','indicator_name'这样的字符串,
    # # 用于区分不同的数据资源: 逻辑视图/接口服务/指标
    # async def _qw_gpt(self, pro_data, prompt_name, table_name, resource_type):
    #
    #     start1 = time.ctime()
    #     start = time.time()
    #     # 根据资源类型选择对应的结果容器
    #     if resource_type == 'formview':
    #         target_container = self.formview_results
    #     elif resource_type == 'svc':
    #         target_container = self.svc_results
    #     elif resource_type == 'indicator':
    #         target_container = self.ind_results
    #     elif resource_type == 'data_catalog':
    #         target_container = self.catalog_results
    #     else:
    #         logger.error(f'{resource_type} 不支持的资源类型!!!')
    #         raise Exception(f'{resource_type} 不支持的资源类型!!!')
    #
    #     # 清空之前的结果
    #     target_container['res'].clear()
    #     target_container['res_reason'] = ''
    #     target_container['res_json'] = {}
    #     target_container['related_info'].clear()
    #     # ad = PromptServices()
    #     # prompt_data 是提示词模版中的变量
    #     prompt_data = {'data_dict': str(pro_data), 'query': self.search_params.query}
    #     # prompt_id 是AD模型工厂中提示词模版的id
    #     _, prompt_id = await prompt_svc.from_anydata(self.search_params.ad_appid, prompt_name)
    #     logger.info(f"prompt_data = {prompt_data}")
    #     logger.info(f"prompt_id = {prompt_id}")
    #     try:
    #         # 调用大模型,
    #         res = await find_number_api.exec_prompt_by_llm(
    #             inputs=prompt_data,
    #             appid=self.search_params.ad_appid,
    #             prompt_id=prompt_id,
    #             search_configs=self.search_configs
    #         )
    #     except Exception as e:
    #         logger.error('调用大模型出错，报错信息如下: {str(e)}')
    #         res = " "
    #     if res:
    #         logger.info(f'大模型调用返回结果 = {res}')
    #         # sp是大模型返回结果中的json部分
    #         sp = res.split("```")
    #         if len(sp) > 1:
    #             if sp[1][:4] == 'json':
    #                 a = sp[1][4:]
    #             else:
    #                 a = sp[1]
    #             try:
    #                 # res_json 是大模型返回结果中的json部分
    #                 target_container['res_json'] = json.loads(a)
    #             except:
    #                 target_container['res_json'] = {}
    #             if "推荐实例" in target_container['res_json']:
    #                 for i in target_container['res_json']["推荐实例"]:
    #                     #  res 是资源名称, 从res_json中拆出来的
    #                     target_container['res'].append(i[table_name])
    #             if "分析步骤" in target_container['res_json']:
    #                 target_container['res_reason'] = target_container['res_json']["分析步骤"]
    #         else:
    #             target_container['res_json'] = {}
    #         end1 = time.ctime()
    #         end = time.time()
    #         logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
    #         # logger.debug('大模型整理结果', res, res_reason,res_json)
    #         # res_json 是大模型原始返回结果
    #         # res 是资源名称, 从res_json中拆出来的
    #         # res_reason是分析思路话术, 从res_json中拆出来的
    #         logger.info(
    #             f'大模型返回结果整理后: \nres = {target_container["res"]}\nres_reason = {target_container["res_reason"]}\nres_json = {target_container["res_json"]}')
    #         return target_container
    #     else:
    #         return {}

    async def _qw_gpt_dip(self, pro_data, prompt_name, table_name, resource_type):

        start1 = time.ctime()
        start = time.time()
        # 根据资源类型选择对应的结果容器
        if resource_type == 'formview':
            target_container = self.formview_results
        elif resource_type == 'svc':
            target_container = self.svc_results
        elif resource_type == 'indicator':
            target_container = self.ind_results
        elif resource_type == 'data_catalog':
            target_container = self.catalog_results
        else:
            logger.error(f'{resource_type} 不支持的资源类型!!!')
            raise Exception(f'{resource_type} 不支持的资源类型!!!')

        # 清空之前的结果
        target_container['res'].clear()
        target_container['res_reason'] = ''
        target_container['res_json'] = {}
        target_container['related_info'].clear()
        # ad = PromptServices()
        # prompt_data 是提示词模版中的变量
        prompt_var_data = {'data_dict': str(pro_data), 'query': self.search_params.query}
        logger.info(f"prompt_var_data = {prompt_var_data}")

        prompt_template = prompt_map.get(prompt_name,"")
        if prompt_template:
            prompt_rendered = prompt_template
            for prompt_var, value in prompt_var_data.items():
                prompt_rendered = prompt_rendered.replace("{{" + str(prompt_var) + "}}", str(value))
            prompt_rendered_msg = [
                {
                    "role": "user",
                    "content": prompt_rendered
                }
            ]
        else:
            raise Exception(f"prompt_template is None, prompt_name={prompt_name}")
        try:
            # 调用大模型,
            # res = await find_number_api.exec_prompt_by_llm_dip_private(
            #     prompt_rendered_msg=prompt_rendered_msg,
            #     search_configs=self.search_configs,
            #     x_account_id=self.x_account_id
            # )
            # 改成外部接口调用
            res = await find_number_api.exec_prompt_by_llm_dip_external(
                token=self.headers.get('Authorization'),
                prompt_rendered_msg=prompt_rendered_msg,
                search_configs=self.search_configs
            )
            logger.info(f'_qw_gpt_dip: 调用大模型成功，返回结果为: {res}')
        except Exception as e:
            logger.error(f'调用大模型出错，报错信息如下: {str(e)}')
            res = " "
        if res:
            logger.info(f'大模型调用返回结果 = {res}')
            # sp是大模型返回结果中的json部分
            sp = res.split("```")
            if len(sp) > 1:
                if sp[1][:4] == 'json':
                    a = sp[1][4:]
                else:
                    a = sp[1]
                try:
                    # res_json 是大模型返回结果中的json部分
                    target_container['res_json'] = json.loads(a)
                except:
                    target_container['res_json'] = {}
                if "推荐实例" in target_container['res_json']:
                    for i in target_container['res_json']["推荐实例"]:
                        #  res 是资源名称, 从res_json中拆出来的
                        target_container['res'].append(i[table_name])
                if "分析步骤" in target_container['res_json']:
                    target_container['res_reason'] = target_container['res_json']["分析步骤"]
            else:
                target_container['res_json'] = {}
            end1 = time.ctime()
            end = time.time()
            logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
            # logger.debug('大模型整理结果', res, res_reason,res_json)
            # res_json 是大模型原始返回结果
            # res 是资源名称, 从res_json中拆出来的
            # res_reason是分析思路话术, 从res_json中拆出来的
            logger.info(
                f'大模型返回结果整理后: \nres = {target_container["res"]}\nres_reason = {target_container["res_reason"]}\nres_json = {target_container["res_json"]}')
            return target_container
        else:
            return {}

    # # 2025.10.15 为报告生成工具用部门职责数据， 将”相关信息“单独解析出来
    # async def _qw_gpt_kecc(self, pro_data, dept_infosystem_duty, prompt_name, table_name, resource_type):
    #     # res = []
    #     # res_reason = ''
    #     # related_info = []
    #     start1 = time.ctime()
    #     start = time.time()
    #     # 根据资源类型选择对应的结果容器
    #     if resource_type == 'formview':
    #         target_container = self.formview_results
    #     elif resource_type == 'svc':
    #         target_container = self.svc_results
    #     elif resource_type == 'indicator':
    #         target_container = self.ind_results
    #     elif resource_type == 'data_catalog':
    #         target_container = self.catalog_results
    #     else:
    #         error_msg = f'不支持的资源类型: {resource_type}!!!'
    #         logger.error(error_msg)
    #         raise Exception(error_msg)
    #     # 清空之前的结果
    #     target_container['res'].clear()
    #     target_container['res_reason'] = ''
    #     target_container['res_json'] = {}
    #     target_container['related_info'].clear()
    #     # ad = PromptServices()
    #     data_str = json.dumps(pro_data, ensure_ascii=False, separators=(',', ':'))
    #     dept_infosystem_duty_str = json.dumps(dept_infosystem_duty, ensure_ascii=False, separators=(',', ':'))
    #     # prompt_var_data 是提示词模版中的变量值
    #     prompt_var_data = {
    #         'data_dict': data_str,
    #         'dept_infosystem_duty': dept_infosystem_duty_str,
    #         'query': self.search_params.query
    #     }
    #     # prompt_data = {'data_dict': str(data), 'dept_infosystem_duty': dept_infosystem_duty, 'query': query}
    #     # prompt_id 是AD模型工厂中提示词模版的id
    #     _, prompt_id = await prompt_svc.from_anydata(self.search_params.ad_appid, prompt_name)
    #     # logger.debug(prompt_data, prompt_id)
    #     try:
    #         # 调用大模型,
    #         res = await find_number_api.exec_prompt_by_llm(
    #             inputs=prompt_var_data,
    #             appid=self.search_params.ad_appid,
    #             prompt_id = prompt_id,
    #             search_configs=self.search_configs
    #         )
    #     except Exception as e:
    #         logger.info(f'调用大模型出错，报错信息如下: {str(e)}')
    #         res = " "
    #     if res:
    #         logger.info(f'大模型调用返回结果 =  {res}')
    #         # sp是大模型返回结果中的json部分
    #         res_sp = res.split("```")
    #         # logger.debug(f"res_sp = {res_sp}")
    #         if len(res_sp) > 1:
    #             if res_sp[1][:4] == 'json':
    #                 answer = res_sp[1][4:]
    #             else:
    #                 answer = res_sp[1]
    #             # logger.debug(f"res_sp = {res_sp}")
    #
    #             try:
    #                 # res_json 是大模型返回结果中的json部分
    #                 target_container['res_json'] = json.loads(answer)
    #             except Exception as e:
    #                 target_container['res_json'] = {}
    #                 logger.info(f"json.loads error:{str(e)}")
    #             # logger.debug(f"res_json={target_container['res_json']}")
    #             if "推荐实例" in target_container['res_json']:
    #                 for item in target_container['res_json']["推荐实例"]:
    #                     #  res 是资源名称, 从res_json中拆出来的
    #                     target_container['res'].append(item[table_name])
    #                     # logger.debug(f"res={target_container['res']}")
    #             if "分析步骤" in target_container['res_json']:
    #                 target_container['res_reason'] = target_container['res_json']["分析步骤"]
    #                 # logger.debug(f"res_reason={target_container['res_reason']}")
    #             # 分析问答型搜索修改提示词后， 相关信息部分大模型输出的是一个json列表
    #             if "相关信息" in target_container['res_json']:
    #                 logger.info(f"res_json['相关信息'] = {target_container['res_json']['相关信息']}")
    #                 for item in target_container['res_json']["相关信息"]:
    #                     target_container['related_info'].append(item)
    #                     # logger.info(f'related_info={target_container["related_info"]}')
    #                 # if isinstance(res_json["相关信息"], str):
    #                 #     res_reason = res_reason + '<br>' + res_json["相关信息"]
    #                 # # 如果“相关信息”的值是列表，这里使用空格作为分隔符连接列表元素
    #                 # elif isinstance(res_json["相关信息"], list):
    #                 #     res_reason = res_reason + '<br>' + ' '.join(res_json["相关信息"])
    #                 # else:
    #                 #     # 对于其他类型的数据，尝试直接转换成字符串
    #                 #     res_reason = res_reason + '<br>' + str(res_json["相关信息"])
    #                 # # logger.debug(f"res_reason={res_reason}")
    #
    #         else:
    #             target_container['res_json'] = {}
    #         end1 = time.ctime()
    #         end = time.time()
    #         logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
    #         # target_container['res_reason'] = target_container['res_reason']
    #
    #         # res_json 是大模型原始返回结果的json部分, 要求大模型返回json形式
    #         # res 是资源名称, 从res_json中拆出来的
    #         # res_reason是分析思路话术, 从res_json中拆出来的
    #         # related_info 是部门职责数据， 单位-职责-信息系统
    #         logger.info(dedent(
    #             f'''
    #             大模型返回结果整理后:
    #             res = {target_container['res']}
    #             res_reason = {target_container['res_reason']}
    #             related_info={target_container['related_info']}
    #             res_json = {target_container['res_json']}
    #             ''').strip())
    #         # return res, res_reason, related_info, res_json
    #         return target_container
    #     else:
    #         return {}

    async def _qw_gpt_kecc_dip(self, pro_data, dept_infosystem_duty, prompt_name, table_name, resource_type):
        # res = []
        # res_reason = ''
        # related_info = []
        start1 = time.ctime()
        start = time.time()
        # 根据资源类型选择对应的结果容器
        if resource_type == 'formview':
            target_container = self.formview_results
        elif resource_type == 'svc':
            target_container = self.svc_results
        elif resource_type == 'indicator':
            target_container = self.ind_results
        elif resource_type == 'data_catalog':
            target_container = self.catalog_results
        else:
            error_msg = f'不支持的资源类型: {resource_type}!!!'
            logger.error(error_msg)
            raise Exception(error_msg)
        # 清空之前的结果
        target_container['res'].clear()
        target_container['res_reason'] = ''
        target_container['res_json'] = {}
        target_container['related_info'].clear()
        # ad = PromptServices()
        data_str = json.dumps(pro_data, ensure_ascii=False, separators=(',', ':'))
        dept_infosystem_duty_str = json.dumps(dept_infosystem_duty, ensure_ascii=False, separators=(',', ':'))
        # prompt_var_data 是提示词模版中的变量值
        prompt_var_data = {
            'data_dict': data_str,
            'dept_infosystem_duty': dept_infosystem_duty_str,
            'query': self.search_params.query
        }

        prompt_template = prompt_map.get(prompt_name,"")

        if prompt_template:
            prompt_rendered = prompt_template
            for prompt_var, value in prompt_var_data.items():
                prompt_rendered = prompt_rendered.replace("{{" + str(prompt_var) + "}}", str(value))
            prompt_rendered_msg = [
                {
                    "role": "user",
                    "content": prompt_rendered
                }
            ]
        else:
            raise Exception(f"prompt_template is empty, prompt_name={prompt_name}")
        try:
            # 调用大模型,
            # res = await find_number_api.exec_prompt_by_llm_dip_private(
            #     prompt_rendered_msg=prompt_rendered_msg,
            #     search_configs=self.search_configs,
            #     x_account_id=self.x_account_id
            # )
            # 改成外部接口调用
            res = await find_number_api.exec_prompt_by_llm_dip_external(
                token=self.headers.get('Authorization'),
                prompt_rendered_msg=prompt_rendered_msg,
                search_configs=self.search_configs
            )
            logger.info(f'_qw_gpt_kecc_dip: 调用大模型成功，返回结果为: {res}')
        except Exception as e:
            logger.info(f'调用大模型出错，报错信息如下: {str(e)}')
            res = " "
        if res:
            logger.info(f'大模型调用返回结果 =  {res}')
            # sp是大模型返回结果中的json部分
            res_sp = res.split("```")
            # logger.debug(f"res_sp = {res_sp}")
            if len(res_sp) > 1:
                if res_sp[1][:4] == 'json':
                    answer = res_sp[1][4:]
                else:
                    answer = res_sp[1]
                # logger.debug(f"res_sp = {res_sp}")

                try:
                    # res_json 是大模型返回结果中的json部分
                    target_container['res_json'] = json.loads(answer)
                except Exception as e:
                    target_container['res_json'] = {}
                    logger.info(f"json.loads error:{str(e)}")
                # logger.debug(f"res_json={target_container['res_json']}")
                if "推荐实例" in target_container['res_json']:
                    for item in target_container['res_json']["推荐实例"]:
                        #  res 是资源名称, 从res_json中拆出来的
                        target_container['res'].append(item[table_name])
                        # logger.debug(f"res={target_container['res']}")
                if "分析步骤" in target_container['res_json']:
                    target_container['res_reason'] = target_container['res_json']["分析步骤"]
                    # logger.debug(f"res_reason={target_container['res_reason']}")
                # 分析问答型搜索修改提示词后， 相关信息部分大模型输出的是一个json列表
                if "相关信息" in target_container['res_json']:
                    logger.info(f"res_json['相关信息'] = {target_container['res_json']['相关信息']}")
                    for item in target_container['res_json']["相关信息"]:
                        target_container['related_info'].append(item)
                        # logger.info(f'related_info={target_container["related_info"]}')
                    # if isinstance(res_json["相关信息"], str):
                    #     res_reason = res_reason + '<br>' + res_json["相关信息"]
                    # # 如果“相关信息”的值是列表，这里使用空格作为分隔符连接列表元素
                    # elif isinstance(res_json["相关信息"], list):
                    #     res_reason = res_reason + '<br>' + ' '.join(res_json["相关信息"])
                    # else:
                    #     # 对于其他类型的数据，尝试直接转换成字符串
                    #     res_reason = res_reason + '<br>' + str(res_json["相关信息"])
                    # # logger.debug(f"res_reason={res_reason}")

            else:
                target_container['res_json'] = {}
            end1 = time.ctime()
            end = time.time()
            logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
            # target_container['res_reason'] = target_container['res_reason']

            # res_json 是大模型原始返回结果的json部分, 要求大模型返回json形式
            # res 是资源名称, 从res_json中拆出来的
            # res_reason是分析思路话术, 从res_json中拆出来的
            # related_info 是部门职责数据， 单位-职责-信息系统
            logger.info(dedent(
                f'''
                大模型返回结果整理后: 
                res = {target_container['res']}
                res_reason = {target_container['res_reason']}
                related_info={target_container['related_info']}
                res_json = {target_container['res_json']}
                ''').strip())
            # return res, res_reason, related_info, res_json
            return target_container
        else:
            return {}

    # # 调用大模型
    # # pro_data 是大模型提示词中 {{data_dict}} 的部分, 含义可能是processed_data, 是经过处理之后的, 可以直接调用大模型的
    # # query 是 大模型提示词中 用户的 query
    # # prompt_name 是提示词模版的名称
    # # table_name 是前一步查询知识库得到的所有候选表名,调用大模型的时候没有用到, 是在解析大模型返回结果的时候用到的
    # # 数据资源版中, table_name是形如 'table_name','interface_name','indicator_name'这样的字符串,
    # # 用于区分不同的数据资源: 逻辑视图/接口服务/指标
    # # all_hits 是调用大模型之后做校验用的, 用来判断大模型返回的数据资源是否在向量召回结果中, 如果不符,说明存在编造
    # async def _llm_invoke(self, pro_data, prompt_id_table, table_name, resource_type):
    #     if not pro_data:
    #         logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
    #         return False
    #     else:
    #         # res_load 是大模型原始返回结果
    #         # res 是资源名称, 从res_load中拆出来的
    #         # res_reason 是分析思路话术, 从res_load中拆出来的
    #         rst_container = await self._qw_gpt(
    #             pro_data=pro_data,
    #             prompt_name=prompt_id_table,
    #             table_name=table_name,
    #             resource_type='formview'
    #         )
    #         # res_id = [i.split('|')[0] for i in res]
    #         source_hits = self.all_hits_new
    #         res_id = [i.split('|')[0] for i in rst_container['res']]
    #         # 清空之前的结果
    #         rst_container['hits_graph'].clear()
    #
    #         # res 是 self.res
    #         # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
    #         # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
    #         # 命名中包含graph的含义是从图谱中查出来的
    #         # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
    #         #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
    #         # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
    #         # self.hits_graph = []
    #         for hit in source_hits:
    #             if '_selfid' in hit and hit['_selfid'] in res_id:
    #                 rst_container['hits_graph'].append(hit)
    #         # for hit in self.all_hits:
    #         #     if '_selfid' in hit and hit['_selfid'] in res_id:
    #         #         self.hits_graph.append(hit)
    #         # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
    #         # 为了后续前端在话术中加上资源序号数字角标
    #         # 生成简洁的命中列表
    #         rst_container['hits'] = [
    #             f"{hit['_selfid']}|{hit['_source']['resourcename']}"
    #             for hit in rst_container['hits_graph']
    #         ]
    #         # self.hits = [i["_selfid"] + '|' + i["_source"]["resourcename"] for i in self.hits_graph]
    #         if resource_type == 'formview':
    #             # source_hits = self.all_hits_new
    #             self.formview_results = rst_container
    #         elif resource_type == 'svc':
    #             # source_hits = self.all_hits_new
    #             self.svc_results = rst_container
    #         elif resource_type == 'indicator':
    #             # source_hits = self.all_hits_new
    #             self.ind_results = rst_container
    #         elif resource_type == 'data_catalog':
    #             # source_hits = self.all_hits_new
    #             self.catalog_results = rst_container
    #         else:
    #             logger.error(f'{resource_type} 不支持的资源类型!!!')
    #             raise  Exception(f'{resource_type} 不支持的资源类型!!!')
    #
    #         # return hits_graph, hits, res, res_reason, res_load
    #         return True


    async def _llm_invoke_dip(self, pro_data, prompt_id_table, table_name, resource_type):
        if not pro_data:
            logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
            return False
        else:
            # res_load 是大模型原始返回结果
            # res 是资源名称, 从res_load中拆出来的
            # res_reason 是分析思路话术, 从res_load中拆出来的
            rst_container = await self._qw_gpt_dip(
                pro_data=pro_data,
                prompt_name=prompt_id_table,
                table_name=table_name,
                resource_type='formview'
            )
            # res_id = [i.split('|')[0] for i in res]
            source_hits = self.all_hits_new
            res_id = [i.split('|')[0] for i in rst_container['res']]
            # 清空之前的结果
            rst_container['hits_graph'].clear()

            # res 是 self.res
            # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
            # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
            # 命名中包含graph的含义是从图谱中查出来的
            # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
            #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
            # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
            # self.hits_graph = []
            for hit in source_hits:
                if '_selfid' in hit and hit['_selfid'] in res_id:
                    rst_container['hits_graph'].append(hit)
            # for hit in self.all_hits:
            #     if '_selfid' in hit and hit['_selfid'] in res_id:
            #         self.hits_graph.append(hit)
            # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
            # 为了后续前端在话术中加上资源序号数字角标
            # 生成简洁的命中列表
            rst_container['hits'] = [
                f"{hit['_selfid']}|{hit['_source']['resourcename']}"
                for hit in rst_container['hits_graph']
            ]
            # self.hits = [i["_selfid"] + '|' + i["_source"]["resourcename"] for i in self.hits_graph]
            if resource_type == 'formview':
                # source_hits = self.all_hits_new
                self.formview_results = rst_container
            elif resource_type == 'svc':
                # source_hits = self.all_hits_new
                self.svc_results = rst_container
            elif resource_type == 'indicator':
                # source_hits = self.all_hits_new
                self.ind_results = rst_container
            elif resource_type == 'data_catalog':
                # source_hits = self.all_hits_new
                self.catalog_results = rst_container
            else:
                logger.error(f'{resource_type} 不支持的资源类型!!!')
                raise  Exception(f'{resource_type} 不支持的资源类型!!!')

            # return hits_graph, hits, res, res_reason, res_load
            return True


    # # 部门职责知识增强算法的大模型调用, 增加入参 dept_infosystem_duty
    # # 将”相关信息“单独解析出来
    # async def _llm_invoke_kecc(self, pro_data, dept_infosystem_duty, prompt_id_table, table_name, resource_type):
    #     if not pro_data:
    #         logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
    #         # return [], [], [], '', {}
    #         return False
    #     else:
    #         # res_load 是大模型原始返回结果
    #         # res 是资源名称, 从res_load中"推荐实例"拆出来的 self.res
    #         # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
    #         # res, res_reason, related_info, res_load = await self._qw_gpt_kecc(
    #         rst_container = await self._qw_gpt_kecc(
    #             pro_data=pro_data,
    #             prompt_name=prompt_id_table,
    #             table_name=table_name,
    #             dept_infosystem_duty=dept_infosystem_duty,
    #             resource_type=resource_type
    #         )
    #
    #         source_hits = self.all_hits_new
    #         res_id = [i.split('|')[0] for i in rst_container['res']]
    #         # 清空之前的结果
    #         rst_container['hits_graph'].clear()
    #         # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
    #         # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
    #         # 命名中包含graph的含义是从图谱中查出来的
    #         # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
    #         #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
    #         # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
    #         # hits_graph = []
    #         for hit in source_hits:
    #             if '_selfid' in hit and hit['_selfid'] in res_id:
    #                 rst_container['hits_graph'].append(hit)
    #         # for hit in self.all_hits_new:
    #         #     if '_selfid' in hit and hit['_selfid'] in res_id:
    #         #         self.hits_graph.append(hit)
    #         # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
    #         # 为了后续前端在话术中加上资源序号数字角标
    #         rst_container['hits'] = [
    #             f"{hit['_selfid']}|{hit['_source']['resourcename']}"
    #             for hit in rst_container['hits_graph']
    #         ]
    #         if resource_type == 'formview':
    #             # source_hits = self.all_hits_new
    #             self.formview_results = rst_container
    #         elif resource_type == 'svc':
    #             # source_hits = self.all_hits_new
    #             self.svc_results = rst_container
    #         elif resource_type == 'indicator':
    #             # source_hits = self.all_hits_new
    #             self.ind_results = rst_container
    #         elif resource_type == 'data_catalog':
    #             # source_hits = self.all_hits_new
    #             self.catalog_results = rst_container
    #         else:
    #             logger.error(f'{resource_type} 不支持的资源类型!!!')
    #             raise  Exception(f'{resource_type} 不支持的资源类型!!!')
    #         #
    #         # if resource_type == 'formview':
    #         #     source_hits = self.all_hits_new
    #         #     rst_container = self.formview_results
    #         # elif resource_type == 'svc':
    #         #     source_hits = self.all_hits_new
    #         #     rst_container = self.svc_results
    #         # elif resource_type == 'indicator':
    #         #     source_hits = self.all_hits_new
    #         #     rst_container = self.ind_results
    #         # elif resource_type == 'data_catalog':
    #         #     source_hits = self.all_hits_new
    #         #     rst_container = self.catalog_results
    #         # else:
    #         #     logger.error(f'{resource_type} 不支持的资源类型!!!')
    #         #     raise  Exception(f'{resource_type} 不支持的资源类型!!!')
    #         # res_id = [i.split('|')[0] for i in rst_container['res']]
    #         # # 清空之前的结果
    #         # rst_container['hits_graph'].clear()
    #         # # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
    #         # # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
    #         # # 命名中包含graph的含义是从图谱中查出来的
    #         # # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
    #         # #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
    #         # # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
    #         # # hits_graph = []
    #         # for hit in source_hits:
    #         #     if '_selfid' in hit and hit['_selfid'] in res_id:
    #         #         rst_container['hits_graph'].append(hit)
    #         # # for hit in self.all_hits_new:
    #         # #     if '_selfid' in hit and hit['_selfid'] in res_id:
    #         # #         self.hits_graph.append(hit)
    #         # # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
    #         # # 为了后续前端在话术中加上资源序号数字角标
    #         # rst_container['hits'] = [
    #         #     f"{hit['_selfid']}|{hit['_source']['resourcename']}"
    #         #     for hit in rst_container['hits_graph']
    #         # ]
    #         # self.hits = [hg["_selfid"] + '|' + hg["_source"]["resourcename"] for hg in self.hits_graph]
    #         # logger.info(f"hits_graph={hits_graph}")
    #         # logger.info(f"hits={hits}")
    #         # logger.info(f"res={res}")
    #         # logger.info(f"res_reason={res_reason}")
    #
    #         # return hits_graph, hits, res, res_reason, related_info, res_load
    #         return True

    async def _llm_invoke_kecc_dip(self, pro_data, dept_infosystem_duty, prompt_id_table, table_name, resource_type):
        if not pro_data:
            logger.info(f'{table_name}, 入参为空,不走大模型,减少此次交互')
            # return [], [], [], '', {}
            return False
        else:
            # res_load 是大模型原始返回结果
            # res 是资源名称, 从res_load中"推荐实例"拆出来的 self.res
            # res_reason 是分析思路话术, 从res_load中拆出来的, "分析步骤"+"相关信息"
            # res, res_reason, related_info, res_load = await self._qw_gpt_kecc(
            rst_container = await self._qw_gpt_kecc_dip(
                pro_data=pro_data,
                prompt_name=prompt_id_table,
                table_name=table_name,
                dept_infosystem_duty=dept_infosystem_duty,
                resource_type=resource_type
            )

            source_hits = self.all_hits_new
            res_id = [i.split('|')[0] for i in rst_container['res']]
            # 清空之前的结果
            rst_container['hits_graph'].clear()
            # 核验大模型返回的id是否在all_hits中(向量召回结果), 判断大模型是否存在编造
            # hits_graph 收集了那些大模型返回的 ID 与向量召回结果中的 ID 相匹配的记录。
            # 命名中包含graph的含义是从图谱中查出来的
            # all_hits 中的['_selfid']字段，是在向量搜索之后，认知搜索算法为每一个召回资源增加了一个简短的id字段，
            #  all_hits['_selfid'] = str(num)   用其在召回结果中的序号来标识， 0，1，2，3这样的简短形式
            # 目的是减少大模型交互中的token数， 将原来冗长的雪花id或者uuid，简化为数字
            # hits_graph = []
            for hit in source_hits:
                if '_selfid' in hit and hit['_selfid'] in res_id:
                    rst_container['hits_graph'].append(hit)
            # for hit in self.all_hits_new:
            #     if '_selfid' in hit and hit['_selfid'] in res_id:
            #         self.hits_graph.append(hit)
            # - `hits` 提供了一个更简洁的形式来表示 `hits_graph` 中的项目，仅保留了项目的 ID 和名称信息。
            # 为了后续前端在话术中加上资源序号数字角标
            rst_container['hits'] = [
                f"{hit['_selfid']}|{hit['_source']['resourcename']}"
                for hit in rst_container['hits_graph']
            ]
            if resource_type == 'formview':
                # source_hits = self.all_hits_new
                self.formview_results = rst_container
            elif resource_type == 'svc':
                # source_hits = self.all_hits_new
                self.svc_results = rst_container
            elif resource_type == 'indicator':
                # source_hits = self.all_hits_new
                self.ind_results = rst_container
            elif resource_type == 'data_catalog':
                # source_hits = self.all_hits_new
                self.catalog_results = rst_container
            else:
                logger.error(f'{resource_type} 不支持的资源类型!!!')
                raise  Exception(f'{resource_type} 不支持的资源类型!!!')
            return True

    async def _invoke_llm_multi_resource_type(self):
        """调用大模型处理不同类型的数据资源"""
        # 逻辑视图处理
        if not self.pro_data_formview:
            task_view = asyncio.create_task(skip_model('form_view'))
        else:
            task_view = asyncio.create_task(
                self._llm_invoke_kecc_dip(
                    pro_data=self.pro_data_formview,
                    dept_infosystem_duty=self.all_hits_kecc,
                    prompt_id_table="all_table_kecc",
                    table_name='table_name',
                    resource_type='formview'
                )
            )

        # 接口服务处理
        if not self.pro_data_svc:
            task_svc = asyncio.create_task(skip_model('interface_service'))
        else:
            task_svc = asyncio.create_task(
                self._llm_invoke_dip(
                    pro_data=self.pro_data_svc,
                    prompt_id_table="all_interface",
                    table_name='interface_name',
                    resource_type='svc'
                )
            )

        # 指标处理
        if not self.pro_data_indicator:
            task_ind = asyncio.create_task(skip_model('indicator'))
        else:
            task_ind = asyncio.create_task(
                self._llm_invoke_dip(
                    self.pro_data_indicator,
                    prompt_id_table="all_indicator",
                    table_name='indicator_name',
                    resource_type='indicator'
                )
            )

        try:
            # 执行成功， rst_status=(True,True,True)， 执行结果在实例属性中，
            # 默认行为：asyncio.gather() 在默认情况下（没有设置 return_exceptions=True），当任何任务抛出异常时，会立即抛出该异常并取消其他仍在运行的任务。
            # 使用 return_exceptions=True：只有设置了 return_exceptions=True 参数时，asyncio.gather() 才会将异常对象作为结果列表中的元素返回，而不是抛出异常。
            rst_status = await asyncio.gather(task_view, task_svc, task_ind)
            # 检查各个任务的执行结果
            # for i, result in enumerate(rst_status):
            #     if isinstance(result, Exception):
            #         task_names = ['逻辑视图', '接口服务', '指标']
            #         logger.error(f"{task_names[i]}任务执行失败: {result}")
            #         # 可以选择继续执行其他任务或直接抛出异常
            #         raise result
        except Exception as e:
            logger.error(f"分析问答型搜索大模型处理异常:{str(e)}!!!")
            raise

        # 等待所有任务完成
        # 通过示例属性来获取任务的结果
        # hits_graph_view, hits_view, res_view, res_view_reason, related_info, res_load_view = await task_view
        # hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = await task_svc
        # hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = await task_ind
        #
        # return {
        #     'view': (hits_graph_view, hits_view, res_view, res_view_reason, related_info, res_load_view),
        #     'svc': (hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc),
        #     'ind': (hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind)
        # }
        return True


    # async def resource_analysis_search_kecc_for_qa(self, search_params=None):
    async def resource_analysis_search_kecc_for_qa(self, search_params=None):
        """有部门职责知识增强的分析问答型搜索"""
        # 如果传入了新的search_params，则更新实例属性
        if search_params is not None:
            self.search_params = search_params
        # logger.info(f"resource_analysis_search_kecc_for_qa() search_params={self.search_params}")

        total_start_time = time.time()

        # 1. 初始化搜索（获取query embedding）
        if not await self._query_embedding():
            return ANALYSIS_SEARCH_EMPTY_RESULT

        try:
            # 2. 执行认知搜索（向量搜索+关键词搜索+关联搜索）
            await self._perform_cognitive_search_resource()

            # 3. 执行部门职责知识增强搜索
            logger.info(f"self.search_configs={self.search_configs}")
            logger.info(f'self._if_kecc()={self._if_kecc()}')
            if self._if_kecc():
                logger.info("执行部门职责知识增强...")
                await self._perform_kecc_search()

            # 4. 获取用户权限信息
            auth_id=[]
            if self._should_auth_check():
                try:
                    auth_id = await find_number_api.user_all_auth(
                        headers=self.headers,
                        subject_id=self.search_params.subject_id
                    )
                except Exception as e:
                    logger.error(f"取用户拥有权限的所有资源id，发生错误：{str(e)}")
                    return ANALYSIS_SEARCH_EMPTY_RESULT

            # 5. 数据运营工程师和开发工程师特殊处理
            if "data-operation-engineer" in self.search_params.roles or "data-development-engineer" in self.search_params.roles:
                logger.info('用户是数据开发工程师和运营工程师,可以搜索查看所有数据')
            else:
                logger.info(f'该用户有权限的id = {auth_id}')

            # 6. 过滤搜索结果, 准备数据给大模型进行判断
            await self._filter_results_and_prepare_llm_input(auth_id)

            # 7. 调用大模型处理
            await self._invoke_llm_multi_resource_type()

            # 8. 处理结果并组装最终输出
            # 从llm_results中提取各类结果
            # res_view,res_svc,res_ind 都是对应的 res
            # hits_graph_view, hits_view, res_view, res_view_reason, related_info, res_load_view = llm_results['view']
            # hits_graph_svc, hits_svc, res_svc, res_svc_reason, res_load_svc = llm_results['svc']
            # hits_graph_ind, hits_ind, res_ind, res_ind_reason, res_load_ind = llm_results['ind']

            # 合并所有实体
            # entities_all = hits_graph_ind + hits_graph_view + hits_graph_svc
            logger.info(f"self.ind_results={self.ind_results}")
            logger.info(f"self.formview_results={self.formview_results}")
            logger.info(f"self.svc_results={self.svc_results}")
            entities_all = self.ind_results['hits_graph']+self.formview_results['hits_graph']+self.svc_results['hits_graph']
            hits_all_name = [entity["_source"]["resourcename"] for entity in entities_all]

            # 构建entities
            entities = []
            for num, i in enumerate(entities_all):
                resource_entity_copy = copy.deepcopy(resource_entity)
                resource_entity_copy["id"] = i["_id"]
                resource_entity_copy["default_property"]["value"] = i["_source"]["resourcename"]
                for props in resource_entity_copy["properties"][0]["props"]:
                    if props["name"] in i["_source"].keys():
                        props['value'] = i["_source"][props["name"]]
                entities.append({
                    "starts": [],
                    "entity": resource_entity_copy,
                    "score": self.search_params.limit - num
                })

            # 构建输出结果
            self.output['entities'] = entities
            self.output['count'] = len(entities_all)
            self.output['answer'], self.output['subgraphs'], self.output['query_cuts'] = ' ', [], []

            # 对大模型输出结果进行校验
            # 处理指标解释
            explanation_service = {}
            res_explain = '以下是一个可能的分析思路建议，可根据指标获取答案:'

            if len(self.ind_results['hits_graph']) > 0:
                if len(self.ind_results['hits_graph']) == len(self.ind_results['res']):
                    explanation_ind, explanation_statu = add_label(self.ind_results['res_reason'], self.ind_results['hits'], 0)
                    logger.info(f"返回的话术和状态码 = {explanation_ind}, {explanation_statu}")
                    if explanation_statu == '0':
                        use_hits = [i["_selfid"] + '|' + i["_source"]["resourcename"] for i in self.ind_results['hits_graph']]
                        explanation_ind = add_label_easy(res_explain, use_hits)
                        logger.info(f"话术不可用时，拼接话术 = {explanation_ind}, {explanation_statu}")
                    res_statu = '1'
                    explanation_statu = '1'
                else:
                    explanation_ind, res_statu, explanation_statu = ' ', '1', '0'
            else:
                explanation_ind, res_statu, explanation_statu = ' ', '0', '0'
            # self.ind_results['explanation_ind'] = explanation_ind

            # 处理逻辑视图解释
            logger.info(f"len(self.formview_results['hits_graph'])={len(self.formview_results['hits_graph'])}")
            logger.info(f"len(self.formview_results['res'])={len(self.formview_results['res'])}")
            logger.info(f"self.formview_results['res_reason']={self.formview_results['res_reason']}")
            logger.info(f"self.formview_results['hits']={self.formview_results['hits']}")
            # logger.info(f"")
            if len(self.formview_results['hits_graph']) > 0:
                if len(self.formview_results['hits_graph']) == len(self.formview_results['res']):
                    logger.info(f"逻辑视图大模型结果校验正常路径...")
                    explanation_formview, explanation_st = add_label(self.formview_results['res_reason'], self.formview_results['hits'], len(self.ind_results['hits_graph']))
                    logger.info(f"逻辑视图话术和状态码 = {explanation_formview}, {explanation_st}")
                    res_statu += '1'
                    explanation_statu += explanation_st
                else:
                    logger.info(f"逻辑视图大模型结果校验异常路径：结果数量不等...")
                    explanation_formview = ' '
                    res_statu += '1'
                    explanation_statu += '0'
            else:
                logger.info(f"逻辑视图大模型结果校验异常路径：搜索结果为空...")
                explanation_formview = ' '
                res_statu += '0'
                explanation_statu += '0'
            # self.formview_results['explanation_formview']=explanation_formview
            logger.info(f"explanation_formview={explanation_formview}")

            # 处理接口服务解释
            if len(self.svc_results['hits_graph']) > 0:
                if len(self.svc_results['hits_graph']) == len(self.svc_results['res']):
                    explanation_service["explanation_params"] =self.svc_results['res_load']
                    for i in self.svc_results['res_load']['推荐实例']:
                        i['interface_name'] = i["interface_name"].split('|')[1]
                    explanation_service["explanation_text"], explana_s = add_label(
                        self.svc_results['res_reason'],
                        self.svc_results['hits'],
                        len(self.ind_results['hits_graph']) + len(self.formview_results['hits_graph'])
                    )
                    res_statu += '1'
                    explanation_statu += explana_s
                else:
                    c_res = self.svc_results['res_load']['推荐实例']
                    c_res1 = c_res[:]
                    for i in c_res1:
                        if i["interface_name"].split('|')[1] not in hits_all_name:
                            self.svc_results['res_load'].remove(i)
                    for i in c_res:
                        i['interface_name'] = i["interface_name"].split('|')[1]
                    self.svc_results['res_load']['推荐实例'] = c_res
                    explanation_service["explanation_params"] = self.svc_results['res_load']
                    explanation_service["explanation_text"] = ''
                    res_statu += '1'
                    explanation_statu += '0'
            else:
                explanation_service["explanation_params"] = ''
                explanation_service["explanation_text"] = ''
                res_statu += '0'
                explanation_statu += '0'
            # self.svc_results['explanation_service']["explanation_params"]=explanation_service["explanation_params"]
            # self.svc_results['explanation_service']["explanation_text"] = explanation_service["explanation_text"]

            # 设置输出中的解释信息
            self.output['explanation_ind'] = explanation_ind
            self.output['explanation_formview'] = explanation_formview
            self.output['explanation_service'] = explanation_service

            # 记录总耗时
            total_end_time = time.time()
            total_time_cost = total_end_time - total_start_time
            logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")

            # 日志记录
            logger.info(dedent(f"""
                ===================返回话术：指标==============
                {self.output['explanation_ind']}
                ===================返回话术：逻辑视图===================
                {self.output['explanation_formview']}
                ===================返回话术：接口服务===================
                {self.output['explanation_service']['explanation_text']}""").strip()
                        )

            log_content = "\n".join(
                f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
                for entity in self.output["entities"]
            )
            logger.info(f'--------------问答部分最终召回的资源-----------------\n{log_content}')
            logger.info(f"output = \n{self.output}")

            return self.output, res_statu, explanation_statu

        except Exception as e:
            logger.error(f"搜索处理过程中发生错误：{str(e)}")
            # raise
            return ANALYSIS_SEARCH_EMPTY_RESULT

    # inputs,API请求的Body部分
    # request,API请求的request部分
    # 按照oop重写 catalog_analysis_main,未完成， 还未使用
    async def catalog_analysis_search_for_qa(self,request, search_params):
        '''数据目录版分析问答型搜索算法主函数'''
        # init_qa(request, inputs)完成 (1)获取图谱信息和 query 向量化;(2) 向量搜索
        # all_hits 是搜索命中的相似向量对应的实体id
        # drop_indices 是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
        if search_params is not None:
            self.search_params = search_params

        total_start_time = time.time()

        # 1. 初始化搜索（获取query embedding）
        if not await self._query_embedding():
            return ANALYSIS_SEARCH_EMPTY_RESULT

        try:
            # 2. 执行认知搜索（向量搜索+关键词搜索+关联搜索）
            total_start_time, drop_indices = await self._perform_cognitive_search_catalog()


            logger.info(f"OpenSearch召回数量：{len(self.all_hits)}")
            # pro_data_catalog = []
            # auth_header = {"Authorization": search_params.auth_header}
            # 当前用的 鉴权函数, 查询出该用户(subject_id)有权限的所有资源id
            # 如果是数据运营和数据开发工程师, 可以针对所有资源进行问答, 不权限
            auth_id = await find_number_api.user_all_auth(self.headers, self.search_params.subject_id)
            if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
                logger.info('用户是数据开发者和运营工程师')
            else:
                logger.info(f'该用户有权限的id = {auth_id}')
            # 把所有的资源并且由权限的, 名称和描述, 都放入pro_data, 后续加入大模型提示词中
            for num, hit in enumerate(self.all_hits):
                # 1数据目录2接口服务3逻辑视图
                # hit['_source']是节点所有属性的字典
                if 'datacatalogname' in hit['_source'].keys():
                    description = hit['_source']['description_name'] if 'description_name' in hit[
                        '_source'].keys() else '暂无描述'
                    # hit['_source']['resource_id']是数据资源目录挂接的数据资源uuid
                    if (hit['_source'][
                        'resource_id'] in auth_id or self.search_configs.sailor_search_if_auth_in_find_data_qa == '0'
                            or "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles):
                        # hit['_source']['resource_type']是挂接的数据资源类型1逻辑视图2接口
                        if hit['_source']['online_status'] in ['online', 'down-auditing', 'down-reject'] and hit['_source'][
                            'resource_type'] == '1':
                            hit['_selfid'] = str(num)
                            self.pro_data_catalog.append(
                                {hit['_selfid'] + '|' + hit['_source']['datacatalogname']: description})
            logger.info(f'放入大模型的数据目录 = {self.pro_data_catalog}')

            # task_qw_gpt = asyncio.create_task(
            #     self._qw_gpt(pro_data=self.pro_data_catalog,
            #                 prompt_name="all_table",
            #                 table_name='table_name',
            #                 resource_type='data_catalog'))
            # res_catalog, res_catalog_reason, res_load = await task_qw_gpt
            rst_container = await self._qw_gpt(
                pro_data=self.pro_data_catalog,
                prompt_name="all_table",
                table_name='table_name',
                resource_type='data_catalog'
            )

            rst_container = self.catalog_results

            logger.info(f"大模型返回结果 = {rst_container['res']}")
            res = rst_container['res']
            # hits_graph = []
            for i in self.all_hits:
                if '_selfid' in i.keys() and i['_selfid'] in [j.split('|')[0] for j in res]:
                    self.catalog_results['hits_graph'].append(i)
            entities = []

            # 组织答案文本
            res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
            hits_all = [i["_selfid"] + '|' + i["_source"]["datacatalogname"] for i in rst_container['hits_graph']]
            if len(rst_container['hits_graph']) > 0:
                if len(rst_container['hits_graph']) == len(res):
                    explanation_formview, explanation_statu = add_label(rst_container['reason'], rst_container['hits_graph'], 0)
                    if explanation_statu == '0':
                        use_hits = [i["_id"] + '|' + i["_source"]["datacatalogname"] for i in rst_container['hits_graph']]
                        explanation_formview = add_label_easy(res_explain, use_hits)
                        logger.info(f"话术不可用时，拼接话术 {explanation_formview}, {explanation_statu}")
                    res_statu = 1
                else:
                    explanation_formview, res_statu, explanation_statu = ' ', '1', '0'
            else:
                explanation_formview, res_statu, explanation_statu = ' ', '1', '0'

            for num, hit in enumerate(rst_container['hits_graph']):
                catalog_entity_copy = copy.deepcopy(prompts_config.catalog_entity)
                catalog_entity_copy["id"] = hit["_id"]
                catalog_entity_copy["default_property"]["value"] = hit["_source"]["datacatalogname"]
                for props in catalog_entity_copy["properties"][0]["props"]:
                    if props["name"] in hit["_source"].keys():
                        props['value'] = hit["_source"][props["name"]]
                if search_params.if_display_graph:
                    # 查该数据资源目录在搜索图谱中连接的子图
                    connected_subgraph = await get_connected_subgraph_catalog(ad_appid=self.search_params.ad_appid,
                                                                              kg_id=self.search_params.kg_id,
                                                                              datacatalog_graph_vid=hit["_id"])

                    # logger.debug(f"connected_subgraph={connected_subgraph}")
                    entities.append({
                        "starts": [],
                        "entity": catalog_entity_copy,
                        "score": search_params.limit - num,
                        "connected_subgraph": connected_subgraph,
                    })
                else:
                    entities.append({
                        "starts": [],
                        "entity": catalog_entity_copy,
                        "score": search_params.limit - num,
                    })

            self.output['explanation_formview'] = explanation_formview
            self.output['entities'] = entities
            self.output['count'] = len(rst_container['hits_graph'])
            self.output['answer'], self.output['subgraphs'], self.output['query_cuts'] = ' ', [], []
            total_end_time = time.time()
            total_time_cost = total_end_time - total_start_time
            logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
            logger.info(f"输出的总结语句------------------\n{self.output['explanation_formview']}")
            logger.info('--------------问答部分最终召回的资源-----------------\n')
            # logger.debug(json.dumps(output, indent=4, ensure_ascii=False), res_statu, explanation_statu)
            log_content = "\n".join(
                f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
                for entity in self.output["entities"]
            )
            logger.info(log_content)
            # for entity in output["entities"]:
            #     logger.debug(entity['entity']["id"], entity['entity']["default_property"]["value"])
            return self.output, res_statu, explanation_statu
        except Exception as e:
            logger.error(f"{str(e)}")
            return ANALYSIS_SEARCH_EMPTY_RESULT

    async def catalog_analysis_main_dip(self, request):
        '''数据目录版分析问答型搜索算法主函数'''
        # init_qa_dip(request, search_params)完成
        # (1) 获取图谱信息和 query 向量化;
        # (2) 向量搜索
        # all_hits 是搜索命中的相似向量对应的实体id
        # drop_indices 是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
        logger.info(f'catalog_analysis_main_dip(): search_params={self.search_params}')

        output, total_start_time, all_hits = await self.init_qa_dip()

        logger.info(f"OpenSearch召回数量：{len(all_hits)}")
        logger.info(f"OpenSearch召回结果 all_hits ：{all_hits}")
        pro_data = []
        # auth_header = {"Authorization": search_params.auth_header}
        # 当前用的 鉴权函数, 查询出该用户(subject_id)有权限的所有资源id
        # 如果是数据运营和数据开发工程师, 可以针对所有资源进行问答
        # 在ADP接口中， 返回的是ADP数据视图的‘统一视图id’：mdl_id, iDRM的form_view表中，会产生自己id（是uuid），
        # 新增了一个字段保存mdl_id和，目录版搜索图谱中数据资源目录节点有该mdl_id，命名为 resource_mdl_id
        token=self.headers.get('Authorization')
        auth_mdl_id = await find_number_api.user_all_auth_dip_external(
            token=token,
            subject_id=self.search_params.subject_id
        )
        logger.info(f'auth_mdl_id={auth_mdl_id}')
        # 要把 auth_mdl_id 转换为 auth_id，其中是iDRM中form_view的id
        # 提取所有有效的 resource_mdl_id 和对应的 resource_id
        valid_mdl_ids = {
            hit['_source']['resource_mdl_id']: hit['_source']['resource_id']
            for hit in all_hits
            if hit.get('class_id') == 'datacatalog' and 'resource_mdl_id' in hit.get('_source', {})
        }
        logger.info(f'valid_mdl_ids={valid_mdl_ids}')

        # 使用集合操作快速匹配
        auth_id = [valid_mdl_ids[mdl_id] for mdl_id in auth_mdl_id if mdl_id in valid_mdl_ids]
        logger.info(f'auth_id={auth_id}')
        if "data-operation-engineer" in self.search_params.roles or "data-development-engineer" in self.search_params.roles:
            logger.info('用户是数据开发者和运营工程师')
        else:
            logger.info(f'该用户有权限的id = {auth_id}')
        # 把所有的资源并且由权限的, 名称和描述, 都放入pro_data, 后续加入大模型提示词中
        for num, hit in enumerate(all_hits):
            # 1数据目录2接口服务3逻辑视图
            # hit['_source']是节点所有属性的字典
            logger.info(f'hit={hit}')
            if 'datacatalogname' in hit['_source']:
                description = hit['_source']['description_name'] if 'description_name' in hit['_source'] else '暂无描述'
                # hit['_source']['resource_id']是数据资源目录挂接的数据资源uuid
                logger.info(f"hit.get('_source').get('resource_id')'={hit.get('_source').get('resource_id')}")
                if (hit.get('_source').get(
                        'resource_id') in auth_id or self.search_configs.sailor_search_if_auth_in_find_data_qa == '0'
                        or "data-operation-engineer" in self.search_params.roles or "data-development-engineer" in self.search_params.roles):
                    # hit['_source']['resource_type']是挂接的数据资源类型1逻辑视图2接口
                    logger.info(f"hit.get('_source').get('online_status') in ['online', 'down-auditing','down-reject']={hit.get('_source').get('online_status') in ['online', 'down-auditing','down-reject']}")
                    resource_type_tmp=hit.get('_source').get('resource_type')
                    logger.info(f"resource_type_tmp={resource_type_tmp} ,type of resource_type_tmp={type(resource_type_tmp)}")
                    logger.info(f"hit.get('_source').get('resource_type')={hit.get('_source').get('resource_type')}")
                    logger.info(f"hit.get('_source').get('resource_type') == '1'={hit.get('_source').get('resource_type') == '1'}")
                    logger.info(f"description={description}")
                    # resource_type原来是str类型， 对接ADP后变成了int类型
                    if hit.get('_source').get('online_status') in ['online', 'down-auditing',
                                                                   'down-reject'] and hit.get('_source').get(
                            # 'resource_type') == '1':
                            'resource_type') == 1:
                        hit['_selfid'] = str(num)
                        pro_data.append(
                            {hit['_selfid'] + '|' + hit['_source']['datacatalogname']: description})
                        logger.info(f"pro_data={pro_data}")
        logger.info(f'放入大模型的库表 = {pro_data}')

        task_qw_gpt = asyncio.create_task(
            qw_gpt_dip(
                headers=self.headers,
                data=pro_data,
                query=self.search_params.query,
                search_configs=self.search_configs,
                prompt_name="all_table",
                table_name='table_name'
            )
        )
        res_catalog, res_catalog_reason, res_load = await task_qw_gpt

        logger.info(f'大模型返回结果 = {res_catalog}')
        res = res_catalog
        hits_graph = []
        for i in all_hits:
            if '_selfid' in i and i['_selfid'] in [j.split('|')[0] for j in res]:
                hits_graph.append(i)
        entities = []

        # 组织答案文本
        res_explain = '以下是一个可能的分析思路建议，可根据以下资源获取答案:'
        hits_all = [i["_selfid"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
        if len(hits_graph) > 0:
            if len(hits_graph) == len(res_catalog):
                explanation_formview, explanation_statu = add_label(
                    reason=res_catalog_reason,
                    cites=hits_all,
                    a=0
                )
                if explanation_statu == '0':
                    use_hits = [i["_id"] + '|' + i["_source"]["datacatalogname"] for i in hits_graph]
                    explanation_formview = add_label_easy(
                        reason=res_explain,
                        cites=use_hits
                    )
                    logger.info(f"话术不可用时，拼接话术 {explanation_formview}, {explanation_statu}")
                res_statu = 1
            else:
                explanation_formview, res_statu, explanation_statu = ' ', '1', '0'
        else:
            explanation_formview, res_statu, explanation_statu = ' ', '1', '0'

        for num, hit in enumerate(hits_graph):
            catalog_entity_copy = copy.deepcopy(prompts_config.catalog_entity)
            # 对接ADP后， hit中没有 "_id" 字段
            # catalog_entity_copy["id"] = hit["_id"]
            catalog_entity_copy["default_property"]["value"] = hit["_source"]["datacatalogname"]
            for props in catalog_entity_copy["properties"][0]["props"]:
                if props["name"] in hit["_source"]:
                    props['value'] = hit["_source"][props["name"]]
            # 对接ADP后没有nebula图数据库，暂时不支持子图查询
            self.search_params.if_display_graph = False
            if self.search_params.if_display_graph:
                # 查该数据资源目录在搜索图谱中连接的子图
                connected_subgraph = await get_connected_subgraph_catalog_dip(
                    x_account_id=self.search_params.subject_id,
                    x_account_type=self.search_params.subject_type,
                    kg_id=self.search_params.kg_id,
                    datacatalog_graph_vid=hit["_id"]
                )

                # logger.debug(f"connected_subgraph={connected_subgraph}")
                entities.append({
                    "starts": [],
                    "entity": catalog_entity_copy,
                    "score": self.search_params.limit - num,
                    "connected_subgraph": connected_subgraph,
                })
            else:
                entities.append({
                    "starts": [],
                    "entity": catalog_entity_copy,
                    "score": self.search_params.limit - num,
                })

        output['explanation_formview'] = explanation_formview
        output['entities'] = entities
        output['count'] = len(hits_graph)
        output['answer'], output['subgraphs'], output['query_cuts'] = ' ', [], []
        total_end_time = time.time()
        total_time_cost = total_end_time - total_start_time
        logger.info(f"认知搜索服务 总耗时 {total_time_cost} 秒")
        logger.info(f"输出的总结语句------------------\n{output['explanation_formview']}")
        logger.info('--------------问答部分最终召回的资源-----------------\n')
        # logger.debug(json.dumps(output, indent=4, ensure_ascii=False), res_statu, explanation_statu)
        log_content = "\n".join(
            f"{entity['entity']['id']}  {entity['entity']['default_property']['value']}"
            for entity in output["entities"]
        )
        logger.info(log_content)
        # for entity in output["entities"]:
        #     logger.debug(entity['entity']["id"], entity['entity']["default_property"]["value"])
        return output, res_statu, explanation_statu

    # 获取认知搜索图谱信息和向量化
    # 向量搜索
    # 还未使用
    async def init_qa(self,request, inputs):
        headers = {"Authorization": request.headers.get('Authorization')}
        output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
        if not inputs.query:
            return output

        total_start_time = time.time()
        # ad的appid，图谱id，用户query，返回结果的数量
        logger.info(
            f'INPUT：appid: {inputs.ad_appid}\nkg_id: {inputs.kg_id}\nquery: {inputs.query}\nlimit: {inputs.limit}\n')
        # entity2service，图谱关系边的权重
        logger.info(
            f'INPUT：entity2service: {inputs.entity2service}\n')

        # 获取图谱信息和向量化
        task_get_kgotl_qa = asyncio.create_task(get_kgotl_qa(inputs))
        task_query_m3e = asyncio.create_task(query_m3e(inputs.query))
        # entity_types 字典{实体类型名：实体本体信息}
        # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        # type2names 字典 是前端传来的停用实体,现在已经废弃
        # data_params['type2names']
        # data_params['space_name']
        # data_params['indextag2tag']
        entity_types, vector_index_filed, data_params = await task_get_kgotl_qa

        embeddings, m_status = await task_query_m3e
        # 分析问答型搜索只做向量搜索
        # 向量搜索
        min_score = 0.5
        task_vector_search = asyncio.create_task(
            vector_search(embeddings, m_status, vector_index_filed, entity_types, data_params, min_score, inputs))
        #
        # all_hits 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素
        # drop_indices是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
        all_hits, drop_indices = await task_vector_search
        for hit in all_hits:
            if hit['_id'] in set(drop_indices):
                all_hits.remove(hit)
        return output, headers, total_start_time, all_hits, drop_indices

    async def init_qa_dip(self):
        logger.info(f"init_qa_dip() running : {self.search_params}")
        # headers = {"Authorization": self.request.headers.get('Authorization')}
        output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
        if not self.search_params.query:
            return output

        total_start_time = time.time()
        # ad的appid，图谱id，用户query，返回结果的数量
        logger.info(
            f'INPUT：kg_id: {self.search_params.kg_id}\nquery: {self.search_params.query}\nlimit: {self.search_params.limit}\n')
        # entity2service，图谱关系边的权重
        logger.info(
            f'INPUT：entity2service: {self.search_params.entity2service}\n')
        # 获取图谱信息
        try:
            entity_types, vector_index_filed, data_params = await get_kgotl_qa_dip_new(
                headers=self.headers,
                search_params=self.search_params
            )
        #     # entity_types 字典{实体类型名：实体本体信息}
        #     # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        #     # type2names 字典 是前端传来的停用实体,现在已经废弃
        #     # data_params['type2names']
        #     # data_params['space_name']
        #     # data_params['indextag2tag']
        except DataCataLogError as e:
            logger.error(f"获取图谱信息或query向量化失败: {e}")
            raise

        # 目录版分析问答型搜索当前版本只做向量搜索
        min_score = safe_str_to_float(self.search_configs.sailor_vec_min_score_analysis_search)

        # drop_indices是按照停用实体信息应该被过滤掉的实体,现在已经废弃
        all_hits = await vector_search_dip_new(
            headers=self.headers,
            vector_index_filed=vector_index_filed,
            entity_types=entity_types,
            data_params=data_params,
            min_score=min_score,
            search_params=self.search_params
        )
        # drop_indices_set = set(drop_indices)
        # all_hits = [hit for hit in all_hits if hit['_id'] not in drop_indices_set]

        return output, total_start_time, all_hits


    # 获取认知搜索图谱信息, 因为部门职责知识增强场景下, 将query向量化提出来,所以要建一个与 init_qa 大部分相同, 但是没有query向量化的函数
    # 向量搜索
    # 还未使用
    async def graph_vector_retriever_search_qa(self,request: Request, search_params: AnalysisSearchParams,
                                               query_embedding: List[str], m_status: int):
        headers = {"Authorization": request.headers.get('Authorization')}
        output = {"count": 0, "entities": [], "answer": "抱歉未查询到相关信息。", "subgraphs": []}
        total_start_time = None
        all_hits, drop_indices = [], []
        # return output, headers, total_start_time, all_hits, drop_indices
        if not search_params.query:
            return output, headers, total_start_time, all_hits, drop_indices

        total_start_time = time.time()
        # ad的appid，图谱id，用户query，返回结果的数量
        logger.info(f'''认知搜索图谱 向量搜索 search_params =
    appid: {search_params.ad_appid}\nkg_id: {search_params.kg_id}
    query: {search_params.query}\nlimit: {search_params.limit}\n''')
        # entity2service，图谱关系边的权重
        logger.info(
            f'认知搜索图谱 向量搜索 INPUT：entity2service: {search_params.entity2service}\n')

        # 获取图谱信息和向量化
        task_get_kgotl_qa = asyncio.create_task(get_kgotl_qa(search_params))
        # entity_types 字典{实体类型名：实体本体信息}
        # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        # type2names 字典 是前端传来的停用实体,现在已经废弃
        # data_params['type2names']
        # data_params['space_name']
        # data_params['indextag2tag']
        entity_types, vector_index_filed, data_params = await task_get_kgotl_qa
        # logger.debug(f'entity_types = \n{entity_types}')
        # logger.debug(f'vector_index_filed = \n{vector_index_filed}')
        # logger.debug(f'data_params = \n{data_params}')

        # 分析问答型搜索只做向量搜索
        # 向量搜索
        # min_score = settings.VEC_MIN_SCORE_ANALYSIS_SEARCH
        # vec_knn_k = settings.VEC_KNN_K_ANALYSIS_SEARCH
        # logger.debug(self.search_configs.sailor_vec_min_score_analysis_search)
        # logger.debug(self.search_configs.sailor_vec_knn_k_analysis_search)
        min_score = safe_str_to_float(self.search_configs.sailor_vec_min_score_analysis_search)
        # logger.debug(f'min_score = {min_score}')
        if min_score is None:
            logger.error(f'获取向量检索 分数下限 参数失败!')
        vec_knn_k = safe_str_to_int(self.search_configs.sailor_vec_knn_k_analysis_search)
        # logger.debug(f'vec_knn_k = {vec_knn_k}')
        if vec_knn_k is None:
            logger.error(f'获取向量检索 knn-k 参数失败!')
        # logger.debug(f'self.search_configs.sailor_vec_min_score_analysis_search = {self.search_configs.sailor_vec_min_score_analysis_search}')
        # logger.debug(f'self.search_configs.sailor_vec_knn_k_analysis_search = {self.search_configs.sailor_vec_knn_k_analysis_search}')
        task_vector_search = asyncio.create_task(
            vector_search(
                embeddings=query_embedding,
                m_status=m_status,
                vector_index_filed=vector_index_filed,
                entity_types=entity_types,
                data_params=data_params,
                search_params=search_params,
                min_score=min_score,
                vec_knn_k=vec_knn_k
            )
        )

        all_hits, drop_indices = await task_vector_search
        # logger.debug(f'all_hits = {all_hits}')
        # logger.debug(f'drop_indices = {drop_indices}')
        # drop_indices_vec是按照前端传参查询出的停用实体信息,应该被过滤掉的向量,现在已经废弃
        # all_hits是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,示例数据如下

        # 删除停用实体(按照前端传参, 现在已经废弃)
        for hit in all_hits:
            if hit['_id'] in set(drop_indices):
                all_hits.remove(hit)
        # output原本是给搜索列表用的， 应为这里是转为分析问答型搜索写的函数， output没有用到
        # 分析问答型搜索 后续流程用 all_hits
        return output, headers, total_start_time, all_hits, drop_indices


    # 获取部门职责知识增强图谱信息(kecc:knowledge enhancement of catalog chain)()
    # 向量搜索
    async def graph_vector_retriever_kecc(self,ad_appid, kg_id_kecc, query, query_embedding, m_status=0,
                                          vec_size_kecc=10, vec_min_score_kecc=0.5, vec_knn_k_kecc=10):
        # headers = {"Authorization": request.headers.get('Authorization')}
        total_start_time = time.time()
        # # ad的appid，图谱id，用户query，返回结果的数量
        logger.info(
            f'''部门职责知识增强图谱 向量搜索 INPUT：\nappid: {ad_appid}\tkg_id_kecc: {kg_id_kecc}\tquery: {query}\tm_status: {m_status}
    vec_size_kecc={vec_size_kecc}\tvec_min_score_kecc:{vec_min_score_kecc}\tvec_knn_k_kecc: {vec_knn_k_kecc}''')

        # 获取部门职责知识增强图谱信息
        task_get_kgotl_kecc = asyncio.create_task(
            get_kgotl_kecc(
                ad_appid=ad_appid,
                kg_id_kecc=kg_id_kecc
            )
        )
        # entity_types 字典{实体类型名：实体本体信息}
        # vector_index_filed 字典 {实体类型名:建立向量索引的字段名称列表,比如{"resource":["description", "name"]}记录向量和索引名,用于向量搜索
        # type2names 字典 是前端传来的停用实体,现在已经废弃
        # data_params['type2names']
        # data_params['space_name']
        # data_params['indextag2tag']
        # logger.debug(f"task_get_kgotl_kecc={task_get_kgotl_kecc}")
        entity_types, vector_index_filed, data_params = await task_get_kgotl_kecc
        # query_m3e返回一个tuple，有两个元素，第一个元素，就是embedding，是一个768个数字组成的列表；第二个元素，是一个数字，代表m3e服务执行状态，0代表成功
        # embeddings, m_status = await task2
        # 分析问答型搜索只做向量搜索
        # 向量搜索
        logger.debug(f"entity_types_kecc={entity_types}")
        logger.debug(f"vector_index_filed_kecc={vector_index_filed}")
        logger.debug(f"data_params_kecc={data_params}")

        task_vector_search_kecc = asyncio.create_task(
            vector_search_kecc(
                ad_appid=ad_appid,
                kg_id_kecc=kg_id_kecc,
                query_embedding=query_embedding,
                m_status=m_status,
                vector_index_filed=vector_index_filed,
                entity_types=entity_types,
                data_params=data_params,
                vec_size_kecc=vec_size_kecc,
                vec_min_score_kecc=vec_min_score_kecc,
                vec_knn_k_kecc=vec_knn_k_kecc
            )
        )
        # all_hits 是搜索命中的相似向量对应的实体id
        # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
        all_hits_entity = await task_vector_search_kecc
        # all_hits, drop_indices = await task4
        # for i in all_hits:
        #     if i['_id'] in set(drop_indices):
        #         all_hits.remove(i)
        # return output, headers, total_start_time, all_hits, drop_indices
        # logger.debug("len(all_hits_entity)=", len(all_hits_entity))
        # all_hits_entity 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素
        all_hits_kecc = []
        for item in all_hits_entity:
            new_item = {
                "信息相关性得分": item["_score"],
                "问题相关信息": {
                    "单位": item["_source"]["dept_name_bdsp"],
                    "信息系统": item["_source"]["info_system_bdsp"],
                    "单位职责": item["_source"]["dept_duty"],
                    "单位职责-明细": item["_source"]["sub_dept_duty"],
                    "业务事项": item["_source"]["duty_items"],
                    "业务事项类型": item["_source"]["duty_items_type"],
                    "数据资源": item["_source"]["data_resource"],
                    "核心数据项": item["_source"]["core_data_fields"]
                }
            }
            all_hits_kecc.append(new_item)
        total_end_time = time.time()
        total_elapsed_time = total_end_time - total_start_time
        # logger.debug("all_hits_cn=\n", json.dumps(all_hits_cn, indent=4, ensure_ascii=False))
        # logger.debug("len(all_hits_kecc) ", len(all_hits_kecc))
        return total_elapsed_time, all_hits_kecc

"""分析问答型——数据目录版"""

if __name__ == '__main__':
    prompt_name="all_table_kecc"
    prompt_template = prompt_map.get(prompt_name)
    print(f'prompt_template=\n{prompt_template}')
