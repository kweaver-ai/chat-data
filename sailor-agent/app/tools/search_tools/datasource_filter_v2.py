# -*- coding: utf-8 -*-
# @Time    : 2026/1/4 11:49
# @Author  : Glen.lv
# @File    : datasource_filter_v2
# @Project : af-agent

import json
import traceback
from io import StringIO
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict, Callable
from collections import OrderedDict
from enum import Enum
import re
import asyncio

import pandas as pd
from sqlalchemy.util import await_only

from app.api.af_api import Services
from app.tools.search_tools.advance_object.data_resource import DataResource
from app.tools.search_tools.datasource_filter import DataSourceFilterTool
from app.datasource.af_data_catalog import AFDataCatalog
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field, PrivateAttr
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.messages import HumanMessage, SystemMessage

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.tools.base import ToolName
# from app.tools.base import ToolMultipleResult
from app.tools.base import _TOOL_MESSAGE_KEY
from app.tools.base import construct_final_answer, async_construct_final_answer
from app.errors import Json2PlotError, ToolFatalError
from app.tools.base import api_tool_decorator


from app.tools.search_tools.prompts.datasource_filter_prompt import DataSourceFilterPrompt
from app.utils.model_types import ModelType4Prompt
from app.parsers.base import BaseJsonParser

from app.utils.llm_utils import estimate_tokens_safe

from fastapi import FastAPI, HTTPException


class DataSourceDescSchema(BaseModel):
    id: str = Field(description="数据资源的 id, 为一个字符串")
    title: str = Field(description="数据资源的名称")
    type: str = Field(description="数据资源的类型")
    description: str = Field(description="数据源的描述")
    columns: Any = Field(default=None, description="数据源的字段信息")


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的完整查询需求，如果是追问，则需要根据上下文总结")
    search_tool_cache_key: str = Field(default="", description=f"""是前几轮问答 {ToolName.from_sailor.value} 工具结果的缓存 key，
    对应`search`工具结果的'result_cache_key','result_cache_key'形如'68a8a4f4b83c32adc3146acdb7b0ef40_CswwizwiRsmRsJ9BV69Gmg',
    不能编造该信息; 注意不是'数据资源的 ID',形如'7ce014e4-6f7e-4e4e-bcf7-6c7a09e339a7',不要混淆!""")
    # data_resource_list: Optional[List[str]] = Field(default=[], description=f"数据源的列表, 每个列表都是一个字典, 格式为: {DataSourceDescSchema.schema_json(ensure_ascii=False)}")


