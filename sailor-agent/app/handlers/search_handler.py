# -*- coding:utf-8 -*-
import sys

from fastapi import APIRouter, Request, Body, Path
from fastapi.responses import JSONResponse

from app.cores.prompt.manage.api_base import API
from app.routers.agent_temp_router import *
from app.service.use_service import GetServiceResult
from config import settings

# sys.path.append("/mnt/pan/zkn/code_agent/feature_633396")

search_api = APIRouter()


@search_api.get(
    SearchInfoRouter,
    summary="获取搜索配置信息",
    description="获取ADB智能体密钥和业务域ID等搜索配置信息",
    responses={
        200: {
            "description": "成功获取搜索配置信息",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "res": {
                                "type": "object",
                                "properties": {
                                    "adp_agent_key": {
                                        "type": "string",
                                        "description": "ADB智能体密钥"
                                    },
                                    "adp_business_domain_id": {
                                        "type": "string",
                                        "description": "ADB业务域ID"
                                    }
                                }
                            }
                        },
                        "example": {
                            "res": {
                                "adp_agent_key": "example_agent_key",
                                "adp_business_domain_id": "example_domain_id"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权访问",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "example": "Unauthorized"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def search_info(request: Request):
    """获取搜索配置信息

    该接口用于获取ADB智能体密钥和业务域ID等搜索配置信息。

    Args:
        request: HTTP请求对象

    Returns:
        JSONResponse: 包含ADB智能体密钥和业务域ID的响应
    """
    if not verify_token(request):  # 验证token
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    _config = GetServiceResult()
    _agent_key = await _config.search_dip_agent_key()
    adp_agent_key = settings.ADP_AGENT_KEY
    if _agent_key:
        adp_agent_key = _agent_key


    return JSONResponse({"res": {
        "adp_agent_key": adp_agent_key,
        "adp_business_domain_id": settings.ADP_BUSINESS_DOMAIN_ID
    }}, status_code=200)

def verify_token(request: Request = None):
    token: str = request.headers.get("Authorization").split(" ")[1]
    api = API(
        data={"token": token},
        method="POST",
        url="{}/admin/oauth2/introspect".format(settings.HYDRA_URL),
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    res = api.call()
    return res.get("active", False)


if __name__ == "__main__":
    pass
    # verify_token()
    # param = {
    #     "id": "a67c0673-9080-4213-b3d7-4ab606678146",
    #     "stream": True,
    #     "session_id": "",
    #     "config": {
    #         "data_indicators": [],
    #         "data_views": [],
    #         "configs": {"task_desc": "", "knowledge": ["", "", "", "", ""], "remark": "",
    #                     "preset_question": []},
    #         "tools": [{"id": "1", "tool_desc": "", "tool_config": ""},
    #                   {"id": "2", "tool_desc": "", "tool_config": ""},
    #                   {"id": "3", "tool_desc": "", "tool_config": ""}],
    #         "work_mode": [{"id": "2", "mode_desc": "", "mode_config": ""}]
    #     },
    #     "que": "你好",
    #     "chat_history": ["你好"],
    #     "is_debug": True,
    #     "user_name": "liberly",
    #     "user_id": "e3e51a0a-0f30-11ef-a09c-62fb8b52b81d"
    # }
    # # async def main(param):
    # #     print(await dpqa_chat(param))
    #
    # import  asyncio
    # asyncio.run(main(param))
