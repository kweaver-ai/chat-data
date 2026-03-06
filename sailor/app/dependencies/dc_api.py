import asyncio
import json
from typing import Any, List, Dict
from urllib.parse import urljoin


from app.cores.text2sql.t2s_base import API
from config import settings
from app.cores.cognitive_assistant.qa_error import *

# 从AF获取数据， 部门和职责
class DataComprehensionAPI(object):
    ad_gateway_url: str = settings.AD_GATEWAY_URL
    data_catalog_url: str = "http://data-catalog:8153/"
    data_application_url: str = "http://data-application-service:8156/"
    data_view_url: str = "http://data-view:8123/"
    auth_service_url: str = "http://auth-service:8155/"
    configuration_center_url: str = "http://configuration-center:8133/"
    af_sailor_service_url: str = "http://af-sailor-service:80/"
    # data_subject_url: str = "http://data-subject:8123/"
    # data_catalog_url: str = "http://10.4.109.85/"
    # data_application_url: str = "http://10.4.109.85/"
    # data_view_url: str = "http://10.4.109.85/"
    # auth_service_url: str = "http://10.4.109.85/"
    # configuration_center_url: str = "http://10.4.109.85/"
    # af_sailor_service_url: str = "http://10.4.109.85:8081/"
    # data_subject_url: str = "http://10.4.109.85/"

    def __init__(self):
        self._use_api_url()

    def _use_api_url(self):
        self.llm_url = settings.LLM_NAME
        # 大模型调用需要AD的appid
        self.get_ad_informs='/api/internal/af-sailor-service/v1/knowledge/configs'
        self.get_cate_nodes='/api/data-catalog/v1/category'
        self.get_roles='/api/configuration-center/v1/users/roles'
        # 获取配置中心的部门id
        self.get_all_department_id = '/api/configuration-center/v1/objects'
        # 获取数据目录挂接的department_id
        self.data_catalog_information = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}"
        # 根据部门id查询部门职责
        self.data_attributes = "/api/configuration-center/v1/objects/{id}"
        # 获取字段详情
        self.catalog_columns='/api/data-catalog/frontend/v1/data-catalog/{id}/column?'
        # 获取部门信息
        self.get_all_table_op = '/api/data-catalog/frontend/v1/data-catalog/operation/search'
        self.get_all_table = '/api/data-catalog/frontend/v1/data-catalog/search'
        # 获取探查的结果数据
        self.explore_report = '/api/data-view/v1/form-view/explore-report?id={catalog_id}'
        # self.subject_domains = '/api/data-subject/v1/subject-domains'

    # 获取部门信息
    async def get_department_data(self, id, headers: dict) -> list[dict[str, Any]]:
        """
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/services/1721066354073600
        body={'data_kind': [], 'shared_type': [], 'update_cycle': [], 'business_object_id': [],'cate_info_req':
            [{'cate_id': "00000000-0000-0000-0000-000000000002", 'node_ids': id}],
              'keyword': ""}
        url = urljoin(
            self.data_catalog_url,
            self.get_all_table_op)
        api = API(
            url=url,
            headers=headers,
            payload=body,
            method='POST'
        )
        try:
            result=[]
            res = await api.call_async()
            # print(json.dumps(res,ensure_ascii=False,indent=4)),'resources_id':i["mount_data_resources"][0]["data_resources_ids"]}
            for i in res['entries']:
                result.append({"id":i["id"],"code":i["code"],"name":i["name"],'description':i['description'], "source_id":i["mount_data_resources"][0]["data_resources_ids"]})
                # source_id.append(i["mount_data_resources"][0]["data_resources_ids"])

            return result
        except Exception as e:
            print('------------------', e)

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
        # try:
        res = await api.call_async()
        return res
        # except Exception as e:
        #     print('------------------', e)

    # 获取字段详情,判断数据类型
    # async def get_filter_details(self, entity_id: str, headers: dict) -> dict:
    async def get_column_details(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """

        url = urljoin(
            self.data_catalog_url,
            self.catalog_columns).format(id=entity_id)

        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()

            return res['columns']
        except Text2SQLError as e:
            raise DataCataLogError(e) from e

    # 获取数据目录挂接的department_id
    async def get_datalog_common(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = urljoin(
            self.data_catalog_url,
            self.data_catalog_information).format(catalog_id=entity_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise DataCataLogError(e) from e

    # 根据部门id查询部门职责
    async def get_department_attributes(self, entity_id: str, headers: dict) -> str:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """

        url = urljoin(
            self.configuration_center_url,
            self.data_attributes).format(id=entity_id)

        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            try:
                return res['attributes']['department_responsibilities']
            except Exception:
                return ""
        except Text2SQLError as e:

            raise DataCataLogError(e) from e

    # 获取探查的结果数据
    async def get_data_explore(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        url = urljoin(
            self.data_view_url,
            self.explore_report).format(catalog_id=entity_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res["explore_field_details"]
        except Text2SQLError as e:
            raise DataCataLogError(e) from e

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
            self.get_ad_informs)
        api = API(
            url=url
        )
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            print('------------------', e)

    # def exec_prompt_by_llm(self, prompt_data, appid, prompt_id):
    #     pass



