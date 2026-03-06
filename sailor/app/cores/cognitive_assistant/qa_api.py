import asyncio
import json
from typing import Any, Optional, Tuple
from urllib.parse import urljoin, urlencode

from app.cores.cognitive_assistant.qa_error import *
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.logs.logger import logger
from app.cores.cognitive_search.search_config.get_params import get_search_configs, SearchConfigs
from config import settings


class FindNumberAPI(object):

    ad_gateway_url: str = settings.DIP_GATEWAY_URL
    dip_gateway_url: str = settings.DEBUG_DIP_GATEWAY_HTTPS
    if settings.IF_DEBUG:
        # 本地调试用以下配置, host改为部署AF的服务器IP
        data_catalog_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8153/'
        data_application_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8156'
        data_view_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8123/'
        auth_service_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8155'
        indicator_management_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8213'
        configuration_center_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8133'
        demand_management_url: str =  f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8280'
        dip_gateway_url_private = f"{settings.DEBUG_DIP_GATEWAY_HTTP}:9898"
        dip_ontology_manager_url_internal = f"{settings.DEBUG_DIP_GATEWAY_HTTP}:13014"
        dip_ontology_query_url_internal = f"{settings.DEBUG_DIP_GATEWAY_HTTP}:13018"
        dip_data_model_url_internal = f"{settings.DEBUG_DIP_GATEWAY_HTTP}:13020"

    else:
        data_catalog_url: str = "http://data-catalog:8153/"
        data_application_url: str = "http://data-application-service:8156"
        data_view_url: str = "http://data-view:8123/"
        auth_service_url: str = "http://auth-service:8155"
        indicator_management_url: str = "http://indicator-management:8213"
        configuration_center_url: str = "http://configuration-center:8133"
        demand_management_url: str = "http://demand-management:8280"
        dip_gateway_url: str = "http://mf-model-api:9898"
        dip_gateway_url_private: str = "http://mf-model-api:9898"
        dip_ontology_query_url_internal: str = "http://ontology-query-svc:13018"
        dip_ontology_manager_url_internal: str = "http://ontology-manager-svc:13014"
        dip_data_model_url_internal = "http://mdl-data-model-svc:13020"


    def __init__(self):
        self._gen_api_url()

    def _gen_api_url(self):
        self.llm_url = settings.LLM_NAME
        self.llm_url_tail = "api/model-factory/v1/prompt-template-run"
        self.llm_url_tail_dip_external = "/api/mf-model-api/v1/chat/completions"
        self.llm_url_tail_dip_private = "/api/private/mf-model-api/v1/chat/completions"

        # 查询数据目录信息项列表
        self.column_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}/column"
        # 查询数据资源目录详情
        self.view_id_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}"
        #
        self.common_url = "/api/data-catalog/frontend/v1/data-catalog/{entity_id}"
        # 查询数据目录信息挂载资源列表
        self.data_catalog_mount = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}/mount"

        # 接口详情
        self.params_url = "/api/data-application-service/frontend/v1/services/{entity_id}"
        # 可用接口列表
        self.sub_serv_enforce_url = "/api/data-application-service/frontend/v1/apply/available-assets"

        # 查看逻辑视图字段
        self.view_column_url = "/api/data-view/v1/form-view/{view_id}"
        # 获取逻辑视图详情
        self.view_detail_url = "/api/data-view/v1/form-view/{view_id}/details"
        # 获取用户有权限下的视图
        self.sub_view_enforce_url = "/api/data-view/v1/user/form-view"
        # self.sub_view_enforce_url = "/api/data-view/v1/user/form-view"

        # 权限资源策略验证
        self.data_view_enforce_url = "/api/auth-service/v1/enforce"
        # 访问者拥有的资源
        self.user_auth = "/api/auth-service/v1/subject/objects"

        # 指标详情
        self.indicator_detail_url = "/api/indicator-management/v1/indicator/{entity_id}"
        # 获取配置信息
        self.by_type_list_url = "/api/internal/configuration-center/v1/byType-list/{num}"
        # 共享申请
        self.shared_declaration_status = "/api/demand-management/v1/shared-declaration/status"

        # dip相关接口
        self.get_object_types_url="/api/ontology-manager/in/v1/knowledge-networks/{kn_id}/object-types"
        self.get_object_types_url_external = "/api/ontology-manager/v1/knowledge-networks/{kn_id}/object-types"
        self.ontology_query_by_object_types = "/api/ontology-query/in/v1/knowledge-networks/{kn_id}/object-types/{class_id}"
        self.ontology_query_by_object_types_external = "/api/ontology-query/v1/knowledge-networks/{kn_id}/object-types/{class_id}"
        # 获取用户有权限的逻辑视图（新API）
        self.user_data_views_url = "/api/mdl-data-model/in/v1/data-views/"
        self.user_data_views_url_external = "/api/mdl-data-model/v1/data-views/"

    async def dip_ontology_query_by_object_types(
            self,
            kn_id: str,
            class_id: str,
            body: dict,
            x_account_id: str,
            x_account_type: Optional[str] = None
    ) -> Tuple[str, dict]:
        logger.info(f'dip_ontology_query_by_object_types() running...')
        url = urljoin(self.dip_ontology_query_url_internal, self.ontology_query_by_object_types.format(
            kn_id=kn_id,
            class_id=class_id
        ))
        logger.info(f'dip_ontology_query_by_object_types() url = {url}')

        logger.info(f"kn_id={kn_id}")
        logger.info(f'body = {body}')
        # payload=body
        # payload = {
        #     "condition": {
        #         "operation": "or",
        #         "sub_conditions": [
        #             {
        #                 "field": "name",
        #                 "operation": "match",
        #                 "value": "发布"
        #             },
        #             {
        #                 "field": "description",
        #                 "operation": "knn",
        #                 "value": "发布",
        #                 "limit_key": "k",
        #                 "limit_value": 10
        #             }
        #         ]
        #     },
        #     "need_total": True,
        #     "limit": 10
        # }

        if x_account_type:
            headers = {
                "x-account-id": x_account_id,
                "x-account-type": x_account_type,
                "x-http-method-override": "GET"
            }
        else:
            headers = {
                "x-account-id": x_account_id
            }
        api = API(
            url=url,
            headers=headers,
            payload=body,
            method=HTTPMethod.POST,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                return class_id,res
            else:
                return class_id,{}
        except Text2SQLError as e:
            raise LLMExecError(e) from e

    async def dip_ontology_query_by_object_types_external(
            self,
            token: str,
            kn_id: str,
            class_id: str,
            body: dict
    ) -> Tuple[str, dict]:
        logger.info(f'dip_ontology_query_by_object_types_external() running...')
        url = urljoin(self.dip_ontology_query_url_internal, self.ontology_query_by_object_types_external.format(
            kn_id=kn_id,
            class_id=class_id
        ))
        logger.info(f'dip_ontology_query_by_object_types() url = {url}')

        logger.info(f"kn_id={kn_id}")
        logger.info(f'body = {body}')
        # payload=body
        # payload = {
        #     "condition": {
        #         "operation": "or",
        #         "sub_conditions": [
        #             {
        #                 "field": "name",
        #                 "operation": "match",
        #                 "value": "发布"
        #             },
        #             {
        #                 "field": "description",
        #                 "operation": "knn",
        #                 "value": "发布",
        #                 "limit_key": "k",
        #                 "limit_value": 10
        #             }
        #         ]
        #     },
        #     "need_total": True,
        #     "limit": 10
        # }
        headers = {
            "Authorization": token,
            "x-http-method-override": "GET"
        }
        api = API(
            url=url,
            headers=headers,
            payload=body,
            method=HTTPMethod.POST,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                return class_id,res
            else:
                return class_id,{}
        except Text2SQLError as e:
            raise LLMExecError(e) from e


    async def dip_get_object_types_internal(
            self,
            kn_id:str,
            x_account_id: str,
            x_account_type: Optional[str] = None
    ) -> dict:

        url = urljoin(self.dip_ontology_manager_url_internal, self.get_object_types_url.format(kn_id=kn_id))

        logger.info(f'dip_get_object_types_internal() running...')
        logger.info(f'url={url}')
        logger.info(f"kn_id={kn_id}")

        if x_account_type:
            headers = {
                "x-account-id": x_account_id,
                "x-account-type": x_account_type
            }
        else:
            headers = {
                "x-account-id": x_account_id
            }
        api = API(
            url=url,
            headers=headers,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                return res
            else:
                return {}
        except Text2SQLError as e:
            raise LLMExecError(e) from e

    async def dip_get_object_types_external(
            self,
            token:str,
            kn_id:str
    ) -> dict:

        url = urljoin(self.dip_ontology_manager_url_internal, self.get_object_types_url_external.format(kn_id=kn_id))

        logger.info(f'dip_get_object_types_external() running...')
        logger.info(f'url={url}')
        logger.info(f"kn_id={kn_id}")
        headers = {"Authorization": token}
        api = API(
            url=url,
            headers=headers,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                return res
            else:
                return {}
        except Text2SQLError as e:
            raise LLMExecError(e) from e


    async def exec_prompt_by_llm_dip_external(
            self,
            token: str,
            prompt_rendered_msg,
            search_configs: SearchConfigs
    ) -> str:
        """Execute prompt by llm
        Args:
            prompt (str): prompt
            appid (str): AD appid
        Returns:
            dict: execute result
        """

        model_para = {
            "temperature": float(search_configs.sailor_search_qa_llm_temperature),
            "top_p": float(search_configs.sailor_search_qa_llm_top_p),
            "presence_penalty": float(search_configs.sailor_search_qa_llm_presence_penalty),
            "frequency_penalty": float(search_configs.sailor_search_qa_llm_frequency_penalty),
            "max_tokens": int(search_configs.sailor_search_qa_llm_max_tokens)
        }
        # model_para = {
        #     "temperature": 0.01,
        #     "top_p": 1,
        #     "presence_penalty": 0,
        #     "frequency_penalty": 0,
        #     "max_tokens": 2000
        # }
        logger.info(f'self.dip_gateway_url={self.dip_gateway_url}')

        url = urljoin(self.dip_gateway_url, self.llm_url_tail_dip_external)
        logger.info(f'url={url}')
        logger.info(f'llm url={url}')
        logger.info(f"model_name={self.llm_url.split('/')[-1]}")
        logger.info(f"model_para={model_para}")
        logger.info(f"prompt_rendered_msg={prompt_rendered_msg}")
        api = API(
            url=url,
            headers={
                "Authorization": token},
            payload={
                "model": self.llm_url.split('/')[-1],
                "top_k": model_para.get("top_k", 1),
                "temperature": model_para.get("temperature", 0.000001),
                "top_p": model_para.get("top_p", 1.0),
                "messages":prompt_rendered_msg,
                "max_tokens": model_para.get("max_tokens", 1000),
                "stream": False
            },
            method=HTTPMethod.POST,
            stream=False
        )
        try:
            res = await api.call_async()
            # logger.info(f'llm res={repr(res)}')
            res_content_str=res.get('choices')[0].get('message').get('content')
            return res_content_str
        # except UnicodeEncodeError:
        #     safe_message = res.encode('utf-8', errors='replace').decode('utf-8')
        #     logger.info(safe_message)
        except Text2SQLError as e:
            raise LLMExecError(e) from e


    async def exec_prompt_by_llm_dip_private(
            self,
            prompt_rendered_msg: list,
            search_configs: SearchConfigs,
            x_account_id: str,
            x_account_type: Optional[str] = None
    ) -> str:
        """Execute prompt by llm
        Args:
            prompt (str): prompt
            appid (str): AD appid
        Returns:
            dict: execute result
        """
        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        # search_configs = get_search_configs()
        model_para = {
            "temperature": float(search_configs.sailor_search_qa_llm_temperature),
            "top_p": float(search_configs.sailor_search_qa_llm_top_p),
            "presence_penalty": float(search_configs.sailor_search_qa_llm_presence_penalty),
            "frequency_penalty": float(search_configs.sailor_search_qa_llm_frequency_penalty),
            "max_tokens": int(search_configs.sailor_search_qa_llm_max_tokens)
        }
        # model_para = {
        #     "temperature": 0.01,
        #     "top_p": 1,
        #     "presence_penalty": 0,
        #     "frequency_penalty": 0,
        #     "max_tokens": 2000
        # }
        url = urljoin(self.dip_gateway_url_private, self.llm_url_tail_dip_private)
        logger.info(f'llm url={url}')
        logger.info(f"model_name={self.llm_url.split('/')[-1]}")
        logger.info(f"model_para={model_para}")
        logger.info(f"prompt_rendered_msg={prompt_rendered_msg}")
        if x_account_type:
            headers = {
                "x-account-id": x_account_id,
                "x-account-type": x_account_type
            }
        else:
            headers = {
                "x-account-id": x_account_id
            }
        api = API(
            url=url,
            headers=headers,
            payload={
                "model": self.llm_url.split('/')[-1],
                "top_k": model_para.get("top_k", 1),
                "temperature": model_para.get("temperature", 0.000001),
                "top_p": model_para.get("top_p", 1.0),
                "messages":prompt_rendered_msg,
                "max_tokens": model_para.get("max_tokens", 1000),
                "stream": False
            },
            method=HTTPMethod.POST,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                res_content_str = res.get('choices')[0].get('message').get('content')
                return res_content_str
            else:
                return ""
        except Text2SQLError as e:
            raise LLMExecError(e) from e

    async def exec_prompt_by_llm_dip_understand(
        self,
        prompt_rendered_msg: list,
        x_account_id: str,
        x_account_type: Optional[str] = None,
        input_max_tokens: int = 5000
    ) -> str:
        """Execute prompt by llm
        Args:
            prompt (str): prompt
            appid (str): AD appid
        Returns:
            dict: execute result
        """
        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        # search_configs = get_search_configs()
        # model_para = {
        #     "temperature": float(search_configs.sailor_search_qa_llm_temperature),
        #     "top_p": float(search_configs.sailor_search_qa_llm_top_p),
        #     "presence_penalty": float(search_configs.sailor_search_qa_llm_presence_penalty),
        #     "frequency_penalty": float(search_configs.sailor_search_qa_llm_frequency_penalty),
        #     "max_tokens": int(search_configs.sailor_search_qa_llm_max_tokens)
        # }
        # model_para = {
        #     "temperature": 0.01,
        #     "top_p": 1,
        #     "presence_penalty": 0,
        #     "frequency_penalty": 0,
        #     "max_tokens": 2000
        # }
        url = urljoin(self.dip_gateway_url_private, self.llm_url_tail_dip_private)
        logger.info(f'llm url={url}')
        logger.info(f"model_name={self.llm_url.split('/')[-1]}")
        # logger.info(f"model_para={model_para}")
        logger.info(f"prompt_rendered_msg={prompt_rendered_msg}")
        if x_account_type:
            headers = {
                "x-account-id": x_account_id,
                "x-account-type": x_account_type
            }
        else:
            headers = {
                "x-account-id": x_account_id
            }
        api = API(
            url=url,
            headers=headers,
            payload={
                "model": self.llm_url.split('/')[-1],
                "top_k": 1,
                "temperature": 0.000001,
                "top_p": 1.0,
                "messages": prompt_rendered_msg,
                "max_tokens": input_max_tokens,
                "stream": False
            },
            method=HTTPMethod.POST,
            stream=False
        )
        try:
            res = await api.call_async()
            if res:
                if "code" in res:
                    raise LLMExecError(res.get("code"))
                res_content_str = res.get('choices')[0].get('message').get('content')
                return res_content_str
            else:
                return ""
        except Text2SQLError as e:
            raise LLMExecError(e) from e

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
        except Text2SQLError as e:
            raise LLMExecError(e)
        # except Exception as e:
        #     logger.error(f'------------------{e}')
            # raise LLMExecError(e) from e

    async def get_column_by_id(self, entity_id: str, headers: dict) -> dict:
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
            self.common_url).format(entity_id=entity_id)

        api = API(
            url=url,
            headers=headers,
        )
        # print(api)
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
        logger.info("--------get_view_column_by_id -----------")
        # print(api)
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_view_detail_by_id(self, view_id: str, headers: dict) -> dict:

        url = urljoin(
            self.data_view_url,
            self.view_detail_url).format(view_id=view_id)
        logger.info(f'...calling api {url}')
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
            logger.info(f"%%%%%%%%%%%%%%%%%%%%%%%% {res}")
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
            logger.info(f'...calling get_data_catalog_mount() api:{api}')
            res = await api.call_async()
            res = res.get("mount_resource", [{}])
            if len(res):
                logger.info(f'{api} mount_resource {res}')
                return ""
            else:
                return res.get("resource_id", "")
            # res = res.get("mount_resource", [{}])[0].get("resource_id", "")
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
            logger.info(f'...calling get_view_basic_info() api: {api}')
            res = await api.call_async()
            mount = await self.get_data_catalog_mount(entity_id, headers)
            logger.info(f'catalog{entity_id} mount resouce:{mount}')
            if mount != "":
                detail = await self.get_view_detail_by_id(mount, headers)
                res["form_view_id"] = mount
                res["owner_id"] = detail.get("owner_id")
                res["technical_name"] = detail.get("technical_name")
            else:
                res["form_view_id"] = ""
                res["owner_id"] = ""
                res["technical_name"] = ""
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
        url_auth_svc = urljoin(
            self.auth_service_url,
            self.user_auth)
        url_view = urljoin(
            self.data_view_url,
            self.sub_view_enforce_url)
        api_auth_svc = API(
            url=url_auth_svc,
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
            res_auth_svc = await api_auth_svc.call_async()
            logger.info(f'res_auth_svc["total_count"] = {res_auth_svc["total_count"]}')
            logger.info(f'res_view["total_count"] = {res_view["total_count"]}')
            if res_auth_svc["total_count"] > 0:
                service_id = [i["object_id"] for i in res_auth_svc["entries"]]
            else:
                service_id = []
            if res_view["total_count"] > 0:
                view_id = [i["id"] for i in res_view["entries"]]
            else:
                view_id = []
            auth_id = service_id + view_id
        except Exception as e:
            auth_id = []
            logger.error(str(e))
        return auth_id

    async def user_all_auth_dip(self, subject_id) -> list[Any]:
        """
        获取用户拥有的逻辑视图权限（使用新的DIP数据模型API）

        Args:
            headers: HTTP请求头
            subject_id: 用户ID

        Returns:
            list[Any]: 有权限的逻辑视图ID列表，例如 ['b855ce34-fabd-4a20-ad4c-6e44766c9322', ...]
        """
        # 使用新的数据模型API获取用户有权限的逻辑视图
        url_data_views = urljoin(
            self.dip_data_model_url_internal,
            self.user_data_views_url
        )

        headers = {
            "Content-Type": "application/json",
            "x-account-id": subject_id,
            "x-account-type": "user"
        }

        query_string = "type=atomic&limit=-1&operations=view_detail&operations=data_query"

        logger.info(f'调用新DIP API获取用户逻辑视图权限: url={url_data_views}, subject_id={subject_id}')

        try:
            api = API(
                url=url_data_views + '?' + query_string,
                headers=headers,
                method=HTTPMethod.GET
            )

            res = await api.call_async()
            logger.info(f'新DIP API返回结果 total_count = {res.get("total_count", 0)}')

            # 从返回结果中提取 data_source_id
            auth_id = []
            entries = res.get("entries", [])
            if entries:
                # 提取每个entry的data_source_id，并去重
                data_source_ids = [
                    entry.get("id")
                    for entry in entries
                    if entry.get("id")
                ]
                # 去重，保持原有顺序
                seen = set()
                auth_id = [
                    ds_id for ds_id in data_source_ids
                    if ds_id not in seen and not seen.add(ds_id)
                ]
                logger.info(f'解析得到 {len(auth_id)} 个唯一的逻辑视图ID')
            else:
                logger.info('新DIP API返回结果中没有entries或entries为空')
                auth_id = []

        except Exception as e:
            auth_id = []
            logger.error(f'调用新DIP API获取用户逻辑视图权限失败: {str(e)}')
            logger.exception(e)

        logger.info(f'最终返回 auth_mdl_id 数量: {len(auth_id)}')
        # 在ADP接口中， 返回的是ADP数据视图的‘统一视图id’：mdl_id, iDRM的form_view表中，会产生自己id（是uuid），
        # 新增了一个字段保存mdl_id和，目录版搜索图谱中数据资源目录节点有该mdl_id，命名为 resource_mdl_id
        return auth_id

    async def user_all_auth_dip_external(self, token,subject_id) -> list[Any]:
        """
        获取用户拥有的逻辑视图权限（使用新的DIP数据模型API）

        Args:
            headers: HTTP请求头
            subject_id: 用户ID

        Returns:
            list[Any]: 有权限的逻辑视图ID列表，例如 ['b855ce34-fabd-4a20-ad4c-6e44766c9322', ...]
        """
        # 使用新的数据模型API获取用户有权限的逻辑视图
        url_data_views = urljoin(
            self.dip_data_model_url_internal,
            self.user_data_views_url_external
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": token
        }

        query_string = "type=atomic&limit=-1&operations=view_detail&operations=data_query"

        logger.info(f'调用新DIP API获取用户逻辑视图权限: url={url_data_views}')

        try:
            api = API(
                url=url_data_views + '?' + query_string,
                headers=headers,
                method=HTTPMethod.GET
            )

            res = await api.call_async()
            logger.info(f'新DIP API返回结果 total_count = {res.get("total_count", 0)}')

            # 从返回结果中提取 data_source_id
            auth_id = []
            entries = res.get("entries", [])
            if entries:
                # 提取每个entry的data_source_id，并去重
                data_source_ids = [
                    entry.get("id")
                    for entry in entries
                    if entry.get("id")
                ]
                # 去重，保持原有顺序
                seen = set()
                auth_id = [
                    ds_id for ds_id in data_source_ids
                    if ds_id not in seen and not seen.add(ds_id)
                ]
                logger.info(f'解析得到 {len(auth_id)} 个唯一的逻辑视图ID')
            else:
                logger.info('新DIP API返回结果中没有entries或entries为空')
                auth_id = []

        except Exception as e:
            auth_id = []
            logger.error(f'调用新DIP API获取用户逻辑视图权限失败: {str(e)}')
            logger.exception(e)

        logger.info(f'最终返回 auth_mdl_id 数量: {len(auth_id)}')
        # 在ADP接口中， 返回的是ADP数据视图的‘统一视图id’：mdl_id, iDRM的form_view表中，会产生自己id（是uuid），
        # 新增了一个字段保存mdl_id和，目录版搜索图谱中数据资源目录节点有该mdl_id，命名为 resource_mdl_id
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
                logger.error('鉴权失败,鉴权报错原因-----------------', e)
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
        logger.debug(f"auth_id = {auth_id}")
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



