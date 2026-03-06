import json
import re
from typing import Any
from urllib.parse import urljoin

import jieba

from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.cores.text2sql.t2s_error import *
from app.models.code_table_model import CodeTableDetailModel
from app.models.rule_model import RuleDetailModel
from app.models.standard_model import StandardDetailModel
from app.models.table_model import ViewTableDetailModel
from app.logs.logger import logger
from config import settings


class Services(object):
    # ad_gateway_url: str = settings.AD_GATEWAY_URL
    ad_gateway_url: str = settings.DIP_GATEWAY_URL
    if settings.IF_DEBUG:
        catalog_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8153/api/data-catalog/frontend/v1/data-catalog'
        # vir_engine_url = "http://virtualization-engine-api-gateway:8099/api/virtual_engine_service/v1/fetch"
        config_url = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8133/api/configuration-center/v1/datasource'
        vir_engine_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8099'
        data_view_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8123'
        standard_info_url: str = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:80'
    else:
        catalog_url: str = "http://data-catalog:8153/api/data-catalog/frontend/v1/data-catalog"
        # vir_engine_url = "http://virtualization-engine-api-gateway:8099/api/virtual_engine_service/v1/fetch"
        config_url = "http://configuration-center:8133/api/configuration-center/v1/datasource"
        vir_engine_url: str = "http://af-vega-gateway:8099"
        data_view_url: str = "http://data-view:8123"
        standard_info_url: str = "http://standardization:80"



    def __init__(self):
        self._gen_api_url()

    def _gen_api_url(self):

        self.llm_url = settings.LLM_NAME
        self.model_name = self.llm_url.split('/')[-1]
        self.search_url = self.catalog_url + "/search/cog"
        self.common_url = self.catalog_url + "/{entity_id}/"
        self.column_url = self.catalog_url + "/{entity_id}/column"
        self.sample_url = self.catalog_url + "/{entity_id}/samples"
        # 执行sql的接口
        self.vir_engine_fetch_url = self.vir_engine_url + "/api/virtual_engine_service/v1/fetch"
        # 以下为样例数据查询接口
        self.vir_engine_preview_url = self.vir_engine_url + "/api/virtual_engine_service/v1/preview/{catalog}/{schema}/{table}"
        self.view_fields_url = self.data_view_url + "/api/data-view/v1/form-view/{view_id}"
        self.view_info_url = self.view_fields_url + "/details"
        self.get_user_view_url = self.data_view_url + "/api/data-view/v1/user/form-view"
        self.explore_report_url = self.data_view_url + "/api/data-view/v1/form-view/explore-report"
        self.llm_url_tail = "api/model-factory/v1/prompt-template-run"
        self.get_standard_detail_url = self.standard_info_url + "/api/standardization/v1/dataelement/internal/detail/?type={type}&value={standard_code}"
        self.get_code_table_detail_url = self.standard_info_url + "/api/standardization/v1/dataelement/dict/internal/getId/{code_table_id}"
        self.get_rule_detail_url = self.standard_info_url + "/api/standardization/v1/rule/internal/getId/{rule_id}"

    async def exec_vir_engine_by_sql(self, user: str, user_id: str, sql: str) -> Any | None:
        """Execute virtual engine by SQL query

        Args:
            user (str): username
            sql (str): SQL
            user_id (str): user id
        Returns:
            dict: VIR engine
        """
        # https://10.4.109.234/api/virtual_engine_service/v1/fetch
        url = self.vir_engine_fetch_url
        api = API(
            url=url,
            headers={
                "X-Presto-User": user,
                'Content-Type': 'text/plain'
            },
            method=HTTPMethod.POST,
            data=sql.encode('utf-8'),
            params={"user_id": user_id}
        )

        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            logger.info(f'vir_engine_by_sql(), 异常信息：{e}')

            raise VirEngineError(e) from e

    async def get_assets_by_search(self, query: str, headers: dict, top_k: int = 2) -> dict:
        """Get result of cognitive search by query

        Args:
            query (str): query
            headers (str): AF token
            top_k (int, optional): number of results to return. Defaults to 2
        returns:
            dict: result of cognitive search
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/data-catalog/search/cog
        url = self.search_url  # cognitive search don't use
        api = API(
            url=url,
            headers=headers,
            payload={
                "keyword": query,
                "asset_type": "data_catalog",
                "size": top_k
            },
            method=HTTPMethod.POST,
        )

        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            logger.info(f'get_assets_by_search(), 异常信息：{e}')
            raise CognitiveSearchError(e) from e

    async def get_column_by_id(self, entity_id: str, headers: dict) -> dict:
        """Get data catalog column by id

        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: data catalog column
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/data-catalog/502494820913184002/column
        url = self.column_url.format(entity_id=entity_id)
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

    async def get_view_sample_by_source(self, source: dict, headers: dict, types=0) -> dict:
        url = self.vir_engine_preview_url.format(
            catalog=source["source"],
            schema=source["schema"],
            table=source["title"] if types == 0 else source["technical_name"],
        )
        headers["X-Presto-User"] = "admin"
        api = API(
            url=url,
            headers=headers,
            params={
                "limit": 1,
                "type": 0
            }
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_view_column_by_id(self, view_id, headers: dict) -> dict:
        url = self.view_fields_url.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise FrontendColumnError(e) from e

    async def get_view_info_by_id(self, view_id: str, headers: dict) -> ViewTableDetailModel:
        url = self.view_info_url.format(view_id=view_id)
        api = API(
            url=url,
            headers=headers,
        )
        try:
            res = await api.call_async()
            try:
                res = ViewTableDetailModel.model_validate(res)
            except ValidationError as e:
                e.url = url
                e.reason = "视图校验不合法"
                e.json = {
                    "code": T2SErrno.VALIDATION_ERROR,
                    "status": 500,
                    "reason": e.reason,
                    "url": e.url,
                    "detail": "\n".join([an_error["msg"] for an_error in e.errors()])
                }
                raise e
            return res
        except Text2SQLError as e:
            e.reason = f"寻找id为：\n{view_id}\n的逻辑视图失败。"
            e.url = url
            raise DataViewError(e) from e

    async def get_standard_detail_by_code(self, standard_code: str, headers: dict) -> StandardDetailModel:
        # logger.info("#####################################")
        # logger.info(standard_code)
        url = self.get_standard_detail_url.format(type=2, standard_code=standard_code)
        # url = f"https://10.4.109.233/api/standardization/v1/dataelement/detail/?type=2&value={standard_code}"
        
        api = API(url=url, headers=headers)
        try:
            res = await api.call_async()
            try:
                res = StandardDetailModel.model_validate(res["data"])
            except ValidationError as e:
                e.url = url
                e.reason = "数据标准校验不合法"
                e.json = {
                    "code": T2SErrno.VALIDATION_ERROR,
                    "status": 500,
                    "reason": e.reason,
                    "url": e.url,
                    "detail": "\n".join([an_error["msg"] for an_error in e.errors()])
                }
                raise e
            return res
        except Text2SQLError as e:
            e.reason = f"寻找id为：\n{standard_code}\n的数据标准失败。"
            e.url = url
            raise DataStandardError(e) from e

    async def get_code_table_detail_by_id(self, code_table_id: str, headers: dict) -> CodeTableDetailModel:
        url = self.get_code_table_detail_url.format(code_table_id=code_table_id)
        # url = f"https://10.4.109.233/api/standardization/v1/dataelement/dict/{code_table_id}"
        api = API(url=url, headers=headers)
        try:
            res = await api.call_async()
            try:
                res = CodeTableDetailModel.model_validate(res["data"])
            except ValidationError as e:
                e.url = url
                e.reason = "码表校验不合法"
                e.json = {
                    "code": T2SErrno.VALIDATION_ERROR,
                    "status": 500,
                    "reason": e.reason,
                    "url": e.url,
                    "detail": "\n".join([an_error["msg"] for an_error in e.errors()])
                }
                raise e
            return res
        except Text2SQLError as e:
            e.reason = f"寻找id为：\n{code_table_id}\n的码表失败。"
            e.url = url
            raise CodeTableError(e) from e

    async def get_rule_detail_by_id(self, rule_id: str, headers: dict) -> RuleDetailModel:
        url = self.get_rule_detail_url.format(rule_id=rule_id)
        # url = f"https://10.4.109.233/api/standardization/v1/rule/{rule_id}"
        api = API(url=url, headers=headers)
        try:
            res = await api.call_async()
            try:
                res = RuleDetailModel.model_validate(res["data"])
            except ValidationError as e:
                e.json = {
                    "code": T2SErrno.VALIDATION_ERROR,
                    "status": 500,
                    "reason": "编码规则校验不合法",
                    "url": url,
                    "detail": "\n".join([an_error["msg"] for an_error in e.errors()])
                }
                raise e
            return res
        except Text2SQLError as e:
            e.reason = f"寻找id为：\n{rule_id}\n的编码规则失败。"
            e.url = url
            raise RuleError(e) from e

    async def get_common_by_id(self, entity_id: str, headers: dict) -> dict:
        """Get data catalog information by id
        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: data catalog information
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/data-catalog/502494820913184002/common
        url = self.common_url.format(entity_id=entity_id)
        api = API(
            url=url,
            headers=headers
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise CognitiveSearchError(e) from e

    async def get_samples_by_id(self, entity_id: str, headers: dict) -> dict:
        """Get samples information by entity ID

        Args:
            entity_id (str): entity ID
            headers (dict): AF token
        Returns:
            dict: data catalog information
        """
        # https://10.4.109.234/api/data-catalog/frontend/v1/data-catalog/503029276795272450/samples
        url = self.sample_url.format(entity_id=entity_id)
        api = API(
            url=url,
            headers=headers
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise CognitiveSearchError(e) from e

    async def get_data_source_by_keyword(self, keyword: str, headers: dict) -> dict:
        """Get data source information by id

        Args:
            keyword (str): search keyword
            headers (dict): AF token
        Returns:
            dict: data source information
        """
        # https://10.4.109.234/api/configuration-center/v1/datasource
        url = self.config_url
        api = API(
            url=url,
            headers=headers,
            params={
                "keyword": keyword,
                "limit": 1
            }
        )

        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise ConfigCenterError(e) from e

    async def exec_prompt_by_llm(self, inputs: dict, appid: str, prompt_id: str,
                                 max_tokens: int = 20000) -> str:
        """Execute prompt by llm
        Args:
            inputs (dict): input data
            prompt_id (str): prompt_id
            appid (str): AD appid
            max_tokens: max tokens
        Returns:
            dict: execute result
        """
        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        model_para = {
            "temperature": 0.01,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "max_tokens": int(max_tokens)
        }
        # logger.info("#####################################")
        # logger.info(inputs.get("schema"))
        # logger.info(inputs.get("column_detail_info"))
        url = urljoin(self.ad_gateway_url, self.llm_url_tail)
        payload = {
            "model_name": self.llm_url.split('/')[-1],
            "model_para": model_para,
            "prompt_id": prompt_id,
            "inputs": inputs,
            "history_dia": []
        }
        logger.info(json.dumps(payload, ensure_ascii=False, indent=4))
        api = API(
            url=url,
            headers={"appid": appid},
            payload=payload,
            method=HTTPMethod.POST,
            stream=True,
        )
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            # logger.info('#' * 50, e)
            logger.info((f"{'#' * 50}\texecute prompt by llm error: {e}"))

    async def get_bi_explore_report(self, entity_id: str, headers: dict) -> dict:
        url = self.explore_report_url
        api = API(
            url=url,
            headers=headers,
            params={
                "id": entity_id
            }
        )
        try:
            res = await api.call_async()
            return res
        except Text2SQLError as e:
            raise DataViewError(e) from e

    async def participle(
        self,
        text,
        appid
    ) -> list | dict:
        _, prompt_id = await PromptServices().from_anydata(appid, "participle")
        inputs = {"text": text}
        words = await self.func(inputs, appid, prompt_id)
        chunk = jieba.lcut(text)

        return words + chunk

    async def check_consistency(
        self,
        sql: str,
        text: str,
        five_row_json: dict,
        five_row_markdown: str,
        appid: str,
    ) -> list | dict:
        params = {
            "question": text,
            "sql": sql,
            "result": json.dumps(five_row_json, ensure_ascii=False, indent=2)
        }
        service = PromptServices()
        _, prompt_id = await service.from_anydata(
            appid,
            name="consistency_check_first"
        )
        first_res = await self.func(
            params,
            appid,
            prompt_id
        )
        if first_res.get("res") == "no":
            params = {
                "question": text,
                "result": five_row_markdown
            }
            _, prompt_id = await service.from_anydata(
                appid,
                name="consistency_check_second"
            )
            second_res = await self.func(
                params,
                appid,
                prompt_id
            )
            return second_res
        else:
            return first_res

    async def func(
        self,
        inputs: dict,
        appid: str,
        prompt_id: str
    ) -> list | dict:
        res = await self.exec_prompt_by_llm(inputs, appid, prompt_id)
        logger.info(f"一致性校验的结果: {res}")
        json_pattern = r'\{[^}]*\}|\[[^\]]*\]'
        matches = re.findall(json_pattern, res)

        for json_part in matches:
            res = json.loads(json_part)
            return res
        return []



