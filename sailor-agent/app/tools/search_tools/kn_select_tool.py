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

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.errors import ToolFatalError
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession
from app.api.adp_api import ADPServices

from app.tools.base import (
    ToolName,
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from app.parsers.base import BaseJsonParser

_SETTINGS = get_settings()

# Redis缓存过期时间（12小时）
CACHE_EXPIRE_TIME = 60 * 60 * 12

# 工具名称
TOOL_NAME = "kn_select_tool"

# 缓存key前缀
KN_NETWORKS_CACHE_KEY = f"{TOOL_NAME}/knowledge_networks"
KN_OBJECT_TYPES_CACHE_KEY_PREFIX = f"{TOOL_NAME}/object_types"
KN_SUMMARY_CACHE_KEY_PREFIX = f"{TOOL_NAME}/kn_summary"


class TableInfo(BaseModel):
    """表信息模型"""
    id: str = Field(description="视图的id")
    uuid: str = Field(description="视图的uuid")
    business_name: str = Field(description="视图的业务名称")
    technical_name: str = Field(description="视图的技术名称")


class KnSelectArgs(BaseModel):
    """工具入参模型"""
    query: str = Field(default="", description="用户输入问题")
    tables: List[TableInfo] = Field(default_factory=list, description="表信息列表")
    kn_ids: List[Any] = Field(
        default_factory=list,
        description="候选知识网络ID列表；非空时不请求知识网络列表接口，仅在这些ID中做表/问题匹配",
    )
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
        - kn_ids: 候选知识网络ID列表（可选）；非空时不调用知识网络列表接口，仅在这些ID中匹配
        
        匹配逻辑：
        1. 如果输入了表，优先使用表匹配；如果没有表则进行问题匹配；都没有则报参数错误
        2. 若 kn_ids 非空，不拉取全量知识网络列表，仅将上述 ID 作为候选；否则拉取列表（带缓存）
        3. 调用知识网络详情接口（含 statistics）合并 name/tags/comment；过滤 statistics.object_types_total=0 的网络（无统计或拉取失败时不据此过滤）
        4. 通过知识网络对象接口拉取对象类型（limit=1000）；若 entries 中无任何 module_type=object_type 的项则排除该网络
        5. 表匹配：视图 id 与对象类型条目中 data_source.id 比较（仅考虑 object_type 条目），匹配率≥50% 取匹配数最多的一个
        6. 问题匹配：将名称、tags、comment 及对象类摘要（name、属性的 display_name/type）送入大模型；可返回多个均相关的网络
        7. 返回值为列表，元素为 kn_id、kn_name（kn_name 优先使用详情/列表中的名称）
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
    
    @staticmethod
    def _normalize_kn_ids(raw: Any) -> List[str]:
        """去空白、转字符串、保序去重后的知识网络 ID 列表。"""
        if raw is None:
            return []
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        seen: set = set()
        for x in raw:
            if x is None or x == "":
                continue
            s = str(x).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out
    
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
    
    @staticmethod
    def _entries_include_object_type(entries: List[Dict[str, Any]]) -> bool:
        """对象类型接口的 entries 中至少有一条 module_type=object_type 才算有效知识网络。"""
        return any(e.get("module_type") == "object_type" for e in (entries or []))
    
    @staticmethod
    def _format_object_types_for_llm(entries: List[Dict[str, Any]]) -> str:
        """对象类匹配信息：name，以及各 data_properties 的 display_name、type。"""
        parts: List[str] = []
        for e in entries or []:
            if e.get("module_type") != "object_type":
                continue
            name = e.get("name", "") or ""
            dps = e.get("data_properties") or []
            prop_strs: List[str] = []
            for dp in dps:
                if not isinstance(dp, dict):
                    continue
                display_name = dp.get("display_name") or dp.get("name") or ""
                ptype = dp.get("type", "") or ""
                prop_strs.append(f"{display_name}({ptype})")
            prop_blob = ", ".join(prop_strs) if prop_strs else ""
            parts.append(f"{name}[{prop_blob}]" if prop_blob else name)
        return "；".join(parts) if parts else ""
    
    def _batch_get_knowledge_network_object_types(
        self, kn_ids: List[str], force_refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """按知识网络 id 批量获取对象类型：已缓存的直读，未命中再请求接口并写入缓存。"""
        result: Dict[str, Dict[str, Any]] = {}
        for kn_id in kn_ids:
            if not kn_id:
                continue
            result[kn_id] = self._get_knowledge_network_object_types(kn_id, force_refresh=force_refresh)
        return result
    
    def _get_kn_summary_from_cache(self, kn_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not hasattr(self.session, "client"):
                return None
            cache_key = f"{KN_SUMMARY_CACHE_KEY_PREFIX}/{kn_id}"
            raw = self.session.client.get(cache_key)
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            logger.warning(f"从缓存解析知识网络摘要 {kn_id} 失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"从缓存读取知识网络摘要 {kn_id} 失败: {e}")
            return None
    
    def _save_kn_summary_to_cache(self, kn_id: str, data: Dict[str, Any]):
        try:
            if not data:
                return
            if not hasattr(self.session, "client"):
                return
            cache_key = f"{KN_SUMMARY_CACHE_KEY_PREFIX}/{kn_id}"
            self.session.client.setex(
                cache_key,
                CACHE_EXPIRE_TIME,
                json.dumps(data, ensure_ascii=False),
            )
        except Exception as e:
            logger.warning(f"写入知识网络摘要缓存 {kn_id} 失败: {e}")
    
    def _delete_kn_summary_from_cache(self, kn_id: str):
        try:
            if not hasattr(self.session, "client"):
                return
            self.session.client.delete(f"{KN_SUMMARY_CACHE_KEY_PREFIX}/{kn_id}")
        except Exception as e:
            logger.warning(f"删除知识网络摘要缓存 {kn_id} 失败: {e}")
    
    def _get_knowledge_network_summary(self, kn_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """单网详情（含 statistics），带 Redis 缓存。"""
        if force_refresh:
            self._delete_kn_summary_from_cache(kn_id)
        cached = self._get_kn_summary_from_cache(kn_id)
        # 空 {} 视为未缓存，避免误缓存导致永久跳过详情接口
        if cached is not None and cached:
            return cached
        try:
            res = self.service.get_knowledge_network(
                kn_id=kn_id,
                headers=self.headers,
                include_detail=False,
                include_statistics=True,
            )
            if res:
                self._save_kn_summary_to_cache(kn_id, res)
            return res if isinstance(res, dict) else {}
        except Exception as e:
            logger.warning(f"获取知识网络详情 {kn_id} 失败: {e}")
            return {}
    
    @staticmethod
    def _merge_detail_into_network(network: Dict[str, Any], detail: Dict[str, Any]) -> None:
        if detail.get("name") is not None:
            network["name"] = detail.get("name") or ""
        if "tags" in detail:
            network["tags"] = detail.get("tags") or []
        if detail.get("comment") is not None:
            network["comment"] = detail.get("comment") or ""
        if detail.get("statistics") is not None:
            network["statistics"] = detail["statistics"]
    
    @staticmethod
    def _object_types_total_value(network: Dict[str, Any]) -> Optional[int]:
        stats = network.get("statistics")
        if not isinstance(stats, dict):
            return None
        v = stats.get("object_types_total")
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    
    def _enrich_networks_filter_statistics(
        self, networks: List[Dict[str, Any]], force_refresh: bool
    ) -> List[Dict[str, Any]]:
        """合并详情中的名称与 statistics，过滤 object_types_total=0 的网络。"""
        kept: List[Dict[str, Any]] = []
        for network in networks:
            kid = network.get("id")
            if not kid:
                continue
            kid_s = str(kid)
            detail = self._get_knowledge_network_summary(kid_s, force_refresh=force_refresh)
            if detail:
                self._merge_detail_into_network(network, detail)
            total = self._object_types_total_value(network)
            if total is not None and total == 0:
                logger.info(f"知识网络 {kid_s} statistics.object_types_total=0，已过滤")
                continue
            kept.append(network)
        return kept
    
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
        networks: List[Dict[str, Any]],
        object_types_map: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        通过表匹配知识网络
        
        Args:
            tables: 表信息列表
            networks: 知识网络列表（已保证对象类型接口含 object_type 条目）
            object_types_map: kn_id -> 对象类型接口完整响应
            
        Returns:
            匹配的知识网络，如果没有匹配则返回None
        """
        if not tables:
            return None
        
        # 与接口 data_source.id 对齐为字符串，避免 str/int 不一致导致匹配失败
        table_ids = {str(table.id) for table in tables if table.id is not None and str(table.id)}
        logger.info(f"开始表匹配，表ID列表: {table_ids}")
        
        # 统计每个网络的匹配数
        network_match_count = {}
        
        for network in networks:
            kn_id = network.get("id")
            if not kn_id:
                continue
            
            try:
                object_types_res = object_types_map.get(str(kn_id)) or {}
                entries = object_types_res.get("entries", [])
                if not self._entries_include_object_type(entries):
                    continue
                
                # 统计匹配的表数量（仅 module_type=object_type 的条目参与 data_source 匹配）
                match_count = 0
                for entry in entries:
                    if entry.get("module_type") != "object_type":
                        continue
                    data_source = entry.get("data_source", {})
                    if data_source.get("type") == "data_view":
                        data_source_id = data_source.get("id")
                        if data_source_id is not None and str(data_source_id) in table_ids:
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
                logger.warning(f"表匹配处理知识网络 {kn_id} 失败: {e}")
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
        networks: List[Dict[str, Any]],
        object_types_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        通过问题匹配知识网络（可返回多个均相关的网络）。
        
        Args:
            query: 用户问题
            networks: 知识网络列表
            object_types_map: kn_id -> 对象类型接口响应（用于对象类匹配信息）
            
        Returns:
            匹配结果列表，元素为 {"kn_id", "kn_name"}
        """
        if not query or not query.strip():
            return []
        
        if not networks:
            return []
        
        try:
            network_by_id: Dict[str, Dict[str, Any]] = {}
            for n in networks:
                nid = n.get("id")
                if nid is None or nid == "":
                    continue
                network_by_id[str(nid)] = n
            lines: List[str] = []
            for network in networks:
                kn_id = network.get("id", "")
                entries = (object_types_map.get(str(kn_id)) or {}).get("entries", [])
                obj_summary = self._format_object_types_for_llm(entries)
                tags = network.get("tags", []) or []
                tag_str = ", ".join(str(t) for t in tags)
                lines.append(
                    f"ID: {kn_id}, 名称: {network.get('name', '')}, 标签: {tag_str}, "
                    f"描述: {network.get('comment', '')}, 对象类信息: {obj_summary}"
                )
            
            networks_text = "\n".join(lines)
            
            prompt_content = f"""你是一个知识网络匹配专家。根据用户的问题，从以下知识网络列表中选择匹配的知识网络。

知识网络列表：
{networks_text}

请仔细分析用户的问题。**优先只返回一个**最匹配的知识网络；若有多个与用户问题**同样高度相关**的网络，可返回多个，但必须都与问题相关。

请以JSON格式返回，格式如下：
{{
    "matched": true/false,
    "matches": [
        {{"kn_id": "知识网络ID", "kn_name": "知识网络名称"}}
    ]
}}
无匹配时 matched 为 false，matches 为空数组。

用户问题：{query}"""
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=prompt_content)
            ])
            
            chain = prompt | self.llm | BaseJsonParser()
            result = chain.invoke({"input": query})
            if not isinstance(result, dict):
                logger.warning(f"大模型返回非对象类型，已忽略: {type(result)}")
                return []
            
            matches = result.get("matches")
            if matches is None and result.get("matched"):
                legacy_id = result.get("kn_id") or ""
                legacy_name = result.get("kn_name") or ""
                if legacy_id:
                    matches = [{"kn_id": legacy_id, "kn_name": legacy_name}]
            if not isinstance(matches, list):
                matches = []
            
            out: List[Dict[str, str]] = []
            seen = set()
            for m in matches:
                if not isinstance(m, dict):
                    continue
                raw_kid = m.get("kn_id")
                if raw_kid is None or raw_kid == "":
                    continue
                kid = str(raw_kid).strip()
                if not kid or kid not in network_by_id or kid in seen:
                    continue
                seen.add(kid)
                nw = network_by_id[kid]
                canon = nw.get("name")
                canon_s = str(canon).strip() if canon is not None else ""
                llm_name = m.get("kn_name")
                llm_s = str(llm_name).strip() if llm_name is not None else ""
                name = canon_s or llm_s
                out.append({"kn_id": kid, "kn_name": name})
            
            if out:
                logger.info(f"问题匹配到知识网络: {[x['kn_id'] for x in out]}")
            else:
                logger.info("问题未匹配到任何知识网络")
            return out
            
        except Exception as e:
            logger.error(f"大模型匹配知识网络失败: {e}")
            logger.error(traceback.format_exc())
            return []
    
    @construct_final_answer
    def _run(
        self,
        query: str = "",
        tables: List[Dict[str, Any]] = None,
        kn_ids: List[Any] = None,
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
            知识网络列表，每项含 kn_id、kn_name；无匹配时返回含空 kn_id 的一项
        """
        return asyncio.run(self._arun(
            query=query,
            tables=tables,
            kn_ids=kn_ids if kn_ids is not None else [],
            force_refresh_cache=force_refresh_cache,
            run_manager=run_manager
        ))
    
    @async_construct_final_answer
    async def _arun(
        self,
        query: str = "",
        tables: List[Dict[str, Any]] = None,
        kn_ids: List[Any] = None,
        force_refresh_cache: bool = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        执行知识网络选择工具
        
        Args:
            query: 用户输入问题
            tables: 表信息列表
            kn_ids: 候选知识网络ID；非空时不请求知识网络列表接口
            force_refresh_cache: 是否强制刷新缓存
            
        Returns:
            知识网络列表 [{kn_id, kn_name}, ...]；无匹配时返回 [{"kn_id":"","kn_name":""}]
        """
        try:
            empty_result: List[Dict[str, str]] = [{"kn_id": "", "kn_name": ""}]
            query_stripped = (query or "").strip()
            candidate_kn_ids = self._normalize_kn_ids(kn_ids if kn_ids is not None else [])
            
            # 验证参数（query 仅空白视为未提供）
            if not query_stripped and (not tables or len(tables) == 0):
                logger.warning("query和tables参数不能同时为空")
                return empty_result
            
            # 转换tables格式
            table_list = []
            if tables:
                for table in tables:
                    if isinstance(table, dict):
                        table_list.append(TableInfo(**table))
                    else:
                        table_list.append(table)
            
            # 1. 候选知识网络：指定 kn_ids 时不调用列表接口，否则拉全量列表（带缓存）
            if candidate_kn_ids:
                logger.info(
                    f"使用入参 kn_ids 指定 {len(candidate_kn_ids)} 个候选知识网络，跳过知识网络列表接口"
                )
                all_networks = [
                    {"id": kid, "name": "", "tags": [], "comment": ""}
                    for kid in candidate_kn_ids
                ]
            else:
                logger.info("获取知识网络列表")
                all_networks = self._get_knowledge_networks(force_refresh=force_refresh_cache)
            
            if not all_networks:
                logger.info("没有可用的知识网络候选")
                return empty_result
            
            # 2. 单网详情（含 statistics）：合并 name 等，过滤 object_types_total=0
            all_networks = self._enrich_networks_filter_statistics(
                all_networks, force_refresh=force_refresh_cache
            )
            if not all_networks:
                logger.info("按 statistics.object_types_total 过滤后无可用知识网络")
                return empty_result
            
            # 3. 批量加载对象类型（limit=1000，缓存未命中再请求），并排除无 object_type 条目的网络
            ids_for_object_types = [str(n["id"]) for n in all_networks if n.get("id")]
            object_types_map = self._batch_get_knowledge_network_object_types(
                ids_for_object_types, force_refresh=force_refresh_cache
            )
            eligible_networks = [
                n for n in all_networks
                if n.get("id")
                and self._entries_include_object_type(
                    (object_types_map.get(str(n["id"])) or {}).get("entries", [])
                )
            ]
            if not eligible_networks:
                logger.info("对象类型接口中无 module_type=object_type 的知识网络已全部过滤")
                return empty_result
            
            # 4. 匹配逻辑
            matched_items: List[Dict[str, str]] = []
            
            if table_list:
                logger.info("使用表匹配模式")
                matched_network = self._match_by_tables(
                    table_list, eligible_networks, object_types_map
                )
                if matched_network:
                    mid = matched_network.get("id", "")
                    mname = matched_network.get("name")
                    matched_items = [
                        {
                            "kn_id": str(mid) if mid is not None else "",
                            "kn_name": str(mname).strip() if mname is not None else "",
                        }
                    ]
            
            if not matched_items and query_stripped:
                logger.info("使用问题匹配模式")
                matched_items = self._match_by_query(
                    query_stripped, eligible_networks, object_types_map
                )
            
            if matched_items:
                return matched_items
            
            logger.info("未找到匹配的知识网络")
            return empty_result
            
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
          ],
          "kn_ids": ["kn_id_1", "kn_id_2"]   // 可选；非空时不请求知识网络列表，仅在这些 ID 中匹配
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
        kn_ids = params.get("kn_ids", [])
        force_refresh_cache = params.get("force_refresh_cache", False)
        
        res = await tool.ainvoke(input={
            "query": query,
            "tables": tables,
            "kn_ids": kn_ids if kn_ids is not None else [],
            "force_refresh_cache": force_refresh_cache
        })
        return res
    
    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API"""
        return {
            "post": {
                "summary": "kn_select",
                "description": "知识网络选择工具。根据用户问题或表在候选知识网络中匹配；可提供 kn_ids 限定候选（不调用列表接口），否则拉取全量列表",
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
                                    "kn_ids": {
                                        "type": "array",
                                        "description": "候选知识网络ID列表（可选）。非空时不请求知识网络列表接口，仅在这些ID中做表/问题匹配",
                                        "items": {
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "integer"}
                                            ],
                                            "description": "知识网络 ID（字符串或与 JSON 数字兼容的整型）"
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
                        "description": "Successful operation；HTTP 层经 api_tool_decorator/make_json_response 包装为 { result }",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "result": {
                                            "type": "array",
                                            "description": "工具业务输出：匹配到的知识网络列表；无匹配时为含空 kn_id 的单元素数组",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "kn_id": {
                                                        "type": "string",
                                                        "description": "知识网络ID"
                                                    },
                                                    "kn_name": {
                                                        "type": "string",
                                                        "description": "知识网络名称（仅 kn_ids 模式可能为空）"
                                                    }
                                                },
                                                "required": ["kn_id", "kn_name"]
                                            }
                                        }
                                    },
                                    "required": ["result"]
                                }
                            }
                        }
                    }
                }
            }
        }

    @classmethod
    def get_openai_tool_schema(cls) -> Dict[str, Any]:
        """
        OpenAI Chat Completions / Responses API 的 tools[] 单项（function）定义。
        仅包含 LangChain 工具入参（KnSelectArgs），不含 HTTP 专有的 llm、auth、config。
        """
        parameters = dict(cls.args_schema.schema())
        # List[Any] 在 JSON Schema 中常生成空 items，此处显式声明 kn_ids 元素为字符串
        props = dict(parameters.get("properties") or {})
        kn_field = cls.args_schema.__fields__.get("kn_ids")
        kn_desc = kn_field.field_info.description if kn_field else ""
        props["kn_ids"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": kn_desc,
        }
        parameters["properties"] = props
        parameters.setdefault("type", "object")
        return {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": dedent(cls.description or "").strip(),
                "parameters": parameters,
            },
        }
