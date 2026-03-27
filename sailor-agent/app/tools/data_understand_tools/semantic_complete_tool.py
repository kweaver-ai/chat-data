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
from app.api.data_model import DataModelService
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
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer
)
from config import get_settings
from app.logs.logger import logger
from .prompts.semantic_complete_prompt import SemanticCompletePrompt
from config import settings


_SETTINGS = get_settings()
ToolName = "semantic_complete_tool"

class ArgsModel(BaseModel):
    query:  str = Field(default="", description="query")
    data_view_list: list[str] = Field(default=[], description="库表id列表")



class SemanticCompleteTool(LLMTool):
    name: str = "semantic_complete_tool"
    description: str = dedent(
        f"""语义补全工具是一款面向数据库开发、数据治理、数据分析场景的智能化辅助工具，核心功能是针对数据库中的库表名称、字段名称，自动完成语义化中文名补全，解决数据库对象 “英文缩写无释义”“命名不规范”“语义不清晰” 的痛点问题。
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
    data_model: DataModelService = None
    knowledge_item_ids: list[str] = [] # 知识条目id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        """
        根据大模型生成的结果，组装生成总结文字
        
        Args:
            result: 大模型返回的结果，包含 views 和 summary
            
        Returns:
            总结文字
        """
        if not result or not isinstance(result, dict):
            return "未获取到语义补全结果。"
        
        summary = result.get("summary", {})
        # 兼容旧格式（tables）和新格式（views）
        views = result.get("views", result.get("tables", []))
        
        if not summary and not views:
            return "未获取到语义补全结果。"
        
        # 提取统计信息（兼容旧格式）
        total_views = summary.get("total_views", summary.get("total_tables", len(views)))
        total_fields = summary.get("total_fields", 0)
        need_completion_count = summary.get("need_completion_count", 0)
        accurate_count = summary.get("accurate_count", 0)
        
        # 构建总结文字
        summary_parts = []
        
        # 总体统计
        summary_parts.append(f"本次语义补全分析共涉及 {total_views} 个视图，{total_fields} 个字段。\n")
        
        # 需要补全的字段统计
        if need_completion_count > 0:
            summary_parts.append(f"发现 {need_completion_count} 个字段需要补全描述，")
            
            # 统计各问题类型
            issue_type_count = {"MISSING": 0, "INACCURATE": 0, "INCOMPLETE": 0}
            for view in views:
                # 兼容旧格式和新格式（form_view_*, view_*, fields_need_completion等）
                fields_need_completion = (view.get("fields_need_completion") or 
                                         view.get("form_view_fields_need_completion") or 
                                         view.get("view_fields_need_completion", []))
                for field in fields_need_completion:
                    issue_type = field.get("issue_type", "")
                    if issue_type in issue_type_count:
                        issue_type_count[issue_type] += 1
            
            issue_details = []
            if issue_type_count["MISSING"] > 0:
                issue_details.append(f"{issue_type_count['MISSING']} 个字段描述缺失")
            if issue_type_count["INACCURATE"] > 0:
                issue_details.append(f"{issue_type_count['INACCURATE']} 个字段描述不准确")
            if issue_type_count["INCOMPLETE"] > 0:
                issue_details.append(f"{issue_type_count['INCOMPLETE']} 个字段描述不完整")
            
            if issue_details:
                summary_parts.append("其中：" + "，".join(issue_details) + "。\n")
            else:
                summary_parts.append("\n")
        else:
            summary_parts.append("所有字段描述均完整准确，无需补全。\n")
        
        # 描述准确的字段统计
        if accurate_count > 0:
            summary_parts.append(f"有 {accurate_count} 个字段描述准确完整。\n")
        
        # 各视图详情
        if views:
            summary_parts.append("各视图详情：\n")
            for view in views:
                # 兼容旧格式和新格式（view_tech_name, view_technical_name, form_view_technical_name等）
                view_name = (view.get("view_tech_name") or 
                            view.get("view_technical_name") or 
                            view.get("form_view_technical_name") or 
                            view.get("table_name", "未知视图"))
                view_summary = view.get("summary", {})
                view_need_count = view_summary.get("need_completion_count", 0)
                view_accurate_count = view_summary.get("accurate_count", 0)
                
                if view_need_count > 0:
                    summary_parts.append(
                        f"  • {view_name}：需要补全 {view_need_count} 个字段，"
                        f"描述准确 {view_accurate_count} 个字段\n"
                    )
                else:
                    summary_parts.append(
                        f"  • {view_name}：所有字段描述完整准确\n"
                    )
        
        return "".join(summary_parts).strip()

    def _transform_input_data(self, data_source_list: List[Dict]) -> List[Dict]:
        """
        将 get_meta_sample_data_v3 返回的数据结构转换为新格式
        
        Args:
            data_source_list: 原始数据列表，格式为 [{"table_id": ..., "table_name": ..., ...}, ...]
            
        Returns:
            转换后的数据列表，格式为 [{"view_id": ..., "view_tech_name": ..., ...}, ...]
        """
        transformed_list = []
        
        for table_data in data_source_list:
            transformed_item = {
                "view_id": table_data.get("table_id", ""),
                "view_tech_name": table_data.get("table_name", ""),
                "view_business_name": table_data.get("table_business_name", ""),
                "desc": table_data.get("table_description", ""),
                "fields": []
            }
            
            # 转换字段数据
            fields = table_data.get("fields", [])
            for field in fields:
                transformed_field = {
                    "field_id": field.get("field_id", ""),
                    "field_tech_name": field.get("field_name", ""),
                    "field_business_name": field.get("field_business_name", ""),
                    "field_type": field.get("field_type", ""),
                    "field_desc": field.get("field_description", "")
                }
                # 如果存在 field_role，添加到转换后的字段中，并进行规范化处理
                if "field_role" in field:
                    transformed_field["field_role"] = SemanticCompleteTool._normalize_field_role(field.get("field_role"))
                # 如果存在 field_comment，添加到转换后的字段中（用于帮助语义理解）
                if "field_comment" in field:
                    transformed_field["field_comment"] = field.get("field_comment")
                transformed_item["fields"].append(transformed_field)
            
            transformed_list.append(transformed_item)
        
        return transformed_list

    @staticmethod
    def _transform_to_new_format(views: List[Dict]) -> List[Dict]:
        """
        将各种格式转换为新格式（view_id, view_tech_name等）
        
        Args:
            views: 视图数据列表，支持多种格式（form_view_*, view_*, table_*等）
            
        Returns:
            转换后的数据列表，格式为 [{"view_id": ..., "view_tech_name": ..., ...}, ...]
        """
        transformed_list = []
        
        for view in views:
            # 兼容多种格式
            view_id = (view.get("view_id") or 
                      view.get("form_view_id") or 
                      view.get("table_id") or "")
            
            view_tech_name = (view.get("view_tech_name") or 
                            view.get("view_technical_name") or 
                            view.get("form_view_technical_name") or 
                            view.get("table_name") or "")
            
            view_business_name = (view.get("view_business_name") or 
                                view.get("form_view_business_name") or 
                                view.get("table_business_name") or "")
            
            desc = (view.get("desc") or 
                   view.get("view_desc") or 
                   view.get("form_view_desc") or 
                   view.get("table_description") or "")
            
            transformed_item = {
                "view_id": view_id,
                "view_tech_name": view_tech_name,
                "view_business_name": view_business_name,
                "desc": desc,
                "fields": []
            }
            
            # 转换字段数据
            fields = (view.get("fields") or 
                     view.get("view_fields") or 
                     view.get("form_view_fields") or [])
            
            for field in fields:
                field_id = (field.get("field_id") or 
                           field.get("view_field_id") or 
                           field.get("form_view_field_id") or "")
                
                field_tech_name = (field.get("field_tech_name") or 
                                 field.get("field_technical_name") or 
                                 field.get("view_field_technical_name") or 
                                 field.get("form_view_field_technical_name") or 
                                 field.get("field_name") or "")
                
                field_business_name = (field.get("field_business_name") or 
                                     field.get("view_field_business_name") or 
                                     field.get("form_view_field_business_name") or "")
                
                field_type = (field.get("field_type") or 
                            field.get("view_field_type") or 
                            field.get("form_view_field_type") or "")
                
                field_desc = (field.get("field_desc") or 
                            field.get("field_description") or 
                            field.get("view_field_desc") or 
                            field.get("form_view_field_desc") or "")
                
                field_role = (field.get("field_role") or 
                            field.get("view_field_role") or 
                            field.get("form_view_field_role"))
                
                field_comment = (field.get("field_comment") or 
                               field.get("view_field_comment") or 
                               field.get("form_view_field_comment") or "")
                
                transformed_field = {
                    "field_id": field_id,
                    "field_tech_name": field_tech_name,
                    "field_business_name": field_business_name,
                    "field_type": field_type,
                    "field_desc": field_desc
                }
                # 如果存在 field_role，添加到转换后的字段中，并进行规范化处理
                if field_role is not None:
                    transformed_field["field_role"] = SemanticCompleteTool._normalize_field_role(field_role)
                # 如果存在 field_comment，添加到转换后的字段中（用于帮助语义理解）
                if field_comment:
                    transformed_field["field_comment"] = field_comment
                transformed_item["fields"].append(transformed_field)
            
            transformed_list.append(transformed_item)
        
        return transformed_list

    @staticmethod
    def _normalize_field_role(field_role: Any) -> int:
        """
        规范化字段角色值
        
        Args:
            field_role: 字段角色值，可能是 int、str、None 等类型
            
        Returns:
            规范化后的 int 类型值，如果为 None 则返回 0，如果是 str 则尝试转换为 int
        """
        if field_role is None:
            return 0
        if isinstance(field_role, str):
            try:
                return int(field_role)
            except (ValueError, TypeError):
                return 0
        if isinstance(field_role, int):
            return field_role
        # 其他类型，尝试转换为 int
        try:
            return int(field_role)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _transform_result_to_new_format(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 LLM 返回的结果转换为新格式（输出格式）
        
        Args:
            result: LLM 返回的结果，格式为 {"views": [...], "summary": {...}}
            
        Returns:
            转换后的结果，格式为 {"views": [...], "summary": {...}}，使用新格式（view_id, view_tech_name等）
        """
        if not result or not isinstance(result, dict):
            return result
        
        transformed_result = {
            "summary": result.get("summary", {})
        }
        
        # 转换 views
        views = result.get("views", [])
        transformed_views = []
        
        for view in views:
            # 处理视图级别的补全
            view_need_completion = view.get("view_need_completion", {})
            need_completion = view_need_completion.get("need_completion", False)
            
            # 如果视图需要补全，使用建议的值
            view_business_name = view.get("view_business_name", "")
            desc = view.get("desc", "")
            
            if need_completion:
                # 使用建议的业务名称和描述
                suggested_business_name = view_need_completion.get("suggested_business_name")
                suggested_description = view_need_completion.get("suggested_description")
                
                if suggested_business_name:
                    view_business_name = suggested_business_name
                if suggested_description:
                    desc = suggested_description
            
            transformed_view = {
                "view_id": view.get("view_id", ""),
                "view_tech_name": view.get("view_tech_name", ""),
                "view_business_name": view_business_name,
                "desc": desc,
                "summary": view.get("summary", {})
            }
            
            # 保留视图补全信息（如果存在）
            if view_need_completion:
                transformed_view["view_need_completion"] = view_need_completion
            
            # 转换需要补全的字段
            fields_need_completion = view.get("fields_need_completion", [])
            transformed_fields_need_completion = []
            for field in fields_need_completion:
                transformed_field = {
                    "field_id": field.get("field_id", ""),
                    "field_tech_name": field.get("field_tech_name", ""),
                    "field_business_name": field.get("field_business_name", ""),
                    "issue_type": field.get("issue_type", ""),
                    "current_description": field.get("current_description", ""),
                    "issue_reason": field.get("issue_reason", ""),
                }
                # 保留 field_role（如果存在），并进行规范化处理
                if "field_role" in field:
                    transformed_field["field_role"] = SemanticCompleteTool._normalize_field_role(field.get("field_role"))
                if "suggested_description" in field:
                    transformed_field["suggested_description"] = field.get("suggested_description")
                # 保留 suggested_business_name（如果存在，用于业务名称补全）
                if "suggested_business_name" in field:
                    transformed_field["suggested_business_name"] = field.get("suggested_business_name")
                # 保留 suggested_field_role（如果存在，用于字段角色补全），并进行规范化处理
                if "suggested_field_role" in field:
                    transformed_field["suggested_field_role"] = SemanticCompleteTool._normalize_field_role(field.get("suggested_field_role"))
                transformed_fields_need_completion.append(transformed_field)
            transformed_view["fields_need_completion"] = transformed_fields_need_completion
            
            transformed_views.append(transformed_view)
        
        transformed_result["views"] = transformed_views
        
        return transformed_result

    @staticmethod
    def _add_accurate_fields(result: Dict[str, Any], input_views: List[Dict]) -> Dict[str, Any]:
        """
        在结果中添加未补全的字段（从输入中提取，不在fields_need_completion中的字段）
        
        Args:
            result: LLM返回的结果，格式为 {"views": [...], "summary": {...}}
            input_views: 输入的视图数据列表，格式为 [{"view_id": ..., "fields": [...]}, ...]
            
        Returns:
            补充了未补全字段的结果
        """
        if not result or not isinstance(result, dict):
            return result
        
        views = result.get("views", [])
        
        # 创建输入视图的映射（按view_id）
        input_views_map = {}
        for input_view in input_views:
            view_id = input_view.get("view_id", "")
            if view_id:
                input_views_map[view_id] = input_view
        
        # 为每个视图补充未补全的字段
        for view in views:
            view_id = view.get("view_id", "")
            input_view = input_views_map.get(view_id)
            
            if not input_view:
                continue
            
            # 获取需要补全的字段ID集合
            fields_need_completion = view.get("fields_need_completion", [])
            need_completion_field_ids = {field.get("field_id") for field in fields_need_completion if field.get("field_id")}
            
            # 从输入中提取所有字段
            input_fields = input_view.get("fields", [])
            
            # 找出未补全的字段（不在fields_need_completion中的字段）
            fields_accurate = []
            for input_field in input_fields:
                field_id = input_field.get("field_id", "")
                
                # 如果字段不在需要补全的列表中，则添加到未补全字段列表
                if field_id and field_id not in need_completion_field_ids:
                    accurate_field = {
                        "field_id": field_id,
                        "field_tech_name": input_field.get("field_tech_name", ""),
                        "field_business_name": input_field.get("field_business_name", ""),
                        "field_type": input_field.get("field_type", ""),
                        "field_desc": input_field.get("field_desc", ""),
                    }
                    # 如果存在field_role，添加到字段中，并进行规范化处理
                    if "field_role" in input_field:
                        accurate_field["field_role"] = SemanticCompleteTool._normalize_field_role(input_field.get("field_role"))
                    # 如果存在field_comment，添加到字段中
                    if "field_comment" in input_field:
                        accurate_field["field_comment"] = input_field.get("field_comment")
                    fields_accurate.append(accurate_field)
            
            # 将未补全的字段添加到结果中
            if fields_accurate:
                view["fields_accurate"] = fields_accurate
        
        return result

    def _config_chain(
        self,
        input_data: dict = [],
        input_sample: list = []
    ):
        # self.refresh_result_cache_key()
        # 将知识条目内容放到背景中
        if self.knowledge_item_ids:
            knowledge_item_ids = ",".join(self.knowledge_item_ids)

            knowledge_items = self.data_model.get_knowledge_items_by_ids(knowledge_item_ids)

            knowledge_item_data_list = []
            for knowledge_item in knowledge_items:
                for knowledge_item_data in knowledge_item["items"]:
                    knowledge_item_data_list.append("英文单词：{} 翻译为{}".format(knowledge_item_data["key"], knowledge_item_data["value"]))
            logger.info("knowledge_item num {}".format(len(knowledge_item_data_list)))
            if knowledge_item_data_list:
                self.background += "\n单词额外信息\n" + "\n".join(knowledge_item_data_list)
            logger.info("background {}".format(self.background))
        # 样例数据
        if self.with_sample:
            if len(input_sample):
                sample_info = []
                for sample in input_sample:
                    sample_info.append(f"逻辑视图{sample['table_name']}的样例数据为：{sample['sample']}")
                if sample_info:
                    self.background += "\n" + "\n".join(sample_info)

        system_prompt = SemanticCompletePrompt(
            input_data=input_data,
            language=self.language,
            background=self.background
        )

        logger.debug(f"{ToolName} -> model_type: {self.model_type}")

        if self.model_type == ModelType4Prompt.DEEPSEEK_R1.value:
            prompt = ChatPromptTemplate.from_messages(
                [
                    HumanMessage(
                        content="下面是你的任务，请务必牢记" + system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName}
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=system_prompt.render(),
                        additional_kwargs={_TOOL_MESSAGE_KEY: ToolName}
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
            data_view_list: [str],
            search_tool_cache_key: Optional[str] = "",
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        return asyncio.run(self._arun(
            query,
            data_view_list,
            search_tool_cache_key=search_tool_cache_key,
            run_manager=run_manager)
        )

    @async_construct_final_answer
    async def _arun(
            self,
            query: str,
            data_view_list: list[str] = [],
            search_tool_cache_key: str = "",
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        data_source_list = []
        sample_data_list = []

        if len(data_view_list) > 0:

            try:
                data_view_source = AFDataSource(
                    view_list=data_view_list,
                    token=self.token,
                    user_id=self.user_id,
                    redis_client=self.session.client,

                )

                logger.info("data_view_list,{} token, {}".format(data_view_list, self.token))
                # logger.info(data_view_source.service.base_url)
                data_view_metadata = data_view_source.get_meta_sample_data_v3(self.with_sample)
                # sample_data = data_view_source.get_data_view_sample()
                raw_data_source_list = data_view_metadata["detail"]

                if self.with_sample:
                    sample_data_list = data_view_metadata["sample"]
                
                # 转换数据格式
                data_source_list = self._transform_input_data(raw_data_source_list)

            except Exception as e:
                logger.error(f"获取数据视图元数据失败: {e}")

        chain = self._config_chain(
            input_data=data_source_list,
            input_sample=sample_data_list
        )
        result = []
        try:
            result = await chain.ainvoke({"input": query})
            
            # 补充未补全的字段（从输入中提取，不在fields_need_completion中的字段）
            result = self._add_accurate_fields(result, data_source_list)

        except Exception as e:
            logger.error(f"获取数据资源失败: {str(e)}")
            raise ToolFatalError(f"获取数据资源失败: {str(e)}")

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
            "max_tokens": 20000
        }
        llm_out_dict = params.get("llm", {})
        if llm_out_dict.get("name"):
            llm_dict["model_name"] = llm_out_dict.get("name")
        if llm_out_dict.get("max_tokens"):
            llm_dict["max_tokens"] = llm_out_dict.get("max_tokens")
        else:
            llm_dict["max_tokens"] = 20000

        logger.info("llm dict: {}".format(llm_dict))
        llm = CustomChatOpenAI(**llm_dict)


        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")

        config_dict = params.get("config", {})
        data_item_ids = config_dict.get('data_item_ids', "")
        if isinstance(data_item_ids, str):
            data_item_ids = data_item_ids.split(",")
            data_item_ids = [item.strip() for item in data_item_ids if item.strip() != ""]
        logger.info("data_item_ids {}".format(data_item_ids))
        data_model = DataModelService(
            headers={
                "x-user": auth_dict.get('user_id', ''),
                "x-account-id": auth_dict.get('user_id', ''),
                "x-account-type": auth_dict.get('account_type', 'user'),
                "Authorization": auth_dict.get('token', '')
            }
        )
        session = RedisHistorySession()

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=session,
            # session_type=config_dict.get("session_type", "redis"),
            # session_id=config_dict.get("session_id", ""),
            data_source_num_limit=config_dict.get("data_source_num_limit", -1),
            dimension_num_limit=config_dict.get("dimension_num_limit", -1),
            with_sample=config_dict.get("with_sample", False),
            knowledge_item_ids=data_item_ids,
            data_model=data_model,
        )

        query = params.get("query", "")
        search_tool_cache_key = params.get("search_tool_cache_key", "")
        data_view_list = params.get("data_view_list", [])

        res = await tool.ainvoke(input={
            "query": query,
            "data_view_list": data_view_list,
            "search_tool_cache_key": search_tool_cache_key
        })
        return res

    @classmethod
    async def as_async_api_cls_with_views(
            cls,
            params: dict
    ):
        """将工具转换为异步 API 类方法，直接接受视图数据"""
        llm_dict = {
            "model_name": settings.TOOL_LLM_MODEL_NAME,
            "openai_api_key": settings.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": settings.TOOL_LLM_OPENAI_API_BASE,
            "max_tokens": 20000
        }
        llm_dict.update(params.get("llm", {}))

        logger.info("llm dict: {}".format(llm_dict))
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
        views = params.get("views", [])

        if not views:
            raise ToolFatalError("views参数不能为空")

        # 将各种格式转换为新格式（view_id, view_tech_name等）
        transformed_views = tool._transform_to_new_format(views)
        
        # 使用转换后的视图数据
        chain = tool._config_chain(input_data=transformed_views)
        result = await chain.ainvoke({"input": query})
        
        # 补充未补全的字段（从输入中提取，不在fields_need_completion中的字段）
        result = tool._add_accurate_fields(result, transformed_views)
        
        # 结果已经是新格式，LLM直接返回新格式
        # 生成总结文字
        summary_text = tool._generate_summary(result)

        return {
            "result": result,
            "summary_text": summary_text,
            "result_cache_key": tool._result_cache_key
        }

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": "语义补全工具",
                "description": "语义补全工具是一款面向数据库开发、数据治理、数据分析场景的智能化辅助工具，核心功能是针对数据库中的库表名称、字段名称，自动完成语义化中文名补全，解决数据库对象 “英文缩写无释义”“命名不规范”“语义不清晰” 的痛点问题",
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
                                            },
                                            "data_item_ids": {
                                                "type": "string",
                                                "description": "知识条目id列表, 逗号隔开"
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
                                        "description": "库表id列表，需要语义补全的表ID列表"
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
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }
