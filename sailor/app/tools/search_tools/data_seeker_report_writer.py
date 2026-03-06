# -*- coding: utf-8 -*-
# @Time    : 2025/10/8 12:27
# @Author  : Glen.lv
# @File    : dataseeker_report_writer
# @Project : af-agent

import asyncio
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict
from collections import OrderedDict

from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.messages import SystemMessage
from langchain.pydantic_v1 import validator

from data_retrieval.logs.logger import logger
from data_retrieval.sessions import BaseChatHistorySession, CreateSession
from data_retrieval.errors import ToolFatalError
from data_retrieval.utils.model_types import ModelType4Prompt
from app.depandencies.af_dataview import AFDataSource
from app.depandencies.af_indicator import AFIndicator
from data_retrieval.utils.llm import CustomChatOpenAI
from data_retrieval.settings import get_settings
from app.utils.password import get_authorization
from app.tools.base import ToolMultipleResult
from data_retrieval.tools.base import (
    ToolName,
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from .base import QueryIntentionName
from .prompts.data_seeker_report_writer_prompt import DataSeekerReportWriterPrompt

_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的完整查询需求，如果是追问，则需要根据上下文总结")
    query_intent: str = Field(default="QueryIntentionName.INTENTION_UNKNOWN.value", description="根据用户问题 query 判断得到的意图标签")
    search_tool_cache_key: str = Field(default="", description=f"""是前几轮问答 {ToolName.from_sailor.value} 工具结果的缓存 key，
    即`search`工具结果的'result_cache_key','result_cache_key'形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg',
    不能编造该信息; 注意不是'数据资源的 ID',形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7',不要混淆!""")

    @validator('query_intent')
    def validate_query_intent(cls, v):
        valid_intents = {intent.value for intent in QueryIntentionName}
        if v not in valid_intents:
            logger.warning(
                f"Received invalid query_intent: '{v}'. Using default: '{QueryIntentionName.INTENTION_UNKNOWN.value}'")
            return QueryIntentionName.INTENTION_UNKNOWN.value
        return v


class DataSeekerReportWriterTool(LLMTool):
    name: str = "ToolName.from_data_seeker_report_writer.value"
    description: str = dedent(
        f"""找数报告撰写工具，基于所获取的元数据，撰写系统性的报告来回答用户的问题。

参数:
- query: 查询语句
- query_intent: 根据用户问题 query 判断得到的意图标签
- search_tool_cache_key: 是前几轮问答 {"ToolName.from_structured_search_tool.value"} 工具结果的缓存 key，对应`search`工具结果`Observation`中的'result_cache_key'
,'result_cache_key'形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg',不能编造该信息; 注意不是'数据资源的 ID',
形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7',不要混淆。

如果没有 search_tool_cache_key 信息(形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg'),你需要仔细甄别，千万不要将数据
资源的 ID(形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7') 作为 search_tool_cache_key , 否则会出现严重错误!

"""
    )
    args_schema: Type[BaseModel] = ArgsModel
    with_sample: bool = False
    data_source_num_limit: int = -1
    dimension_num_limit: int = -1
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    return_direct = True

    token: str = ""
    user_id: str = ""
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _config_chain(
            self,
            dept_duty_infosystem: Optional[List[dict]] = [],
            data_source_list: List[dict] = [],
            data_source_list_description: str = "",
            query_intent: str = QueryIntentionName.INTENTION_UNKNOWN.value
    ):
        self.refresh_result_cache_key()
        # intention_faq_human_or_house = ''
        # intention_faq_enterprise = ''
        intention_generic_demand = ''
        intention_specific_demand = ''

        # if query_intent == QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value:
        #     logger.info(f'query_intent == QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value={query_intent == QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value}')
        #     intention_faq_human_or_house = QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value
        # if query_intent == QueryIntentionName.INTENTION_FAQ_ENTERPRISE.value:
        #     logger.info(
        #         f'query_intent == QueryIntentionName.INTENTION_FAQ_ENTERPRISE.value={query_intent == QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value}')
        #     intention_faq_enterprise = QueryIntentionName.INTENTION_FAQ_ENTERPRISE.value
        if query_intent == QueryIntentionName.INTENTION_GENERIC_DEMAND.value:
            logger.info(f'query_intent == QueryIntentionName.INTENTION_GENERIC_DEMAND.value={query_intent == QueryIntentionName.INTENTION_GENERIC_DEMAND.value}')
            intention_generic_demand = QueryIntentionName.INTENTION_GENERIC_DEMAND.value
        if query_intent == QueryIntentionName.INTENTION_SPECIFIC_DEMAND.value:
            logger.info(f'query_intent == QueryIntentionName.INTENTION_SPECIFIC_DEMAND.value={query_intent == QueryIntentionName.INTENTION_SPECIFIC_DEMAND.value}')
            intention_specific_demand = QueryIntentionName.INTENTION_SPECIFIC_DEMAND.value
        if query_intent == QueryIntentionName.INTENTION_UNKNOWN.value:
            logger.info(
                f'query_intent == QueryIntentionName.INTENTION_UNKNOWN.value={query_intent == QueryIntentionName.INTENTION_UNKNOWN.value}')
            logger.info(f"如果意图是'{QueryIntentionName.INTENTION_UNKNOWN.value}'，按照'{QueryIntentionName.INTENTION_GENERIC_DEMAND.value}'的模板")
            intention_generic_demand = QueryIntentionName.INTENTION_GENERIC_DEMAND.value
        if dept_duty_infosystem is None:
            dept_duty_infosystem = []
        system_prompt = DataSeekerReportWriterPrompt(
            dept_duty_infosystem=dept_duty_infosystem,
            data_source_list=data_source_list,
            prompt_manager=self.prompt_manager,
            language=self.language,
            data_source_list_description=data_source_list_description,
            background=self.background,
            # intention_faq_human_or_house=intention_faq_human_or_house,
            # intention_faq_enterprise=intention_faq_enterprise,
            intention_generic_demand=intention_generic_demand,
            intention_specific_demand=intention_specific_demand,
        )

        logger.debug(f"{ToolName.from_data_seeker_report_writer.value} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            logger.info(f'找数报告撰写工具暂不支持 {ModelType4Prompt.DEEPSEEK_R1.value} 模型')
            return None
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName.from_data_seeker_report_writer.value}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )
        logger.info(f'找数报告撰写工具 prompt: {prompt}')
        chain = (
                prompt
                | self.llm
        )
        return chain

    @construct_final_answer
    def _run(
            self,
            input: str,
            search_tool_cache_key: Optional[str] = "",
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            input,
            search_tool_cache_key=search_tool_cache_key,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
            self,
            query: str,
            query_intent: str = QueryIntentionName.INTENTION_UNKNOWN.value,
            search_tool_cache_key: Optional[str] = "",
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_view_list, metric_list = OrderedDict(), OrderedDict()
        data_view_metadata, metric_metadata = {}, {}
        dept_duty_infosystem = []
        data_source_list_description = ""

        if search_tool_cache_key:
            tool_res = self.session.get_agent_logs(
                search_tool_cache_key
            )
            if tool_res:
                dept_duty_infosystem = tool_res.get("related_info", [])
                logger.info(f'dept_duty_infosystem from search_result_related_info: {dept_duty_infosystem}')
                data_source_list = tool_res.get("cites", [])
                data_source_list_description = tool_res.get("description", "")
            else:
                return {
                    "result": f"搜索工具的缓存 key 不存在: {search_tool_cache_key}"
                }

        if data_source_list:
            for data_source in data_source_list:
                if data_source["type"] == "data_view":
                    data_view_list[data_source["id"]] = data_source
                elif data_source["type"] == "indicator":
                    metric_list[data_source["id"]] = data_source
                else:
                    return {
                        "result": f"数据资源类型错误: {data_source['type']}"
                    }

        if len(data_view_list) > 0:
            data_view_source = AFDataSource(
                view_list=list(data_view_list.keys()),
                token=self.token,
                user_id=self.user_id
            )

            try:
                data_view_metadata = data_view_source.get_meta_sample_data(
                    query,
                    self.data_source_num_limit,
                    self.dimension_num_limit,
                    self.with_sample
                )

                for k, v in data_view_list.items():
                    for detail in data_view_metadata["detail"]:
                        if detail["id"] == k:
                            v["columns"] = detail.get("en2cn", {})
                            break
            except Exception as e:
                logger.error(f"获取数据视图元数据失败: {e}")

        if len(metric_list) > 0:
            metric_source = AFIndicator(
                indicator_list=list(metric_list.keys()),
                token=self.token,
                user_id=self.user_id
            )
            try:
                metric_metadata = metric_source.get_details(
                    input_query=query,
                    indicator_num_limit=self.data_source_num_limit,
                    input_dimension_num_limit=self.dimension_num_limit
                )

                for k, v in metric_list.items():
                    for detail in metric_metadata["details"]:
                        if detail["id"] == k:
                            v["columns"] = {
                                dimension["technical_name"]: dimension["business_name"]
                                for dimension in detail.get("dimensions", [])
                            }
                            break

            except Exception as e:
                logger.error(f"获取指标元数据失败: {str(e)}")

        if not data_view_list and not metric_list:
            return {
                "result": f"没有找到符合要求的数据资源"
            }

        chain = self._config_chain(
            dept_duty_infosystem=dept_duty_infosystem,
            data_source_list=list(data_view_list.values()) + list(metric_list.values()),
            data_source_list_description=data_source_list_description,
            query_intent=query_intent
        )

        try:
            result = await chain.ainvoke({"input": query})
            markdown_report = result.content if hasattr(result, 'content') else str(result)
            return_text = "答案已经成功生成！完整答案保存在缓存里。"

            self.session.add_agent_logs(
                self._result_cache_key,
                logs={
                    "result": markdown_report,
                }
            )
        except Exception as e:
            logger.error(f"获取数据资源失败: {str(e)}")
            raise ToolFatalError(f"获取数据资源失败: {str(e)}")

        return {
            "result": return_text,
            "result_cache_key": self._result_cache_key
        }

    def handle_result(
            self,
            result_cache_key: str,
            log: Dict[str, Any],
            ans_multiple: ToolMultipleResult
    ) -> None:
        logger.info(f'DataSeekerReportWriterTool handle_result: {result_cache_key}')
        tool_res = self.session.get_agent_logs(
            result_cache_key
        )
        if tool_res:
            log["result"] = tool_res

            if tool_res.get("result"):
                ans_multiple.text = tool_res.get("result", [])

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
            cls,
            params: dict
    ):
        """将工具转换为异步 API 类方法"""
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict.update(params.get("llm", {}))
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

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session_type=config_dict.get("session_type", "redis"),
            session_id=config_dict.get("session_id", ""),
            data_source_num_limit=config_dict.get("data_source_num_limit", -1),
            dimension_num_limit=config_dict.get("dimension_num_limit", -1),
            with_sample=config_dict.get("with_sample", False),
        )

        query = params.get("query", "")
        query_intent = params.get("query_intent", QueryIntentionName.INTENTION_UNKNOWN.value)
        search_tool_cache_key = params.get("search_tool_cache_key", "")

        res = await tool.ainvoke(input={
            "query": query,
            "query_intent": query_intent,
            "search_tool_cache_key": search_tool_cache_key
        })
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": ToolName.from_data_seeker_report_writer.value,
                "description": "找数报告撰写工具，基于所获取的元数据，撰写系统性的报告来回答用户的问题",
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
                                    "query_intent": {
                                        "type": "string",
                                        "description": "用户意图标签",
                                        "enum": [
                                            "人房高频查询场景",
                                            "企业高频查询场景",
                                            "宽泛的需求",
                                            "具体的需求",
                                            "超出范围",
                                            "未知意图"
                                        ]
                                    },
                                    "search_tool_cache_key": {
                                        "type": "string",
                                        "description": "search 工具结果的缓存 key"
                                    }
                                },
                                "required": ["query", "search_tool_cache_key"]
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
