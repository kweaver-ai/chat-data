# -*- coding: utf-8 -*-
import math
import asyncio
import traceback
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict
from collections import OrderedDict

from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.messages import HumanMessage, SystemMessage

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.datasource.af_data_catalog import AFDataCatalog
from app.errors import ToolFatalError
from app.utils.model_types import ModelType4Prompt
from app.parsers.base import BaseJsonParser
from app.depandencies.af_dataview import AFDataSource
from app.depandencies.af_indicator import AFIndicator
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from config import settings

from app.tools.base import (
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from .prompts.datasource_rerank_prompt import DataSourceRerankPrompt

_SETTINGS = get_settings()
from_datasource_rerank = "datasource_rerank_tool"

class DataSourceDescSchema(BaseModel):
    id: str = Field(description="数据资源的 id, 为一个字符串")
    title: str = Field(description="数据资源的名称")
    type: str = Field(description="数据资源的类型")
    description: str = Field(description="数据资源的描述")
    columns: Any = Field(default=None, description="数据源的字段信息")


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的完整查询需求，如果是追问，则需要根据上下文总结")
    data_source_list: List[Dict[str, str]] = Field(default=[], description="粗召回的数据资源列表，每个资源包含 id 和 type 字段")
    department_duty_cache_key: Optional[str] = Field(default=None, description="部门职责查询工具结果的缓存key")
    custom_rule_strategy_cache_key: Optional[str] = Field(default=None, description="自定义搜索策略工具查询结果的缓存key")


class DataSourceRerankTool(LLMTool):
    name: str = from_datasource_rerank
    description: str = dedent(
        """数据资源重排序工具，用于对粗召回的数据资源进行筛选和重排序，选择最符合用户输入的资源。

筛选依据：主要根据资源名称和字段名称进行匹配和筛选。

参数:
- query: 查询语句
- data_source_list: 粗召回的数据资源列表，每个资源是一个字典，必须包含 id 和 type 字段
- department_duty_cache_key: 可选，部门职责查询结果的缓存key，用于提供部门职责相关的背景信息
- custom_rule_strategy_cache_key: 可选，自定义规则策略查询结果的缓存key，用于提供自定义规则策略相关的背景信息

该工具会根据用户查询中的关键词，匹配资源名称和字段名称，筛选出最符合用户需求的数据资源。
"""
        )
    args_schema: Type[BaseModel] = ArgsModel
    with_sample: bool = False
    data_source_num_limit: int = -1
    dimension_num_limit: int = -1
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None

    token: str = ""
    user_id: str = ""
    background: str = ""
    use_priority_strategy: bool = False
    use_department_duty: bool = False



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _config_chain(
        self,
        data_source_list: List[dict] = [],
        data_source_list_description: str = "",
        background: Optional[str] = None
    ):
        # self.refresh_result_cache_key()
        
        # 使用传入的background，如果没有则使用self.background
        background_to_use = background if background is not None else self.background

        system_prompt = DataSourceRerankPrompt(
            data_source_list=data_source_list,
            language=self.language,
            data_source_list_description=data_source_list_description,
            background=background_to_use
        )

        logger.debug(f"{from_datasource_rerank} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            prompt = ChatPromptTemplate.from_messages(
                [
                    HumanMessage(
                        content="下面是你的任务，请务必牢记" + system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: from_datasource_rerank}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: from_datasource_rerank}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )

        chain = (
            prompt
            | self.llm
            | BaseJsonParser()
        )
        return chain
        

    @construct_final_answer
    def _run(
        self,
        input: str,
        data_source_list: Optional[List[Dict[str, str]]] = None,
        department_duty_cache_key: Optional[str] = None,
        custom_rule_strategy_cache_key: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            input,
            data_source_list=data_source_list or [],
            department_duty_cache_key=department_duty_cache_key,
            custom_rule_strategy_cache_key=custom_rule_strategy_cache_key,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
        self,
        query: str,
        data_source_list: Optional[List[Dict[str, str]]] = None,
        department_duty_cache_key: Optional[str] = None,
        custom_rule_strategy_cache_key: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_view_list, metric_list, data_catalog_list = OrderedDict(), OrderedDict(), OrderedDict()
        data_source_list = data_source_list or []

        data_source_list_description = ""
        logger.info("data_source_list {} ".format(data_source_list))
        
        # 读取缓存数据并整合到background中
        background_parts = []
        if self.background:
            background_parts.append(self.background)
        
        # 保存部门职责信息，用于输出结果
        department_duty_info = []
        department_duty_map = {}
        
        # 读取部门职责缓存数据（仅在启用三定职责时）
        if self.use_department_duty and department_duty_cache_key:
            try:
                duty_cache_data = self.session.get_agent_logs(department_duty_cache_key)
                if duty_cache_data:
                    duty_result = duty_cache_data.get("result", {})
                    relevant_duties = duty_result.get("relevant_duties", [])
                    if relevant_duties:
                        # 保存完整的部门职责信息用于输出
                        # department_duty_info = relevant_duties
                        
                        # 添加到background中
                        # background_parts.append("\n## 部门职责信息")
                        for duty in relevant_duties:
                            # department_duty_info.append({
                            #     "部门": duty.get("dept_name_bdsp", ""),
                            #     "信息系统": duty.get("info_system_bdsp", ""),
                            #     "职责": duty.get("dept_duty", "") + " " + duty.get("sub_dept_duty", ""),
                            # })
                            department_duty_map["{}-{}".format(duty.get("dept_name_bdsp", ""), duty.get("info_system_bdsp", ""))] = {
                                "score": duty.get("_score", 0.0),
                                "部门": duty.get("dept_name_bdsp", ""),
                                "信息系统": duty.get("info_system_bdsp", ""),
                                "职责": duty.get("dept_duty", "") + " " + duty.get("sub_dept_duty", "")
                                }
                            # dept_name = duty.get("dept_name", "")
                            # sub_dept_duty = duty.get("sub_dept_duty", "")
                            # info_system = duty.get("info_system", "")
                            # if dept_name or sub_dept_duty:
                            #     duty_info = f"- 部门：{dept_name}"
                            #     if sub_dept_duty:
                            #         duty_info += f"，职责：{sub_dept_duty}"
                            #     if info_system:
                            #         duty_info += f"，信息系统：{info_system}"
                            #     background_parts.append(duty_info)
            except Exception as e:
                logger.warning(f"读取部门职责缓存失败: {e}")
        
        # 保存自定义规则策略信息，用于输出结果
        custom_rule_strategy_info = None
        priority_table_id = ""
        rule_base_name = ""
        rule_value = ""
        
        # 读取自定义规则策略缓存数据（仅在启用优先搜索策略时）
        if self.use_priority_strategy and custom_rule_strategy_cache_key:
            try:
                strategy_cache_data = self.session.get_agent_logs(custom_rule_strategy_cache_key)
                if strategy_cache_data:
                    # 缓存数据可能是单个对象或列表
                    strategy_result = strategy_cache_data.get("result", {})
                    if not strategy_result:
                        # 如果result为空，尝试直接使用缓存数据
                        strategy_result = strategy_cache_data
                    
                    # 处理单个对象或列表
                    if isinstance(strategy_result, list):
                        # 如果是列表，取第一个（通常只有一个规则）
                        if strategy_result:
                            strategy_result = strategy_result[0]
                        else:
                            strategy_result = None
                    
                    if strategy_result and isinstance(strategy_result, dict):
                        # 保存完整的策略信息用于输出
                        custom_rule_strategy_info = strategy_result
                        
                        # 添加到background中，格式化为更友好的描述
                        # background_parts.append("\n## 自定义规则策略信息")
                        rule_base_name = strategy_result.get("rule_key", "")
                        # rule_key = strategy_result.get("rule_key", "")
                        rule_value = strategy_result.get("rule_value", "")
                        priority_table_id = strategy_result.get("priority_table_id", "")
                        rule_type = strategy_result.get("type", "")
                        
                        # rule_description = f"规则名称：{rule_base_name}"
                        # if rule_key:
                        #     rule_description += f"\n规则关键词：{rule_key}"
                        # if rule_value:
                        #     rule_description += f"\n规则说明：{rule_value}"
                        # if priority_table_id:
                        #     rule_description += f"\n优先推荐表ID：{priority_table_id}"
                        #     if rule_type:
                        #         rule_description += f"（类型：{rule_type}）"
                        #
                        # background_parts.append(rule_description)
            except Exception as e:
                logger.warning(f"读取自定义规则策略缓存失败: {e}")
        
        # 更新background
        enhanced_background = "\n".join(background_parts) if background_parts else ""

        if not data_source_list:
            raise ToolFatalError("数据资源列表为空")

        for data_source in data_source_list:
            if data_source["type"] in ["data_view", "form_view"]:
                data_view_list[data_source["id"]] = data_source
            elif data_source["type"] == "indicator":
                metric_list[data_source["id"]] = data_source
            elif data_source["type"] == "datacatalog":
                data_catalog_list[data_source["id"]] = data_source
            else:
                continue
        priority_table_info = {}
        n_data_view_list = []
        if len(data_view_list) > 0:

            # 查看优先匹配的库表是否在召回中（仅在启用优先搜索策略时）
            if self.use_priority_strategy and priority_table_id and priority_table_id not in data_view_list:
                data_view_list[priority_table_id] = {"id": priority_table_id, "type": "form_view"}

            try:
                data_view_source = AFDataSource(
                    view_list=list(data_view_list.keys()),
                    token=self.token,
                    user_id=self.user_id,
                    redis_client=self.session.client,

                )

                data_view_metadata = data_view_source.get_meta_sample_data_v2(
                    query,
                )

                for k, v in data_view_list.items():
                    for detail in data_view_metadata["detail"]:
                        if detail["id"] == k:
                            v["columns"] = detail.get("en2cn", {})
                            if "title" not in v or not v.get("title"):
                                v["title"] = detail.get("name", detail.get("title", ""))
                            if "description" not in v or not v.get("description"):
                                v["description"] = detail.get("description", "")
                            v["department_id"] = detail.get("department_id", "")
                            v["department"] = detail.get("department", "")
                            v["info_system_id"] = detail.get("info_system_id", "")
                            v["info_system"] = detail.get("info_system", "")

                            n_data_view_list.append({
                                "id": v["id"],
                                "type": v["type"],
                                "title": v.get("title", ""),
                                "description": v.get("description", ""),
                                "columns": v["columns"],
                            })
                            break
                if priority_table_id in data_view_list:
                    priority_table_info = data_view_list[priority_table_id]
                    none_value = data_view_list.pop(priority_table_id, None)

            except Exception as e:
                logger.error(f"获取数据视图元数据失败: {e}")

        n_data_catalog_list = []
        if len(data_catalog_list) > 0:
            catalog_source = AFDataCatalog(
                data_catalog_list=list(data_catalog_list.keys()),
                token=self.token,
                user_id=self.user_id
            )
            catalog_metadata = catalog_source.get_meta_sample_data_v2(
                query,
                self.data_source_num_limit,
                self.dimension_num_limit,

            )

            for k, v in data_catalog_list.items():
                for detail in catalog_metadata["detail"]:
                    if detail["id"] == k:
                        v["columns"] = detail.get("columns", {})
                        # 补充 title 和 description 字段
                        if "title" not in v or not v.get("title"):
                            v["title"] = detail.get("name", detail.get("title", ""))
                        if "description" not in v or not v.get("description"):
                            v["description"] = detail.get("description", "")
                        v["department_id"] = detail.get("department_id", "")
                        v["department"] = detail.get("department", "")
                        v["info_system_id"] = detail.get("info_system_id", "")
                        v["info_system"] = detail.get("info_system", "")

                        n_data_catalog_list.append({
                            "id": v["id"],
                            "type": v["type"],
                            "title": v.get("title", ""),
                            "description": v.get("description", ""),
                            "columns": v["columns"],
                        })
                        break
        
        if not n_data_view_list and not metric_list and not n_data_catalog_list:
            result = {
                "result": f"没有找到符合要求的数据资源"
            }
            # 即使没有数据资源，也返回部门职责和策略信息（如果有）
            if department_duty_info:
                result["department_duty_info"] = department_duty_info
            if custom_rule_strategy_info:
                result["custom_rule_strategy_info"] = custom_rule_strategy_info
            return result

        logger.info("resource token size {}".format(len(str(n_data_view_list))))
        try:
            chain = self._config_chain(
                data_source_list=n_data_view_list + list(metric_list.values()) + n_data_catalog_list,
                data_source_list_description=data_source_list_description,
                background=enhanced_background
            )
        except Exception as e:
            error_info = traceback.format_exc()
            # 打印到控制台
            print("自定义异常输出：\n", error_info)
            # 写入日志文件
            logger.error("程序出错：\n%s", error_info)
            raise ToolFatalError(f"初始化agent失败: {str(e)}")

        try:
            result = await chain.ainvoke({"input": query})

            result_datasource_list = []
            filtered_out_list = []

            # 合并所有资源字典，方便查找
            all_data_sources = {}
            all_data_sources.update(data_view_list)
            all_data_sources.update(metric_list)
            all_data_sources.update(data_catalog_list)

            view_ids = [data_view["id"] for data_view in data_view_list.values()]
            metric_ids = [metric["id"] for metric in metric_list.values()]
            catalog_ids = [catalog["id"] for catalog in data_catalog_list.values()]

            # 添加优先规则匹配的资源（仅在启用优先搜索策略时）
            if self.use_priority_strategy and priority_table_info:
                result["result"] = [{"id": priority_table_id,
                                     "type": "form_view",
                                     "reason": f"根据规则策略'{rule_base_name}'优先推荐",
                                     "matched_columns": [],
                                     "relevance_score": 100}] + result.get("result", [])
            # 处理选中的资源
            selected_ids = set()
            selected_duty_keys = set()
            for res in result.get("result", []):
                # 确保 reason 和 relevance_score 字段存在
                if "reason" not in res:
                    res["reason"] = ""
                if "relevance_score" not in res:
                    res["relevance_score"] = 1.0
                
                selected_ids.add(res["id"])


                select_flag = True
                duty_key = ""
                if res["id"] in view_ids:
                    res["title"] = data_view_list[res["id"]].get("title", "")
                    res["type"] = data_view_list[res["id"]].get("type", "form_view")

                    # 三定职责匹配
                    duty_key = "{}-{}".format(data_view_list[res["id"]].get("department", ""), data_view_list[res["id"]].get("info_system", ""))


                elif res["id"] in metric_ids:
                    res["title"] = metric_list[res["id"]].get("title", "")
                    res["type"] = metric_list[res["id"]].get("type", "indicator")
                elif res["id"] in catalog_ids:
                    res["title"] = data_catalog_list[res["id"]].get("title", "")
                    res["type"] = data_catalog_list[res["id"]].get("type", "data_catalog")
                    # 三定职责匹配
                    duty_key = "{}-{}".format(res.get("department", ""), res.get("info_system", ""))

                elif res["id"] == priority_table_id:
                    res["title"] = priority_table_info["title"]
                    res["type"] = priority_table_info["type"]

                else:
                    select_flag = False

                if select_flag:
                    # 三定职责匹配（仅在启用三定职责时）
                    if self.use_department_duty and duty_key in department_duty_map:
                        logger.info("资源{} 匹配部门和信息系统{}".format(res["id"], duty_key))
                        res["relevance_score"] = 99 + convert_number_numeric(department_duty_map[duty_key]["score"])

                        if duty_key not in selected_duty_keys:
                            selected_duty_keys.add(duty_key)
                            department_duty_info.append({
                                "部门": department_duty_map[duty_key]["部门"],
                                "信息系统": department_duty_map[duty_key]["信息系统"],
                                "职责": department_duty_map[duty_key]["职责"],
                            })
                    result_datasource_list.append(res)


            result_datasource_list.sort(key=lambda x: x["relevance_score"], reverse=True)

            # 处理被过滤掉的资源
            filtered_out_from_llm = result.get("filtered_out", [])
            filtered_out_ids = {item["id"] for item in filtered_out_from_llm}
            
            # 找出所有未选中的资源
            all_input_ids = set(all_data_sources.keys())
            missing_ids = all_input_ids - selected_ids - filtered_out_ids
            
            # 处理 LLM 返回的 filtered_out
            for filtered_item in filtered_out_from_llm:
                filtered_id = filtered_item.get("id")
                if filtered_id in all_data_sources:
                    filtered_item["title"] = all_data_sources[filtered_id].get("title", "")
                    filtered_item["type"] = all_data_sources[filtered_id].get("type", "")
                    if "filter_reason" not in filtered_item:
                        filtered_item["filter_reason"] = ""
                    # 确保 unmatched_columns 字段存在
                    if "unmatched_columns" not in filtered_item:
                        filtered_item["unmatched_columns"] = []
                    # 如果 filter_reason 中没有字段相关信息，尝试从 unmatched_columns 补充
                    if filtered_item["unmatched_columns"] and "字段" not in filtered_item["filter_reason"]:
                        unmatched_str = "、".join(filtered_item["unmatched_columns"][:3])  # 最多显示3个字段
                        if filtered_item["filter_reason"]:
                            filtered_item["filter_reason"] += f"，不匹配字段：{unmatched_str}"
                        else:
                            filtered_item["filter_reason"] = f"缺少或不匹配关键字段：{unmatched_str}"
                    filtered_out_list.append(filtered_item)
            
            # 处理 LLM 遗漏的资源（补充到 filtered_out）
            for missing_id in missing_ids:
                if missing_id in all_data_sources:
                    # 尝试分析字段信息，生成更详细的过滤原因
                    missing_source = all_data_sources[missing_id]
                    columns = missing_source.get("columns", {})
                    column_names = list(columns.keys()) if isinstance(columns, dict) else []
                    
                    filter_reason = "未在筛选结果中，可能缺少用户查询所需的关键字段"
                    if column_names:
                        # 如果有关键字段信息，可以更具体
                        filter_reason += f"，现有字段可能不匹配用户需求"
                    
                    filtered_out_list.append({
                        "id": missing_id,
                        "type": missing_source.get("type", ""),
                        "title": missing_source.get("title", ""),
                        "filter_reason": filter_reason,
                        "unmatched_columns": []
                    })


            logger.info(f"result_datasource_list: {result_datasource_list}")
            logger.info(f"filtered_out_list: {filtered_out_list}")

            # self.session.add_agent_logs(
            #     self._result_cache_key,
            #     logs={
            #         "result": result_datasource_list,
            #         "cites": [
            #             {
            #                 "id": data_source["id"],
            #                 "type": data_source["type"],
            #                 "title": data_source["title"],
            #             } for data_source in result_datasource_list
            #         ]
            #     }
            # )
        except Exception as e:
            logger.error(f"数据资源重排序失败: {str(e)}")
            raise ToolFatalError(f"数据资源重排序失败: {str(e)}")

        # 构建返回结果
        result = {
            "result": result_datasource_list,
            "filtered_out": filtered_out_list,
            "result_cache_key": self._result_cache_key
        }
        
        # 添加部门职责信息到输出结果
        if selected_duty_keys:
            result["department_duty_info"] = department_duty_info
        else:
            result["department_duty_info"] = []
        
        # # 添加自定义规则策略信息到输出结果
        # if custom_rule_strategy_info:
        #     result["custom_rule_strategy_info"] = custom_rule_strategy_info
        
        return result


    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict
    ):
        """将工具转换为异步 API 类方法"""
        logger.info(f"datasource_rerank as_async_api_cls params: {params}")
        llm_dict = {
            "model_name": settings.TOOL_LLM_MODEL_NAME,
            "openai_api_key": settings.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": settings.TOOL_LLM_OPENAI_API_BASE,
            "max_tokens": 20000
        }

        # llm_dict.update(params.get("llm", {}))
        # llm_dict["max_tokens"] = 20000
        llm_out_dict = params.get("llm", {})
        if llm_out_dict.get("name"):
            llm_dict["model_name"] = llm_out_dict.get("name")
        llm = CustomChatOpenAI(**llm_dict)

        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")
        if not token or token == "''":
            user = auth_dict.get("user", "")
            password = auth_dict.get("password", "")
            try:
                token = get_authorization(auth_dict.get("auth_url", _SETTINGS.AF_DEBUG_IP), user, password)
            except Exception as e:
                logger.error(f"Error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})
        session = RedisHistorySession()

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=session,
            with_sample=config_dict.get("with_sample", False),
            use_priority_strategy=params.get("use_priority_strategy", False),
            use_department_duty=params.get("use_department_duty", False)
        )

        query = params.get("query", "")
        data_source_list = params.get("data_source_list", [])
        department_duty_cache_key = params.get("department_duty_cache_key")
        custom_rule_strategy_cache_key = params.get("custom_rule_strategy_cache_key")

        res = await tool.ainvoke(input={
            "query": query,
            "data_source_list": data_source_list,
            "department_duty_cache_key": department_duty_cache_key,
            "custom_rule_strategy_cache_key": custom_rule_strategy_cache_key,
        })
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": "datasource_rerank",
                "description": "数据资源重排序工具，用于对粗召回的数据资源进行筛选和重排序，选择最符合用户输入的资源",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数"
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数",
                                        "properties": {
                                            "auth_url": {"type": "string"},
                                            "user": {"type": "string"},
                                            "password": {"type": "string"},
                                            "token": {"type": "string"},
                                            "user_id": {"type": "string"}
                                        }
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数"
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户查询"
                                    },
                                    "data_source_list": {
                                        "type": "array",
                                        "description": "粗召回的数据资源列表",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {
                                                    "type": "string",
                                                    "description": "数据资源的 id。 如果数据资源类型是form_view, 那么id格式是uuid, 如果数据资源类型是datacatalog, 那么id格式是雪花id"
                                                },
                                                "type": {
                                                    "type": "string",
                                                    "description": "数据资源的类型，如 'form_view' 或 'datacatalog'"
                                                }
                                            },
                                            "required": ["id", "type"]
                                        }
                                    },
                                    "department_duty_cache_key": {
                                        "type": "string",
                                        "description": "可选，部门职责查询结果的缓存key，用于提供部门职责相关的背景信息"
                                    },
                                    "custom_rule_strategy_cache_key": {
                                        "type": "string",
                                        "description": "可选，自定义规则策略查询结果的缓存key，用于提供自定义规则策略相关的背景信息"
                                    },
                                    "use_priority_strategy": {
                                        "type": "boolean",
                                        "description": "可选，是否使用优先搜索策略，默认为False。如果为True，会根据自定义规则策略中的优先推荐表ID进行排序"
                                    },
                                    "use_department_duty": {
                                        "type": "boolean",
                                        "description": "可选，是否使用部门职责，默认为False。如果为True，会根据部门职责信息对数据资源进行匹配和评分"
                                    }
                                },
                                "required": ["query", "data_source_list"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }


def convert_number_numeric(num):
    # 处理0的特殊情况
    if num == 0:
        return 0.0

    # 分离整数和小数部分，计算总位数
    # 先取绝对值（避免负数影响位数计算）
    abs_num = abs(num)
    # 整数部分的位数
    int_part = math.floor(abs_num)
    int_digits = len(str(int_part)) if int_part != 0 else 0
    # 小数部分的位数（通过转为字符串辅助计算，也可通过循环判断）
    decimal_part = abs_num - int_part
    decimal_digits = len(str(decimal_part).split('.')[-1]) if decimal_part != 0 else 0

    # 总位数 = 整数位数 + 小数位数
    total_digits = int_digits + decimal_digits
    # 计算结果：原数 / 10^total_digits
    result = num / (10 ** total_digits)
    return result

if __name__ == "__main__":
    pass
