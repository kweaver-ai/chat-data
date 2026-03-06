# -*- coding: utf-8 -*-
"""
知识网络选择工具

根据用户的问题或表，在知识网络列表中找到合适的知识网络，以便后续的问数功能
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

from data_retrieval.logs.logger import logger
from data_retrieval.sessions import BaseChatHistorySession, CreateSession
from data_retrieval.errors import ToolFatalError
from data_retrieval.utils.llm import CustomChatOpenAI
from data_retrieval.settings import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from app.api.adp_api import ADPServices

from data_retrieval.tools.base import (
    ToolName,
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from data_retrieval.parsers.base import BaseJsonParser

_SETTINGS = get_settings()

# Redis缓存过期时间（12小时）
CACHE_EXPIRE_TIME = 60 * 60 * 12

# 工具名称
TOOL_NAME = "kn_select_tool"

# 缓存key前缀
KN_NETWORKS_CACHE_KEY = f"{TOOL_NAME}/knowledge_networks"
KN_OBJECT_TYPES_CACHE_KEY_PREFIX = f"{TOOL_NAME}/object_types"


class TableInfo(BaseModel):
    """表信息模型"""
    id: str = Field(description="视图的id")
    uuid: str = Field(description="视图的uuid")
    business_name: str = Field(description="视图的业务名称")
    technical_name: str = Field(description="视图的技术名称")


class KnSelectArgs(BaseModel):
    """工具入参模型"""
    query: str = Field(default="", description="用户输入问题")
    tables: List[TableInfo] = Field(default=[], description="表信息列表")
    force_refresh_cache: bool = Field(default=False, description="是否强制刷新缓存")


class KnSelectTool(LLMTool):
    """
    知识网络选择工具
    
    功能：
    - 根据用户的问题或表，在知识网络列表中找到合适的知识网络
    - 支持表匹配和问题匹配两种方式
    """
    
    name: str = TOOL_NAME
    description: str = dedent(
        """
        知识网络选择工具。
        
        根据用户的问题或表，在知识网络列表中找到合适的知识网络，以便后续的问数功能。
        
        参数:
        - query: 用户输入问题（可选，如果提供了tables则优先使用表匹配）
        - tables: 表信息列表（可选，包含id、uuid、business_name、technical_name）
        
        匹配逻辑：
        1. 如果输入了表，优先使用表匹配；如果没有表则进行问题匹配；都没有则报参数错误
        2. 过滤掉对象类数量为0的网络
        3. 表匹配使用id和知识网络对象里面的data_source.id比较，相等则匹配上
        4. 如果是表匹配，有50%以上的表匹配就算匹配上了，选择匹配最多的网络返回，只要一个即可
        5. 问题匹配使用知识网络的名称、tags、comment等和用户问题输入大模型，让大模型得出匹配的知识网络
        6. 有结果返回知识网络ID和名称，没结果，返回空ID字符串
        """
    )
    
    args_schema: Type[BaseModel] = KnSelectArgs
    
    # 认证与会话相关配置
    token: str = ""
    user_id: str = ""
    background: str = ""
    
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    
    # ADP 服务封装
    service: Any = None
    headers: Dict[str, str] = {}
    base_url: str = ""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)
        
        # 初始化服务
        if self.service is None:
            self.service = ADPServices(base_url=self.base_url)
        
        # 设置请求头，从 kwargs 或 self.token 获取 token
        token_value = kwargs.get("token") or self.token
        if token_value:
            self.headers = {
                "Authorization": token_value,
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}
    
    def _get_knowledge_networks_from_cache(self) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存中获取知识网络列表
        
        Returns:
            知识网络列表，如果缓存中没有则返回None
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                return None
            
            # 使用 Redis Hash 获取所有知识网络
            cached_data = self.session.client.hgetall(KN_NETWORKS_CACHE_KEY)
            
            if cached_data:
                networks = []
                for kn_id, kn_json in cached_data.items():
                    try:
                        # 解码 bytes 类型
                        if isinstance(kn_json, bytes):
                            kn_json = kn_json.decode('utf-8')
                        if isinstance(kn_id, bytes):
                            kn_id = kn_id.decode('utf-8')
                        
                        network = json.loads(kn_json)
                        networks.append(network)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"从缓存解析知识网络 {kn_id} 失败: {e}")
                        continue
                
                if networks:
                    logger.info(f"从缓存获取到 {len(networks)} 个知识网络")
                    return networks
            
            return None
        except Exception as e:
            logger.warning(f"从缓存获取知识网络列表失败: {e}")
            return None
    
    def _save_knowledge_networks_to_cache(self, networks: List[Dict[str, Any]]):
        """
        将知识网络列表保存到缓存
        
        Args:
            networks: 知识网络列表
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                logger.warning("session 没有 client 属性，跳过缓存保存")
                return
            
            # 使用 Redis Hash 保存知识网络，每个知识网络以 id 作为 field
            pipe = self.session.client.pipeline()
            
            for network in networks:
                kn_id = network.get("id")
                if kn_id:
                    pipe.hset(
                        KN_NETWORKS_CACHE_KEY,
                        kn_id,
                        json.dumps(network, ensure_ascii=False)
                    )
            
            # 设置整个 Hash 的过期时间
            pipe.expire(KN_NETWORKS_CACHE_KEY, CACHE_EXPIRE_TIME)
            pipe.execute()
            
            logger.info(f"知识网络列表已保存到缓存: {len(networks)} 个网络")
        except Exception as e:
            logger.error(f"保存知识网络列表到缓存失败: {e}")
            # 不抛出异常，允许继续执行
    
    def _delete_knowledge_network_from_cache(self, kn_id: str):
        """
        从缓存中删除指定的知识网络
        
        Args:
            kn_id: 知识网络ID
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                return
            
            self.session.client.hdel(KN_NETWORKS_CACHE_KEY, kn_id)
            logger.info(f"已从缓存删除知识网络: {kn_id}")
        except Exception as e:
            logger.warning(f"从缓存删除知识网络失败: {e}")
    
    def _clear_knowledge_networks_cache(self):
        """
        清空知识网络列表缓存
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                return
            
            self.session.client.delete(KN_NETWORKS_CACHE_KEY)
            logger.info("已清空知识网络列表缓存")
        except Exception as e:
            logger.warning(f"清空知识网络列表缓存失败: {e}")
    
    def _get_knowledge_networks(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取所有知识网络列表（带缓存）
        
        Args:
            force_refresh: 是否强制刷新缓存
        
        Returns:
            知识网络列表
        """
        try:
            # 如果强制刷新，先清空缓存
            if force_refresh:
                self._clear_knowledge_networks_cache()
            
            # 先尝试从缓存获取
            cached_networks = self._get_knowledge_networks_from_cache()
            if cached_networks is not None:
                return cached_networks
            
            # 缓存中没有，从接口获取
            logger.info("缓存中没有知识网络列表，从接口获取")
            all_networks = []
            offset = 0
            limit = 50
            
            while True:
                res = self.service.get_knowledge_networks(
                    headers=self.headers,
                    offset=offset,
                    limit=limit,
                    direction="desc",
                    sort="update_time"
                )
                
                entries = res.get("entries", [])
                if not entries:
                    break
                
                all_networks.extend(entries)
                
                total_count = res.get("total_count", 0)
                if offset + limit >= total_count:
                    break
                
                offset += limit
            
            logger.info(f"从接口获取到 {len(all_networks)} 个知识网络")
            
            # 保存到缓存
            if all_networks:
                self._save_knowledge_networks_to_cache(all_networks)
            
            return all_networks
        except Exception as e:
            logger.error(f"获取知识网络列表失败: {e}")
            logger.error(traceback.format_exc())
            raise ToolFatalError(f"获取知识网络列表失败: {str(e)}")
    
    def _filter_networks_by_object_count(self, networks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤掉对象类数量为0的网络
        
        Args:
            networks: 知识网络列表
            
        Returns:
            过滤后的知识网络列表
        """
        filtered = []
        for network in networks:
            try:
                # 解析detail字段获取object_types_count
                detail_str = network.get("detail", "{}")
                if isinstance(detail_str, str):
                    detail = json.loads(detail_str)
                else:
                    detail = detail_str
                
                network_info = detail.get("network_info", {})
                object_types_count = network_info.get("object_types_count", 0)
                
                if object_types_count > 0:
                    filtered.append(network)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"解析知识网络detail失败，跳过: {e}")
                continue
        
        logger.info(f"过滤后剩余 {len(filtered)} 个知识网络（对象类数量>0）")
        return filtered
    
    def _get_knowledge_network_object_types_from_cache(self, kn_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取知识网络的对象类型列表
        
        Args:
            kn_id: 知识网络ID
            
        Returns:
            对象类型列表，如果缓存中没有则返回None
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                return None
            
            cache_key = f"{KN_OBJECT_TYPES_CACHE_KEY_PREFIX}/{kn_id}"
            cached_data = self.session.client.get(cache_key)
            
            if cached_data:
                # 解码 bytes 类型
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                
                data = json.loads(cached_data)
                logger.info(f"从缓存获取知识网络 {kn_id} 的对象类型")
                return data
            
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"从缓存解析知识网络 {kn_id} 的对象类型失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"从缓存获取知识网络 {kn_id} 的对象类型失败: {e}")
            return None
    
    def _save_knowledge_network_object_types_to_cache(self, kn_id: str, object_types: Dict[str, Any]):
        """
        将知识网络的对象类型列表保存到缓存
        
        Args:
            kn_id: 知识网络ID
            object_types: 对象类型列表
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                logger.warning("session 没有 client 属性，跳过缓存保存")
                return
            
            cache_key = f"{KN_OBJECT_TYPES_CACHE_KEY_PREFIX}/{kn_id}"
            self.session.client.setex(
                cache_key,
                CACHE_EXPIRE_TIME,
                json.dumps(object_types, ensure_ascii=False)
            )
            logger.info(f"知识网络 {kn_id} 的对象类型已保存到缓存")
        except Exception as e:
            logger.warning(f"保存知识网络 {kn_id} 的对象类型到缓存失败: {e}")
    
    def _delete_knowledge_network_object_types_from_cache(self, kn_id: str):
        """
        从缓存中删除指定知识网络的对象类型
        
        Args:
            kn_id: 知识网络ID
        """
        try:
            # 检查 session 是否有 client 属性（Redis session 才有）
            if not hasattr(self.session, 'client'):
                return
            
            cache_key = f"{KN_OBJECT_TYPES_CACHE_KEY_PREFIX}/{kn_id}"
            self.session.client.delete(cache_key)
            logger.info(f"已从缓存删除知识网络 {kn_id} 的对象类型")
        except Exception as e:
            logger.warning(f"从缓存删除知识网络 {kn_id} 的对象类型失败: {e}")
    
    def _get_knowledge_network_object_types(self, kn_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取知识网络的对象类型列表（带缓存）
        
        Args:
            kn_id: 知识网络ID
            force_refresh: 是否强制刷新缓存
            
        Returns:
            对象类型列表
        """
        try:
            # 如果强制刷新，先删除缓存
            if force_refresh:
                self._delete_knowledge_network_object_types_from_cache(kn_id)
            
            # 先尝试从缓存获取
            cached_data = self._get_knowledge_network_object_types_from_cache(kn_id)
            if cached_data is not None:
                return cached_data
            
            # 缓存中没有，从接口获取
            logger.info(f"缓存中没有知识网络 {kn_id} 的对象类型，从接口获取")
            object_types_res = self.service.get_knowledge_network_object_types(
                kn_id=kn_id,
                headers=self.headers,
                offset=0,
                limit=1000
            )
            
            # 保存到缓存
            if object_types_res:
                self._save_knowledge_network_object_types_to_cache(kn_id, object_types_res)
            
            # 确保返回字典类型，即使接口返回 None
            return object_types_res if object_types_res else {}
        except Exception as e:
            logger.error(f"获取知识网络 {kn_id} 的对象类型失败: {e}")
            # 返回空字典而不是抛出异常，避免影响表匹配逻辑
            return {}
    
    def _match_by_tables(
        self,
        tables: List[TableInfo],
        networks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        通过表匹配知识网络
        
        Args:
            tables: 表信息列表
            networks: 知识网络列表
            
        Returns:
            匹配的知识网络，如果没有匹配则返回None
        """
        if not tables:
            return None
        
        table_ids = {table.id for table in tables}
        logger.info(f"开始表匹配，表ID列表: {table_ids}")
        
        # 统计每个网络的匹配数
        network_match_count = {}
        
        for network in networks:
            kn_id = network.get("id")
            if not kn_id:
                continue
            
            try:
                # 获取知识网络的对象类型（带缓存）
                object_types_res = self._get_knowledge_network_object_types(kn_id)
                
                entries = object_types_res.get("entries", [])
                if not entries:
                    continue
                
                # 统计匹配的表数量
                match_count = 0
                for entry in entries:
                    data_source = entry.get("data_source", {})
                    if data_source.get("type") == "data_view":
                        data_source_id = data_source.get("id")
                        if data_source_id and data_source_id in table_ids:
                            match_count += 1
                
                # 计算匹配率：匹配的表数量 / 输入的表数量
                if match_count > 0:
                    match_rate = match_count / len(tables)
                    if match_rate >= 0.5:  # 50%以上的表匹配
                        network_match_count[kn_id] = {
                            "network": network,
                            "match_count": match_count,
                            "match_rate": match_rate
                        }
                        logger.info(f"知识网络 {network.get('name')} 匹配 {match_count}/{len(tables)} 个表，匹配率: {match_rate:.2%}")
            
            except Exception as e:
                logger.warning(f"获取知识网络 {kn_id} 的对象类型失败: {e}")
                continue
        
        if not network_match_count:
            logger.info("没有找到匹配的知识网络")
            return None
        
        # 选择匹配最多的网络
        best_match = max(network_match_count.values(), key=lambda x: x["match_count"])
        logger.info(f"选择匹配最多的知识网络: {best_match['network'].get('name')}")
        return best_match["network"]
    
    def _match_by_query(
        self,
        query: str,
        networks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        通过问题匹配知识网络
        
        Args:
            query: 用户问题
            networks: 知识网络列表
            
        Returns:
            匹配的知识网络，如果没有匹配则返回None
        """
        if not query or not query.strip():
            return None
        
        if not networks:
            return None
        
        try:
            # 构建知识网络信息列表
            networks_info = []
            for network in networks:
                kn_info = {
                    "id": network.get("id", ""),
                    "name": network.get("name", ""),
                    "tags": network.get("tags", []),
                    "comment": network.get("comment", "")
                }
                networks_info.append(kn_info)
            
            networks_text = "\n".join([
                f"ID: {kn.get('id')}, 名称: {kn.get('name')}, 标签: {', '.join(kn.get('tags', []))}, 描述: {kn.get('comment', '')}"
                for kn in networks_info
            ])
            
            prompt_content = f"""你是一个知识网络匹配专家。根据用户的问题，从以下知识网络列表中选择最匹配的知识网络。

知识网络列表：
{networks_text}

请仔细分析用户的问题，判断哪个知识网络最匹配。如果匹配，请返回知识网络的ID和名称。

请以JSON格式返回，格式如下：
{{
    "matched": true/false,
    "kn_id": "知识网络ID，如果没有匹配则为空字符串",
    "kn_name": "知识网络名称，如果没有匹配则为空字符串"
}}

用户问题：{query}"""
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=prompt_content)
            ])
            
            chain = prompt | self.llm | BaseJsonParser()
            result = chain.invoke({"input": query})
            
            if result.get("matched") and result.get("kn_id"):
                kn_id = result.get("kn_id")
                # 查找对应的网络
                for network in networks:
                    if network.get("id") == kn_id:
                        logger.info(f"问题匹配到知识网络: {network.get('name')}")
                        return network
            
            logger.info("问题未匹配到任何知识网络")
            return None
            
        except Exception as e:
            logger.error(f"大模型匹配知识网络失败: {e}")
            logger.error(traceback.format_exc())
            return None
    
    @construct_final_answer
    def _run(
        self,
        query: str = "",
        tables: List[Dict[str, Any]] = None,
        force_refresh_cache: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行知识网络选择工具
        
        Args:
            query: 用户输入问题
            tables: 表信息列表
            force_refresh_cache: 是否强制刷新缓存
            run_manager: 回调管理器
            
        Returns:
            处理后的结果，包含知识网络ID和名称
        """
        return asyncio.run(self._arun(
            query=query,
            tables=tables,
            force_refresh_cache=force_refresh_cache,
            run_manager=run_manager
        ))
    
    @async_construct_final_answer
    async def _arun(
        self,
        query: str = "",
        tables: List[Dict[str, Any]] = None,
        force_refresh_cache: bool = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        执行知识网络选择工具
        
        Args:
            query: 用户输入问题
            tables: 表信息列表
            force_refresh_cache: 是否强制刷新缓存
            
        Returns:
            处理后的结果，包含知识网络ID和名称
        """
        try:
            # 验证参数
            if not query and (not tables or len(tables) == 0):
                logger.warning("query和tables参数不能同时为空")
                return {
                    "kn_id": "",
                    "kn_name": ""
                }
            
            # 转换tables格式
            table_list = []
            if tables:
                for table in tables:
                    if isinstance(table, dict):
                        table_list.append(TableInfo(**table))
                    else:
                        table_list.append(table)
            
            # 1. 获取所有知识网络（带缓存）
            logger.info("获取知识网络列表")
            all_networks = self._get_knowledge_networks(force_refresh=force_refresh_cache)
            
            if not all_networks:
                logger.info("没有找到任何知识网络")
                return {
                    "kn_id": "",
                    "kn_name": ""
                }
            
            # 2. 过滤掉对象类数量为0的网络
            filtered_networks = self._filter_networks_by_object_count(all_networks)
            
            if not filtered_networks:
                logger.info("过滤后没有剩余的知识网络")
                return {
                    "kn_id": "",
                    "kn_name": ""
                }
            
            # 3. 匹配逻辑
            matched_network = None
            
            # 优先表匹配
            if table_list:
                logger.info("使用表匹配模式")
                matched_network = self._match_by_tables(table_list, filtered_networks)
            
            # 如果没有表匹配结果，使用问题匹配
            if not matched_network and query:
                logger.info("使用问题匹配模式")
                matched_network = self._match_by_query(query, filtered_networks)
            
            # 4. 返回结果
            if matched_network:
                return {
                    "kn_id": matched_network.get("id", ""),
                    "kn_name": matched_network.get("name", "")
                }
            else:
                logger.info("未找到匹配的知识网络")
                return {
                    "kn_id": "",
                    "kn_name": ""
                }
            
        except Exception as e:
            logger.error(f"执行知识网络选择工具失败: {e}")
            logger.error(traceback.format_exc())
            raise ToolFatalError(f"执行知识网络选择工具失败: {str(e)}")
    
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
                logger.error(f"[KnSelectTool] get token error: {e}")
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
          "query": "用户输入的问题",        // 可选
          "tables": [                     // 可选
            {
              "id": "视图的id",
              "uuid": "视图的uuid",
              "business_name": "视图的业务名称",
              "technical_name": "视图的技术名称"
            }
          ]
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
                logger.error(f"[KnSelectTool] get token error: {e}")
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
        tables = params.get("tables", [])
        force_refresh_cache = params.get("force_refresh_cache", False)
        
        res = await tool.ainvoke(input={
            "query": query,
            "tables": tables,
            "force_refresh_cache": force_refresh_cache
        })
        return res
    
    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API"""
        return {
            "post": {
                "summary": "kn_select",
                "description": "知识网络选择工具。根据用户的问题或表，在知识网络列表中找到合适的知识网络",
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
                                        "description": "用户输入的问题（可选，如果提供了tables则优先使用表匹配）"
                                    },
                                    "tables": {
                                        "type": "array",
                                        "description": "表信息列表（可选）",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string", "description": "视图的id"},
                                                "uuid": {"type": "string", "description": "视图的uuid"},
                                                "business_name": {"type": "string", "description": "视图的业务名称"},
                                                "technical_name": {"type": "string", "description": "视图的技术名称"}
                                            },
                                            "required": ["id", "uuid", "business_name", "technical_name"]
                                        }
                                    },
                                    "force_refresh_cache": {
                                        "type": "boolean",
                                        "description": "是否强制刷新缓存（可选，默认为false）",
                                        "default": False
                                    }
                                }
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
                                        "kn_id": {"type": "string", "description": "知识网络ID"},
                                        "kn_name": {"type": "string", "description": "知识网络名称"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
