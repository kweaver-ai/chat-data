# -*- coding: utf-8 -*-
import asyncio
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict
from app.errors import ToolFatalError
from app.parsers.base import BaseJsonParser
from app.session import BaseChatHistorySession, CreateSession
from langchain_core.pydantic_v1 import BaseModel, Field
from app.utils.llm import CustomChatOpenAI
from app.depandencies.af_dataview import AFDataSource
from collections import OrderedDict
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.model_types import ModelType4Prompt
from app.session.redis_session import RedisHistorySession
from app.tools.base import  api_tool_decorator
from app.tools.base import (
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer
)
from config import get_settings
from app.logs.logger import logger
from .prompts.sensitive_data_detect_prompt import SensitiveDataDetectPrompt
from config import settings


_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的查询需求，用于理解检测上下文")
    data_view_list: list[str] = Field(default=[], description="库表id列表，需要检测敏感字段的表ID列表")


class SensitiveDataDetectTool(LLMTool):
    name: str = "sensitive_data_detect"
    description: str = dedent(
        """敏感字段检测工具，用于检测数据库表中可能包含敏感信息的字段。
        
该工具能够识别以下类型的敏感数据：
- 个人身份信息 (PII)：身份证号、手机号、邮箱、地址等
- 财务信息：银行卡号、账户余额、交易金额等
- 健康信息：病历号、诊断信息等
- 位置信息：GPS坐标、IP地址等
- 其他敏感信息：密码、密钥等

参数:
- query: 用户的查询需求，用于理解检测上下文
- data_view_list: 库表id列表，需要检测敏感字段的表ID列表

工具会返回每个表的敏感字段检测结果，包括：
- 敏感字段类型、敏感级别、检测原因和处理建议
- 匹配敏感数据的正则表达式（用于数据扫描和验证）
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

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        """
        根据大模型生成的结果，组装生成总结文字
        
        Args:
            result: 大模型返回的结果，包含 tables 和 summary
            
        Returns:
            总结文字
        """
        if not result or not isinstance(result, dict):
            return "未获取到敏感信息检测结果。"
        
        # 检查是否有错误
        if "error" in result:
            return f"敏感信息检测失败：{result.get('error', '未知错误')}。"
        
        summary = result.get("summary", {})
        tables = result.get("tables", [])
        
        if not summary and not tables:
            return "未获取到敏感信息检测结果。"
        
        # 提取统计信息
        total_tables = summary.get("total_tables", len(tables))
        total_fields = summary.get("total_fields", 0)
        total_sensitive_fields = summary.get("total_sensitive_fields", 0)
        high_risk_fields = summary.get("high_risk_fields", 0)
        medium_risk_fields = summary.get("medium_risk_fields", 0)
        low_risk_fields = summary.get("low_risk_fields", 0)
        
        # 构建总结文字
        summary_parts = []
        
        # 总体统计
        summary_parts.append(f"本次敏感信息检测共涉及 {total_tables} 个表，{total_fields} 个字段。\n")
        
        # 敏感字段统计
        if total_sensitive_fields > 0:
            summary_parts.append(f"发现 {total_sensitive_fields} 个敏感字段，")
            
            risk_details = []
            if high_risk_fields > 0:
                risk_details.append(f"{high_risk_fields} 个高风险字段")
            if medium_risk_fields > 0:
                risk_details.append(f"{medium_risk_fields} 个中等风险字段")
            if low_risk_fields > 0:
                risk_details.append(f"{low_risk_fields} 个低风险字段")
            
            if risk_details:
                summary_parts.append("其中：" + "，".join(risk_details) + "。\n")
            else:
                summary_parts.append("\n")
            
            # 统计敏感数据类型分布
            sensitive_type_count = {}
            for table in tables:
                sensitive_fields = table.get("sensitive_fields", [])
                for field in sensitive_fields:
                    sensitive_type = field.get("sensitive_type", "未知类型")
                    sensitive_type_count[sensitive_type] = sensitive_type_count.get(sensitive_type, 0) + 1
            
            if sensitive_type_count:
                summary_parts.append("敏感数据类型分布：\n")
                for sensitive_type, count in sorted(sensitive_type_count.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {sensitive_type}：{count} 个字段\n")
        else:
            summary_parts.append("未发现敏感字段，所有字段均安全。\n")
        
        # 各表详情
        if tables:
            summary_parts.append("\n各表检测详情：\n")
            for table in tables:
                table_name = table.get("table_name", "未知表")
                table_summary = table.get("summary", {})
                table_sensitive_count = table_summary.get("sensitive_count", 0)
                table_high_risk = table_summary.get("high_risk_count", 0)
                table_medium_risk = table_summary.get("medium_risk_count", 0)
                table_low_risk = table_summary.get("low_risk_count", 0)
                
                if table_sensitive_count > 0:
                    risk_info = []
                    if table_high_risk > 0:
                        risk_info.append(f"高风险 {table_high_risk} 个")
                    if table_medium_risk > 0:
                        risk_info.append(f"中等风险 {table_medium_risk} 个")
                    if table_low_risk > 0:
                        risk_info.append(f"低风险 {table_low_risk} 个")
                    
                    risk_str = "，".join(risk_info) if risk_info else ""
                    summary_parts.append(
                        f"  • {table_name}：发现 {table_sensitive_count} 个敏感字段"
                        + (f"（{risk_str}）" if risk_str else "") + "\n"
                    )
                else:
                    summary_parts.append(f"  • {table_name}：未发现敏感字段\n")
        
        return "".join(summary_parts).strip()

    def _config_chain(
        self,
        input_data: dict = [],
        input_sample: list = []
    ):
        if self.with_sample:
            if len(input_sample):
                sample_info = []
                for sample in input_sample:
                    sample_info.append(f"逻辑视图{sample['table_name']}的样例数据为：{sample['sample']}")
                if sample_info:
                    self.background += "\n" + "\n".join(sample_info)

        system_prompt = SensitiveDataDetectPrompt(
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
        sample_data_list = []

        if len(data_view_list) == 0:
            error_result = {
                "error": "请提供需要检测的库表ID列表",
                "tables": [],
                "summary": {
                    "total_tables": 0,
                    "total_fields": 0,
                    "total_sensitive_fields": 0,
                    "high_risk_fields": 0,
                    "medium_risk_fields": 0,
                    "low_risk_fields": 0
                }
            }
            summary_text = self._generate_summary(error_result)
            return {
                "result": error_result,
                "summary_text": summary_text,
                "result_cache_key": self._result_cache_key
            }

        try:
            data_view_source = AFDataSource(
                view_list=data_view_list,
                token=self.token,
                user_id=self.user_id,
                redis_client=self.session.client,
            )

            data_view_metadata = data_view_source.get_meta_sample_data_v3(self.with_sample)
            data_source_list = data_view_metadata.get("detail", [])
            if self.with_sample:
                sample_data_list = data_view_metadata["sample"]

            if not data_source_list:
                error_result = {
                    "error": "未获取到表数据，请检查表ID是否正确",
                    "tables": [],
                    "summary": {
                        "total_tables": 0,
                        "total_fields": 0,
                        "total_sensitive_fields": 0,
                        "high_risk_fields": 0,
                        "medium_risk_fields": 0,
                        "low_risk_fields": 0
                    }
                }
                summary_text = self._generate_summary(error_result)
                return {
                    "result": error_result,
                    "summary_text": summary_text,
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
            logger.error(f"敏感字段检测失败: {str(e)}")
            raise ToolFatalError(f"敏感字段检测失败: {str(e)}")

        # 生成总结文字
        summary_text = self._generate_summary(result)

        return {
            "result": result,
            "summary_text": summary_text,
            "result_cache_key": self._result_cache_key
        }

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
        if llm_out_dict.get("max_tokens"):
            llm_dict["max_tokens"] = llm_out_dict.get("max_tokens")
        else:
            llm_dict["max_tokens"] = 20000
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
                "summary": "敏感字段检测工具",
                "description": "检测数据库表中可能包含敏感信息的字段，识别个人身份信息、财务信息、健康信息等敏感数据类型",
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
                                        "description": "用户的查询需求，用于理解检测上下文"
                                    },
                                    "data_view_list": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "库表id列表，需要检测敏感字段的表ID列表"
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
                                            "description": "敏感字段检测结果"
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
