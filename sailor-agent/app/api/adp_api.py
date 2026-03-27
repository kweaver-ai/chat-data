# -*- coding: utf-8 -*-
"""
ADP API 服务封装

用于调用ADP相关的API接口，包括知识网络相关的接口
"""

from typing import Optional, List, Dict, Any
from urllib.parse import quote

from app.api.base import API, HTTPMethod
from app.api.error import AfDataSourceError, DataViewError
from config import get_settings

settings = get_settings()


class ADPServices(object):
    """ADP服务封装类"""
    
    ontology_manager_url: str = settings.ADP_ONTOLOGY_MANAGER_HOST
    
    def __init__(self, base_url: str = ""):
        if settings.AF_DEBUG_IP or base_url:
            ip = settings.AF_DEBUG_IP or base_url
            self.ontology_manager_url = ip
        
        self._gen_api_url()
    
    def _gen_api_url(self):
        """生成API URL"""
        self.knowledge_networks_url = self.ontology_manager_url + "/api/ontology-manager/v1/knowledge-networks"
        self.knowledge_network_detail_url = (
            self.ontology_manager_url + "/api/ontology-manager/v1/knowledge-networks/{kn_id}"
        )
        self.knowledge_network_object_types_url = self.ontology_manager_url + "/api/ontology-manager/v1/knowledge-networks/{kn_id}/object-types"
    
    def get_knowledge_networks(
        self,
        headers: dict,
        offset: int = 0,
        limit: int = 50,
        direction: str = "desc",
        sort: str = "update_time",
        name_pattern: Optional[str] = None
    ) -> dict:
        """
        获取知识网络列表
        
        Args:
            headers: 请求头
            offset: 偏移量
            limit: 返回数量限制
            direction: 排序方向，asc或desc
            sort: 排序字段
            name_pattern: 名称模式（可选）
            
        Returns:
            知识网络列表，包含entries和total_count
        """
        url = self.knowledge_networks_url
        params = {
            "offset": offset,
            "limit": limit,
            "direction": direction,
            "sort": sort
        }
        
        if name_pattern:
            params["name_pattern"] = name_pattern
        
        # 添加固定的 header 参数
        request_headers = headers.copy() if headers else {}
        request_headers["x-business-domain"] = settings.ADP_BUSINESS_DOMAIN_ID
        
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=request_headers,
            params=params
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise DataViewError(e) from e
    
    def get_knowledge_network(
        self,
        kn_id: str,
        headers: dict,
        include_detail: bool = False,
        include_statistics: bool = True,
    ) -> dict:
        """
        获取单个知识网络信息（可选统计、详情）
        
        Args:
            kn_id: 知识网络 ID
            headers: 请求头
            include_detail: 是否包含 detail
            include_statistics: 是否包含 statistics（含 object_types_total 等）
        
        Returns:
            知识网络对象
        """
        kn_seg = quote(str(kn_id), safe="")
        url = self.knowledge_network_detail_url.format(kn_id=kn_seg)
        params = {
            "include_detail": "true" if include_detail else "false",
            "include_statistics": "true" if include_statistics else "false",
        }
        request_headers = headers.copy() if headers else {}
        request_headers["x-business-domain"] = settings.ADP_BUSINESS_DOMAIN_ID
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=request_headers,
            params=params,
        )
        try:
            res = api.call()
            return res if isinstance(res, dict) else {}
        except AfDataSourceError as e:
            raise DataViewError(e) from e
    
    def get_knowledge_network_object_types(
        self,
        kn_id: str,
        headers: dict,
        offset: int = 0,
        limit: int = 1000
    ) -> dict:
        """
        获取知识网络的对象类型列表
        
        Args:
            kn_id: 知识网络ID
            headers: 请求头
            offset: 偏移量
            limit: 返回数量限制
            
        Returns:
            对象类型列表，包含entries和total_count
        """
        kn_seg = quote(str(kn_id), safe="")
        url = self.knowledge_network_object_types_url.format(kn_id=kn_seg)
        params = {
            "offset": offset,
            "limit": limit
        }
        
        # 添加固定的 header 参数
        request_headers = headers.copy() if headers else {}
        request_headers["x-business-domain"] = settings.ADP_BUSINESS_DOMAIN_ID
        
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=request_headers,
            params=params
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise DataViewError(e) from e
