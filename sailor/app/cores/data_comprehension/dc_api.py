import asyncio
import json
from typing import Any, List, Dict
from urllib.parse import urljoin

from app.cores.text2sql.t2s_base import API
from config import settings
# from app.cores.cognitive_assistant.qa_error import *
from app.cores.data_comprehension.dc_error import (DataCataLogOfDepartmentError, DataCatalogInfoError,
                                                   DataCataLogMountResourceError, DepartmentResponsibilitiesError,
                                                   ConfigurationCenterError, DataExploreError,
                                                   )
from app.cores.text2sql.t2s_error import (FrontendColumnError, Text2SQLError)
from app.logs.logger import logger

# 从AF获取数据， 部门和部门职责
class DataComprehensionAPI(object):
    ad_gateway_url: str = settings.DIP_GATEWAY_URL
    if settings.IF_DEBUG:
        data_catalog_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8153/'
        data_application_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8156/'
        data_view_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8123/'
        auth_service_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8155/'
        configuration_center_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8133/'
        af_sailor_service_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8081/'
        data_subject_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8123/'
        basic_search_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8163/'
    else:
        data_catalog_url: str = "http://data-catalog:8153/"
        data_application_url: str = "http://data-application-service:8156/"
        data_view_url: str = "http://data-view:8123/"
        auth_service_url: str = "http://auth-service:8155/"
        configuration_center_url: str = "http://configuration-center:8133/"
        af_sailor_service_url: str = "http://af-sailor-service:80/"
        data_subject_url: str = "http://data-subject:8123/"
        basic_search_url: str = "http://basic-search:8163/"


    def __init__(self):
        self._use_api_url()

    def _use_api_url(self):
        self.llm_url = settings.LLM_NAME
        # 大模型调用需要AD的appid
        self.get_ad_info='/api/internal/af-sailor-service/v1/knowledge/configs'
        self.get_cate_nodes='/api/data-catalog/v1/category'
        self.get_roles='/api/configuration-center/v1/users/roles'
        # 获取配置中心的部门id
        self.get_all_department_id = '/api/configuration-center/v1/objects'
        # 获取数据目录挂接的department_id
        self.data_catalog_information = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}"
        # 查询数据目录信息挂载资源列表
        self.data_catalog_mount_resource = "/api/data-catalog/v1/data-catalog/{catalog_id}/mount"
        # 根据部门id查询部门职责
        self.data_attributes = "/api/configuration-center/v1/objects/{id}"
        # 查询数据目录信息项列表
        self.catalog_columns='/api/data-catalog/frontend/v1/data-catalog/{catalog_id}/column?'
        # 获取部门信息
        # self.get_all_table_op = '/api/data-catalog/frontend/v1/data-catalog/operation/search'
        # self.get_all_table = '/api/data-catalog/frontend/v1/data-catalog/search'
        # 获取探查的结果数据
        self.explore_report = '/api/data-view/v1/form-view/explore-report?id={formview_uuid}'
        # self.subject_domains = '/api/data-subject/v1/subject-domains'
        #     basic-search 搜索数据目录下的所有数据资源
        self.basic_search_data_catalog = '/api/basic-search/v1/data-catalog/search'

    # 获取数据目录详情，其中有department_id
    async def get_data_catalog_info(self, headers: dict, catalog_id: str) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = urljoin(
            self.data_catalog_url,
            self.data_catalog_information).format(catalog_id=catalog_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise DataCatalogInfoError(e) from e

    async def get_data_catalog_mount_resource(self, headers: dict, catalog_id: str) -> dict:
        """查询数据目录信息挂载资源列表，'数据资源类型 resource_type 枚举值 1：逻辑视图 2：接口 3:文件资源'"""
        url = urljoin(
            self.data_catalog_url,
            self.data_catalog_mount_resource).format(catalog_id=catalog_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise DataCataLogMountResourceError(e) from e

    # 根据部门id查询部门职责
    async def get_department_attributes(self, headers: dict, department_id: str) -> str:
        """根据部门id查询部门职责"""

        url = urljoin(
            self.configuration_center_url,
            self.data_attributes).format(id=department_id)

        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            try:
                return res['attributes']['department_responsibilities']
            except Exception as e:
                logger.error(f'根据部门id查询部门职责时，发生通用类型的异常: {e}')
                return ""
        except Text2SQLError as e:
            raise DepartmentResponsibilitiesError(e) from e





    async def get_basic_search_result(self, headers: dict, catalog_id,department_id_list: list, size: int = 50) -> list[
        dict[str, Any]]:
        """
        Args:
            headers (dict): AF token
            department_id_list (list): department id list
            size (int, optional): size. Defaults to 50.
        Returns:
            dict: all data_catalog info of the department
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/services/1721066354073600
        # 'cate_id': "00000000-0000-0000-0000-000000000001": 组织架构
        # 'cate_id': "00000000-0000-0000-0000-000000000002"：信息系统
        # body={'data_kind': [], 'shared_type': [], 'update_cycle': [], 'business_object_id': [],'cate_info_req':
        #     [{'cate_id': "00000000-0000-0000-0000-000000000002", 'node_ids': id}],
        #       'keyword': ""}
        # body = {'data_kind': [], 'shared_type': [], 'update_cycle': [], 'business_object_id': [], 'cate_info_req':
        #     [{'cate_id': "00000000-0000-0000-0000-000000000001", 'node_ids': id}],
        #         'keyword': ""}

        # body = {"filter": {"data_kind": [], "shared_type": [], "size": size, "update_cycle": [], "business_object_id": [],
        #                    "cate_info_req": [{"cate_id": "00000000-0000-0000-0000-000000000001",
        #                                       "node_ids": department_id_list}]},
        #         "size": size}
        body = {"id":catalog_id,
            "filter": {"data_kind": [], "shared_type": [], "update_cycle": [], "business_object_id": [],
                       "cate_info_req": [{"cate_id": "00000000-0000-0000-0000-000000000001",
                                          "node_ids": department_id_list}]},
            "size": size}
        logger.info(f'get_department_all_data body={json.dumps(body, indent=4, ensure_ascii=False)}')
        # {
        #     "filter": {
        #         "data_kind": [],
        #         "shared_type": [],
        #         "size": 20,
        #         "update_cycle": [],
        #         "cate_info_req": [
        #             {
        #                 "cate_id": "00000000-0000-0000-0000-000000000001",
        #                 "node_ids": [
        #                     "680d50d8-50c9-11f0-a6cd-daa7e4d41f1d"
        #                 ]
        #             }
        #         ]
        #     }
        # }

        url = urljoin(
            self.basic_search_url,
            self.basic_search_data_catalog)
        api = API(
            url=url,
            headers=headers,
            payload=body,
            method='POST'
        )
        try:
            result = []
            res = await api.call_async()
            logger.info(f'get_all_table_op res={len(res["entries"])}')
            # logger.info(f'get_all_table_op res={res}')
            # print(json.dumps(res,ensure_ascii=False,indent=4)),'resources_id':i["mount_data_resources"][0]["data_resources_ids"]}
            for entry in res['entries']:
                result.append({"id": entry.get("id", ""),
                               "code": entry.get("code", ""),
                               "name": entry.get("name", ""),
                               'description': entry.get("description", ""),
                               "source_id": entry.get("mount_data_resources", [])[0].get("data_resources_ids",
                                                                                         []) if entry.get(
                                   "mount_data_resources", []) else []})
                # source_id.append(i["mount_data_resources"][0]["data_resources_ids"])
                # if not entry.get("mount_data_resources", []):
                #     logger.info(f'entry={entry}')
                #     logger.info(f'result={result}')
            # logger.info(f'获取该部门下所有的数据资源id,code,name,description, result=\n{result}')
            logger.info(f'获取该部门下所有的数据资源id,code,name,description, result={len(result)}')
            return result
        except Text2SQLError as e:
            raise DataCataLogOfDepartmentError(e)
    # 获取部门id
    async def get_department_id(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = urljoin(
            self.configuration_center_url,
            self.get_all_department_id)
        if entity_id=='':
            params={}
        else:
            params = {'id': entity_id}

        api = API(
            url=url,
            headers=headers,
            params=params
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise ConfigurationCenterError(e)

    # 获取数据目录的信息项详情,判断数据类型
    # async def get_filter_details(self, entity_id: str, headers: dict) -> dict:
    async def get_catalog_column_details(self, catalog_id: str, headers: dict,limit: int=100) -> dict:
        """这个接口默认只返回最多10个信息项，需要放开"""

        url = urljoin(
            self.data_catalog_url,
            self.catalog_columns).format(catalog_id=catalog_id)

        api = API(
            url=url,
            headers=headers,
            params={'limit':limit}
        )
        try:
            res = await api.call_async()
            # logger.info(f'get_column_details res={res}')
            logger.info(f'length of get_column_details res={len(res["columns"])}')
            return res['columns']
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    # 获取探查的结果数据
    async def get_data_explore(self, formview_uuid: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = urljoin(
            self.data_view_url,
            self.explore_report).format(formview_uuid=formview_uuid)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            # return res
            return res.get("explore_field_details",[])
        except Text2SQLError as e:
            raise DataExploreError(e) from e

    # 获取全部业务对象
    # todo， L1-L3应该都支持， 是业务对象的不同层级，方便实际应用场景中概念的泛化和细化，
    # async def get_subject_domains(self, headers: dict,limit=1000, offset=1) -> list[dict[str, Any]]:
    #     """
    #         todo
    #     """
    #     # http://10.4.109.85/api/data-subject/v1/subject-domains?limit=10&offset=1&type=business_object,business_activity&keyword&is_all=true&need_count=true
    #     domain_type = 'business_object,business_activity'
    #     keyword = ''
    #     is_all = 'true'
    #     need_count = 'true'
    #
    #     params = {
    #         "limit": limit,
    #         "offset": offset,
    #         "type": domain_type,
    #         "keyword": keyword,
    #         "is_all": is_all,
    #         "need_count": need_count
    #     }
    #
    #     url = urljoin(
    #         self.data_subject_url,
    #         self.subject_domains)
    #     api = API(
    #         url=url,
    #         headers=headers,
    #         params=params,
    #         method='GET'
    #     )
    #     try:
    #         result=[]
    #         res = await api.call_async()
    #         # print(json.dumps(res,ensure_ascii=False,indent=4))
    #         # print(json.dumps(res,ensure_ascii=False,indent=4)),'resources_id':i["mount_data_resources"][0]["data_resources_ids"]}
    #         for sd in res['entries']:
    #             if sd["type"] == "business_object":
    #                 result.append({"id":sd["id"],
    #                                "name":sd["name"],
    #                                # "description":sd["description"],
    #                                # "type":sd["type"],
    #                                "path_name":sd["path_name"]
    #                                })
    #             # source_id.append(i["mount_data_resources"][0]["data_resources_ids"])
    #         # return res
    #         return result
    #     except Exception as e:
    #         print('------------------', e)

    # 大模型调用需要AD的appid
    async def get_ad_ids(self) -> dict:
        """Get graph_id,synonyms_id,stopwords_id,app_id

        Args:
            source_type (str): source_type
            headers (dict): AF token
        Returns:
            dict: graph_id,synonyms_id,stopwords_id,app_id
        """
        # https://10.4.109.234/api/internal/af-sailor-service/v1/knowledge/configs
        url = urljoin(
            self.af_sailor_service_url,
            self.get_ad_info)
        api = API(
            url=url
        )
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            logger.error(f'调用AD接口获取appid报错，报错信息如下: {str(e)}')
            return {}

    # def exec_prompt_by_llm(self, prompt_data, appid, prompt_id):
    #     pass



