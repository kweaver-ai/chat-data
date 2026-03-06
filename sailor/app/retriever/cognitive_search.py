# -*- coding: utf-8 -*-
# @Time    : 2026/1/7 11:17
# @Author  : Glen.lv
# @File    : cognitive_search
# @Project : af-sailor

import json
import traceback
from textwrap import dedent

import urllib3

from app.cores.cognitive_assistant.qa_config import search_limit  # 问答的 引用资源 原限最多4个， 已更改
from app.cores.cognitive_assistant.qa_model import CognitiveSearchResponseModel, AfEdition, QAParamsModelDIP
from app.cores.cognitive_search.analysis_searcher import AnalysisSearcher
from app.cores.cognitive_search.asset_searcher import AssetSearcher


from app.cores.cognitive_search.re_asset_search import run_func_catalog_for_qa, run_func_resource_for_qa
from app.cores.cognitive_search.search_config.get_params import SearchConfigs
from app.cores.cognitive_search.search_model import (ANALYSIS_SEARCH_EMPTY_RESULT, AnalysisSearchParamsDIP,
                                                     AssetSearchParamsDIP,AnalysisSearchResponseModel,
                                                     DEFAULT_FILTER,DEAFULT_REQUIRED_RESOURCE,ALL_ROLES )

from app.logs.logger import logger
from app.retriever.base import DataResourceAttribute, Append
from config import settings

urllib3.disable_warnings()


