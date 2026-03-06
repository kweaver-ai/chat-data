import asyncio
import json
from typing import Any
from urllib.parse import urljoin

from app.cores.cognitive_assistant.qa_error import *
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.logs.logger import logger
from config import settings



# 整合了qa_api, dc_api中的所有api， 集中管理，避免重复

# class FindNumberAPI(object):
class DependentAPIs(object):
    ad_gateway_url: str = settings.DIP_GATEWAY_URL
    if not settings.IF_DEBUG:
        data_catalog_url: str = "http://data-catalog:8153/"
        data_application_url: str = "http://data-application-service:8156"
        data_view_url: str = "http://data-view:8123/"
        auth_service_url: str = "http://auth-service:8155"
        indicator_management_url: str = "http://indicator-management:8213"
        configuration_center_url: str = "http://configuration-center:8133"
        demand_management_url: str = "http://demand-management:8280"
        af_sailor_service_url: str = "http://af-sailor-service:80/"
        data_subject_url: str = "http://data-subject:8123/"
    # 本地调试用以下配置, host改为部署AF的服务器IP
    else:
        data_catalog_url: str = "http://10.4.109.85:8153/"
        data_application_url: str = "http://10.4.109.85:8156"
        data_view_url: str = "http://10.4.109.85:8123/"
        auth_service_url: str = "http://10.4.109.85:8155"
        indicator_management_url: str = "http://10.4.109.85:8213"
        configuration_center_url: str = "http://10.4.109.85:8133"
        demand_management_url: str = "http://10.4.109.85:8280"
        af_sailor_service_url: str = "http://10.4.109.85:8081/"
        data_subject_url: str = "http://10.4.109.85/"


    def __init__(self):
        self._gen_api_url()

    def _gen_api_url(self):
        # AnyDATA相关APIs
        # 大模型相关
        self.llm_url = settings.LLM_NAME
        self.llm_url_tail = "api/model-factory/v1/prompt-template-run"
        # 获取AD的appid， 图谱id， 词库id
        # self.get_ad_informs = '/api/internal/af-sailor-service/v1/knowledge/configs'
        self.endpoint_get_ad_kn_params = '/api/internal/af-sailor-service/v1/knowledge/configs'

        # 鉴权服务相关的APIs
        self.data_view_enforce_url = "/api/auth-service/v1/enforce"
        self.user_auth = "/api/auth-service/v1/subject/objects"

        # 配置中心相关APIs

        self.get_roles = '/api/configuration-center/v1/users/roles'
        # 获取配置中心的部门id
        self.get_all_department_id = '/api/configuration-center/v1/objects'
        # 根据部门id查询部门职责
        self.data_attributes = "/api/configuration-center/v1/objects/{id}"
        # 获取配置表中数据， 比如direct_qa的值
        self.by_type_list_url = "/api/internal/configuration-center/v1/byType-list/{num}"

        # 数据资源目录相关的APIs
        # 获取数据目录挂接的department_id
        self.data_catalog_information = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}"
        self.get_cate_nodes = '/api/data-catalog/v1/category'
        # 获取数据资源目录的信息项（字段）详情
        self.catalog_columns = '/api/data-catalog/frontend/v1/data-catalog/{id}/column?'
        # 获取部门信息
        self.get_all_table_op = '/api/data-catalog/frontend/v1/data-catalog/operation/search'
        self.get_all_table = '/api/data-catalog/frontend/v1/data-catalog/search'
        self.column_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}/column"
        self.view_id_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}"
        self.common_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}"
        self.data_catalog_mount = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}/mount"

        # 逻辑视图相关的APIs
        # 获取探查的结果数据
        self.explore_report = '/api/data-view/v1/form-view/explore-report?id={catalog_id}'
        self.view_column_url = "/api/data-view/v1/form-view/{view_id}"
        self.view_detail_url = "/api/data-view/v1/form-view/{view_id}/details"
        self.sub_view_enforce_url = "/api/data-view/v1/user/form-view"
        self.sub_view_enforce_url = "/api/data-view/v1/user/form-view"

        # 指标管理相关的APIs
        self.indicator_detail_url = "/api/indicator-management/v1/indicator/{entity_id}"
        # self.subject_domains = '/api/data-subject/v1/subject-domains'

        # 数据应用服务相关的APIs
        self.params_url = "/api/data-application-service/frontend/v1/services/{entity_id}"
        self.sub_serv_enforce_url = "/api/data-application-service/frontend/v1/apply/available-assets"

        # 需求管理中的APIs
        self.shared_declaration_status = "/api/demand-management/v1/shared-declaration/status"

    async def exec_prompt_by_llm(self, inputs: dict, appid: str, prompt_id: str) -> str:
        """Execute prompt by llm
        Args:
            prompt (str): prompt
            appid (str): AD appid
        Returns:
            dict: execute result
        """
        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        model_para = {
            "temperature": 0.01,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "max_tokens": 2000
        }
        url = urljoin(self.ad_gateway_url, self.llm_url_tail)
        api = API(
            url=url,
            headers={
                "appid": appid
            },
            payload={
                "model_name": self.llm_url.split('/')[-1],
                "model_para": model_para,
                "prompt_id": prompt_id,
                "inputs": inputs,
                "history_dia": []
            },
            method=HTTPMethod.POST,
            stream=True
        )
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            print('------------------', e)
            # raise LLMExecError(e) from e

    async def get_data_catalog_column_by_id(self, entity_id: str, headers: dict) -> dict:
        # async def get_column_by_id(self, entity_id: str, headers: dict) -> dict:
        """Get data catalog column by id

        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: data catalog column
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/data-catalog/502494820913184002/column
        url = urljoin(
            self.data_catalog_url,
            self.column_url).format(entity_id=entity_id)
        api = API(
            url=url,
            headers=headers,
            params={
                "limit": 1000
            }
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_data_catalog_common(self, entity_id: str, headers: dict) -> dict:
        # async def get_datalog_common(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """

        url = urljoin(
            self.data_catalog_url,
            self.common_url).format(entity_id=entity_id)

        api = API(
            url=url,
            headers=headers,
        )
        print(api)
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise DataCataLogError(e) from e

    async def get_indicator_detail(self, entity_id: str, headers: dict) -> dict:
        """
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/services/1721066354073600
        url = urljoin(
            self.indicator_management_url,
            self.indicator_detail_url).format(entity_id=entity_id)

        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise IndicatorManagementError(e) from e

    async def get_params_by_id(self, entity_id: str, headers: dict) -> dict:
        """Get svc info including require and response
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: svc info
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/services/1721066354073600
        url = urljoin(
            self.data_application_url,
            self.params_url).format(entity_id=entity_id)

        api = API(
            url=url,
            headers=headers,
            params={
                "limit": 1000
            }
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendParamsError(e) from e

    async def get_view_column_by_id(self, view_id: str, headers: dict) -> dict:
        url = urljoin(
            self.data_view_url,
            self.view_column_url).format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        print("--------get_view_column_by_id -----------")
        print(api)
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_view_detail_by_id(self, view_id: str, headers: dict) -> dict:
        url = urljoin(
            self.data_view_url,
            self.view_detail_url).format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_user_auth_by_id(self, view_id: str, params, headers: dict) -> str:
        auth_params = [
            {
                "action": "read",
                "object_id": view_id,
                "object_type": "data_view",
                "subject_id": params.subject_id,
                "subject_type": params.subject_type
            }
        ]
        url = urljoin(
            self.auth_service_url,
            self.data_view_enforce_url)
        api = API(
            url=url,
            headers=headers,
            payload=auth_params,
            method="POST"
        )
        try:
            res = await api.call_async()
            return res[0]["effect"]
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    # TODO 换接口
    async def get_view_id_by_code(self, entity_id: str, headers: dict) -> str:
        url = urljoin(
            self.data_catalog_url,
            self.view_id_url).format(entity_id=entity_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            print("%%%%%%%%%%%%%%%%%%%%%%%%", res)
            return res.get("form_view_id")
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_data_catalog_mount(self, catalog_id: str, headers: dict) -> str:
        url = urljoin(
            self.data_catalog_url,
            self.data_catalog_mount).format(catalog_id=catalog_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            print('+++++++++++++++++++', api)
            res = await api.call_async()
            res = res.get("mount_resource", [{}])[0].get("resource_id", "")
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_view_basic_info(self, entity_id: str, headers: dict) -> dict:
        url = urljoin(
            self.data_catalog_url,
            self.view_id_url).format(entity_id=entity_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            print('+++++++++++++++++++', api)
            res = await api.call_async()
            mount = await self.get_data_catalog_mount(entity_id, headers)
            detail = await self.get_view_detail_by_id(mount, headers)
            res["form_view_id"] = mount
            res["owner_id"] = detail.get("owner_id")
            res["technical_name"] = detail.get("technical_name")
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_user_auth_state(self, assets, params, headers: dict) -> str:
        # 数据owner 默认拥有所有权限
        data_map = {
            "1": "data_catalog",
            "2": "api",
            "3": "data_view",
        }
        object_type = data_map[assets["asset_type"]]

        if object_type == "data_catalog":
            object_id = await self.get_data_catalog_mount(assets["datacatalogid"], headers)
            detail = await self.get_view_detail_by_id(object_id, headers)
            owner_id = detail.get("owner_id", None)

            if owner_id == params.subject_id:
                auth_state = "allow"
                return auth_state
            object_name = assets["datacatalogname"]
            object_type = data_map["3"]  # 通过视图去请求数据目录的权限
        else:
            if assets["owner_id"] == params.subject_id:
                auth_state = "allow"
                return auth_state
            object_id = assets["resourceid"]
            object_name = assets["resourcename"]

        auth_params = [
            {
                "action": "read",
                "object_id": object_id,
                "object_type": object_type,
                "subject_id": params.subject_id,
                "subject_type": params.subject_type
            }
        ]
        logger.debug(
            f""" "{object_name}" 请求权限接口：\n {json.dumps(auth_params, ensure_ascii=False, indent=4)}""")
        url = urljoin(
            self.auth_service_url,
            self.data_view_enforce_url)
        api = API(
            url=url,
            headers=headers,
            payload=auth_params,
            method="POST"
        )
        try:
            res = await api.call_async()
            auth_state = res[0]["effect"]
            logger.info(f""" 结果: {auth_state}""")

            return auth_state
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def user_all_auth(self, headers: dict, subject_id) -> list[Any]:
        # 数据owner 默认拥有所有权限
        url_ser = urljoin(
            self.auth_service_url,
            self.user_auth)
        url_view = urljoin(
            self.data_view_url,
            self.sub_view_enforce_url)
        api_ser = API(
            url=url_ser,
            headers=headers,
            method="GET",
            params={"object_type": 'api,indicator', 'subject_id': subject_id, 'subject_type': 'user'}
        )
        api_view = API(
            url=url_view,
            headers=headers,
            method="GET",
            params={"limit": 2000}

        )
        try:
            res_view = await api_view.call_async()
            res_ser = await api_ser.call_async()
            if res_ser["total_count"] > 0:
                service_id = [i["object_id"] for i in res_ser["entries"]]
            else:
                service_id = []
            if res_view["total_count"] > 0:
                view_id = [i["id"] for i in res_view["entries"]]
            else:
                view_id = []
            auth_id = service_id + view_id
        except Exception as e:
            auth_id = []
            print(e)
        return auth_id

    async def sub_user_auth_state(self, assets, params, headers: dict, auth_id) -> str:
        if assets["asset_type"] == "2":
            return "deny"

        if "data-operation-engineer" in params.roles or "data-development-engineer" in params.roles:
            return "allow"
        # 数据owner 默认拥有所有权限
        data_map = {
            "1": "data_catalog",
            "2": "api",
            "3": "data_view",
            "4": "indicator",
        }
        object_type = data_map[assets["asset_type"]]
        if object_type == "data_catalog":
            try:
                object_id = await self.get_data_catalog_mount(assets["datacatalogid"], headers)
                detail = await self.get_view_detail_by_id(object_id, headers)
                owner_id = detail.get("owner_id", None)
                if owner_id == params.subject_id:
                    auth_state = "allow"
                    return auth_state
            except Exception as e:
                print('鉴权失败,鉴权报错原因-----------------', e)
                return "deny"
            object_name = assets["datacatalogname"]
            object_type = data_map["3"]  # 通过视图去请求数据目录的权限
        else:
            if "owner_id" not in assets.keys():
                return "deny"
            if assets["owner_id"] == params.subject_id:
                auth_state = "allow"
                return auth_state
            object_id = assets["resourceid"]
            object_name = assets["resourcename"]
        auth_params = [
            {
                "action": "read",
                "object_id": object_id,
                "object_type": object_type,
                "subject_id": params.subject_id,
                "subject_type": params.subject_type
            }
        ]
        logger.debug(
            f""" "{object_name}" 请求权限接口：\n {json.dumps(auth_params, ensure_ascii=False, indent=4)}""")
        print("==================================")
        print(auth_id)
        if object_id in auth_id:
            return "allow"
        else:
            logger.info(
                f""" "{object_name}" 资源没有权限""")
            return "deny"

    async def get_config_dict(
            self,
            num: int | str,
            headers: dict | None = None
    ) -> list:
        url = urljoin(
            self.configuration_center_url,
            self.by_type_list_url).format(num=num)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            # if len(res) != 3:
            #     raise Text2SQLError(
            #         url=url,
            #         reason="config 酝置错误，请检查数据库中是否存在 sailor_agent_react_mode，sql_limit，direct_qa",
            #     )
            return res
        except Text2SQLError as e:
            raise ConfigurationCenterError(e) from e

    # 共享申请状态查询
    async def get_shared_declaration_status(self, catalog_id: list[str], headers: dict) -> str:
        url = urljoin(
            self.demand_management_url,
            self.shared_declaration_status)
        api = API(
            url=url,
            headers=headers,
            method="POST",
            payload={'catalog_ids': catalog_id}
        )
        try:
            res = await api.call_async()
            shared_state = res[0]["status"]
            return shared_state
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e
        # get_shared_stauts


    # AD 相关接口调用

    async def get_ad_kn_params(self,headers: dict):
        url = urljoin(
            self.af_sailor_service_url,
            self.endpoint_get_ad_kn_params)
        print(f"url={url}")
        api = API(
            url=url,
            headers=headers,
            method=HTTPMethod.GET
        )
        try:
            res = await api.call_async()
            # res={}
            print("response = ", json.dumps(res, ensure_ascii=False, indent=4))
            return (res.get("app_id", ""),
                            res.get("cognitive_search_data_catalog_graph_id", ""))
            # return (res.get("app_id", ""),
            #         res.get("cognitive_search_data_catalog_graph_id", ""),
            #         res.get("cognitive_search_data_resource_graph_id", ""),
            #         res.get("cognitive_search_synonyms_id", ""),
            #         res.get("cognitive_search_stopwords_id", ""))
        except Exception as e:
            print(e)
            # return ("","","","","")
            return ("", "")

if __name__ == '__main__':
    from app.utils.password import get_authorization
    apies = DependentAPIs()
    Authorization = get_authorization("https://10.4.109.85", "", "")
    headers = {"Authorization": Authorization}
    res = asyncio.run(apies.get_ad_kn_params(headers))
    print(res)