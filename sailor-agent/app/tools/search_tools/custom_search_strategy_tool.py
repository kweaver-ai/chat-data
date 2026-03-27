# -*- coding: utf-8 -*-
"""
用户自定义搜索策略工具

根据用户输入的问题，找出可能匹配的自定义搜索策略，然后将结果保存到缓存中，返回缓存的key
"""

import asyncio
import json
import traceback
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict

from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.errors import ToolFatalError
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from app.api.af_api import Services

from app.tools.base import (
    ToolName,
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from app.parsers.base import BaseJsonParser

_SETTINGS = get_settings()

# Redis缓存过期时间（24小时）
CACHE_EXPIRE_TIME = 60 * 60 * 24

# 工具名称
TOOL_NAME = "custom_search_strategy_tool"


class CustomSearchStrategyArgs(BaseModel):
    """工具入参模型"""
    query: str = Field(default="", description="用户输入的问题")
    rule_base_name: str = Field(default="自定义规则库", description="规则库的名称，默认为'自定义规则库'")


class CustomSearchStrategyTool(LLMTool):
    """
    用户自定义搜索策略工具
    
    功能：
    - 根据用户输入的问题，找出可能匹配的自定义搜索策略
    - 将优先表信息保存到缓存中，返回缓存的key，供下个工具使用
    """
    
    name: str = TOOL_NAME
    description: str = dedent(
        """
        用户自定义搜索策略工具，强制性意图工具。
        
        根据用户输入的问题，找出可能匹配的自定义搜索策略，然后将结果保存到缓存中，返回缓存的key，供下个工具使用。
        
        参数:
        - query: 用户输入的问题
        - rule_base_name: 规则库的名称，默认为"自定义规则库"
        
        该工具会：
        1. 根据规则库名称查询所有规则
        2. 使用大模型判断命中了哪个规则、优先表名称和数据源名称
        3. 如果没有命中规则，结束
        4. 如果命中规则，查找或创建优先表缓存，返回缓存的key
        """
    )
    
    args_schema: Type[BaseModel] = CustomSearchStrategyArgs
    
    # 认证与会话相关配置
    token: str = ""
    user_id: str = ""
    background: str = ""
    
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    
    # AF 服务封装
    service: Any = None
    headers: Dict[str, str] = {}
    base_url: str = ""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)
        
        # 初始化服务
        if self.service is None:
            self.service = Services(base_url=self.base_url)
        
        # 设置请求头，从 kwargs 或 self.token 获取 token
        token_value = kwargs.get("token") or self.token
        if token_value:
            self.headers = {
                "Authorization": token_value,
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}
    
    def _get_rule_base(self, rule_base_name: str) -> Optional[Dict[str, Any]]:
        """
        根据规则库名称查询规则库
        
        Args:
            rule_base_name: 规则库名称
            
        Returns:
            规则库信息，包含id和items（键值对），如果未找到则返回None
        """
        try:
            # 使用 Services 类的方法查询规则库列表
            rule_bases = self.service.get_data_dict_by_name_pattern(
                name_pattern=rule_base_name,
                headers=self.headers
            )
            
            if not rule_bases or len(rule_bases) == 0:
                logger.warning(f"未找到规则库: {rule_base_name}")
                return None
            
            rule_base = rule_bases[0]
            rule_base_id = rule_base.get("id")
            
            if not rule_base_id:
                logger.warning(f"规则库ID为空: {rule_base_name}")
                return None
            
            # 获取规则库的键值对（items）
            items_res = self.service.get_data_dict_items(
                dict_id=rule_base_id,
                headers=self.headers,
                limit=1000,
                offset=0
            )
            
            rule_base["items"] = items_res.get("entries", [])
            
            return rule_base
        except Exception as e:
            logger.error(f"查询规则库失败: {e}")
            logger.error(traceback.format_exc())
            raise ToolFatalError(f"查询规则库失败: {str(e)}")
    
    def _match_rule_with_llm(
        self,
        query: str,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用大模型判断命中了哪个规则、优先表名称和数据源名称
        
        Args:
            query: 用户输入的问题
            rules: 规则列表，每个规则包含id、key和value
            
        Returns:
            匹配结果，包含：
            - matched: 是否命中规则
            - rule_key: 命中的规则key
            - rule_id: 命中的规则id
            - priority_table_name: 优先表名称
            - datasource_name: 数据源名称（可选）
        """
        try:
            # 构建规则列表的字符串表示
            rules_text = "\n".join([
                f"规则key: {rule.get('key', '')}, 规则value: {rule.get('value', '')}"
                for rule in rules
            ])
            
            prompt_content = f"""你是一个规则匹配专家。根据用户的问题，判断是否命中了以下规则中的某一个。

规则列表：
{rules_text}

请仔细分析用户的问题，判断是否命中了某个规则。如果命中，请返回：
1. 命中的规则key
2. 优先表名称（从规则value中提取）
3. 数据源名称（如果有，从规则value中提取，如果没有则为空字符串）

请以JSON格式返回，格式如下：
{{
    "matched": true/false,
    "rule_key": "命中的规则key，如果没有命中则为空字符串",
    "priority_table_name": "优先表名称，如果没有命中则为空字符串",
    "datasource_name": "数据源名称，如果没有或无法提取则为空字符串"
}}

用户问题：{query}"""
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=prompt_content)
            ])
            
            chain = prompt | self.llm | BaseJsonParser()
            result = chain.invoke({"input": query})
            
            # 根据 rule_key 查找对应的 rule_id
            if result.get("matched") and result.get("rule_key"):
                rule_key = result.get("rule_key")
                for rule in rules:
                    if rule.get("key") == rule_key:
                        result["rule_id"] = rule.get("id", "")
                        break
                else:
                    result["rule_id"] = ""
            else:
                result["rule_id"] = ""
            
            return result
        except Exception as e:
            logger.error(f"大模型匹配规则失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "matched": False,
                "rule_key": "",
                "rule_id": "",
                "priority_table_name": "",
                "datasource_name": ""
            }
    
    def _get_priority_table_cache_key(self, rule_base_id: str, rule_id: str) -> str:
        """
        生成优先表缓存的key
        
        Args:
            rule_base_id: 规则库ID
            rule_id: 规则ID
            
        Returns:
            缓存key
        """
        return f"{TOOL_NAME}/rules/{rule_base_id}/{rule_id}"
    
    def _get_priority_table_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取优先表信息
        
        Args:
            cache_key: 缓存key
            
        Returns:
            优先表信息，如果缓存中没有则返回None
        """
        try:
            cached_data = self.session.client.get(cache_key)
            
            if cached_data:
                # 如果cached_data是bytes类型，需要先解码
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                
                data = json.loads(cached_data)
                # 验证数据合法性：检查是否有必要的字段
                if data.get("priority_table_id") and data.get("type") == "data_view":
                    return data
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"从缓存解析优先表信息失败，可能是数据格式错误: {e}")
            return None
        except Exception as e:
            logger.error(f"从缓存获取优先表信息失败: {e}")
            return None
    
    def _save_priority_table_to_cache(
        self,
        cache_key: str,
        priority_table_id: str,
        rule_base_name: str,
        rule_key: str,
        rule_value: str
    ):
        """
        将优先表信息保存到缓存
        
        Args:
            cache_key: 缓存key
            priority_table_id: 优先表ID
            rule_base_name: 规则库名称
            rule_key: 规则key
            rule_value: 规则value
        """
        try:
            cache_data = {
                "priority_table_id": priority_table_id,
                "type": "data_view",
                "rule_base_name": rule_base_name,
                "rule_key": rule_key,
                "rule_value": rule_value
            }
            
            self.session.client.setex(
                cache_key,
                CACHE_EXPIRE_TIME,
                json.dumps(cache_data, ensure_ascii=False)
            )
            logger.info(f"优先表信息已保存到缓存: {cache_key}")
        except Exception as e:
            logger.error(f"保存优先表信息到缓存失败: {e}")
            raise ToolFatalError(f"保存优先表信息到缓存失败: {str(e)}")
    
    def _init_priority_table(
        self,
        datasource_name: str,
        table_name: str
    ) -> Optional[str]:
        """
        初始化优先表，返回优先表的ID
        
        Args:
            datasource_name: 数据源名称（可选）
            table_name: 表的中文名称
            
        Returns:
            优先表ID，如果未找到则返回None
        """
        try:
            # 1. 根据数据源列表接口，遍历数据源结果，和传入数据源名称一样的就是命中的数据源
            datasource_id = None
            datasource_res = self.service.get_data_view_datasource_list(
                headers=self.headers,
                limit=1000
            )
            
            entries = datasource_res.get("entries", [])
            if datasource_name and datasource_name.strip():
                # 遍历查找匹配的数据源
                for entry in entries:
                    if entry.get("name") == datasource_name:
                        datasource_id = entry.get("id")
                        break
            else:
                # 如果没有指定数据源名称，取第一个
                if entries and len(entries) > 0:
                    datasource_id = entries[0].get("id")
            
            if not datasource_id:
                logger.warning("未找到数据源")
                return None
            
            # 2. 根据视图列表接口，传入数据源ID和表的中文名称，查询到的第一个表为优先表
            view_list = self.service.get_data_view_form_view_list(
                datasource_id=datasource_id,
                keyword=table_name,
                headers=self.headers,
                view_type="datasource",
                include_sub_department=True
            )
            
            if not view_list or len(view_list) == 0:
                logger.warning(f"未找到表: {table_name}")
                return None
            
            # 3. 将优先表的UUID拿出来
            priority_table_id = view_list[0].get("id")
            
            if not priority_table_id:
                logger.warning(f"优先表ID为空: {table_name}")
                return None
            
            return priority_table_id
        except Exception as e:
            logger.error(f"初始化优先表失败: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _get_or_create_priority_table_cache(
        self,
        rule_base_id: str,
        rule_base_name: str,
        rule_id: str,
        rule_key: str,
        rule_value: str,
        datasource_name: str,
        priority_table_name: str
    ) -> Optional[str]:
        """
        获取或创建优先表缓存，返回缓存key
        
        Args:
            rule_base_id: 规则库ID
            rule_base_name: 规则库名称
            rule_id: 规则ID
            rule_key: 规则key
            rule_value: 规则value
            datasource_name: 数据源名称
            priority_table_name: 优先表名称
            
        Returns:
            缓存key，如果失败则返回None
        """
        # 生成缓存key
        cache_key = self._get_priority_table_cache_key(rule_base_id, rule_id)
        
        # 1. 先尝试从缓存中获取
        cached_data = self._get_priority_table_from_cache(cache_key)
        if cached_data:
            logger.info(f"从缓存获取优先表信息: {cache_key}")
            return cache_key
        
        # 2. 如果缓存中没有，调用初始化策略
        logger.info(f"缓存中没有，初始化优先表: {priority_table_name}")
        priority_table_id = self._init_priority_table(datasource_name, priority_table_name)
        
        if not priority_table_id:
            logger.warning(f"无法获取优先表ID: {priority_table_name}")
            return None
        
        # 3. 保存到缓存
        self._save_priority_table_to_cache(
            cache_key=cache_key,
            priority_table_id=priority_table_id,
            rule_base_name=rule_base_name,
            rule_key=rule_key,
            rule_value=rule_value
        )
        
        return cache_key
    
    @construct_final_answer
    def _run(
        self,
        query: str,
        rule_base_name: str = "自定义规则库",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行自定义搜索策略工具
        
        Args:
            query: 用户输入的问题
            rule_base_name: 规则库名称，默认为"自定义规则库"
            run_manager: 回调管理器
            
        Returns:
            处理后的结果，包含缓存key
        """
        return asyncio.run(self._arun(
            query=query,
            rule_base_name=rule_base_name,
            run_manager=run_manager
        ))
    
    @async_construct_final_answer
    async def _arun(
        self,
        query: str,
        rule_base_name: str = "自定义规则库",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        执行自定义搜索策略工具
        
        Args:
            query: 用户输入的问题
            rule_base_name: 规则库名称，默认为"自定义规则库"
            
        Returns:
            处理后的结果，包含缓存key
        """
        try:
            # 验证必需参数
            if not query or not query.strip():
                logger.warning("query参数为空")
                return {
                    "result": "query参数不能为空",
                    "matched": False
                }
            
            # 1. 根据规则库的名称，查询规则库的所有键值对
            logger.info(f"查询规则库: {rule_base_name}")
            rule_base = self._get_rule_base(rule_base_name)
            
            if not rule_base or not rule_base.get("items"):
                logger.info("规则库为空或没有规则，结束")
                return {
                    "result": "规则库为空或没有规则",
                    "matched": False
                }
            
            rules = rule_base.get("items", [])
            rule_base_id = rule_base.get("id")
            logger.info(f"获取到 {len(rules)} 条规则")
            
            # 2. 将所有的规则组成数组，结合用户输入，让大模型判断命中了哪个规则
            logger.info("使用大模型匹配规则")
            match_result = self._match_rule_with_llm(query, rules)
            
            if not match_result.get("matched"):
                logger.info("未命中任何规则，结束")
                return {
                    "result": "未命中任何规则",
                    "matched": False
                }
            
            rule_key = match_result.get("rule_key", "").strip()
            rule_id = match_result.get("rule_id", "").strip()
            priority_table_name = match_result.get("priority_table_name", "").strip()
            datasource_name = match_result.get("datasource_name", "").strip()
            
            # 验证必要字段
            if not rule_key or not priority_table_name or not rule_id:
                logger.warning(f"大模型返回的数据不完整: rule_key={rule_key}, rule_id={rule_id}, priority_table_name={priority_table_name}")
                # 尝试获取 rule_value
                rule_value = ""
                for rule in rules:
                    if rule.get("key") == rule_key:
                        rule_value = rule.get("value", "")
                        break
                return {
                    "result": "大模型返回的数据不完整，无法继续处理",
                    "matched": True,
                    "rule_key": rule_key,
                    "priority_table_name": priority_table_name,
                    "rule_value": rule_value
                }
            
            logger.info(f"命中规则: rule_key={rule_key}, rule_id={rule_id}, 优先表: {priority_table_name}, 数据源: {datasource_name}")
            
            # 3. 如果没有命中规则，结束（已在上面处理）
            # 4. 如果命中了规则，根据规则和规则名称找到优先表缓存
            # 找到对应的规则value
            rule_value = ""
            for rule in rules:
                if rule.get("key") == rule_key:
                    rule_value = rule.get("value", "")
                    break
            
            if not rule_value:
                logger.warning(f"未找到规则value，rule_key: {rule_key}")
                return {
                    "result": f"未找到规则value，rule_key: {rule_key}",
                    "matched": True,
                    "rule_key": rule_key,
                    "priority_table_name": priority_table_name,
                    "rule_value": ""
                }
            
            # 5. 获取或创建优先表缓存
            cache_key = self._get_or_create_priority_table_cache(
                rule_base_id=rule_base_id,
                rule_base_name=rule_base_name,
                rule_id=rule_id,
                rule_key=rule_key,
                rule_value=rule_value,
                datasource_name=datasource_name,
                priority_table_name=priority_table_name
            )
            
            if not cache_key:
                logger.warning(f"无法获取或创建优先表缓存")
                return {
                    "result": f"无法获取或创建优先表缓存: {priority_table_name}",
                    "matched": True,
                    "rule_key": rule_key,
                    "priority_table_name": priority_table_name,
                    "rule_value": rule_value
                }
            
            logger.info(f"成功获取或创建优先表缓存: {cache_key}")
            
            # 从缓存中获取 rule_value（如果缓存中有的话）
            cached_data = self._get_priority_table_from_cache(cache_key)
            rule_value_from_cache = rule_value  # 默认使用已有的 rule_value
            if cached_data and cached_data.get("rule_value"):
                rule_value_from_cache = cached_data.get("rule_value")
            
            return {
                "result": f"成功匹配规则并创建优先表缓存",
                "matched": True,
                "rule_key": rule_key,
                "priority_table_name": priority_table_name,
                "cache_key": cache_key,
                "rule_value": rule_value_from_cache
            }
            
        except Exception as e:
            logger.error(f"执行自定义搜索策略工具失败: {e}")
            logger.error(traceback.format_exc())
            raise ToolFatalError(f"执行自定义搜索策略工具失败: {str(e)}")
    
    @classmethod
    def from_config(cls, params: Dict[str, Any]):
        """
        从配置创建工具实例
        
        Args:
            params: 配置参数字典，包含：
                - llm: LLM配置
                - auth: 认证配置（token, user, password, user_id, auth_url）
                - config: 其他配置（background, session_type, base_url）
        """
        # LLM 配置
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict.update(params.get("llm", {}))
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
                logger.error(f"[CustomSearchStrategyTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e
        
        config_dict = params.get("config", {})
        
        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
            base_url=config_dict.get("base_url", ""),
        )
        
        return tool
    
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
            "session_type": "redis"        // 可选，会话类型
          },
          "query": "用户输入的问题",        // 必填
          "rule_base_name": "自定义规则库"  // 可选，默认为"自定义规则库"
        }
        """
        # LLM 配置
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict.update(params.get("llm", {}))
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
                logger.error(f"[CustomSearchStrategyTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e
        
        config_dict = params.get("config", {})
        
        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
            base_url=config_dict.get("base_url", ""),
        )
        
        query = params.get("query", "")
        rule_base_name = params.get("rule_base_name", "自定义规则库")
        
        res = await tool.ainvoke(input={
            "query": query,
            "rule_base_name": rule_base_name
        })
        return res
    
    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API"""
        return {
            "post": {
                "summary": "custom_search_strategy",
                "description": "用户自定义搜索策略工具，强制性意图工具。根据用户输入的问题，找出可能匹配的自定义搜索策略，然后将结果保存到缓存中，返回缓存的key",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数（可选）"
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数",
                                        "properties": {
                                            "auth_url": {"type": "string", "description": "认证服务URL（可选）"},
                                            "user": {"type": "string", "description": "用户名（可选）"},
                                            "password": {"type": "string", "description": "密码（可选）"},
                                            "token": {"type": "string", "description": "认证令牌，如提供则无需用户名和密码（推荐）"},
                                            "user_id": {"type": "string", "description": "用户ID（可选）"}
                                        }
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "base_url": {
                                                "type": "string",
                                                "description": "AF 服务基础 URL（可选，覆盖默认服务地址）"
                                            },
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型",
                                                "enum": ["in_memory", "redis"],
                                                "default": "redis"
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息（可选）"
                                            }
                                        }
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "用户输入的问题（必填）"
                                    },
                                    "rule_base_name": {
                                        "type": "string",
                                        "description": "规则库的名称，默认为'自定义规则库'（可选）",
                                        "default": "自定义规则库"
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
                                    "type": "object",
                                    "properties": {
                                        "result": {"type": "string"},
                                        "matched": {"type": "boolean"},
                                        "rule_key": {"type": "string"},
                                        "priority_table_name": {"type": "string"},
                                        "cache_key": {"type": "string"},
                                        "rule_value": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }