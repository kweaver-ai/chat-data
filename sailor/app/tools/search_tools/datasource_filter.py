# -*- coding: utf-8 -*-
import asyncio
import time
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

from data_retrieval.logs.logger import logger
from data_retrieval.sessions import BaseChatHistorySession
from data_retrieval.errors import ToolFatalError
from data_retrieval.utils.model_types import ModelType4Prompt
from data_retrieval.parsers.base import BaseJsonParser
from app.depandencies.af_dataview import AFDataSource
from app.depandencies.af_indicator import AFIndicator
from app.datasource.af_data_catalog import AFDataCatalog
from data_retrieval.utils.llm import CustomChatOpenAI
from data_retrieval.settings import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from app.session.in_memory_session import InMemoryChatSession
from app.tools.base import ToolMultipleResult
from config import settings

from data_retrieval.tools.base import (
    ToolName,
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from .prompts.datasource_filter_prompt import DataSourceFilterPrompt

_SETTINGS = get_settings()

def CreateSession(session_type: str):
    if session_type == "redis":
        return RedisHistorySession()
    elif session_type == "in_memory":
        return InMemoryChatSession()
    elif session_type == "":
        return None
    else:
        raise ValueError(f"不支持的 session_type: {session_type}")


class DataSourceDescSchema(BaseModel):
    id: str = Field(description="数据资源的 id, 为一个字符串")
    title: str = Field(description="数据资源的名称")
    type: str = Field(description="数据资源的类型")
    description: str = Field(description="数据资源的描述")
    columns: Any = Field(default=None, description="数据源的字段信息")


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的完整查询需求，如果是追问，则需要根据上下文总结")
    search_tool_cache_key: str = Field(default="", description=f"""是前几轮问答 {ToolName.from_sailor.value} 工具结果的缓存 key，
    对应`search`工具结果的'result_cache_key','result_cache_key'形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg',
    不能编造该信息; 注意不是'数据资源的 ID',形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7',不要混淆!""")


class DataSourceFilterTool(LLMTool):
    name: str = ToolName.from_datasource_filter.value
    description: str = dedent(
        f"""数据资源过滤工具，如果用户针对上一论问答的结果做进一步追问的时候，可以使用该工具。一定要注意如果本轮问答使用了 {ToolName.from_sailor.value} 工具, 就不能再使用该工具!

参数:
- query: 查询语句
- search_tool_cache_key: 是前几轮问答 {ToolName.from_sailor.value} 工具结果的缓存 key，对应`search`工具结果的'result_cache_key'
,'result_cache_key'形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg',不能编造该信息; 注意不是'数据资源的 ID',
形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7',不要混淆。

如果没有 search_tool_cache_key 信息(形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg'),你需要仔细甄别，千万不要将数据
资源的 ID(形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7') 作为 search_tool_cache_key , 否则会出现严重错误!

注意: 在同一次问答中, 该工具不能与 {ToolName.from_sailor.value} 工具同时使用,只能使用其中的一个。
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _config_chain(
            self,
            data_source_list: List[dict] = None,
            data_source_list_description: str = ""
    ):
        self.refresh_result_cache_key()

        system_prompt = DataSourceFilterPrompt(
            data_source_list=data_source_list,
            prompt_manager=self.prompt_manager,
            language=self.language,
            data_source_list_description=data_source_list_description,
            background=self.background
        )

        logger.debug(f"{ToolName.from_datasource_filter.value} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            prompt = ChatPromptTemplate.from_messages(
                [
                    HumanMessage(
                        content="下面是你的任务，请务必牢记" + system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName.from_datasource_filter.value}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName.from_datasource_filter.value}
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
        search_tool_cache_key: Optional[str] = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_view_list, metric_list, data_catalog_list = OrderedDict(), OrderedDict(), OrderedDict()
        data_view_metadata, metric_metadata, data_catalog_metadata = {}, {}, {}
        data_source_list = []
        data_source_list_description = ""

        if search_tool_cache_key:
            try:
                tool_res = self.session.get_agent_logs(
                    search_tool_cache_key
                )
            except Exception as e:
                logger.error(e)
                tool_res = {}
            if tool_res:
                data_source_list = tool_res.get("cites", [])
                # 删除 cites 中的子图信息，防止大模型看到
                for cite in data_source_list:
                    if "connected_subgraph" in cite:
                        del cite["connected_subgraph"]
                data_source_list_description = tool_res.get("description", "")
            else:
                return {
                    "result": f"搜索工具的缓存 key 不存在: {search_tool_cache_key}"
                }

        for data_source in data_source_list:
            if data_source["type"] == "data_view":
                data_view_list[data_source["id"]] = data_source
            elif data_source["type"] == "indicator":
                metric_list[data_source["id"]] = data_source
            elif data_source["type"] == "data_catalog":
                data_catalog_list[data_source["id"]] = data_source
            else:
                return {
                    "result": f"数据资源类型错误: {data_source['type']}"
                }

        if len(data_view_list) > 0:

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
                        break

        if not data_view_list and not metric_list and not data_catalog_list:
            return {
                "result": f"没有找到符合要求的数据资源"
            }

        chain = self._config_chain(
            data_source_list = list(data_view_list.values()) + list(metric_list.values()) + list(data_catalog_list.values()),
            data_source_list_description=data_source_list_description
        )

        try:
            start = time.time()
            result = await chain.ainvoke({"input": query})
            logger.info("datasource filter cost {}".format(time.time() - start))
            result_datasource_list = []

            view_ids = [data_view["id"] for data_view in data_view_list.values()]
            metric_ids = [metric["id"] for metric in metric_list.values()]
            data_catalog_ids = [data_catalog["id"] for data_catalog in data_catalog_list.values()]

            for res in result["result"]:
                if res["id"] in view_ids:
                    # 结果中补充 title
                    res["title"] = data_view_list[res["id"]].get("title", "")
                    result_datasource_list.append(res)
                elif res["id"] in metric_ids:
                    res["title"] = metric_list[res["id"]].get("title", "")
                    result_datasource_list.append(res)
                elif res["id"] in data_catalog_ids:
                    res["title"] = data_catalog_list[res["id"]].get("title", "")
                    result_datasource_list.append(res)

            logger.info(f"result_datasource_list: {result_datasource_list}")

            self.session.add_agent_logs(
                self._result_cache_key,
                logs={
                    "result": result_datasource_list,
                    "cites": [
                        {
                            "id": data_source["id"],
                            "type": data_source["type"],
                            "title": data_source["title"],
                        } for data_source in result_datasource_list
                    ]
                }
            )
        except Exception as e:
            logger.error(f"获取数据资源失败: {str(e)}")
            raise ToolFatalError(f"获取数据资源失败: {str(e)}")

        # 给大模型的数据
        return {
            "result": result_datasource_list,
            "result_cache_key": self._result_cache_key
        }

    def handle_result(
        self,
        result_cache_key: str,
        log: Dict[str, Any],
        ans_multiple: ToolMultipleResult
    ) -> None:
        tool_res = self.session.get_agent_logs(
            result_cache_key
        )
        if tool_res:
            log["result"] = tool_res
            # 替换 cites
            if tool_res.get("cites"):
                ans_multiple.cites = tool_res.get("cites", [])

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict
    ):
        """将工具转换为异步 API 类方法"""
        llm_dict = {
            "model_name": settings.TOOL_LLM_MODEL_NAME,
            "openai_api_key": settings.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": settings.TOOL_LLM_OPENAI_API_BASE,
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
        session = RedisHistorySession()

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=session,
            # session_type=config_dict.get("session_type", "redis"),
            session_id=config_dict.get("session_id", ""),
            data_source_num_limit=config_dict.get("data_source_num_limit", -1),
            dimension_num_limit=config_dict.get("dimension_num_limit", -1),
            with_sample=config_dict.get("with_sample", False),
        )

        query = params.get("query", "")
        search_tool_cache_key = params.get("search_tool_cache_key", "")

        res = await tool.ainvoke(input={
            "query": query,
            "search_tool_cache_key": search_tool_cache_key
        })
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": ToolName.from_datasource_filter.value,
                "description": "数据资源过滤工具，如果用户针对上一轮问答的结果做进一步追问的时候，可以使用该工具",
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
                                        "description": "工具配置参数",
                                        "properties": {
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型",
                                                "enum": ["in_memory", "redis"],
                                                "default": "in_memory"
                                            },
                                            "session_id": {
                                                "type": "string",
                                                "description": "会话ID"
                                            }
                                        }
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户查询"
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


if __name__ == "__main__":
    pass