# 修改变量名称， 反映准确含义
# save_tab 改成 save_catalog
# save_tab_cn 改成 save_catalog_cn
# save_tab_text2sql 改成 save_catalog_text2sql
# 方法 save_tab_append() 改成 save_catalog_append()
# save_index 改成 save_indicator
# 方法 save_index_append() 改成 save_indicator_append()
class CognitiveSearch(Append):

    def __init__(self, request, params: QAParamsModelDIP, headers, search_configs: SearchConfigs):
        super().__init__()
        self.request = request
        self.qa_params: QAParamsModelDIP = params
        # 临时
        self.qa_params.af_editions = AfEdition.CATALOG
        self.headers = headers

        self.save_catalog = []  # 存储所有的数据目录
        self.save_catalog_cn = []  # 存储所有的数据目录，信息中过滤掉英文
        self.save_catalog_text2sql = []  # 为Text2SQL提供的数据目录

        self.save_svc = []  # 存储所有的接口服务
        self.save_svc_cn = []  # 存储所有的接口服务，信息中过滤掉英文
        self.save_svc_dict = {}  # 以字典的形式存储所有的接口服务，后续利用

        self.save_cites = []  # 保存所有数据目录和数据资源（逻辑视图、接口服务、指标），返回给agent和前端，作为问答“参考资源”
        self.save_cites_dict = {}  # 以字典的形式保存所有数据目录和数据资源（逻辑视图、接口服务、指标）

        self.save_view = []  # 保存所有逻辑视图
        self.save_view_cn = []  # 保存所有逻辑视图，信息中过滤掉英文？
        self.save_view_text2sql = []  # 为Text2SQL提供的逻辑视图

        self.save_indicator = []  # 保存所有指标

        self.search_configs = search_configs

        # 相比 以上的 QAParamsModel， 减少了 "stream" ,"direct_qa","resources" 这三个参数
        self.search_params = AnalysisSearchParamsDIP(**self.qa_params.model_dump())
        self.asset_search_params = AssetSearchParamsDIP(**self.qa_params.model_dump())
        self.search_params.kg_id = search_configs.kn_id_catalog
        self.search_params.filter = DEFAULT_FILTER
        self.search_params.required_resource = DEAFULT_REQUIRED_RESOURCE
        self.search_params.roles = ALL_ROLES
        self.search_params.stopwords=[]
        self.search_params.stop_entities = []


        self.asset_search_params.kg_id = search_configs.kn_id_catalog
        self.asset_search_params.filter = DEFAULT_FILTER
        self.asset_search_params.required_resource = DEAFULT_REQUIRED_RESOURCE
        self.asset_search_params.roles = ALL_ROLES
        self.asset_search_params.stopwords = []
        self.asset_search_params.stop_entities = []

        self.analysis_searcher = AnalysisSearcher(
            request=self.request,
            search_params=self.search_params,
            search_configs=self.search_configs
        )
        self.asset_searcher = AssetSearcher(
            request=self.request,
            search_params=self.asset_search_params,
            search_configs=self.search_configs
        )

    def _should_auth_check(self) -> bool:
        """检查是否需要进行权限验证"""
        return self.search_configs.sailor_search_if_auth_in_find_data_qa == '1'

    def _if_history_qa_enhance(self) -> bool:
        """检查是否启用历史问答增强功能"""
        return self.search_configs.sailor_search_if_history_qa_enhance == '1'

    def _if_kecc(self) -> bool:
        """检查是否启用部门职责知识增强（KECC）功能"""
        return self.search_configs.sailor_search_if_kecc == '1'

    async def _add_data(self, assets):
        logger.info(f'_add_data() running!')
        logger.info(f'asset_type = {assets["asset_type"]}')
        # 新业务知识网络 asset_type 是 int 型
        # if assets["asset_type"] == "1":  # 数据目录
        if assets["asset_type"] == 1:  # 数据目录
            self.save_catalog, self.save_catalog_cn, self.save_catalog_text2sql = \
                await self.save_catalog_append(
                    save_catalog=self.save_catalog,
                    save_catalog_cn=self.save_catalog_cn,
                    save_catalog_text2sql=self.save_catalog_text2sql,
                    assets=assets,
                    headers=self.headers
                )
            self.save_cites, self.save_cites_dict = \
                await self.save_cites_append(
                    save_cites=self.save_cites,
                    save_cites_dict=self.save_cites_dict,
                    assets=assets
                )
        elif assets["asset_type"] == "2":  # 接口服务
            self.save_svc, self.save_svc_cn, self.save_svc_dict = \
                await self.save_svc_append(
                    save_svc=self.save_svc,
                    save_svc_cn=self.save_svc_cn,
                    save_svc_dict=self.save_svc_dict,
                    assets=assets,
                    headers=self.headers
                )
            assets = DataResourceAttribute(**assets)
            self.save_cites, self.save_cites_dict = \
                await self.save_resource_cites_append(
                    save_cites=self.save_cites,
                    save_cites_dict=self.save_cites_dict,
                    assets=assets,
                    headers=self.headers
                )
        elif assets["asset_type"] == "3":  # 逻辑视图
            # logger.info(f'in _add_data, input assets = {assets}')
            assets = DataResourceAttribute(**assets)
            self.save_view, self.save_view_cn, self.save_view_text2sql = \
                await self.save_view_append(
                    save_view=self.save_view,
                    save_view_cn=self.save_view_cn,
                    save_view_text2sql=self.save_view_text2sql,
                    assets=assets,
                    headers=self.headers
                )
            self.save_cites, self.save_cites_dict = \
                await self.save_resource_cites_append(
                    save_cites=self.save_cites,
                    save_cites_dict=self.save_cites_dict,
                    assets=assets,
                    headers=self.headers
                )
        elif assets["asset_type"] == "4":  # 计算指标
            assets = DataResourceAttribute(**assets)
            self.save_indicator = await  self.save_indicator_append(
                save_indicator=self.save_indicator,
                assets=assets,
                headers=self.headers
            )
            await self.save_resource_cites_append(
                save_cites=self.save_cites,
                save_cites_dict=self.save_cites_dict,
                assets=assets,
                headers=self.headers
            )

    async def _post_analysis_search(self, response):
    # async def sub_analysis_search(self, response):
        logger.info(f'response={response}')
        logger.info("分析问答型搜索：查询相关接口， 丰富搜索结果的 metadata 信息")
        logger.info(f'qa_params.if_display_graph={self.qa_params.if_display_graph}')
        if self.qa_params.if_display_graph:

            for idx, entity in enumerate(response[0]["entities"]):
                props = entity["entity"]["properties"][0]["props"]
                # logger.info(f'in sub_analysis_search, props = {props}')
                assets = {
                    prop["name"]: prop["value"]
                    for prop in props
                }
                logger.info(f'assets = {assets}')
                # 增加输出”关联子图“
                if "connected_subgraph" in entity:
                    assets["connected_subgraph"] = entity["connected_subgraph"]
                else:
                    assets["connected_subgraph"] = []
                logger.info(f'assets["connected_subgraph"]={assets["connected_subgraph"]}')
                # logger.debug(json.dumps(assets, indent=4, ensure_ascii=False))
                await self._add_data(
                    assets=assets
                )
        else:
            for idx, entity in enumerate(response[0]["entities"]):
                props = entity["entity"]["properties"][0]["props"]
                # logger.info(f'in sub_analysis_search, props = {props}')
                assets = {
                    prop["name"]: prop["value"]
                    for prop in props
                }
                # logger.debug(json.dumps(assets, indent=4, ensure_ascii=False))
                await self._add_data(
                    assets=assets
                )

    async def _analysis_search(self):
        """分析问答型"""

        logger.info(dedent(
            f"""
            analysis search: search_configs = 
            服务超市 direct_qa = {self.search_configs.direct_qa}
            找数问答是否控制普通用户的表权限 sailor_search_if_auth_in_find_data_qa = {self.search_configs.sailor_search_if_auth_in_find_data_qa}
            是否进行基于历史问答对的知识增强 sailor_search_if_history_qa_enhance = {self.search_configs.sailor_search_if_history_qa_enhance}
            是否进行基于'组织结构-部门职责-信息系统'的知识增强 sailor_search_if_kecc = {self.search_configs.sailor_search_if_kecc}
            """).strip())
        # 数据资源版
        related_info = []
        if self.qa_params.af_editions == AfEdition.RESOURCE:
            # 如果有部门职责知识增强, resource_analysis_search_kecc 函数内部通过参数控制是否需要对普通用户进行问答资源的权限管控
            # 在向量搜索的基础上增加了关键词搜索和关联搜索
            # 因为基于历史问答对的知识增强效果不理想，暂不支持
            logger.info("resource_analysis_search_kecc_for_qa() running...")
            response = await self.analysis_searcher.resource_analysis_search_kecc_for_qa()
            logger.info(f"resource_analysis_search_kecc_for_qa() response = {response}")

            logger.info(
                f'"related_info":response[3] if len(response) > 3 else []={response[3] if len(response) > 3 else []}')
            # response[0] 是搜索结果 output， response[1] 是 status_res，
            # response[2] 是 status_explanation， response[3] 如果存在，则是 related_info
            filtered_data = {
                "count": response[0].get("count"),
                "answer": response[0].get("answer"),
                "subgraphs": response[0].get("subgraphs"),
                "explanation_ind": response[0].get("explanation_ind"),
                "explanation_formview": response[0].get("explanation_formview"),
                "explanation_service": response[0].get("explanation_service"),
                "query_cuts":response[0].get("query_cuts"),
                "status_res":response[1],
                "status_explanation":response[2],
                "related_info":response[3] if len(response) > 3 else []
            }

            # logger.info("分析问答型搜索算法结果\n{}".format(json.dumps(response[0], indent=4, ensure_ascii=False)))
            logger.info("分析问答型搜索算法初步整理后的结果，entities加入之前：\n{}".format(json.dumps(filtered_data, indent=4, ensure_ascii=False)))
            status_res = response[1]
            # status_explanation是三位由0\1组成的字符串, 分别代表指标\逻辑视图\接口服务的解释话术是否可用, 1代表可用
            status_explanation = response[2]
            related_info = response[3] if len(response) > 3 else []
            # 111: 指标；视图；接口
            explanation = []  # 存储分析问答型搜索的话术

            if status_explanation[0] == "1":
                explanation.append({"index": response[0].get("explanation_ind")})
            if status_explanation[1] == "1":
                explanation.append({"view": response[0].get("explanation_formview")})
            if status_explanation[2] == "1":
                explanation.append({"api": response[0].get("explanation_service").get("explanation_text")})

            select_interface = response[0].get("explanation_service").get("explanation_params")
            if select_interface == "":
                select_interface = []
            logger.info("分析问答型搜索返回的解释话术：\n{}".format(json.dumps(explanation, ensure_ascii=False, indent=4)))
            # logger.info(f'_analysis_search() ,response[0]={response[0]}')
            # 查询相关接口， 丰富搜索结果的 metadata 信息
            if status_res != "000":  # 000代表指标，接口和视图的搜索结果都不可用
                await self._post_analysis_search(
                    response=response
                )
                # await self.sub_analysis_search(response)
        # 数据目录版
        elif self.qa_params.af_editions == AfEdition.CATALOG:
            logger.info(f"数据目录版: catalog_analysis_main_dip() running！")
            response = await self.analysis_searcher.catalog_analysis_main_dip(
                request=self.request
            )
            status_res = response[1]
            status_explanation = response[2]

            explanation = []  # 存储分析问答型搜索的话术
            if status_explanation:
                explanation.append({"catalog": response[0].get("explanation_formview")})
            select_interface = []
            logger.info("分析问答型的解释话术：\n{}".format(json.dumps(explanation, ensure_ascii=False, indent=4)))
            # 查询相关接口， 丰富搜索结果的 metadata 信息
            if status_res != "00":  # 00代表接口和视图都不可用
                await self._post_analysis_search(
                    response=response
                )
        else:
            raise Exception("Unsupported AF version")
        return status_res, explanation, select_interface, related_info

    async def _fallback_to_asset_search(self):
        await self._calculate_search()

    async def _calculate_search(self):
        """向量计算，相似度计算型, 实际上就是认知搜索列表的算法函数"""
        logger.info("使用搜索列表的认知搜索算法")
        # 限制为4个结果
        self.qa_params.limit = search_limit

        if self.qa_params.af_editions == AfEdition.RESOURCE:
            response = await run_func_resource_for_qa(
                request=self.request,
                search_params=self.search_params,
                search_configs=self.search_configs
            )

        elif self.qa_params.af_editions == AfEdition.CATALOG:
            # response = await run_func_catalog_for_qa(
            #     request=self.request,
            #     search_params=self.qa_params,
            #     search_configs=self.search_configs
            # )
            # response = await self.asset_searcher.run_func_catalog_for_qa_dip()
            response = await self.asset_searcher.asset_search_for_qa_dip_catalog()

        else:
            raise Exception("Unsupported AF version")

        num = 0
        for idx, entity in enumerate(response["entities"]):
            score = entity["entity"]["score"]
            props = entity["entity"]["properties"][0]["props"]

            try:
                if score >= settings.CS_FILTER_VALUE or idx == 0:
                    assets = {
                        prop["name"]: prop["value"]
                        for prop in props
                    }
                    # logger.debug(json.dumps(assets, indent=4, ensure_ascii=False))
                    ###
                    if self.qa_params.af_editions == AfEdition.RESOURCE:
                        # https://confluence.xxx.cn/pages/viewpage.action?pageId=233763175
                        # 【逻辑设计】611605, 640280: 【认知助手】认知搜索支持搜索未发布数据资源，支持按照角色进行权限控制;
                        # 认知搜索适配重构后的指标管理
                        # 当时因为指标计算接口未就绪，所以在“全部”tab先不出指标，逻辑为：
                        # 在”全部“tab中，分析问答型搜索接口不出”指标“了，”回答“部分就按照之前正常的text2sql,text2api来做
                        # 在”指标“tab，分析问答型搜索接口要返回”指标“
                        # 2025.09.19 放开这个限制
                        # if self.qa_params.filter["asset_type"][0]== -1:
                        #     if assets["asset_type"] == "4":
                        #         continue
                        if assets["online_status"] not in ['online','down-auditing','down-reject']:
                            if assets["publish_status_category"] != "published_category":
                                continue
                    await self._add_data(
                        assets=assets
                    )
                    num += 1
                    if num >= search_limit:
                        break
            except Exception as e:
                logger.error(f'{"#" * 50}, {e}')
                continue

    async def _appointed_search(self, assets, headers):
        logger.info("使用用户指定的资源")
        appointed_resource = []

        for asset in assets:
            if asset["type"] == "3":
                detail = await self.get_view_detail(asset["id"], headers)
                appointed_resource.append(
                    {
                        "asset_type": asset["type"],
                        'resourceid': asset["id"],
                        'code': detail.get("uniform_catalog_code", None),
                        'resourcename': detail.get("business_name", None),
                        'technical_name': detail.get("technical_name", None),
                        "description": detail.get("description", None),
                        "owner_id": detail.get("owner_id", None),
                    }
                )
            elif asset["type"] == "1":
                detail = await self.get_datalog_common(
                    entity_id=asset["id"],
                    headers=headers
                )
                basic_info = await self.get_view_basic_info(
                    entity_id=asset["id"],
                    headers=headers
                )
                view_basic_info = await self.get_view_column_by_id(
                    view_id=basic_info["form_view_id"],
                    headers=headers
                )
                logger.debug("&&&&&&&&&&&&&&&&&")
                # logger.debug(basic_info)
                appointed_resource.append(
                    {
                        "asset_type": asset["type"],
                        'datacatalogid': asset["id"],
                        'code': basic_info.get("code", None),
                        'datacatalogname': detail.get("name", None),
                        "description_name": detail.get("description", None),
                        "metadata_schema": "default",
                        "form_view_id": basic_info["form_view_id"],
                        "owner_id": basic_info["owner_id"],
                        "technical_name": basic_info["technical_name"],
                        "ves_catalog_name": view_basic_info["view_source_catalog_name"][4:].split(".")[0],

                    }
                )

            elif asset["type"] == "2":
                detail = await self.get_params_by_id(
                    entity_id=asset["id"],
                    headers=headers
                )
                appointed_resource.append(
                    {
                        "asset_type": asset["type"],
                        'resourceid': asset["id"],
                        'code': detail["service_info"].get("service_code", None),
                        'resourcename': detail["service_info"].get("service_name", None),
                        "description": detail["service_info"].get("description", None),
                        "owner_id": detail["service_info"].get("owner_id", None),
                    }
                )
            elif asset["type"] == "4":
                detail = await self.get_indicator_detail(
                    entity_id=asset["id"],
                    headers=headers
                )
                appointed_resource.append(
                    {
                        "asset_type": asset["type"],
                        'resourceid': asset["id"],
                        'code': detail.get("code", None),
                        'resourcename': detail.get("name", None),
                        "description": detail.get("description", None),
                        "owner_id": detail.get("owner_id", None),
                    }
                )

        return appointed_resource

    # async def _fallback_to_asset_search(self, status_res):
    #     """
    #     当分析问答型搜索不可用时，回退到认知搜索列表的算法。
    #     该算法使用关键词搜索、向量搜索和关联搜索，没有经过大模型判断。
    #     """
    #     if status_res in ["0", "00", "000"]:
    #         logger.info("分析问答型搜索不可用")
    #         await self._calculate_search()



    async def call(self) -> CognitiveSearchResponseModel:
        select_interface = []
        explanation = []
        related_info = []
        logger.info(
            f"analysis search: input qa_params = \n{self.qa_params.model_dump()}")
        # logger.info(f"analysis search: input qa_params = \n{json.dumps(self.qa_params.model_dump(),indent=4,ensure_ascii=False)}")
        # 1A 引用资源问答
        if self.qa_params.resources:
            resources = await self._appointed_search(
                assets=self.qa_params.resources,
                headers=self.headers
            )
            for resource in resources:
                # 鉴权
                auth_id = await self.user_all_auth(
                    headers=self.headers,
                    subject_id=self.qa_params.subject_id
                )
                auth_state = await self.sub_user_auth_state(
                    assets=resource,
                    params=self.qa_params,
                    headers=self.headers,
                    auth_id=auth_id
                )

                if auth_state == "allow" or not self._should_auth_check():
                    await self._add_data(
                        assets=resource
                    )
        # 1B 非引用资源问答
        else:
            # 1B.1 调用分析问答型搜索主函数
            try:
                status_res, explanation, select_interface, related_info = await self._analysis_search()
            except Exception as e:
                tb_str = traceback.format_exc()
                logger.debug(f"============================== {tb_str}")
                logger.debug(f"{'#' * 100} {e}")
                status_res = "0"

            # 1B.2 托底策略：如果分析问答型搜索结果状态是不可用， 则使用搜索列表的算法得到搜索结果
            # 当分析问答型搜索不可用时，回退到认知搜索列表的算法。该算法使用关键词搜索、向量搜索和关联搜索，没有经过大模型判断。

            if status_res in ["0", "00", "000"]:
            # if True:
                logger.info("分析问答型搜索不可用")
                # _fallback_to_asset_search 还未完成适配 ADP
                await self._fallback_to_asset_search()

        save_props = {
            "数据目录": self.save_catalog,
            "接口服务": self.save_svc,
            "逻辑视图": self.save_view,
            "指标分析": self.save_indicator
        }
        save_props_cn = {
            "数据目录": self.save_catalog_cn,
            "接口服务": self.save_svc_cn,
            "逻辑视图": self.save_view_cn,
            "指标分析": []
        }
        # 2 如果有部门职责知识增强，才需要以下步骤：从数据资源中取单位和信息系统集合， 然后与部门职责数据中的单位、信息系统集合取交集
        if self._if_kecc():
            related_info_refined = []  # 用于存储通过交叉验证的部门职责数据
            dept_set_from_data_source_list = set()
            dept_set_from_extended_metadata = set()
            info_system_set_from_data_source_list = set()
            info_system_set_from_extended_metadata = set()

            if self.save_cites:
                for data_source in self.save_cites:
                    dept_set_from_data_source_list.add(data_source.get("department", None))
                    info_system_set_from_data_source_list.add(data_source.get("info_system", None))
                logger.info(f'dept_set_from_data_source_list: {dept_set_from_data_source_list}')
                logger.info(f'info_system_set_from_data_source_list: {info_system_set_from_data_source_list}')

            if related_info:
                for duty_info in related_info:
                    dept_set_from_extended_metadata.add(duty_info["相关负责单位"])
                    info_system_set_from_extended_metadata.add(duty_info["信息系统"])
                logger.info(f'dept_set_from_extended_metadata: {dept_set_from_extended_metadata}')
                logger.info(f'info_system_set_from_extended_metadata: {info_system_set_from_extended_metadata}')
            # 取交集
            dept_set_intersection = dept_set_from_data_source_list.intersection(dept_set_from_extended_metadata)
            info_system_set_intersection = info_system_set_from_data_source_list.intersection(
                info_system_set_from_extended_metadata)
            logger.info(f'dept_set_intersection: {dept_set_intersection}')
            logger.info(f'info_system_set_intersection: {info_system_set_intersection}')
            if len(dept_set_intersection) > 0 and len(info_system_set_intersection) > 0:
                for duty_info in related_info:
                    if duty_info["相关负责单位"] in dept_set_intersection and duty_info[
                        "信息系统"] in info_system_set_intersection:
                        related_info_refined.append(duty_info)
        else:
            related_info_refined=[]
        # 将结果组装成 CognitiveSearchResponseModel 返回
        props = {
            "props": save_props,
            "props_cn": save_props_cn,
            "cites": self.save_cites,
            "cites_dict": self.save_cites_dict,
            "svc_dict": self.save_svc_dict,
            "catalog_text2sql": self.save_catalog_text2sql,
            "view_text2sql": self.save_view_text2sql,
            "explanation": explanation,
            "select_interface": select_interface,
            "related_info": related_info_refined,
        }
        search_response = CognitiveSearchResponseModel(**props)

        return search_response

