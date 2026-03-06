# -*- coding: utf-8 -*-
import asyncio
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict
from data_retrieval.errors import ToolFatalError
from data_retrieval.parsers.base import BaseJsonParser
from data_retrieval.sessions import BaseChatHistorySession, CreateSession
from langchain_core.pydantic_v1 import BaseModel, Field
from data_retrieval.utils.llm import CustomChatOpenAI
from app.depandencies.af_dataview import AFDataSource
from collections import OrderedDict
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.messages import HumanMessage, SystemMessage
from data_retrieval.utils.model_types import ModelType4Prompt
from app.session.redis_session import RedisHistorySession
from app.tools.base import ToolMultipleResult
from data_retrieval.tools.base import (
    ToolName,
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from data_retrieval.settings import get_settings
from data_retrieval.logs.logger import logger
from .prompts.explore_rule_identification import ExploreRuleIdentificationPrompt
from config import settings


_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的查询需求，用于理解质量规则识别上下文")
    data_view_list: list[str] = Field(default=[], description="库表id列表，需要识别质量规则的表ID列表")


class ExploreRuleIdentificationTool(LLMTool):
    name: str = "explore_rule_identification"
    description: str = dedent(
        """质量规则识别工具，用于从库表列表中识别数据质量规则和约束条件。
        
该工具能够识别以下类型的数据质量规则：
- **完整性规则**：非空约束、必填字段、完整性检查等
- **准确性规则**：格式校验、范围校验、精度校验、类型校验等
- **一致性规则**：唯一性约束、主键约束、外键约束、业务一致性等
- **时效性规则**：时间范围、过期检查、时效性要求等
- **有效性规则**：枚举值约束、正则表达式、业务规则等
- **合理性规则**：数值合理性、逻辑合理性、业务合理性等

参数:
- query: 用户的查询需求，用于理解质量规则识别上下文
- data_view_list: 库表id列表，需要识别质量规则的表ID列表

工具会返回每个表的质量规则识别结果，包括字段级规则和表级规则，以及规则的严重程度和置信度。
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
        input_data: dict = []
    ):
        self.refresh_result_cache_key()

        system_prompt = ExploreRuleIdentificationPrompt(
            input_data=input_data,
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

    @construct_final_answer
    def _run(
        self,
        query: str,
        data_view_list: list[str],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            query,
            data_view_list,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
        self,
        query: str,
        data_view_list: list[str] = [],
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_view_metadata = {}
        data_source_list = []

        if len(data_view_list) == 0:
            return {
                "result": {
                    "error": "请提供需要识别质量规则的库表ID列表",
                    "tables": [],
                    "summary": {
                        "total_tables": 0,
                        "total_rules": 0,
                        "rule_type_distribution": {
                            "完整性": 0,
                            "准确性": 0,
                            "一致性": 0,
                            "时效性": 0,
                            "有效性": 0,
                            "合理性": 0
                        },
                        "severity_distribution": {
                            "HIGH": 0,
                            "MEDIUM": 0,
                            "LOW": 0
                        }
                    }
                },
                "result_cache_key": self._result_cache_key
            }

        try:
            data_view_source = AFDataSource(
                view_list=data_view_list,
                token=self.token,
                user_id=self.user_id,
                redis_client=self.session.client,
            )

            data_view_metadata = data_view_source.get_meta_sample_data_v3()
            data_source_list = data_view_metadata.get("detail", [])

            if not data_source_list:
                return {
                    "result": {
                        "error": "未获取到表数据，请检查表ID是否正确",
                        "tables": [],
                        "summary": {
                            "total_tables": 0,
                            "total_rules": 0,
                            "rule_type_distribution": {
                                "完整性": 0,
                                "准确性": 0,
                                "一致性": 0,
                                "时效性": 0,
                                "有效性": 0,
                                "合理性": 0
                            },
                            "severity_distribution": {
                                "HIGH": 0,
                                "MEDIUM": 0,
                                "LOW": 0
                            }
                        }
                    },
                    "result_cache_key": self._result_cache_key
                }

        except Exception as e:
            logger.error(f"获取数据视图元数据失败: {e}")
            raise ToolFatalError(f"获取数据视图元数据失败: {str(e)}")

        chain = self._config_chain(
            input_data=data_source_list,
        )
        
        result = {}
        try:
            result = await chain.ainvoke({"input": query})

        except Exception as e:
            logger.error(f"质量规则识别失败: {str(e)}")
            raise ToolFatalError(f"质量规则识别失败: {str(e)}")

        return {
            "result": result,
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
        llm_out_dict = params.get("llm", {})
        if llm_out_dict.get("name"):
            llm_dict["model_name"] = llm_out_dict.get("name")
        llm = CustomChatOpenAI(**llm_dict)

        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")

        config_dict = params.get("config", {})
        session = RedisHistorySession()

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=session,
            data_source_num_limit=config_dict.get("data_source_num_limit", -1),
            dimension_num_limit=config_dict.get("dimension_num_limit", -1),
            with_sample=config_dict.get("with_sample", False),
        )

        query = params.get("query", "")
        data_view_list = params.get("data_view_list", [])

        res = await tool.ainvoke(input={
            "query": query,
            "data_view_list": data_view_list
        })
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": "质量规则识别工具",
                "description": "从库表列表中识别数据质量规则和约束条件，包括完整性、准确性、一致性、时效性、有效性、合理性等规则",
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
                                            "background": {
                                                "type": "string",
                                                "description": "背景上下文信息"
                                            },
                                            "data_source_num_limit": {
                                                "type": "integer",
                                                "description": "数据源数量限制，默认-1（无限制）"
                                            },
                                            "dimension_num_limit": {
                                                "type": "integer",
                                                "description": "维度数量限制，默认-1（无限制）"
                                            },
                                            "with_sample": {
                                                "type": "boolean",
                                                "description": "是否包含样例数据，默认false"
                                            }
                                        }
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户的查询需求，用于理解质量规则识别上下文"
                                    },
                                    "data_view_list": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "库表id列表，需要识别质量规则的表ID列表"
                                    }
                                },
                                "required": ["query", "data_view_list"]
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
                                        "result": {
                                            "type": "object",
                                            "description": "质量规则识别结果"
                                        },
                                        "result_cache_key": {
                                            "type": "string",
                                            "description": "结果缓存key"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }


if __name__ == "__main__":
    pass
