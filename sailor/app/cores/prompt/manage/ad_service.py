import base64
import json
import os
from typing import Any
from urllib.parse import urljoin

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from app.cores.prompt.manage.payload_prompt import *
from app.cores.text2sql.t2s_base import API, HTTPMethod
from app.logs.logger import logger
from config import settings


class PromptServices(object):
    ad_gateway_url: str = settings.DIP_GATEWAY_URL

    def __init__(self):
        self._gen_api_url()
        self._file_name()
        self.payload = payload
        self.path = os.path.abspath(
            os.path.join(os.path.abspath(__file__), os.pardir, "prompt2id.json")
        )

    def _gen_api_url(self):
        self.get_appid_url = "/api/rbac/v1/user/login/appId"
        self.get_prompt_url = "/api/model-factory/v1/prompt/{prompt_id}"
        self.save_prompt_url = "/api/model-factory/v1/prompt/batch_add"
        self.ad_graph_search = "/api/engine/v1/custom-search/kgs/{kg_id}"
        self.get_prompt_item_url = "/api/model-factory/v1/prompt-item-source"
        self.get_prompt_id_url = "/api/model-factory/v1/prompt-source"
        self.get_model_max_tokens_length_url = "/api/model-factory/v1/llm-config"
        self.tokenize_and_count_url = "/api/model-factory/v1/encode"
        self.get_model_list_url = "/api/model-factory/v1/llm-source"
        self.tokenize_and_count_v2_url = "/api/model-factory/v2/encode"

    def _file_name(self):
        af_ip = settings.AF_IP
        self.file_name = "af_sailor"
        if af_ip != "":
            self.file_name += "_" + af_ip

    @staticmethod
    def encrypt():
        password = f"{settings.AD_GATEWAY_PASSWORD}"
        pub_key = RSA.importKey(base64.b64decode(pub_key_ad))
        rsa = PKCS1_v1_5.new(pub_key)
        password = rsa.encrypt(password.encode("utf-8"))
        password_base64 = base64.b64encode(password).decode()
        return password_base64

    def get_appid(self):
        try:
            url = urljoin(self.ad_gateway_url, self.get_appid_url)
            api = API(
                url=url,
                payload={
                    "username": settings.AD_GATEWAY_USER,
                    "password": self.encrypt(),
                    "isRefresh": 0,
                },
                method="POST"
            )
            res = api.call()
            return res["res"]
        except Exception as e:
            logger.info(f'获取appid异常，异常信息：{e}')
            logger.info(f"获取appid错误, 账号：{settings.AD_GATEWAY_USER}， 密码：{settings.AD_GATEWAY_PASSWORD}")

    async def get_prompt(self, appid: str, prompt_id: str):
        try:
            url = urljoin(self.ad_gateway_url, self.get_prompt_url.format(prompt_id=prompt_id))
            api = API(
                url=url,
                headers={"appid": appid},
            )
            res = await api.call_async()
            prompt = res["res"]["messages"]
            return prompt
        except Exception as e:
            logger.info(f'获取prompt异常，异常信息：{e}')
            return None

    def save_prompt_to_anydata(self, payloads=None):
        url = urljoin(self.ad_gateway_url, self.save_prompt_url)
        if payloads is None:
            payloads = self.payload
        for items in payloads:
            items["prompt_item_type_name"] = self.file_name
        api = API(
            url=url,
            payload=payloads,
            headers={"appid": self.get_appid()},
            method="POST"
        )
        res = api.call()
        map_prompt = {
            key: str(value)
            for key, value in res["res"][0]["prompt_list"].items()
        }
        map_prompt["file_name"] = self.file_name

        with open(self.path, 'w') as json_file:
            json.dump(map_prompt, json_file, indent=4, ensure_ascii=False)
        logger.info(msg=f"prompt成功写入：{self.ad_gateway_url}: AnyFabric, {self.file_name}")
        return map_prompt, self.ad_gateway_url

    @staticmethod
    def from_local(name):
        """get the prompt from local file

        :param name: prompt name
        :return: the prompt content
        """

        logger.info("get anydata prompt error: used local prompt")
        return prompt_map[name]

    async def from_anydata(self, appid: str, name: str) -> tuple:
        """get the prompt that has already been saved on anydata

        :param appid: anydata appid
        :param name: prompt name
        :return: the prompt content
        """
        try:
            logger.info(f"获取prompt的路径：{self.path}")
            with open(self.path, 'r') as file:
                data = json.load(file)
            prompt_id = data.get(name, None)
            logger.info(f"当前prompt 分组名字：{self.file_name}")
            assert prompt_id is not None, f"get {name} prompt error: {os.path.abspath(__file__)}"
            prompt = await self.get_prompt(prompt_id=prompt_id, appid=appid)
            logger.info(f"prompt = {prompt}")
            return prompt, prompt_id
        except Exception as e:
            logger.error(e)
            return None,None

    async def get_prompt_id(self, name: str) -> str:
        with open(self.path, 'r') as file:
            data = json.load(file)
        prompt_id = data.get(name, None)
        assert prompt_id is not None, f"get {name} prompt error: {os.path.abspath(__file__)}"

        return prompt_id

    def get_all_prompt_item(self) -> tuple:
        url = urljoin(self.ad_gateway_url, self.get_prompt_item_url)
        api = API(
            url=url,
            headers={"appid": self.get_appid()},
            params={
                "is_management": "true",
                "size": 10000,
            }
        )
        res = api.call()
        msg = [name["prompt_item_types"] for name in res["res"]["data"] if name.get("prompt_item_name") == "AnyFabric"]
        name = []
        for x in msg:
            for y in x:
                name.append(y["name"])

        if self.file_name in name:
            return name, False

        return name, True

    def get_prompt_item_type_id(self) -> tuple|None:
        """
        Gets the prompt word item and group id
        """
        url = urljoin(self.ad_gateway_url, self.get_prompt_item_url)
        api = API(
            url=url,
            headers={"appid": self.get_appid()},
            params={
                "size": 10000,
                "is_management": "true",
                "prompt_item_name": "AnyFabric",
            }
        )
        res = api.call()["res"]["data"]
        for item in res:
            if item["prompt_item_name"] == "AnyFabric":
                res = item
                break
        prompt_item_id = res["prompt_item_id"]
        for items in res["prompt_item_types"]:
            if items["name"] == self.file_name:
                prompt_item_type_id = items["id"]
                return prompt_item_id, prompt_item_type_id

    def update_prompt(self) -> None:
        try:
            item_type_id = self.get_prompt_item_type_id()
            url = urljoin(self.ad_gateway_url, self.get_prompt_id_url)
            api = API(
                url=url,
                headers={"appid": self.get_appid()},
                params={
                    "prompt_item_id": item_type_id[0],
                    "prompt_item_type_id": item_type_id[1],
                    "is_management": "true",
                    "rule": "create_time",
                    "order": "desc",
                    "deploy": "all",
                    "prompt_type": "all",
                    "size": 10000,
                    "page": 1,
                }
            )
            prompt2id = {}
            res = api.call()["res"]["data"]
            for msg in res:
                prompt2id[msg["prompt_name"]] = msg["prompt_id"]
            prompt2id["file_name"] = self.file_name

            updated_prompt = []  # 相较于上个版本新增的提示词
            for key in prompt_map.keys():
                if key not in prompt2id.keys():
                    updated_prompt.append(key)

            if updated_prompt:
                payloads = self.payload
                prompt_list = []
                for prompt in payloads[0]["prompt_list"]:
                    if prompt["prompt_name"] in updated_prompt:
                        prompt_list.append(prompt)
                payloads[0]["prompt_list"] = prompt_list
                res = self.save_prompt_to_anydata(payloads)
                for key, value in res[0].items():
                    prompt2id[key] = value

            with open(self.path, 'w') as json_file:
                json.dump(prompt2id, json_file, indent=4, ensure_ascii=False)

            logger.info(f"prompt id has been updated: {self.ad_gateway_url}")
            logger.info(json.dumps(
                prompt2id,
                indent=4,
                ensure_ascii=False)
            )

        except Exception as e:
            logger.info(f"提示词 id 更新错误，异常信息：{e}")

    async def custom_search_graph_call(
            self,
            kg_id: str,
            appid: dict,
            params: str,
            timeout: int = 600
    ) -> dict|None:
        """_summary_
        Args:
            kg_id (str): kg id
            appid (dict): appid
            params (str): params
            timeout (int, optional): 请求超时时间

        Raises:
            CogEngineError: CogEngineError

        Returns:
            dict: return result in dict
        """
        url = urljoin(
            self.ad_gateway_url,
            self.ad_graph_search.format(kg_id=kg_id)
        )
        params_l = {'kg_id': str(kg_id), "statements": [params]}
        # get result from builder
        api = API(
            url=url,
            method=HTTPMethod.POST,
            headers={
                "appid": appid,
            },
            payload=params_l
        )
        try:
            res = api.call(timeout=timeout)
            return res
        except Exception as e:
            logger.error(f'AF-AD-SDK 认知引擎自定义图语言查询接口错误！错误信息 = {e}')
            # return {}

    async def tokens_count(self, input_text: str, model_name: str, appid: str):
        url = urljoin(
            self.ad_gateway_url,
            self.tokenize_and_count_url
        )
        params_l = {'text': input_text, "model_name": model_name}
        api = API(
            url=url,
            method=HTTPMethod.POST,
            headers={
                "appid": appid,
            },
            payload=params_l
        )
        try:
            res = await api.call_async()
            return res["res"]["count"]
        except Exception as e:
            logger.info(f'AF-AD-SDK 认知引擎自定义图语言查询接口错误！异常信息：{e}')
            # return None

    async def get_model_max_tokens_length(self, model_name: str, appid: str) -> int|None:
        url = urljoin(
            self.ad_gateway_url,
            self.get_model_max_tokens_length_url.format(model_name=model_name)
        )
        params_l = {"model_name": model_name}
        api = API(
            url=url,
            headers={
                "appid": appid,
            },
            params=params_l
        )
        try:
            res = await api.call_async()
            return res["res"]["max_tokens_length"]
        except Exception as e:
            logger.info(f'AD大模型窗口大小查询接口错误！异常信息：{e}')
            # return None
            # retrun -1

    async def get_model_list(self, model_name: str, appid: str) -> list:
        url = urljoin(
            self.ad_gateway_url,
            self.get_model_list_url
        )
        params_l = {"page": 1, "size": 2, "name": model_name}
        api = API(
            url=url,
            headers={
                "appid": appid,
            },
            params=params_l
        )
        try:
            res = await api.call_async()
            logger.info(f'get_model_list(), res = \n{res}')
            return res["res"]["data"]
        except Exception as e:
            logger.info(f'AD大模型窗口大小查询接口错误！异常信息：{e}')
            return []

