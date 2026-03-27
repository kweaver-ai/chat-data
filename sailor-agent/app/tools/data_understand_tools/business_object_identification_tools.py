# -*- coding: utf-8 -*-
import asyncio
import re
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict
from app.errors import ToolFatalError
from app.parsers.base import BaseJsonParser
from app.session import BaseChatHistorySession, CreateSession
from langchain_core.pydantic_v1 import BaseModel, Field
from app.utils.llm import CustomChatOpenAI
from app.depandencies.af_dataview import AFDataSource
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.model_types import ModelType4Prompt
from app.session.redis_session import RedisHistorySession
from app.api.data_model import DataModelService
from app.tools.base import api_tool_decorator
from app.tools.base import (
    LLMTool,
    _TOOL_MESSAGE_KEY,
    construct_final_answer,
    async_construct_final_answer
)
from config import get_settings
from app.logs.logger import logger
from .prompts.business_object_identification import BusinessObjectIdentificationPrompt

from config import settings


_SETTINGS = get_settings()


class ArgsModel(BaseModel):
    query: str = Field(default="", description="用户的查询需求，用于理解业务对象识别上下文")
    data_view_list: list[str] = Field(default=[], description="库表id列表，需要识别业务对象的表ID列表")


class BusinessObjectIdentificationTool(LLMTool):
    name: str = "business_object_identification"
    description: str = dedent(
        """业务对象识别工具，用于从库表列表中识别业务对象（Business Object）。
        
业务对象是业务领域中的核心实体，具有明确的业务含义和生命周期，通常对应现实世界中的业务概念。

该工具能够：
- **识别业务对象**：判断表是否代表业务对象，以及对象的类型和名称
- **分析对象属性**：识别主键、关键字段、生命周期字段、关联字段等
- **分析业务特征**：判断是否为主数据、交易数据、参考数据等
- **统计对象分布**：统计业务对象的类型分布和分类分布

常见业务对象类型包括：
- 人员相关：客户、用户、员工、供应商等
- 产品相关：产品、商品、服务、物料等
- 交易相关：订单、合同、发票、支付等
- 组织相关：组织、部门、岗位、项目等
- 财务相关：账户、科目、预算、成本等
- 库存相关：仓库、库存、入库、出库等

参数:
- query: 用户的查询需求，用于理解业务对象识别上下文
- data_view_list: 库表id列表，需要识别业务对象的表ID列表

工具会返回每个表的业务对象识别结果，包括对象类型、对象属性、业务特征等详细信息。
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
    knowledge_item_ids: list[str] = []  # 知识条目id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        """
        根据大模型生成的结果，组装生成总结文字
        
        Args:
            result: 大模型返回的结果，包含 tables 和 business_objects_summary
            
        Returns:
            总结文字
        """
        if not result or not isinstance(result, dict):
            return "未获取到业务对象识别结果。"
        
        # 检查是否有错误
        if "error" in result:
            return f"业务对象识别失败：{result.get('error', '未知错误')}。"
        
        summary = result.get("business_objects_summary", {})
        tables = result.get("tables", [])
        
        if not summary and not tables:
            return "未获取到业务对象识别结果。"
        
        # 提取统计信息
        total_tables = summary.get("total_tables", len(tables))
        business_object_count = summary.get("business_object_count", 0)
        non_business_object_count = summary.get("non_business_object_count", 0)
        object_type_dist = summary.get("object_type_distribution", {})
        object_category_dist = summary.get("object_category_distribution", {})
        
        # 构建总结文字
        summary_parts = []
        
        # 总体统计
        summary_parts.append(f"本次业务对象识别共涉及 {total_tables} 个表。\n")
        
        # 业务对象统计
        if business_object_count > 0:
            summary_parts.append(f"识别出 {business_object_count} 个业务对象，")
            if non_business_object_count > 0:
                summary_parts.append(f"{non_business_object_count} 个非业务对象。\n")
            else:
                summary_parts.append("所有表均为业务对象。\n")
            
            # 对象类型分布
            if object_type_dist:
                summary_parts.append("\n业务对象类型分布：\n")
                for obj_type, count in sorted(object_type_dist.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {obj_type}：{count} 个\n")
            
            # 对象分类分布
            if object_category_dist:
                summary_parts.append("\n业务对象分类分布：\n")
                for category, count in sorted(object_category_dist.items(), key=lambda x: x[1], reverse=True):
                    summary_parts.append(f"  • {category}：{count} 个\n")
        else:
            summary_parts.append("未识别出业务对象，所有表均为非业务对象。\n")
        
        # 各表详情
        if tables:
            summary_parts.append("\n各表识别详情：\n")
            for table in tables:
                table_name = table.get("table_name", "未知表")
                is_business_object = table.get("is_business_object", False)
                
                if is_business_object:
                    business_object = table.get("business_object", {})
                    object_type = business_object.get("object_type", "未知类型")
                    object_name_cn = business_object.get("object_name_cn", "")
                    object_category = business_object.get("object_category", "")
                    
                    info_parts = [f"{table_name}：识别为业务对象"]
                    if object_name_cn:
                        info_parts.append(f"「{object_name_cn}」")
                    if object_type:
                        info_parts.append(f"（类型：{object_type}）")
                    if object_category:
                        info_parts.append(f"（分类：{object_category}）")
                    
                    summary_parts.append("  • " + "".join(info_parts) + "\n")
                else:
                    summary_parts.append(f"  • {table_name}：非业务对象\n")
        
        return "".join(summary_parts).strip()

    def _config_chain(
        self,
        input_data: dict = [],
        input_sample: list = []
    ):
        # self.refresh_result_cache_key()
        if self.knowledge_item_ids:
            knowledge_item_ids = ",".join(self.knowledge_item_ids)

            knowledge_items = self.data_model.get_knowledge_items_by_ids(knowledge_item_ids)

            knowledge_item_data_list = []
            for knowledge_item in knowledge_items:
                for knowledge_item_data in knowledge_item["items"]:
                    knowledge_item_data_list.append(knowledge_item_data["value"])

            if knowledge_item_data_list:
                self.background += "\n" + "\n".join(knowledge_item_data_list)
        # 样例数据
        if self.with_sample:
            if len(input_sample):
                sample_info = []
                for sample in input_sample:
                    sample_info.append(f"逻辑视图{sample['table_name']}的样例数据为：{sample['sample']}")
                if sample_info:
                    self.background += "\n" + "\n".join(sample_info)

        system_prompt = BusinessObjectIdentificationPrompt(
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
                "error": "请提供需要识别业务对象的库表ID列表",
                "tables": [],
                "business_objects_summary": {
                    "total_tables": 0,
                    "business_object_count": 0,
                    "non_business_object_count": 0,
                    "object_type_distribution": {},
                    "object_category_distribution": {}
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
                    "business_objects_summary": {
                        "total_tables": 0,
                        "business_object_count": 0,
                        "non_business_object_count": 0,
                        "object_type_distribution": {},
                        "object_category_distribution": {}
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
            input_sample=sample_data_list,
        )
        
        result = {}
        try:
            result = await chain.ainvoke({"input": query})
            
            # 补充未关联到业务对象属性的字段（从输入中提取，不在attributes中的字段）
            # 需要将data_source_list转换为新格式
            transformed_views = self._transform_input_data_to_new_format(data_source_list)
            
            # 确保所有属性名称都是中文名
            result = self._ensure_chinese_attr_name(result, transformed_views)
            
            # 补充未关联字段
            result = self._add_non_attribute_fields(result, transformed_views)

        except Exception as e:
            logger.error(f"业务对象识别失败: {str(e)}")
            raise ToolFatalError(f"业务对象识别失败: {str(e)}")

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

        # llm_dict.update(params.get("llm", {}))
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

    def _transform_input_data(self, views: List[Dict]) -> List[Dict]:
        """
        将新格式的视图数据转换为工具内部使用的旧格式（用于LLM prompt）
        
        Args:
            views: 新格式的视图数据列表，每个视图包含：
                - view_id: 视图ID
                - view_tech_name: 视图技术名称
                - view_business_name: 视图业务名称
                - desc: 视图描述
                - fields: 字段列表（包含field_id, field_tech_name等）
        
        Returns:
            旧格式的数据列表，每个表包含：
                - table_id: 表ID
                - table_name: 表名
                - table_business_name: 表业务名称
                - table_description: 表描述
                - fields: 字段列表（包含field_id, field_name等）
        """
        old_format_list = []
        
        for view in views:
            # 兼容多种格式
            view_id = (view.get("view_id") or 
                      view.get("table_id") or "")
            
            view_tech_name = (view.get("view_tech_name") or 
                            view.get("view_technical_name") or 
                            view.get("table_name") or "")
            
            view_business_name = (view.get("view_business_name") or 
                                view.get("table_business_name") or "")
            
            desc = (view.get("desc") or 
                   view.get("view_desc") or 
                   view.get("table_description") or "")
            
            old_format_item = {
                "table_id": view_id,
                "table_name": view_tech_name,
                "table_business_name": view_business_name,
                "table_description": desc,
                "fields": []
            }
            
            # 转换字段数据
            fields = (view.get("fields") or 
                     view.get("view_fields") or [])
            
            for field in fields:
                field_id = (field.get("field_id") or 
                           field.get("view_field_id") or "")
                
                field_tech_name = (field.get("field_tech_name") or 
                                 field.get("field_technical_name") or 
                                 field.get("view_field_technical_name") or 
                                 field.get("field_name") or "")
                
                field_business_name = (field.get("field_business_name") or 
                                     field.get("view_field_business_name") or "")
                
                field_type = (field.get("field_type") or 
                            field.get("view_field_type") or "")
                
                field_desc = (field.get("field_desc") or 
                            field.get("field_description") or 
                            field.get("view_field_desc") or "")
                
                old_format_field = {
                    "field_id": field_id,
                    "field_name": field_tech_name,
                    "field_business_name": field_business_name,
                    "field_type": field_type,
                    "field_description": field_desc
                }
                old_format_item["fields"].append(old_format_field)
            
            old_format_list.append(old_format_item)
        
        return old_format_list

    @staticmethod
    def _transform_input_data_to_new_format(old_format_list: List[Dict]) -> List[Dict]:
        """
        将旧格式（table_*）转换为新格式（view_*）
        
        Args:
            old_format_list: 旧格式的数据列表，每个表包含：
                - table_id: 表ID
                - table_name: 表名
                - table_business_name: 表业务名称
                - table_description: 表描述
                - fields: 字段列表（包含field_id, field_name等）
        
        Returns:
            新格式的数据列表，每个视图包含：
                - view_id: 视图ID
                - view_tech_name: 视图技术名称
                - view_business_name: 视图业务名称
                - desc: 视图描述
                - fields: 字段列表（包含field_id, field_tech_name等）
        """
        new_format_list = []
        
        for old_item in old_format_list:
            new_item = {
                "view_id": old_item.get("table_id", ""),
                "view_tech_name": old_item.get("table_name", ""),
                "view_business_name": old_item.get("table_business_name", ""),
                "desc": old_item.get("table_description", ""),
                "fields": []
            }
            
            # 转换字段数据
            old_fields = old_item.get("fields", [])
            for old_field in old_fields:
                new_field = {
                    "field_id": old_field.get("field_id", ""),
                    "field_tech_name": old_field.get("field_name", ""),
                    "field_business_name": old_field.get("field_business_name", ""),
                    "field_type": old_field.get("field_type", ""),
                    "field_desc": old_field.get("field_description", "")
                }
                new_item["fields"].append(new_field)
            
            new_format_list.append(new_item)
        
        return new_format_list

    @staticmethod
    def _contains_chinese(text: str) -> bool:
        """检查字符串是否包含中文字符"""
        if not text:
            return False
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    @staticmethod
    def _ensure_chinese_attr_name(result: Dict[str, Any], input_views: List[Dict]) -> Dict[str, Any]:
        """
        确保所有属性名称（attr_name）都是中文名
        
        Args:
            result: LLM返回的结果
            input_views: 输入的视图数据列表，用于获取字段的业务名称
            
        Returns:
            修正后的结果
        """
        if not result or not isinstance(result, dict):
            return result
        
        # 创建字段映射（按view_id和field_id）
        field_map = {}
        for input_view in input_views:
            view_id = (input_view.get("view_id") or 
                      input_view.get("table_id") or "")
            if not view_id:
                continue
            
            fields = (input_view.get("fields") or 
                     input_view.get("view_fields") or [])
            
            for field in fields:
                field_id = (field.get("field_id") or 
                           field.get("view_field_id") or "")
                if field_id:
                    field_business_name = (field.get("field_business_name") or 
                                         field.get("view_field_business_name") or "")
                    field_tech_name = (field.get("field_tech_name") or 
                                      field.get("field_technical_name") or 
                                      field.get("view_field_technical_name") or 
                                      field.get("field_name") or "")
                    
                    key = f"{view_id}:{field_id}"
                    field_map[key] = {
                        "field_business_name": field_business_name,
                        "field_tech_name": field_tech_name,
                    }
        
        # 兼容新格式（views）和旧格式（tables）
        views_or_tables = result.get("views") or result.get("tables", [])
        
        # 修正每个视图的属性名称
        for view_or_table in views_or_tables:
            view_id = (view_or_table.get("view_id") or 
                      view_or_table.get("table_id") or "")
            if not view_id:
                continue
            
            object_attributes = view_or_table.get("object_attributes", {})
            attributes = object_attributes.get("attributes", [])
            
            # 修正attributes中的attr_name
            for attr in attributes:
                attr_name = attr.get("attr_name", "")
                field_id = attr.get("field_id", "")
                
                # 如果属性名称不是中文，则使用字段的业务名称
                if attr_name and not BusinessObjectIdentificationTool._contains_chinese(attr_name):
                    key = f"{view_id}:{field_id}"
                    field_info = field_map.get(key, {})
                    field_business_name = field_info.get("field_business_name", "")
                    
                    if field_business_name:
                        # 使用字段的业务名称
                        attr["attr_name"] = field_business_name
                        logger.info(f"属性名称 '{attr_name}' 不是中文，已替换为业务名称 '{field_business_name}'")
                    else:
                        # 如果没有业务名称，记录警告
                        logger.warning(f"属性名称 '{attr_name}' 不是中文，且字段 {field_id} 没有业务名称")
        
        return result
    
    @staticmethod
    def _add_non_attribute_fields(result: Dict[str, Any], input_views: List[Dict]) -> Dict[str, Any]:
        """
        在结果中添加未关联到业务对象属性的字段（从输入中提取，不在attributes中的字段）
        
        Args:
            result: LLM返回的结果，格式为 {"views": [...], "summary": {...}}
            input_views: 输入的视图数据列表，格式为 [{"view_id": ..., "fields": [...]}, ...]
            
        Returns:
            补充了未关联字段的结果
        """
        if not result or not isinstance(result, dict):
            return result
        
        # 兼容新格式（views）和旧格式（tables）
        views_or_tables = result.get("views") or result.get("tables", [])
        
        # 创建输入视图的映射（按view_id）
        input_views_map = {}
        for input_view in input_views:
            view_id = (input_view.get("view_id") or 
                      input_view.get("table_id") or "")
            if view_id:
                input_views_map[view_id] = input_view
        
        # 为每个视图补充未关联的字段
        for view_or_table in views_or_tables:
            view_id = (view_or_table.get("view_id") or 
                      view_or_table.get("table_id") or "")
            input_view = input_views_map.get(view_id)
            
            if not input_view:
                continue
            
            # 获取object_attributes
            object_attributes = view_or_table.get("object_attributes", {})
            
            # 收集所有已关联的字段ID（从attributes、primary_key、key_fields、relationship_fields中）
            associated_field_ids = set()
            
            # 从attributes中收集
            attributes = object_attributes.get("attributes", [])
            for attr in attributes:
                field_id = attr.get("field_id")
                if field_id:
                    associated_field_ids.add(field_id)
            
            # 从primary_key中收集
            primary_key = object_attributes.get("primary_key", {})
            if primary_key and primary_key.get("field_id"):
                associated_field_ids.add(primary_key.get("field_id"))
            
            # 从key_fields中收集
            key_fields = object_attributes.get("key_fields", [])
            for field in key_fields:
                field_id = field.get("field_id")
                if field_id:
                    associated_field_ids.add(field_id)
            
            # 从relationship_fields中收集
            relationship_fields = object_attributes.get("relationship_fields", [])
            for field in relationship_fields:
                field_id = field.get("field_id")
                if field_id:
                    associated_field_ids.add(field_id)
            
            # 从输入中提取所有字段
            input_fields = (input_view.get("fields") or 
                          input_view.get("view_fields") or [])
            
            # 找出未关联的字段（不在已关联字段列表中的字段）
            non_attribute_fields = []
            for input_field in input_fields:
                field_id = (input_field.get("field_id") or 
                           input_field.get("view_field_id") or "")
                
                # 如果字段不在已关联的字段列表中，则添加到未关联字段列表
                if field_id and field_id not in associated_field_ids:
                    non_attribute_field = {
                        "field_id": field_id,
                        "field_tech_name": (input_field.get("field_tech_name") or 
                                          input_field.get("field_technical_name") or 
                                          input_field.get("view_field_technical_name") or 
                                          input_field.get("field_name") or ""),
                        "field_business_name": (input_field.get("field_business_name") or 
                                              input_field.get("view_field_business_name") or ""),
                        "field_type": (input_field.get("field_type") or 
                                     input_field.get("view_field_type") or ""),
                        "field_desc": (input_field.get("field_desc") or 
                                     input_field.get("field_description") or 
                                     input_field.get("view_field_desc") or ""),
                    }
                    # 如果存在field_role，添加到字段中
                    if "field_role" in input_field:
                        non_attribute_field["field_role"] = input_field.get("field_role")
                    non_attribute_fields.append(non_attribute_field)
            
            # 将未关联的字段添加到object_attributes中
            if non_attribute_fields:
                object_attributes["non_attribute_fields"] = non_attribute_fields
        
        return result

    @classmethod
    async def as_async_api_cls_with_views(
        cls,
        params: dict
    ):
        """将工具转换为异步 API 类方法，直接接受视图数据（新格式）"""
        llm_dict = {
            "model_name": settings.TOOL_LLM_MODEL_NAME,
            "openai_api_key": settings.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": settings.TOOL_LLM_OPENAI_API_BASE,
            "max_tokens": 20000
        }
        llm_dict.update(params.get("llm", {}))
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

        # 将新格式转换为旧格式（供 prompt 使用）
        # old_format_views = tool._transform_input_data(views)
        
        # 使用转换后的数据配置 chain
        chain = tool._config_chain(input_data=views)
        result = await chain.ainvoke({"input": query})
        
        # 确保所有属性名称都是中文名
        result = tool._ensure_chinese_attr_name(result, views)
        
        # 补充未关联到业务对象属性的字段（从输入中提取，不在attributes中的字段）
        result = tool._add_non_attribute_fields(result, views)
        
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
                "summary": "业务对象识别工具",
                "description": "从库表列表中识别业务对象，分析表的业务含义和对象特征",
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
                                        "description": "用户的查询需求，用于理解业务对象识别上下文"
                                    },
                                    "data_view_list": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "库表id列表，需要识别业务对象的表ID列表"
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
                                            "description": "业务对象识别结果"
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
