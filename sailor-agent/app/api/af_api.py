import json

from app.api.error import (
    Text2SQLError, VirEngineError, FrontendColumnError, AfDataSourceError, FrontendSampleError,
    IndicatorDescError, IndicatorDetailError, IndicatorQueryError, DataViewError
)
from app.api.base import API, HTTPMethod
from typing import Any, List

import urllib3
import os

from config import get_settings

urllib3.disable_warnings()

CREATE_SCHEMA_TEMPLATE = """CREATE TABLE {source}.{schema}.{title}
(
                            {
    middle}
                            ); \
                         """

RESP_TEMPLATE = """根据<strong>"{table}"</strong><i slice_idx=0>{index}</i>，检索到如下数据："""

settings = get_settings()


class Services(object):
    vir_engine_url: str = settings.VIR_ENGINE_URL
    data_view_url: str = settings.DATA_VIEW_URL
    indicator_management_url: str = settings.INDICATOR_MANAGEMENT_URL
    auth_service_url: str = settings.AUTH_SERVICE_URL
    catalog_url: str = settings.CATALOG_URL
    data_model_url: str = settings.DATA_MODEL_URL

    def __init__(self, base_url: str = ""):
        if settings.AF_DEBUG_IP or base_url:
            ip = settings.AF_DEBUG_IP or base_url
            self.vir_engine_url: str = ip
            self.data_view_url: str = ip
            self.indicator_management_url: str = ip
            self.auth_service_url: str = ip
            self.catalog_url: str = ip

        self._gen_api_url()

    def _gen_api_url(self):
        self.vir_engine_fetch_url = self.vir_engine_url + \
                                    "/api/virtual_engine_service/v1/fetch"
        self.vir_engine_preview_url = self.vir_engine_url + \
                                      "/api/virtual_engine_service/v1/preview/{catalog}/{schema}/{table}"
        self.view_fields_url = self.data_view_url + \
                               "/api/data-view/v1/form-view/{view_id}"
        self.view_details_url = self.data_view_url + \
                                "/api/data-view/v1/form-view/{view_id}/details"
        self.view_data_preview_url = self.data_view_url + \
                                     "/api/data-view/v1/form-view/data-preview"
        self.view_white_policy_sql = self.data_view_url + \
                                     "/api/data-view/v1/white-list-policy/{view_id}/where-sql"
        self.view_field_info = self.data_view_url + \
                               "/api/data-view/v1/desensitization/{view_id}/filed-info"
        self.indicator_details_url = self.indicator_management_url + \
                                     "/api/indicator-management/v1/indicator/{indicator_id}"
        self.indicator_query_url = self.indicator_management_url + \
                                   "/api/indicator-management/v1/indicator/query"
        self.auth_service_details_url = self.auth_service_url + \
                                        "/api/auth-service/v1/enforce"
        self.catalog_details_url = self.catalog_url + \
                                   "/api/data-catalog/v1/data-catalog/{catalogID}"
        self.catalog_fields_url = self.catalog_url + \
                                  "/api/data-catalog/v1/data-catalog/{catalogID}/column"
        self.data_view_explore_report = self.data_view_url + \
                                        "/api/data-view/v1/form-view/explore-report?id={formview_uuid}"
        self.data_view_explore_report_batch = self.data_view_url + \
                                              "/api/data-view/v1/form-view/explore-report/batch"
        self.data_view_sample_data_url = self.data_view_url + "/api/data-view/v1/logic-view/{formview_uuid}/sample-data"
        self.data_model_data_dict_url= self.data_model_url+"/api/mdl-data-model/v1/data-dicts"

        self.data_view_datasource_url = self.data_view_url + "/api/data-view/v1/datasource"
        self.data_view_form_view_url = self.data_view_url + "/api/data-view/v1/form-view"

    def get_indicator_description(self, indicator_id, headers: dict) -> dict:
        url = self.indicator_details_url.format(indicator_id=indicator_id)
        api = API(url=url, headers=headers)
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise IndicatorDescError(e) from e

    def get_indicator_details(self, indicator_id: str, headers: dict) -> dict:
        url = self.indicator_details_url.format(indicator_id=indicator_id)
        api = API(url=url, headers=headers)
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise IndicatorDetailError(e) from e

    def get_indicator_query(self, indicator_id: str, headers: dict, data: dict) -> dict:
        url = self.indicator_query_url
        headers["Content-Type"] = "application/json"
        api = API(
            method=HTTPMethod.POST,
            url=url,
            headers=headers,
            params={"id": indicator_id},
            payload=data
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise IndicatorQueryError(e) from e

    async def aget_indicator_query(self, indicator_id: str, headers: dict, data: dict) -> dict:
        url = self.indicator_query_url
        headers["Content-Type"] = "application/json"
        api = API(
            method=HTTPMethod.POST,
            url=url,
            headers=headers,
            params={"id": indicator_id},
            payload=data
        )
        try:
            res = await api.call_async()
            return res
        except AfDataSourceError as e:
            raise IndicatorQueryError(e) from e

    def exec_vir_engine_by_sql(self, user: str, user_id: str, sql: str) -> Any | None:
        """Execute virtual engine by SQL query

        Args:
            user (str): username
            sql (str): SQL
            user_id (str): user id
        Returns:
            dict: VIR engine
        """
        # https://10.4.109.234/api/virtual_engine_service/v1/fetch
        # user_id=''
        url = self.vir_engine_fetch_url
        api = API(
            url=url,
            headers={
                "X-Presto-User": user,
                'Content-Type': 'text/plain'
            },
            method=HTTPMethod.POST,
            data=sql.encode(),
            params={"user_id": user_id}
        )
        # 虚拟引擎超时限定20分钟
        try:
            res = api.call(timeout=1200)
            return res
        except AfDataSourceError as e:
            raise VirEngineError(e) from e

    def get_view_column_info_for_prompt(self, idx: str, headers: dict) -> tuple:
        formview_column_info = self.get_view_column_by_id(idx, headers)
        formview_column_info_for_prompt = [
            {"id": field["id"], "business_name": field["business_name"], "technical_name": field["technical_name"],
             "comment": field["comment"], "data_type": field["data_type"]}
            for field in formview_column_info["fields"]
        ]
        # formview_column_info["view_source_catalog_name"]的值形如 'vdm_maria_0kr8mdtm.default'
        # 需要的是default之前的部分
        view_source_catalog_name = formview_column_info["view_source_catalog_name"]

        return formview_column_info_for_prompt, view_source_catalog_name

    # 获取探查的结果数据
    def get_data_explore(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = self.data_view_explore_report.format(formview_uuid=entity_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res["explore_field_details"]
        except Text2SQLError as e:
            raise DataViewError(e) from e

    # 批量获取探查的结果数据
    def get_data_explore_batch(self, entity_ids: List[str], headers: dict) -> dict:
        """Batch get explore result data for multiple form views.

        Args:
            entity_ids (List[str]): form view ID 列表
            headers (dict): AF token

        Returns:
            dict: 批量探查结果，具体结构由数据视图服务返回决定
        """
        url = self.data_view_explore_report_batch
        api = API(
            method=HTTPMethod.POST,
            url=url,
            headers=headers,
            payload={"ids": entity_ids},
        )
        try:
            res = api.call()
            return res
        except Text2SQLError as e:
            raise DataViewError(e) from e

    def get_view_sample_by_source(self, source: dict, headers: dict) -> dict:
        url = self.vir_engine_preview_url.format(
            catalog=source["source"],
            schema=source["schema"],
            table=source["title"],
        )
        headers["X-Presto-User"] = "af"
        api = API(
            url=url,
            headers=headers,
            payload={
                "limit": 1,
                "type": 0
            }
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise VirEngineError(e) from e

    def get_view_data_preview(self, view_id: str, headers: dict, fields: list[str]) -> dict:
        url = self.view_data_preview_url
        api = API(
            method=HTTPMethod.POST,
            url=url,
            headers=headers,
            payload={
                "filters": [],
                "fields": fields,
                "limit": 1,
                "form_view_id": view_id,
                "offset": 1,
            }
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    def get_view_column_by_id(self, view_id, headers: dict) -> dict:
        url = self.view_fields_url.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e

    def get_view_details_by_id(self, view_id, headers: dict) -> dict:
        url = self.view_details_url.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    # 获取白名单策略筛选sql
    def get_view_white_policy_sql(self, view_id, headers: dict) -> dict:
        url = self.view_white_policy_sql.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    # 获取脱敏、数据分级字段
    def get_view_field_info(self, view_id, headers: dict) -> dict:
        url = self.view_field_info.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    # 获取资源是否有读取权限，object_type data_view api indicator
    def get_auth_info(self, object_id: str, object_type: str, user_id: str, headers: dict) -> dict:
        url = self.auth_service_details_url
        params_item = {
            "action": "read",
            "object_id": object_id,
            "object_type": object_type,
            "subject_id": user_id,
            "subject_type": "user",
        }
        params = [params_item]
        api = API(
            method=HTTPMethod.POST,
            url=url,
            headers=headers,
            data=json.dumps(params)
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    def get_data_catalog_detail_by_id(self, catalog_id, headers: dict) -> dict:
        url = self.catalog_details_url.format(catalogID=catalog_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    def get_data_dict_by_name_pattern(self, name_pattern: str, headers: dict) -> list:
        """根据名称模式查询规则库（数据字典）列表
        
        Args:
            name_pattern: 规则库名称模式
            headers: 请求头
            
        Returns:
            规则库列表（数组）
        """
        url = self.data_model_data_dict_url
        params = {
            "name_pattern": name_pattern
        }
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=headers,
            params=params
        )
        try:
            res = api.call()
            # 根据文档，返回的是对象，包含 entries 字段
            if isinstance(res, dict) and "entries" in res:
                return res.get("entries", [])
            # 兼容旧格式（直接返回数组）
            if isinstance(res, list):
                return res
            return []
        except AfDataSourceError as e:
            raise DataViewError(e) from e
    
    def get_data_dict_items(self, dict_id: str, headers: dict, limit: int = 1000, offset: int = 0) -> dict:
        """获取规则库的键值对（items）
        
        Args:
            dict_id: 规则库ID
            headers: 请求头
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            规则库的键值对列表
        """
        url = f"{self.data_model_data_dict_url}/{dict_id}/items"
        params = {
            "limit": limit,
            "offset": offset
        }
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=headers,
            params=params
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise DataViewError(e) from e
    
    def get_data_view_datasource_list(self, headers: dict, limit: int = 1000, sort: str = "updated_at", direction: str = "desc") -> dict:
        """查询数据源列表（data-view服务）
        
        Args:
            headers: 请求头
            limit: 返回数量限制
            sort: 排序字段
            direction: 排序方向
            
        Returns:
            数据源列表
        """
        url = self.data_view_datasource_url
        import time
        params = {
            "limit": limit,
            "direction": direction,
            "sort": sort,
            "_t": int(time.time() * 1000)
        }
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=headers,
            params=params
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise DataViewError(e) from e
    
    def get_data_view_form_view_list(
        self,
        datasource_id: str,
        keyword: str = "",
        headers: dict = None,
        view_type: str = "datasource",
        include_sub_department: bool = True
    ) -> list:
        """根据数据源ID和表名查询视图列表（data-view服务）
        
        Args:
            datasource_id: 数据源ID
            keyword: 表名关键词
            headers: 请求头
            view_type: 视图类型，默认为"datasource"
            include_sub_department: 是否包含子部门
            
        Returns:
            视图列表（数组）
        """
        url = self.data_view_form_view_url
        params = {
            "type": view_type,
            "include_sub_department": str(include_sub_department).lower(),
            "keyword": keyword,
            "datasource_id": datasource_id
        }
        api = API(
            method=HTTPMethod.GET,
            url=url,
            headers=headers or {},
            params=params
        )
        try:
            res = api.call()
            # 根据文档，返回的是对象，包含 entries 字段
            if isinstance(res, dict) and "entries" in res:
                return res.get("entries", [])
            # 兼容旧格式（直接返回数组）
            if isinstance(res, list):
                return res
            return []
        except AfDataSourceError as e:
            raise DataViewError(e) from e

    def get_data_catalog_fields_by_id(self, catalog_id, headers: dict, offset: int = 1, limit: int = 100) -> dict:
        url = self.catalog_fields_url.format(catalogID=catalog_id)
        api = API(
            url=url,
            headers=headers,
            params={
                "offset": offset,
                "limit": limit
            }
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            raise FrontendSampleError(e) from e

    def get_data_view_sample_data(self, formview_uuid: str, headers: dict) -> dict:
        """获取数据视图样例数据
        
        Args:
            formview_uuid (str): 数据视图 UUID
            headers (dict): 请求头，包含认证信息
            
        Returns:
            dict: 样例数据，如果数据量为0则返回空结果并标记总数量为0
        """
        url = self.data_view_sample_data_url.format(formview_uuid=formview_uuid)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = api.call()
            return res
        except AfDataSourceError as e:
            # 检查是否是数据条目数为0的错误
            error_detail = e.detail
            if error_detail:
                # detail 可能是字符串（JSON字符串）或字典
                detail_str = ""
                nested_detail = None

                if isinstance(error_detail, str):
                    detail_str = error_detail
                    try:
                        error_detail = json.loads(error_detail)
                    except (json.JSONDecodeError, TypeError):
                        pass

                # 检查错误代码是否为 ViewDataEntriesEmpty
                if isinstance(error_detail, dict):
                    error_code = error_detail.get("code", "")
                    # 检查 detail 字段（可能是嵌套的 JSON 字符串）
                    nested_detail_str = error_detail.get("detail", "")
                    if isinstance(nested_detail_str, str):
                        try:
                            nested_detail = json.loads(nested_detail_str)
                        except (json.JSONDecodeError, TypeError):
                            nested_detail = nested_detail_str
                    elif isinstance(nested_detail_str, dict):
                        nested_detail = nested_detail_str
                else:
                    error_code = str(error_detail)

                # 检查是否包含 ViewDataEntriesEmpty 错误码
                # 可能在顶层 code、嵌套 detail 的 code，或者 detail 字符串中
                error_code_str = str(error_code)
                nested_code = ""
                if isinstance(nested_detail, dict):
                    nested_code = nested_detail.get("code", "")

                if ("ViewDataEntriesEmpty" in error_code_str or
                        "ViewDataEntriesEmpty" in str(nested_code) or
                        "ViewDataEntriesEmpty" in detail_str):
                    # 返回空结果，标记总数量为0
                    return {
                        "data": [],
                        "total": 0,
                        "formview_uuid": formview_uuid,
                        "empty": True
                    }

            raise FrontendSampleError(e) from e