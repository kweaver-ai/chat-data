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
from app.tools.base import api_tool_decorator
from app.tools.base import (
    ToolName,
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
)
from config import get_settings
from app.logs.logger import logger
from .prompts.data_classification_prompt import DataClassificationPrompt
from config import settings


_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的查询需求，用于理解分类分级上下文")
    data_view_list: list[str] = Field(default=[], description="库表id列表，需要分类分级的表ID列表")


class DataClassificationDetectTool(LLMTool):
    name: str = "data_classification_detect"
    description: str = dedent(
        """数据分类分级工具，用于对数据库表进行业务分类和数据分级。
        
该工具能够：
- **业务领域分类**：识别表所属的业务领域（如人力资源、财务管理、销售管理等）
- **数据类型分类**：识别数据类型（主数据、交易数据、分析数据等）
- **数据来源分类**：识别数据来源（业务系统、外部系统、手工录入等）
- **数据分级**：评估数据重要性级别（L1核心级、L2重要级、L3一般级、L4参考级）

参数:
- query: 用户的查询需求，用于理解分类分级上下文
- data_view_list: 库表id列表，需要分类分级的表ID列表

工具会返回每个表的分类分级结果，包括业务分类、数据类型、重要性级别、分级原因等详细信息。
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
            return "未获取到数据分类分级结果。"
        
        # 检查是否有错误
        if "error" in result:
            return f"数据分类分级失败：{result.get('error', '未知错误')}。"
        
        summary = result.get("summary", {})
        tables = result.get("tables", [])
        
        if not summary and not tables:
            return "未获取到数据分类分级结果。"
        
        # 提取统计信息
        total_tables = summary.get("total_tables", len(tables))
        classification_dist = summary.get("classification_distribution", {})
        grading_dist = summary.get("grading_distribution", {})
        
        # 构建总结文字
        summary_parts = []
        
        # 总体统计
        summary_parts.append(f"本次数据分类分级共涉及 {total_tables} 个表。\n")
        
        # 分类分布统计
        if classification_dist:
            business_domain = classification_dist.get("business_domain", {})
            data_type = classification_dist.get("data_type", {})
            data_source = classification_dist.get("data_source", {})
            
            if business_domain:
                summary_parts.append("\n业务领域分布：\n")
                for domain, count in sorted(business_domain.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {domain}：{count} 个表\n")
            
            if data_type:
                summary_parts.append("\n数据类型分布：\n")
                for dtype, count in sorted(data_type.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {dtype}：{count} 个表\n")
            
            if data_source:
                summary_parts.append("\n数据来源分布：\n")
                for source, count in sorted(data_source.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {source}：{count} 个表\n")
        
        # 分级分布统计
        if grading_dist:
            summary_parts.append("\n数据分级分布：\n")
            level_names = {
                "L1": "核心级",
                "L2": "重要级",
                "L3": "一般级",
                "L4": "参考级"
            }
            for level in ["L1", "L2", "L3", "L4"]:
                count = grading_dist.get(level, 0)
                if count > 0:
                    level_name = level_names.get(level, level)
                    summary_parts.append(f"  • {level}（{level_name}）：{count} 个表\n")
        
        # 各表详情
        if tables:
            summary_parts.append("\n各表分类分级详情：\n")
            for table in tables:
                table_name = table.get("table_name", "未知表")
                classification = table.get("classification", {})
                grading = table.get("grading", {})
                
                info_parts = [f"{table_name}："]
                
                # 分类信息
                if classification:
                    class_info = []
                    business_domain = classification.get("business_domain")
                    if business_domain:
                        class_info.append(f"业务领域：{business_domain}")
                    data_type = classification.get("data_type")
                    if data_type:
                        class_info.append(f"数据类型：{data_type}")
                    if class_info:
                        info_parts.append("，".join(class_info))
                
                # 分级信息
                if grading:
                    level = grading.get("level", "")
                    level_name = grading.get("level_name", "")
                    if level:
                        if level_name:
                            info_parts.append(f"，级别：{level}（{level_name}）")
                        else:
                            info_parts.append(f"，级别：{level}")
                
                summary_parts.append("  • " + "".join(info_parts) + "\n")
        
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

        system_prompt = DataClassificationPrompt(
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
                "error": "请提供需要分类分级的库表ID列表",
                "tables": [],
                "summary": {
                    "total_tables": 0,
                    "classification_distribution": {
                        "business_domain": {},
                        "data_type": {},
                        "data_source": {}
                    },
                    "grading_distribution": {
                        "L1": 0,
                        "L2": 0,
                        "L3": 0,
                        "L4": 0
                    }
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
                        "classification_distribution": {
                            "business_domain": {},
                            "data_type": {},
                            "data_source": {}
                        },
                        "grading_distribution": {
                            "L1": 0,
                            "L2": 0,
                            "L3": 0,
                            "L4": 0
                        }
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
            logger.error(f"数据分类分级失败: {str(e)}")
            raise ToolFatalError(f"数据分类分级失败: {str(e)}")

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
                "summary": "数据分类分级工具",
                "description": "对数据库表进行业务分类和数据分级，识别业务领域、数据类型、数据来源和重要性级别",
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
                                        "description": "用户的查询需求，用于理解分类分级上下文"
                                    },
                                    "data_view_list": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "库表id列表，需要分类分级的表ID列表"
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
                                            "description": "数据分类分级结果"
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
