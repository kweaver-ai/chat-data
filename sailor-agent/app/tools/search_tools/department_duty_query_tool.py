# -*- coding: utf-8 -*-
"""
部门职责查询工具

用于查询部门职责（department duty）信息。
"""

from textwrap import dedent
from typing import Any, Dict, Optional, Type, List

from langchain_core.callbacks import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.errors import ToolFatalError
from app.tools.base import (
    ToolName,
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
    _TOOL_MESSAGE_KEY,
)
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.utils.model_types import ModelType4Prompt
from app.parsers.base import BaseJsonParser
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from app.service.adp_service import ADPService
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.messages import HumanMessage, SystemMessage
from .prompts.department_duty_judge_prompt import DepartmentDutyJudgePrompt

_SETTINGS = get_settings()


class DepartmentDutyQueryArgs(BaseModel):
    """工具入参模型"""
    query: str = Field(
        default="",
        description="用户的完整查询需求，用于理解查询上下文"
    )



class DepartmentDutyQueryTool(LLMTool):
    """
    部门职责查询工具

    说明：
    - 用于查询部门职责（department duty）信息
    - 支持通过部门名称、部门ID或关键词进行查询
    """

    name: str = "department_duty_query"
    description: str = dedent(
        """
        部门职责查询工具：
        - 用于查询部门职责（department duty）信息
        - 返回部门的职责描述和相关信息
        
        参数：
        - query: 用户的完整查询需求，用于理解查询上下文
        """
    )

    args_schema: Type[BaseModel] = DepartmentDutyQueryArgs

    # 认证与会话相关配置
    token: str = ""
    user_id: str = ""
    background: str = ""

    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None

    # AF 服务封装
    adp_service: Any = None
    headers: Dict[str, str] = {}
    base_url: str = ""  # 可选：用于覆盖默认 AF 地址
    kn_id: str = ""

    return_direct: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 会话
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

        # token / headers
        token_value = kwargs.get("token") or self.token
        if token_value:
            self.token = token_value
            self.headers = {"Authorization": self.token}
        else:
            self.headers = {}

        # Service 实例
        self.base_url = kwargs.get("base_url", self.base_url or "")
        self.adp_service = ADPService()

    def _config_chain(
        self,
        query: str,
        search_results: Dict[str, Any]
    ):
        """
        配置LLM chain用于判定相关三定职责
        
        Args:
            query: 用户查询需求
            search_results: 搜索返回结果
            
        Returns:
            LLM chain
        """
        self.refresh_result_cache_key()

        system_prompt = DepartmentDutyJudgePrompt(
            query=query,
            search_results=search_results,
            language=self.language,
            background=self.background
        )

        logger.debug(f"{self.name} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            prompt = ChatPromptTemplate.from_messages(
                [
                    HumanMessage(
                        content="下面是你的任务，请务必牢记" + system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: self.name}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: self.name}
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

    async def _judge_relevant_duties(
        self,
        query: str,
        search_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用LLM判定哪些三定职责与用户查询相关
        
        Args:
            query: 用户查询需求
            search_results: 搜索返回结果
            
        Returns:
            判定结果，只包含相关的三定职责
        """
        if not search_results or not search_results.get("datas"):
            return {
                "relevant_duties": [],
                "summary": {
                    "total_count": 0,
                    "relevant_count": 0,
                    "avg_relevance_score": 0
                }
            }

        try:
            chain = self._config_chain(query=query, search_results=search_results)
            result = await chain.ainvoke({"input": query})
            
            logger.info(f"[DepartmentDutyQueryTool] LLM judge result: {result}")
            return result
        except Exception as e:
            logger.error(f"[DepartmentDutyQueryTool] LLM judge failed: {e}")
            # 如果LLM判定失败，返回原始搜索结果，标记所有为相关
            datas = search_results.get("datas", [])
            relevant_duties = []
            for item in datas:
                relevant_duties.append({
                    "id": item.get("id"),
                    "relevance_score": 50,  # 默认评分
                    "relevance_reason": "LLM判定失败，默认标记为相关",
                    "sub_dept_duty": item.get("sub_dept_duty", ""),
                    "dept_name": item.get("dept_name", ""),
                    "dept_name_bdsp": item.get("dept_name_bdsp", ""),
                    "dept_duty": item.get("dept_duty", ""),
                    "info_system": item.get("info_system", ""),
                    "info_system_bdsp": item.get("info_system_bdsp", ""),
                    "duty_items": item.get("duty_items", ""),
                    "duty_items_type": item.get("duty_items_type", ""),
                    "data_resource": item.get("data_resource", ""),
                    "core_data_fields": item.get("core_data_fields", "")
                })
            
            return {
                "relevant_duties": relevant_duties,
                "summary": {
                    "total_count": len(datas),
                    "relevant_count": len(relevant_duties),
                    "avg_relevance_score": 50
                }
            }

    async def _query_department_duty(
        self,
        query: str = "",
    ) -> Dict[str, Any]:
        """
        查询部门职责信息，并使用LLM判定相关三定职责。

        Args:
            query: 用户查询需求

        Returns:
            部门职责查询结果，包含LLM判定结果和缓存key
        """
        if not self.headers:
            raise ToolFatalError("缺少认证信息，请提供有效的 token")

        logger.info(
            f"[DepartmentDutyQueryTool] start query department duty, "
            f"query={query}"
        )

        # 刷新结果缓存key
        self.refresh_result_cache_key()

        try:
            # 调用ADP服务查询部门职责
            query_params = {
                "condition": {
                    "operation": "or",
                    "sub_conditions": [
                        {
                            "field": "dept_duty",
                            "operation": "match",
                            "value": query
                        },
                        {
                            "field": "sub_dept_duty",
                            "operation": "match",
                            "value": query
                        },
                    ]
                },
                "need_total": True,
                "limit": 10
            }
            
            search_results = await self.adp_service.dip_ontology_query_by_object_types_external(
                self.token,
                kn_id=self.kn_id or "duty",
                class_id="menu_kg_dept_infosystem_duty",
                body=query_params
            )
            
            logger.info(f"[DepartmentDutyQueryTool] search success, total_count={search_results.get('total_count', 0)}")
            
            # 使用LLM判定相关三定职责
            judge_result = await self._judge_relevant_duties(query=query, search_results=search_results)
            
            # 从搜索结果中补充部门和信息系统信息到相关职责中
            relevant_duties = judge_result.get("relevant_duties", [])
            datas_dict = {item.get("id"): item for item in search_results.get("datas", [])}
            
            # 补充完整信息
            for duty in relevant_duties:
                duty_id = duty.get("id")
                if duty_id in datas_dict:
                    original_item = datas_dict[duty_id]
                    # 补充部门和信息系统信息
                    if "dept_name_bdsp" not in duty:
                        duty["dept_name_bdsp"] = original_item.get("dept_name_bdsp", "")
                    if "info_system" not in duty:
                        duty["info_system"] = original_item.get("info_system", "")
                    if "info_system_bdsp" not in duty:
                        duty["info_system_bdsp"] = original_item.get("info_system_bdsp", "")
                    if "duty_items" not in duty:
                        duty["duty_items"] = original_item.get("duty_items", "")
                    if "duty_items_type" not in duty:
                        duty["duty_items_type"] = original_item.get("duty_items_type", "")
                    if "data_resource" not in duty:
                        duty["data_resource"] = original_item.get("data_resource", "")
                    if "core_data_fields" not in duty:
                        duty["core_data_fields"] = original_item.get("core_data_fields", "")
            
            # 只返回筛选后的相关职责
            result = {
                "relevant_duties": relevant_duties,
                "summary": judge_result.get("summary", {})
            }
            
            # 保存结果到缓存（缓存中保留完整信息以便后续使用）
            cache_data = {
                "result": {
                    "judge_result": judge_result,
                    "relevant_duties": relevant_duties,
                    "summary": judge_result.get("summary", {})
                },
                "query": query
            }
            
            try:
                self.session.add_agent_logs(
                    session_id=self._result_cache_key,
                    logs=cache_data
                )
                logger.info(f"[DepartmentDutyQueryTool] cache saved, cache_key={self._result_cache_key}")
            except Exception as cache_error:
                logger.warning(f"[DepartmentDutyQueryTool] cache save failed: {cache_error}, but continue")
            
            # 添加缓存key到返回结果
            result["result_cache_key"] = self._result_cache_key
            
            logger.info(f"[DepartmentDutyQueryTool] query and judge success, relevant_count={result['summary'].get('relevant_count', 0)}")
            
        except Exception as e:
            logger.error(f"[DepartmentDutyQueryTool] query failed, error={e}")
            import traceback
            logger.error(traceback.format_exc())
            raise ToolFatalError(f"查询部门职责失败: {e}") from e

        return result

    @construct_final_answer
    def _run(
        self,
        query: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行接口（LangChain 同步工具入口）
        """
        import asyncio
        result = asyncio.run(self._query_department_duty(query=query))
        return result

    @async_construct_final_answer
    async def _arun(
        self,
        query: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        异步执行接口（LangChain 异步工具入口）
        """
        result = await self._query_department_duty(query=query)
        return result

    # -------- 作为独立异步 API 的封装 --------
    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict,
    ):
        """
        将工具转换为异步 API 类方法，供外部 HTTP 调用：

        请求示例 JSON：
        {
          "llm": { ... 可选，沿用其他工具配置 ... },
          "auth": {
            "auth_url": "http://xxx",   // 可选，获取 token 时使用
            "user": "xxx",              // 可选
            "password": "xxx",          // 可选
            "token": "Bearer xxx",      // 推荐，直接透传 AF 的 token
            "user_id": "123456"         // 可选
          },
          "config": {
            "base_url": "http://af-host",  // 可选，覆盖默认服务地址
            "session_type": "redis"        // 可选
          },
          "query": "查询部门职责",          // 必填，用户查询需求
          "kn_id": "duty"                  // 可选，知识网络ID，默认 duty
        }
        """
        # LLM 这里实际上不会被使用，但为了与现有框架保持一致，仍按约定创建
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_out_dict = params.get("llm", {})
        if llm_out_dict.get("name"):
            llm_dict["model_name"] = llm_out_dict.get("name")
        llm = CustomChatOpenAI(**llm_dict)

        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")

        # 如果没有直接传 token，则尝试根据 user/password 获取
        if not token or token == "''":
            user = auth_dict.get("user", "")
            password = auth_dict.get("password", "")
            if not user or not password:
                raise ToolFatalError("缺少 token，且未提供 user/password 获取 token")
            try:
                token = get_authorization(auth_dict.get("auth_url", _SETTINGS.AF_DEBUG_IP), user, password)
            except Exception as e:
                logger.error(f"[DepartmentDutyQueryTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})
        kn_id = params.get("kn_id", "duty")

        tool = cls(
            llm=llm,
            token=token,
            kn_id=kn_id,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
            base_url=config_dict.get("base_url", ""),
        )

        # 获取参数
        query = params.get("query", "")


        # 直接走异步接口
        res = await tool.ainvoke(
            input={
                "query": query,
            }
        )
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API。"""
        return {
            "post": {
                "summary": "department_duty_query",
                "description": "查询部门职责（department duty）信息，支持通过 kn_id 指定知识网络。",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数（本工具不会真正使用，仅保持接口一致）",
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数",
                                        "properties": {
                                            "auth_url": {"type": "string"},
                                            "user": {"type": "string"},
                                            "password": {"type": "string"},
                                            "token": {"type": "string"},
                                            "user_id": {"type": "string"},
                                        },
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "base_url": {
                                                "type": "string",
                                                "description": "AF 服务基础 URL（可选）",
                                            },
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型",
                                                "enum": ["in_memory", "redis"],
                                                "default": "redis",
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息（可选，不影响结果）",
                                            },
                                        },
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户的完整查询需求，用于理解查询上下文",
                                    },
                                    "kn_id": {
                                        "type": "string",
                                        "description": "知识网络ID（kn_id），默认 duty",
                                        "default": "duty",
                                    },
                                },
                                "required": ["query"],
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
                                    "type": "object",
                                    "properties": {
                                        "relevant_duties": {
                                            "type": "array",
                                            "description": "相关的三定职责列表",
                                            "items": {"type": "object"},
                                        },
                                        "summary": {
                                            "type": "object",
                                            "description": "统计信息",
                                        },
                                        "result_cache_key": {
                                            "type": "string",
                                            "description": "结果缓存 key",
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