class DataSourceFilterToolV2(DataSourceFilterTool):
    name: str = "datasource_filter"
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
    # with_sample: bool = True
    with_sample: bool = False
    data_resource_num_limit: int = -1  # 数据资源数量上限，-1代表不限制
    dimension_num_limit: int = -1  # 字段（维度）数量上限，-1代表不限制
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    batch_size: int = 10  # map-reduce 批次大小，每批处理的数据源数量（回退方案）
    max_tokens_per_chunk: Optional[int] = None  # 每个批次的最大 token 数，如果设置则按 token 数分块
    search_configs: Optional[Any] = None
    service: Any = None
    base_url: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)  # HTTP 请求头

    token: str = ""
    user_id: str = ""
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f'*args={args}, \n**kwargs={kwargs}')
        self.service = Services(base_url=self.base_url)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)
        if kwargs.get("batch_size") is not None:
            self.batch_size = kwargs.get("batch_size")
        if kwargs.get("max_tokens_per_chunk") is not None:
            self.max_tokens_per_chunk = kwargs.get("max_tokens_per_chunk")
        if kwargs.get("search_configs") is not None:
            logger.info(f'search_configs={kwargs.get("search_configs")}')
            self.search_configs = kwargs.get("search_configs")
        else:
            raise ToolFatalError("search_configs is required")

        # 初始化 headers，使用 token 字段（可能来自 kwargs 或类默认值）
        token_value = kwargs.get("token") or self.token
        if token_value:
            self.headers = {"Authorization": token_value}
        else:
            self.headers = {}

    def _config_chain(
            self,
            data_resource_list: List[dict] = [],
            data_resource_list_description: str = "",
            skip_refresh_cache_key: bool = False
    ):
        # 刷新结果缓存key（除非明确要求跳过）
        if not skip_refresh_cache_key:
            self.refresh_result_cache_key()

        system_prompt = DataSourceFilterPrompt(
            data_source_list=data_resource_list,
            prompt_manager=self.prompt_manager,
            language=self.language,
            data_source_list_description=data_resource_list_description,
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
            # data_resource_list: Optional[List[str]] = [],
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            query=input,
            search_tool_cache_key=search_tool_cache_key,
            #  data_resource_list=data_resource_list,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
            self,
            query: str,
            search_tool_cache_key: Optional[str] = "",
            # data_resource_list: Optional[List[str]] = [],
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_resource_list = []
        data_resource_list_description = ""
        if search_tool_cache_key:
            tool_res = self.session.get_agent_logs(search_tool_cache_key)
            if tool_res:
                data_resource_list = tool_res.get("cites", [])
                data_resource_list_description = tool_res.get("description", "")
            else:
                return {
                    "result": f"搜索工具的缓存 key 不存在: {search_tool_cache_key}"
                }

        # cites和最终处理完渲染提示词的变量 data_source_list 结构几乎完全相同，把 cites 中的 "fields" 字段改名为 "columns"
        # 将 cites 格式转换为 data_source_list 格式
        data_resource_list = self._convert_cites_to_data_source_list(data_resource_list)

        data_resource_filter = self.new_data_resource(data_resource_list, data_resource_list_description)
        # 检查是否合格
        valid_result = data_resource_filter.valid()
        if valid_result:
            return valid_result

        await data_resource_filter.init_all_data_resources(query)
        # 在开始处理前刷新一次 cache key，确保所有批次使用同一个 key
        self.refresh_result_cache_key()
        try:
            result_datasource_list = await data_resource_filter.run(self.process_batch)
            logger.info(f"result_datasource_list: {result_datasource_list}")
            self.session.add_agent_logs(
                self._result_cache_key,
                logs={
                    "result": result_datasource_list,
                    "cites": [
                        {
                            "id": data_resource["id"],
                            "type": data_resource["type"],
                            "title": data_resource["title"],
                        } for data_resource in result_datasource_list
                    ]
                }
            )
        except Exception as e:
            logger.error(f"获取数据源失败: {str(e)}")
            raise ToolFatalError(f"获取数据源失败: {str(e)}")

        # 给大模型的数据
        return {
            "result": result_datasource_list,
            "result_cache_key": self._result_cache_key
        }


    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
            cls,
            params: dict
    ):
        """将工具转换为异步 API 类方法"""
        from app.utils.llm import CustomChatOpenAI
        from app.utils.llm_params import merge_llm_params
        from app.utils.password import get_authorization
        from app.session.redis_session import RedisHistorySession
        from config import settings

        llm_dict = {
            "model_name": settings.TOOL_LLM_MODEL_NAME,
            "openai_api_key": settings.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": settings.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict = merge_llm_params(llm_dict, params.get("llm", {}) or {})
        llm = CustomChatOpenAI(**llm_dict)

        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")
        if not token or token == "''":
            user = auth_dict.get("user", "")
            password = auth_dict.get("password", "")
            try:
                token = get_authorization(auth_dict.get("auth_url", settings.AF_DEBUG_IP), user, password)
            except Exception as e:
                logger.error(f"Error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})
        session = RedisHistorySession()

        # DataSourceFilterToolV2 需要额外的参数
        search_configs = config_dict.get("search_configs")
        if not search_configs:
            raise ToolFatalError(reason="search_configs 参数是必需的",
                                 detail="DataSourceFilterToolV2 需要 search_configs 配置")

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=session,
            session_type=config_dict.get("session_type", "redis"),
            session_id=config_dict.get("session_id", ""),
            data_source_num_limit=config_dict.get("data_source_num_limit", -1),
            dimension_num_limit=config_dict.get("dimension_num_limit", -1),
            with_sample=config_dict.get("with_sample", False),
            batch_size=config_dict.get("batch_size", 10),
            max_tokens_per_chunk=config_dict.get("max_tokens_per_chunk"),
            search_configs=search_configs,
            base_url=config_dict.get("base_url", ""),
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
                "description": "数据资源过滤工具V2，如果用户针对上一轮问答的结果做进一步追问的时候，可以使用该工具。支持批量处理和 token 数分块。",
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
                                                "default": "redis"
                                            },
                                            "session_id": {
                                                "type": "string",
                                                "description": "会话ID"
                                            },
                                            "data_source_num_limit": {
                                                "type": "integer",
                                                "description": "数据资源数量上限，-1代表不限制",
                                                "default": -1
                                            },
                                            "dimension_num_limit": {
                                                "type": "integer",
                                                "description": "字段（维度）数量上限，-1代表不限制",
                                                "default": -1
                                            },
                                            "with_sample": {
                                                "type": "boolean",
                                                "description": "是否包含样本数据",
                                                "default": False
                                            },
                                            "batch_size": {
                                                "type": "integer",
                                                "description": "map-reduce 批次大小，每批处理的数据源数量（回退方案）",
                                                "default": 10
                                            },
                                            "max_tokens_per_chunk": {
                                                "type": "integer",
                                                "description": "每个批次的最大 token 数，如果设置则按 token 数分块",
                                                "default": None
                                            },
                                            "search_configs": {
                                                "type": "object",
                                                "description": "搜索配置参数（必需）",
                                                "required": True
                                            },
                                            "base_url": {
                                                "type": "string",
                                                "description": "基础URL",
                                                "default": ""
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息",
                                                "default": ""
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

    @classmethod
    # 转换 cites 格式为 data_source_list 格式：将 fields 改名为 columns
    def _convert_cites_to_data_source_list(cls, cites: List[dict]) -> List[dict]:
        """
        将 cites 格式转换为 data_source_list 格式
        主要转换：将 'fields' 字段改名为 'columns'

        Args:
            cites: cites 格式的数据源列表，包含 'fields' 字段

        Returns:
            data_source_list: 转换后的数据源列表，包含 'columns' 字段
        """
        data_source_list = []
        for cite in cites:
            # 创建新的字典，复制所有字段
            data_source = cite.copy()

            # 如果存在 'fields' 字段，改名为 'columns'
            if 'fields' in data_source:
                data_source['columns'] = data_source.pop('fields')
            # 如果已经存在 'columns' 字段，保持不变
            # 如果两者都不存在，保持原样（后续可能会通过 API 获取）

            data_source_list.append(data_source)

        return data_source_list

    def new_data_resource(self, data_resource_list: List[dict], data_resource_list_description: str) -> DataResource:
        return DataResource(data_resource_list=data_resource_list,
                            data_resource_list_description=data_resource_list_description,
                            batch_size=self.batch_size,
                            max_tokens_per_chunk=self.max_tokens_per_chunk,
                            search_configs=self.search_configs,
                            dimension_num_limit=self.dimension_num_limit,
                            data_resource_num_limit=self.data_resource_num_limit,
                            prompt_manager=self.prompt_manager,
                            language=self.language,
                            background=self.background,
                            token=self.token)

        # Map 阶段：对每个批次并行处理

    def process_batch(self, batch: List[dict], batch_index: int,
                      total_batches: int) -> Callable:
        async def invoke(query: str, data_resource_list_description: str) -> dict:
            """处理单个批次的异步函数"""
            logger.info(f"处理第 {batch_index + 1}/{total_batches} 批次，包含 {len(batch)} 个数据源")
            # 注意：这里不调用 refresh_result_cache_key，使用之前统一的 cache key
            chain = self._config_chain(
                data_resource_list=batch,
                data_resource_list_description=data_resource_list_description,
                skip_refresh_cache_key=True,  # 跳过刷新 cache key
            )
            return await chain.ainvoke({"input": query})

        return invoke


if __name__ == "__main__":
    import asyncio
    from langchain_openai import ChatOpenAI
    from af_agent.prompts.manager.base import BasePromptManager
    from af_agent.sessions.in_memory_session import InMemoryChatSession

    # 创建模拟的数据源列表（基于用户提供的示例）
    test_data_resource_list = [

    ]

    # 创建模拟的 session，用于存储测试数据
    test_session = InMemoryChatSession()
    test_cache_key = "test_search_cache_key_12345"

    # 将测试数据存储到 session 中
    test_session.add_agent_logs(
        test_cache_key,
        logs={
            "cites": test_data_resource_list,
            "description": "测试数据源列表描述：包含部门、位置、等相关数据源"
        }
    )

    print("=" * 80)
    print("测试 1: 按 token 数分块")
    print("=" * 80)
    search_configs = {'sailor_search_if_history_qa_enhance': '0', 'sailor_search_if_kecc': '1',
                      'sailor_search_if_auth_in_find_data_qa': '0', 'direct_qa': 'false',
                      'sailor_vec_min_score_analysis_search': '0.5',
                      'sailor_vec_knn_k_analysis_search': '100', 'sailor_vec_size_analysis_search': '100',
                      'sailor_vec_min_score_kecc': '0.5', 'sailor_vec_knn_k_kecc': '20', 'sailor_vec_size_kecc': '20',
                      'kg_id_kecc': '19475', 'sailor_vec_min_score_history_qa': '0.7',
                      'sailor_vec_knn_k_history_qa': '10',
                      'sailor_vec_size_history_qa': '10', 'kg_id_history_qa': '19467',
                      'sailor_token_tactics_history_qa': '1',
                      'sailor_search_qa_llm_temperature': '0.0000001', 'sailor_search_qa_llm_top_p': '1',
                      'sailor_search_qa_llm_presence_penalty': '0', 'sailor_search_qa_llm_frequency_penalty': '0',
                      'sailor_search_qa_llm_max_tokens': '16000', 'sailor_search_qa_llm_input_len': '8000',
                      'sailor_search_qa_llm_output_len': '8000', 'sailor_search_qa_cites_num_limit': '100'}

    # 测试1: 按 token 数分块
    tool1 = DataSourceFilterToolV2(
        session=test_session,
        max_tokens_per_chunk=2000,  # 设置较小的 token 限制，确保会分块
        batch_size=10,
        search_configs=search_configs
    )

    # 设置 LLM 和 prompt_manager（可选，仅用于测试分块逻辑）
    tool1.llm = ChatOpenAI(
        model_name="Qwen-72B-Chat",
        openai_api_key="EMPTY",
        openai_api_base="http://192.168.173.19:8304/v1",
        max_tokens=8000,
        temperature=0
    )
    tool1.prompt_manager = BasePromptManager()

    # 测试分块功能
    query = "查找某部门相关信息"
    chunks = tool1._split_into_batches(
        test_data_resource_list,
        query=query,
        data_resource_list_description="测试数据源列表描述"
    )

    print(f"\n数据源总数: {len(test_data_resource_list)}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        chunk_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
        estimated_tokens = estimate_tokens_safe(chunk_str)
        print(f"  批次 {i + 1}: {len(chunk)} 个数据源, 约 {estimated_tokens} tokens")

    print("\n" + "=" * 80)
    print("测试 2: 按数量分块（回退方案）")
    print("=" * 80)

    # 测试2: 按数量分块
    tool2 = DataSourceFilterToolV2(
        session=test_session,
        max_tokens_per_chunk=None,  # 不设置 token 限制，使用数量分块
        batch_size=2,  # 每批2个
        search_configs=search_configs
    )

    chunks2 = tool2._split_into_batches(
        test_data_resource_list,
        query=query,
        data_resource_list_description="测试数据源列表描述"
    )

    print(f"\n数据源总数: {len(test_data_resource_list)}")
    print(f"分块数量: {len(chunks2)}")
    for i, chunk in enumerate(chunks2):
        print(f"  批次 {i + 1}: {len(chunk)} 个数据源")

    print("\n" + "=" * 80)
    print("测试 3: 测试单个数据源的 token 估算")
    print("=" * 80)

    # 测试单个数据源的 token 估算
    for i, data_resource in enumerate(test_data_resource_list[:2]):  # 只测试前2个
        item_str = json.dumps(data_resource, ensure_ascii=False, separators=(',', ':'))
        estimated_tokens = estimate_tokens_safe(item_str)
        print(f"\n数据源 {i + 1} ({data_resource['id'][:8]}...):")
        print(f"  Title: {data_resource['title'][:50]}...")
        print(f"  估算 token 数: {estimated_tokens}")
        print(f"  JSON 长度: {len(item_str)} 字符")

    print("\n" + "=" * 80)
    print("测试 4: cites 格式转换为 data_source_list 格式")
    print("=" * 80)

    # 测试 cites 格式转换为 data_source_list 格式
    test_cites = [

    ]


    # 使用工具类中的转换函数（需要创建一个临时实例来访问方法）
    # 或者直接定义转换函数
    def convert_cites_to_data_source_list(cites: List[dict]) -> List[dict]:
        """将 cites 格式转换为 data_source_list 格式"""
        data_source_list = []
        for cite in cites:
            data_source = cite.copy()
            if 'fields' in data_source:
                data_source['columns'] = data_source.pop('fields')
            data_source_list.append(data_source)
        return data_source_list


    converted_list = convert_cites_to_data_source_list(test_cites)

    print(f"\ncites 格式数据源数量: {len(test_cites)}")
    print(f"转换后 data_source_list 数量: {len(converted_list)}")
    print("\n转换示例:")
    for i, (cite, converted) in enumerate(zip(test_cites, converted_list)):
        print(f"\n  数据源 {i + 1}:")
        print(f"    cites 格式 - 字段名: {'fields' if 'fields' in cite else '无'}")
        print(f"    转换后格式 - 字段名: {'columns' if 'columns' in converted else '无'}")
        if 'fields' in cite:
            print(f"    cites.fields: {cite['fields']}")
        if 'columns' in converted:
            print(f"    data_source_list.columns: {converted['columns']}")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
