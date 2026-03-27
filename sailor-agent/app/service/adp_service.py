import json

import requests
import sseclient
from config import settings
from typing import Any, Optional, Tuple
from urllib.parse import urljoin
from app.logs.logger import logger



class ADPService(object):

    def __init__(self):
        self.host = "http://{}:{}".format(settings.ADP_HOST, settings.ADP_PORT)
        self.adp_agent_factory_host = settings.ADP_AGENT_FACTORY_HOST
        self.adp_ontology_manager_host = settings.ADP_ONTOLOGY_MANAGER_HOST
        self.adp_ontology_query_host = settings.ADP_ONTOLOGY_QUERY_HOST
        self.adp_model_api_host = settings.ADP_MODEL_API_HOST

        self.agent_key = "01K4PQ0X84MKYV5X1ZB9TW07K9"

        self.debug_url = "{}/api/agent-app/v1/app/{}/debug/completion".format(self.host, self.agent_key)
        self.chat_url = "{}/api/agent-app/v1/app/{}/chat/completion".format(self.host, self.agent_key)
        self.chat_url_inner = "{}/api/agent-app/internal/v1/app/{}/chat/completion".format(self.host, self.agent_key)
        self.conversation_list_url = "{}/api/agent-app/v1/app/{}/conversation".format(self.host, self.agent_key)
        self.conversation_get_id_url = "{}/api/agent-app/v1/app/{}/conversation".format(self.host, self.agent_key)
        self.agent_list_url = "{}/api/agent-factory/v3/published/agent".format(self.adp_agent_factory_host)
        self.dip_ontology_manager_url_internal = self.adp_ontology_manager_host+"/api/ontology-manager/in/v1/knowledge-networks/{kn_id}/object-types"
        self.ontology_query_by_object_types_external = "/api/ontology-query/v1/knowledge-networks/{kn_id}/object-types/{class_id}"
        self.agent_embedding_url = "{}/api/private/mf-model-api/v1/small-model/embeddings".format(self.adp_model_api_host)
    def stream_debug(self, query, token):
        headers = {
            "authorization": token
        }

        params = {"agent_id": self.agent_key,
                  "agent_version": "v0",
                  "input": {"query": query},
                  "conversation_id": "01KC3NRWD872C7PEJR6HEJWD0H", "stream": True, "inc_stream": True,
                  "executor_version": "v2"}

        request = requests.post(self.debug_url, json=params, stream=True, verify=False, headers=headers)

        client = sseclient.SSEClient(request)
        #
        for event in client.events():
            yield event.data

    async def stream_chat(self, query, conversation_id, agent_key, x_account_id, x_account_type):
        if x_account_id == "":
            x_account_id = settings.XAccountID
        if x_account_type == "":
            x_account_type = settings.XAccountType
        headers = {
            "x-account-id": x_account_id,
            "x-account-type": x_account_type
        }

        if agent_key == "":
            agent_key = self.agent_key

        params = {"agent_id": agent_key,
                  "agent_version": "v0",
                  "input": {"query": query},
                  "conversation_id": conversation_id, "stream": True, "inc_stream": True,
                  "executor_version": "v2"}
        request = requests.post(self.chat_url, json=params, stream=True, verify=False, headers=headers)

        # print(request.status_code)
        #
        client = sseclient.SSEClient(request)

        #
        for event in client.events():
            # print(type(event.data))
            yield f"data: {event.data}\n\n"

    async def stream_chat_v2(self, input_params, authorization):

        agent_key = input_params.get("agent_key", "")
        params = {
                "agent_id": input_params.get("agent_id", ""),
                "agent_version": input_params.get("agent_version", ""),
                "stream": input_params.get("stream", True),
                "inc_stream": input_params.get("inc_stream", True),
                "conversation_id": input_params.get("conversation_id", ""),
                "temporary_area_id": "",
               "temp_files": [],
               "query": input_params.get("query", ""),
               "custom_querys": {
              },
              "tool": {
              },
             "interrupted_assistant_message_id": "",
              "chat_mode": "normal",
              "confirm_plan": True,
              "regenerate_user_message_id": "",
              "regenerate_assistant_message_id": ""
}
        self.chat_url = "{}/api/agent-app/v1/app/{}/chat/completion".format(self.host, agent_key)
        headers = {
            "Authorization": authorization
        }
        print(self.chat_url)
        request = requests.post(self.chat_url, json=params, stream=True, verify=False, headers=headers)
        if request.status_code != 200:
            logger.info(json.dumps(request.json(), indent=4, ensure_ascii=False))
        client = sseclient.SSEClient(request)
        try:
            for event in client.events():
                print(event.data)
                yield f"data: {event.data}\n\n"
        except Exception as e:
            error_data = {"conversation_id": params.get("conversation_id", ""), "error": "af_agent 请求 adp_agent发生错误"}
            yield  f"data: {json.dumps(error_data)}\n\n"
    def conversation_list(self, token):
        params = {
            "page": 1,
            "size": 10
        }

        headers = {
            "authorization": token
        }
        try:
            resp = requests.get(self.conversation_list_url, params=params, verify=False, headers=headers)
        except Exception as e:
            return {"entries": []}

        final_resp = {
            "entries": resp["entries"]
        }
        return final_resp

    def conversation_get_id(self, token):

        params = {"agent_id": "01K4PQ0X84MKYV5X1ZB9TW07K9",
                  "agent_version": "v0",
                  "executor_version": "v2"}

        headers = {
            "authorization": token
        }
        try:
            resp = requests.post(self.conversation_get_id_url, json=params, verify=False, headers=headers)
        except Exception as e:
            return {"id": "",
                    "ttl": 600}

        final_resp = {
            "id": resp["id"]
        }
        return final_resp

    def agent_list(self, req, token):
        headers = {
            "x-business-domain": "bd_public",
            "Content-Type": "application/json",
            "Authorization": token
        }
        try:
            response = requests.post(self.agent_list_url, json=req, verify=False, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Agent list request failed with status code: {response.status_code}")
                return {"entries": [], "pagination_marker_str": "", "is_last_page": True}
        except Exception as e:
            logger.error(f"Agent list request failed: {str(e)}")
            return {"entries": [], "pagination_marker_str": "", "is_last_page": True}

    async def dip_ontology_query_by_object_types_external(
            self,
            token: str,
            kn_id: str,
            class_id: str,
            body: dict
    ) -> dict:
        logger.info(f'dip_ontology_query_by_object_types_external() running...')
        url = urljoin(self.adp_ontology_query_host, self.ontology_query_by_object_types_external.format(
            kn_id=kn_id,
            class_id=class_id
        ))
        logger.info(f'dip_ontology_query_by_object_types() url = {url}')

        logger.info(f"kn_id={kn_id}")
        logger.info(f'body = {body}')

        headers = {
            "Authorization": token,
            "x-http-method-override": "GET"
        }

        try:
            res = requests.post(url, json=body, headers=headers)
            if res:
                return res.json()
            else:
                return {}
        except Exception as e:
            logger.error(f"Agent list request failed: {str(e)}")
            return {}

    def get_adp_embedding(self, input_text_list):
        """
        调用 ADP 小模型服务获取文本 embedding 向量。

        返回形如 {"data": [...]} 的字典，供上层直接读取 "data" 字段。
        """
        try:
            resp = requests.post(
                self.agent_embedding_url,
                json={"model": "embedding", "input": input_text_list},
                verify=False,
            )
        except Exception as e:
            logger.error(f"请求 ADP embedding 服务异常: {e}")
            return {"object": "list", "data": []}

        try:
            resp_json = resp.json()
        except Exception as e:
            logger.error(f"解析 ADP embedding 响应为 JSON 失败: {e}")
            return {"object": "list", "data": []}

        data = resp_json.get("data") or []
        return {"data": data}