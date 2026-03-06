import asyncio
import json
import urllib3
import requests
from typing import List, Type
from urllib.parse import urlsplit
from app.utils.get_token import init_token
from app.cores.cognitive_assistant.qa_func import get_path
from pydantic import BaseModel, Field, create_model
from app.cores.cognitive_assistant.qa_model import (
    AFDataServiceInfoModel,
    AFDataServiceParameterModel
)
from app.cores.cognitive_assistant.qa_error import Text2SQLError
from app.cores.prompt.qa import TIMEOUT_ERROR
from app.logs.logger import logger
import aiohttp

urllib3.disable_warnings()


class AFServiceFunction:
    post_list: list = ["post", "POST"]

    def __init__(self, app_id, app_secret, url_path, url_type):
        self.url_path = url_path
        self.url_type = url_type
        self.app_id = app_id
        self.app_secret = app_secret

    async def __call__(self, **kwargs):
        token = init_token(
            url_type=self.url_type,
            url_path=urlsplit(self.url_path)[2],
            app_id=self.app_id,
            app_secret=self.app_secret,
            **kwargs
        )
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            if self.url_type in self.post_list:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                            url=self.url_path,
                            json=kwargs,
                            verify_ssl=False,
                            headers={"Authorization": token}
                    ) as resp:
                        if resp.status == 200:
                            res = await resp.text()
                        else:
                            res = ""
                            # print("#" * 100, resp.status, await resp.text())
                            # raise Text2SQLError(
                            #     url=self.url_path,
                            #     status=resp.status,
                            #     reason=resp.reason,
                            #     detail=await resp.json()
                            # )
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                            url=self.url_path,
                            params=kwargs,
                            headers={"Authorization": token},
                            verify_ssl=False
                    ) as resp:
                        if resp.status == 200:
                            res = await resp.text()
                        else:
                            res = ""
                            # raise Text2SQLError(
                            #     url=self.url_path,
                            #     status=resp.status,
                            #     reason=resp.reason,
                            #     detail= await resp.json()
                            # )
                            # print("#" * 100, resp.status, await resp.text())

        except asyncio.TimeoutError:
            res = TIMEOUT_ERROR
        logger.info("实际执行结果：{}".format(res))
        resp = {
            "res": res,
            "info": {
                "method": self.url_type,
                "url": self.url_path.replace("http://data-application-gateway:8157", "https://{IP}:"),
                "params": json.dumps(kwargs, ensure_ascii=False)
            }
        }

        return resp


async def exec_func_of_service(headers: dict, cites, **kwargs):
    title = [attr["title"] + attr["type"] for attr in cites]
    index = title.index(kwargs["interface_name"] + "interface_svc")
    serve = get_af_services(headers, cites[index])
    funcs = {}
    for info in serve:
        try:
            func = get_func_from_af_service(info, headers)
            funcs[info.name] = func
        except KeyError:
            continue
    exec_svc = funcs.get(kwargs["interface_name"])
    if not exec_svc:
        resp_svc = "没有找到接口"
    else:
        resp_svc = await exec_svc(**kwargs["params"])
    return resp_svc


def get_af_services(headers: dict, svc_info: dict) -> List[AFDataServiceInfoModel]:
    """获取af 的数据服务信息 """
    service = []
    code = svc_info["id"]
    url = get_path("service").format(code=code)
    res_info = api(url=url, headers=headers)
    svc_path = get_path("gateway").format(
        path=res_info['service_info']['service_path']
    )
    svc_params = [
        AFDataServiceParameterModel(
            name=param["en_name"],
            type=param["data_type"],
            default=param["default_value"],
            required=param["required"],
            operator=param["operator"],
            description=param["cn_name"]
        )
        for param in res_info["service_param"]["data_table_request_params"]
    ]
    service.append(
        AFDataServiceInfoModel(
            code=code,
            path=svc_path,
            name=svc_info["title"],
            type=res_info["service_info"]["http_method"],
            description=svc_info["description"],
            parameters=svc_params
        )
    )
    return service


def get_func_from_af_service(svc_info: AFDataServiceInfoModel, headers: dict) -> AFServiceFunction:
    """
    将一个AF数据服务接口转化成远程调用的函数
    """
    url = get_path("auth_info").format(code=svc_info.code)
    resp = api(url=url, headers=headers)
    app_id = resp["app_id"]  # app_id
    app_secret = resp["app_secret"]  # app_secret
    url_path = svc_info.path  # 路径
    url_type = svc_info.type  # 参数
    svc_func = AFServiceFunction(
        app_id=app_id,
        url_path=url_path,
        url_type=url_type,
        app_secret=app_secret
    )

    return svc_func


def create_args_schema(json_dict: dict) -> Type[BaseModel]:
    field_dict = {
        prop: (
            json_dict[prop]["type"],
            Field(
                default=json_dict[prop].get("default", None),
                description=json_dict[prop]["description"]
            )
        ) for prop in json_dict
    }
    dynamic_model = create_model(
        'AFInterfaceServiceParameterModel',
        **field_dict,
    )
    return dynamic_model


def api(method: str = "get", url: str = None, headers: dict = None):
    if method == "get":
        resp = requests.get(url=url, headers=headers, verify=False)
    else:
        resp = requests.post(url=url, headers=headers, verify=False)
    return resp.json()
