"""
@File: utils.py
@Date:2024-07-08
@Author : Danny.gao
@Desc:
"""

import json
from urllib.parse import urljoin

from config import settings
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.cores.text2sql.t2s_api import Services
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.logs.logger import logger
from jinja2 import Template

class LLMServices(Services):

    async def exec_prompt_by_llm(self, inputs: dict, appid: str, prompt_id: str, max_tokens: int = 4000) -> str:
        """
        AD部署的大模型执行AD管理的prompt
        :param max_tokens:
        :param inputs: prompt的参数dict
        :param appid: ad的appid
        :param prompt_id: ad管理的prompt id
        :return:
        """
        # 大模型参数
        self.llm_url = settings.TABLE_COMPLETION_LLM_NAME

        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        model_para = {
            'temperature': 0.01,
            'top_p': 1,
            'presence_penalty': 0,
            'frequency_penalty': 0,
            'max_tokens': max_tokens
        }
        url = urljoin(self.ad_gateway_url, self.llm_url_tail)

        payload = {
            'model_name': self.llm_url.split('/')[-1],
            'model_para': model_para,
            'prompt_id': prompt_id,
            'inputs': inputs,
            'history_dia': []
        }
        logger.info(f'大模型请求参数：{json.dumps(payload, ensure_ascii=False, indent=4)}')

        api = API(
            url=url,
            headers={
                'appid': appid
            },
            payload=payload,

            method=HTTPMethod.POST,
            stream=True
        )
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            logger.info(f'{e}')
            return f'报错：{e}'

    async def exec_prompt_by_llm_dip(self, inputs: dict, prompt: str, user_id: str, max_tokens: int = 4000) -> str:
        """
        AD部署的大模型执行AD管理的prompt
        :param max_tokens:
        :param inputs: prompt的参数dict
        :param appid: ad的appid
        :param prompt_id: ad管理的prompt id
        :return:
        """

        api = FindNumberAPI()
        x_account_id = user_id
        x_account_type = "user"
        tpl = Template(prompt)
        content = tpl.render(user_data=inputs["user_data"], field_ids=inputs["field_ids"])
        prompt_rendered_msg = [{
            "role": "user",
            "content": content
        }]
        res = await api.exec_prompt_by_llm_dip_understand(prompt_rendered_msg, x_account_id, x_account_type)

        # 大模型参数
        # self.llm_url = settings.TABLE_COMPLETION_LLM_NAME

        # "https://10.4.109.199:8444/api/model-factory/v1/prompt-run-stream"
        # model_para = {
        #     'temperature': 0.01,
        #     'top_p': 1,
        #     'presence_penalty': 0,
        #     'frequency_penalty': 0,
        #     'max_tokens': max_tokens
        # }
        # url = urljoin(self.ad_gateway_url, self.llm_url_tail)

        # payload = {
        #     'model_name': self.llm_url.split('/')[-1],
        #     'model_para': model_para,
        #     'prompt_id': prompt_id,
        #     'inputs': inputs,
        #     'history_dia': []
        # }
        # logger.info(f'大模型请求参数：{json.dumps(payload, ensure_ascii=False, indent=4)}')

        # api = API(
        #     url=url,
        #     headers={
        #         'appid': appid
        #     },
        #     payload=payload,
        #
        #     method=HTTPMethod.POST,
        #     stream=True
        # )
        # try:
        #     res = await api.call_async()
        #     return res
        # except Exception as e:
        #     logger.info(f'{e}')
        #     return f'报错：{e}'
        return res

class AnyFabricServices(Services):
    async def get_view_sample_by_source(self, catalog: dict, headers: dict) -> dict:
        """

        :param catalog:
        :param headers:
        :return:
        """
        # self.vir_engine_preview_url = 'https://10.4.109.234/api/virtual_engine_service/v1/preview/{source}/{schema}/{table}'
        url = self.vir_engine_preview_url.format(
            catalog=catalog['source'],
            schema=catalog['schema'],
            table=catalog['technical_name'],
        )
        headers['X-Presto-User'] = 'admin'
        api = API(
            url=url,
            headers=headers,
            params={
                'limit': 1,
                'type': 0
            }
        )
        logger.info(f'样例数据请求地址&参数：{url} || {headers}')
        try:
            res = await api.call_async()
            return res
        except Exception as e:
            logger.info(f'{e}')

# # vdm_maria_nmw7gwid.default
# # http://virtualization-engine-api-gateway:8099
# # headers = {"Authorization": request.headers.get('Authorization')}
# url = 'https://10.4.109.234/api/virtual_engine_service/v1/preview/vdm_maria_et0hnz6q/default/t_sales'
# headers = {'Authorization': 'Bearer ory_at_ppFwOfH7UIX6zEpBJpPeOzFdIYbXjIkPpghXgsMWAp8.bZqSVQLtW2tPZxqxNCdiC2KVBraKRt0wikQn4-IHcbE'}
# headers['X-Presto-User'] = 'admin'
# api = API(
#             url=url,
#             headers=headers,
#             params={
#                 'limit': 1,
#                 'type': 0
#             }
#         )
# import asyncio
# res = asyncio.run(api.call_async())
# print(res)
#
#
# datas = res.get('data', [])
# columns = res.get('columns', [])
# if datas:
#     data = datas[0]
#     for value, col in zip(data, columns):
#         print(col['name'], value)
