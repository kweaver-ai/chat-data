# -*- coding: utf-8 -*-
import ast
import asyncio
from textwrap import dedent
from typing import Optional, Type, Any, Dict

from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.messages import SystemMessage

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.errors import ToolFatalError
from app.utils.model_types import ModelType4Prompt
from app.parsers.base import BaseJsonParser
from app.api.ad_api import (
    ad_builder_get_kg_info,
    ad_builder_get_kg_info_async,
    ad_opensearch_with_kgid_connector_async,
    ad_opensearch_with_kgid_connector,
    AD_CONNECT
)
from app.utils.llm import CustomChatOpenAI
from config import get_settings

from app.tools.base import (
    ToolName,
    # QueryIntentionName,
    ToolMultipleResult,
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from .base import QueryIntentionName
from .prompts.data_seeker_intention_recognizer_prompt import DataSeekerIntentionRecognizerPrompt

_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的完整查询需求，如果是追问，则需要根据上下文总结")


class DataSeekerIntentionRecognizerTool(LLMTool):
    name: str = "ToolName.from_data_seeker_intention_recognizer.value"
    description: str = dedent(
        f"""用户问题理解、意图识别工具，识别用户问题中提及的实体和关系，对用户问题的意图进行判断， 并给出回答用户问题的整体规划路径。

参数:
- query: 用户的问题，或者称为查询语句。

"""
    )
    args_schema: Type[BaseModel] = ArgsModel
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    background: str = ""
    ad_connect: AD_CONNECT = None
    ad_appid: str = ""
    kg_id_data_scpe: str | None = None
    space_name: str = ""
    data_scope_dept_infosystem: str = ""
    data_scope_dept_infosystem_description: str = ""
    model_type = "ModelType4Prompt.DATA_SEEKER.value"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kg_id_data_scpe = kwargs.get('kg_id_data_scope_dept_infosystem', None)
        self.ad_connect = AD_CONNECT()
        self.ad_appid = self.ad_connect.get_appid()
        self.space_name = self.get_space_name()
        cal_query = "data_scope_dept_infosystem"
        entity_classes = ["data_scope_dept_infosystem"]
        if self.kg_id_data_scpe is None:
            self.data_scope_dept_infosystem = ""
        else:
            self.data_scope_dept_infosystem = ast.literal_eval(self.search_by_keyword_with_kgid(cal_query, entity_classes))

        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _config_chain(self):
        self.refresh_result_cache_key()

        system_prompt = DataSeekerIntentionRecognizerPrompt(
            prompt_manager=self.prompt_manager,
            language=self.language,
            data_scope_dept_infosystem=self.data_scope_dept_infosystem,
            data_scope_dept_infosystem_description=self.data_scope_dept_infosystem_description,
            background=self.background,
            # intention_faq_human_or_house=QueryIntentionName.INTENTION_FAQ_HUMAN_OR_HOUSE.value,
            # intention_faq_enterprise=QueryIntentionName.INTENTION_FAQ_ENTERPRISE.value,
            intention_generic_demand=QueryIntentionName.INTENTION_GENERIC_DEMAND.value,
            intention_specific_demand=QueryIntentionName.INTENTION_SPECIFIC_DEMAND.value,
            intention_out_of_scope=QueryIntentionName.INTENTION_OUT_OF_SCOPE.value,
            intention_unknown=QueryIntentionName.INTENTION_UNKNOWN.value,
        )
        logger.info(f'type of system_prompt =  {type(system_prompt)}')
        logger.info(f"{ToolName.from_data_seeker_intention_recognizer.value} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            logger.info(f'找数报告撰写工具暂不支持 {ModelType4Prompt.DEEPSEEK_R1.value} 模型')
            return None
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName.from_data_seeker_intention_recognizer.value}
                    ),

                    HumanMessagePromptTemplate.from_template("{query_in_prompt}")
                ]
            )
            logger.info(f'type of prompt =  {type(prompt)}')
            logger.info(f'{ToolName.from_data_seeker_intention_recognizer.value} -> prompt: {prompt}')
        chain = (
                prompt
                | self.llm
                | BaseJsonParser()
        )
        logger.info(f'type of chain =  {type(chain)}')
        return chain

    @construct_final_answer
    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            query=query,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        chain = self._config_chain()

        try:
            result = await chain.ainvoke({"query_in_prompt": query})
            intent = result["result"][0].get("intent", "")
            confidence = result["result"][0].get("confidence", 0)

            mentioned_time = result["result"][0].get("entities").get("mentioned_time", "")
            mentioned_region = result["result"][0].get("entities").get("mentioned_region", "")
            mentioned_department = result["result"][0].get("entities").get("mentioned_department", "")
            mentioned_info_system = result["result"][0].get("entities").get("mentioned_info_system", "")
            mentioned_subject = result["result"][0].get("entities").get("mentioned_subject", "")
            mentioned_topic = result["result"][0].get("entities").get("mentioned_topic", "")
            mentioned_tables = result["result"][0].get("entities").get("mentioned_tables", "")
            mentioned_fields = result["result"][0].get("entities").get("mentioned_fields", "")

            mentioned_relation_between_department_and_info_system = result["result"][0].get("relations").get(
                "mentioned_relation_between_department_and_info_system", "")
            mentioned_relation_between_info_system_and_tables = result["result"][0].get("relations").get(
                "mentioned_relation_between_info_system_and_tables", "")
            mentioned_relation_between_tables_and_fields = result["result"][0].get("relations").get(
                "mentioned_relation_between_tables_and_fields", "")

            is_within_the_scope_of_department_infosystem = result["result"][0].get(
                "is_within_the_scope_of_department_infosystem", "")

            self.session.add_agent_logs(
                self._result_cache_key,
                logs={
                    "is_within_the_scope_of_department_infosystem": is_within_the_scope_of_department_infosystem,
                    "intent": intent,
                    "confidence": confidence,
                    "entities": {
                        "mentioned_time": mentioned_time,
                        "mentioned_region": mentioned_region,
                        "mentioned_department": mentioned_department,
                        "mentioned_info_system": mentioned_info_system,
                        "mentioned_subject": mentioned_subject,
                        "mentioned_topic": mentioned_topic,
                        "mentioned_tables": mentioned_tables,
                        "mentioned_fields": mentioned_fields
                    },
                    "relations": {
                        "mentioned_relation_between_department_and_info_system": mentioned_relation_between_department_and_info_system,
                        "mentioned_relation_between_info_system_and_tables": mentioned_relation_between_info_system_and_tables,
                        "mentioned_relation_between_tables_and_fields": mentioned_relation_between_tables_and_fields
                    },
                }
            )
        except Exception as e:
            logger.error(f"智能找数意图识别工具执行失败 error: {str(e)}")
            raise ToolFatalError(f"智能找数意图识别工具执行失败: {str(e)}")

        return {
            "is_within_the_scope_of_department_infosystem": is_within_the_scope_of_department_infosystem,
            "intent": intent,
            "confidence": confidence,
            "entities": {
                "mentioned_time": mentioned_time,
                "mentioned_region": mentioned_region,
                "mentioned_department": mentioned_department,
                "mentioned_info_system": mentioned_info_system,
                "mentioned_subject": mentioned_subject,
                "mentioned_topic": mentioned_topic,
                "mentioned_tables": mentioned_tables,
                "mentioned_fields": mentioned_fields
            },
            "relations": {
                "mentioned_relation_between_department_and_info_system": mentioned_relation_between_department_and_info_system,
                "mentioned_relation_between_info_system_and_tables": mentioned_relation_between_info_system_and_tables,
                "mentioned_relation_between_tables_and_fields": mentioned_relation_between_tables_and_fields
            },
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

    def get_space_name(self):
        if self.kg_id_data_scpe:
            kg_otl = ad_builder_get_kg_info(self.ad_appid, self.kg_id_data_scpe)

            kg_otl = kg_otl['res']
            if isinstance(kg_otl['graph_baseInfo'], list):
                space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
            else:
                space_name = kg_otl['graph_baseInfo']['graph_DBName']
        else:
            space_name = ""
        return space_name

    def search_by_keyword_with_kgid(self, cal_query, entity_classes) -> str:
        logger.debug(f"search_by_keyword_async_with_kgid -> cal_query: {cal_query}")

        body_data_scope_retriever = {
            "query": {
                "term": {
                    "name": {
                        "value": cal_query
                    }
                }
            },
            "_source": ["content"]
        }

        logger.info("entity_classes: {}".format(entity_classes))
        res = ad_opensearch_with_kgid_connector(self.ad_appid, self.kg_id_data_scpe, body_data_scope_retriever,
                                                entity_classes=entity_classes)
        hits = res.get('hits', {}).get('hits')
        data_scope_content = ""
        if hits:
            data_scope_content = hits[0]["_source"]["content"]
            data_scope_content = data_scope_content.replace("\\\\", "\\")
        return data_scope_content

    async def get_space_name_async(self):
        if self.kg_id_data_scpe:
            kg_otl = await ad_builder_get_kg_info_async(self.ad_appid, self.kg_id_data_scpe)

            kg_otl = kg_otl['res']
            if isinstance(kg_otl['graph_baseInfo'], list):
                space_name = kg_otl['graph_baseInfo'][0]['graph_DBName']
            else:
                space_name = kg_otl['graph_baseInfo']['graph_DBName']
        else:
            space_name = ""
        return space_name

    async def search_by_keyword_async_with_kgid(self, appid, kg_id_data_scpe, cal_query, entity_classes) -> str:
        logger.debug(f"search_by_keyword_async_with_kgid -> cal_query: {cal_query}")

        body_data_scope_retriever = {
            "query": {
                "term": {
                    "name": {
                        "value": cal_query
                    }
                }
            },
            "_source": ["content"]
        }

        logger.info("entity_class {}".format(entity_classes))
        res = await ad_opensearch_with_kgid_connector_async(appid, kg_id_data_scpe, body_data_scope_retriever,
                                                            entity_classes=entity_classes)
        hits = res.get('hits', {}).get('hits')
        data_scope_content = ""
        if hits:
            data_scope_content = hits[0]["_source"]["content"]
            data_scope_content = data_scope_content.replace("\\\\", "\\")
        return data_scope_content

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

        config_dict = params.get("config", {})
        kg_id = config_dict.get("kg_id_data_scope_dept_infosystem", "")

        tool = cls(
            llm=llm,
            kg_id_data_scope_dept_infosystem=kg_id,
            background=config_dict.get("background", ""),
            session_type=config_dict.get("session_type", "redis"),
            session_id=config_dict.get("session_id", ""),
        )

        query = params.get("query", "")

        res = await tool.ainvoke(input={"query": query})
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": ToolName.from_data_seeker_intention_recognizer.value,
                "description": "用户问题理解、意图识别工具，识别用户问题中提及的实体和关系，对用户问题的意图进行判断",
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
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "kg_id_data_scope_dept_infosystem": {
                                                "type": "string",
                                                "description": "知识图谱 ID"
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景知识"
                                            },
                                            "session_type": {
                                                "type": "string",
                                                "enum": ["in_memory", "redis"],
                                                "default": "redis"
                                            },
                                            "session_id": {
                                                "type": "string",
                                                "description": "会话 ID"
                                            }
                                        }
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户查询"
                                    }
                                },
                                "required": ["query"]
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
